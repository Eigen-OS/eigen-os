"""gRPC service implementations for System API (MVP skeleton)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from datetime import timedelta
from hashlib import sha256
from io import BytesIO

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
import pyarrow as pa
import pyarrow.parquet as pq

from .errors import abort_invalid_argument
from .observability import log_request_end, log_request_start, new_request_context
from .qfs_store import QFS_STORE
from .security import enforce_authn, enforce_authz
from .validation import (
    validate_device_id,
    validate_job_id,
    validate_reserve_device,
    validate_submit_job,
)

TERMINAL_JOB_STATES = {
    "JOB_STATE_DONE",
    "JOB_STATE_ERROR",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_TIMEOUT",
}


def _ts_now() -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.now(timezone.utc))
    return ts


def _serialize_results_parquet(
    *,
    job_id: str,
    counts: dict[str, int],
    metadata: dict[str, str],
) -> bytes:
    """Serialize deterministic result rows into Apache Parquet bytes."""
    ordered_counts = sorted(counts.items(), key=lambda kv: kv[0])
    ordered_metadata = json.dumps(
        {k: metadata[k] for k in sorted(metadata)},
        sort_keys=True,
        separators=(",", ":"),
    )
    table = pa.table(
        {
            "job_id": [job_id for _ in ordered_counts],
            "bitstring": [k for k, _ in ordered_counts],
            "count": [int(v) for _, v in ordered_counts],
            "metadata_json": [ordered_metadata for _ in ordered_counts],
        }
    )
    out = BytesIO()
    pq.write_table(table, out, compression="zstd")
    return out.getvalue()


@dataclass
class _JobRecord:
    job_id: str
    created_at: Timestamp
    created_at_dt: datetime
    updates: list
    counts: dict[str, int]
    results_metadata: dict[str, str]
    results_parquet: bytes | None
    completed_at: Timestamp | None
    error_code: str
    error_summary: str
    error_details_ref: str
    should_fail: bool
    run_duration_sec: float
    timeout_at: datetime | None
    timeout_reason: str
    cancel_requested: bool
    finalized: bool
    temp_refs: list[str]
    trace_id: str | None
    max_iters: int
    dispatch_rationale: dict[str, object]
    batch_manifest_ref: str
    batch_id: str
    queue_delay_sec: float


@dataclass
class _IdempotencyRecord:
    job_id: str
    request_fingerprint: str


class JobService:
    """Implementation of eigen.api.v1.JobService."""

    def __init__(self, job_pb, types_pb):
        self._job_pb = job_pb
        self._types_pb = types_pb
        self._jobs: dict[str, _JobRecord] = {}
        self._idempotency: dict[str, _IdempotencyRecord] = {}
        self._lock = threading.RLock()
        self._batch_mode_enabled = os.getenv("EIGEN_BATCH_MODE", "1").strip() not in {"0", "false", "off"}
        self._batch_size = max(int(os.getenv("EIGEN_BATCH_SIZE", "4")), 2)
        self._batch_wait_window_sec = max(float(os.getenv("EIGEN_BATCH_WAIT_WINDOW_SEC", "0.2")), 0.0)
        self._batch_dispatch_gap_sec = max(float(os.getenv("EIGEN_BATCH_DISPATCH_GAP_SEC", "0.15")), 0.0)
        self._batch_inflight_limit = max(int(os.getenv("EIGEN_BATCH_INFLIGHT_LIMIT", "64")), self._batch_size)
        self._dispatch_slot_seq = 0

    def _request_fingerprint(self, request) -> str:
        payload = {
            "name": request.name,
            "target": request.target,
            "priority": int(request.priority),
            "compiler_options": sorted(request.compiler_options.items()),
            "dependencies": list(request.dependencies),
            "metadata": sorted(request.metadata.items()),
            "program": request.WhichOneof("program") or "",
        }
        program = request.WhichOneof("program")
        if program == "eigen_lang":
            payload["eigen_lang"] = {
                "entrypoint": request.eigen_lang.entrypoint,
                "sha256": request.eigen_lang.sha256,
                "source_sha256": sha256(bytes(request.eigen_lang.source)).hexdigest(),
            }
        elif program == "qasm":
            payload["qasm"] = {
                "version": request.qasm.version,
                "source_sha256": sha256(bytes(request.qasm.source)).hexdigest(),
            }
        elif program == "aqo_ref":
            payload["aqo_ref"] = {"qfs_ref": request.aqo_ref.qfs_ref}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def _idempotency_key(self, request) -> str | None:
        key = request.metadata.get("client_request_id", "").strip()
        if key:
            return f"client_request_id:{key}"
        if request.WhichOneof("program") == "eigen_lang":
            digest = request.eigen_lang.sha256.strip()
            if digest:
                return f"eigen_lang.sha256:{digest}:{request.eigen_lang.entrypoint}:{request.target}"
        return None
    
    def _msg_with_trace(self, message: str, trace_id: str | None) -> str:
        return f"{message} trace_id={trace_id}" if trace_id else message

    def _mk_update(self, *, job_id: str, state: int, stage: str, progress: float, message: str, event_seq: int):
        return self._types_pb.JobUpdate(
            job_id=job_id,
            state=state,
            stage=stage,
            progress=progress,
            message=message,
            event_seq=event_seq,
            timestamp=_ts_now(),
        )

    def _mk_default_updates(self, job_id: str, trace_id: str | None) -> list:
        return [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message="pending",
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILED",
                progress=0.25,
                message=self._msg_with_trace("compiled", trace_id),
                event_seq=2,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="DISPATCHED",
                progress=0.35,
                message=self._msg_with_trace("dispatched", trace_id),
                event_seq=3,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.7,
                message=self._msg_with_trace("running", trace_id),
                event_seq=4,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="COMPLETED",
                progress=1.0,
                message="completed",
                event_seq=5,
            ),
        ]
    
    def _mk_error_updates(self, *, job_id: str, summary: str, trace_id: str | None) -> list:
        return [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message=self._msg_with_trace("queued", trace_id),
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILED",
                progress=0.25,
                message=self._msg_with_trace("compiled", trace_id),
                event_seq=2,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="DISPATCHED",
                progress=0.45,
                message=self._msg_with_trace("dispatched", trace_id),
                event_seq=3,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.6,
                message="dispatching_to_backend",
                event_seq=4,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_ERROR,
                stage="ERROR",
                progress=1.0,
                message=summary,
                event_seq=5,
            ),
        ]

    def _mk_vqe_updates(self, *, job_id: str, trace_id: str | None, max_iters: int) -> list:
        updates = [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message="pending",
                event_seq=1,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILED",
                progress=0.2,
                message="compiling",
                event_seq=2,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="DISPATCHED",
                progress=0.35,
                message=self._msg_with_trace("dispatched", trace_id),
                event_seq=3,
            ),
        ]

        simulated_iters = max(2, min(max_iters, 3))
        for idx in range(1, simulated_iters + 1):
            progress = min(0.4 + (0.45 * idx / simulated_iters), 0.9)
            updates.append(
                self._mk_update(
                    job_id=job_id,
                    state=self._types_pb.JOB_STATE_RUNNING,
                    stage="RUNNING",
                    progress=progress,
                    message=self._msg_with_trace(f"vqe_iteration iteration={idx}", trace_id),
                    event_seq=len(updates) + 1,
                )
            )

        updates.append(
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="COMPLETED",
                progress=1.0,
                message=self._msg_with_trace("completed", trace_id),
                event_seq=len(updates) + 1,
            )
        )
        return updates

    def _append_update(self, record: _JobRecord, *, state: int, stage: str, progress: float, message: str) -> None:
        record.updates.append(
            self._mk_update(
                job_id=record.job_id,
                state=state,
                stage=stage,
                progress=progress,
                message=self._msg_with_trace(message, record.trace_id),
                event_seq=len(record.updates) + 1,
            )
        )

    def _store_timeline(self, record: _JobRecord) -> None:
        payload = {
            "version": "2.0.0",
            "job_id": record.job_id,
            "trace_id": record.trace_id or "",
            "events": [
                {
                    "event_seq": int(item.event_seq),
                    "state": self._types_pb.JobState.Name(item.state),
                    "stage": item.stage,
                    "message": item.message,
                    "timestamp": item.timestamp.ToJsonString(),
                    "trace_id": record.trace_id or "",
                }
                for item in record.updates
            ],
        }
        QFS_STORE.atomic_write_bytes(
            record.results_metadata["qfs_job_timeline"],
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )

    def _provision_temporary_artifacts(self, record: _JobRecord) -> None:
        compiled = record.results_metadata["qfs_compiled_aqo"]
        temp_prefix = f"qfs://jobs/{record.job_id}/tmp/"
        temp_refs = [
            f"{temp_prefix}request.json",
            f"{temp_prefix}compiled.tmp",
        ]
        QFS_STORE.put_bytes(compiled, b"{\"version\":\"0.1\",\"operations\":[]}")
        for temp_ref in temp_refs:
            QFS_STORE.put_bytes(temp_ref, b"tmp")
        record.temp_refs = temp_refs

    def _finalize_terminal_state(self, record: _JobRecord) -> None:
        if record.finalized:
            return
        terminal_state = record.updates[-1].state
        if terminal_state in {self._types_pb.JOB_STATE_DONE, self._types_pb.JOB_STATE_ERROR}:
            counts_payload = record.counts or {"error": 0}
            results_parquet = _serialize_results_parquet(
                job_id=record.job_id,
                counts=counts_payload,
                metadata=record.results_metadata,
            )
            record.results_parquet = results_parquet
            QFS_STORE.atomic_write_bytes(record.results_metadata["qfs_results_parquet"], results_parquet)
            if terminal_state == self._types_pb.JOB_STATE_ERROR and record.error_details_ref:
                error_payload = json.dumps(
                    {
                        "job_id": record.job_id,
                        "error_code": record.error_code,
                        "error_summary": record.error_summary,
                        "backend_target": record.results_metadata.get("backend", "sim:local"),
                    },
                    sort_keys=True,
                ).encode("utf-8")
                QFS_STORE.atomic_write_bytes(record.error_details_ref, error_payload)
        else:
            QFS_STORE.delete_bytes(record.results_metadata["qfs_results_parquet"])
            if record.error_details_ref:
                QFS_STORE.delete_bytes(record.error_details_ref)
            record.results_parquet = None
            record.counts = {}

        for temp_ref in record.temp_refs:
            QFS_STORE.delete_bytes(temp_ref)
        self._store_timeline(record)
        record.finalized = True
        if record.completed_at is None:
            record.completed_at = _ts_now()

    def _advance_job(self, record: _JobRecord) -> None:
        if self._batch_mode_enabled and not record.batch_id and len(record.updates) == 1:
            self._try_batch_assignments()
        if record.updates[-1].state in {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}:
            self._finalize_terminal_state(record)
            return
        if len(record.updates) == 1 and record.run_duration_sec <= 0:
            if record.max_iters > 0:
                record.updates = self._mk_vqe_updates(
                    job_id=record.job_id,
                    trace_id=record.trace_id,
                    max_iters=record.max_iters,
                )
            elif record.should_fail:
                record.updates = self._mk_error_updates(
                    job_id=record.job_id,
                    summary=record.error_summary,
                    trace_id=record.trace_id,
                )
            else:
                record.updates = self._mk_default_updates(record.job_id, record.trace_id)
            self._finalize_terminal_state(record)
            return

        now_dt = datetime.now(timezone.utc)
        elapsed = max((now_dt - record.created_at_dt).total_seconds(), 0.0)
        scheduling_delay = max(record.queue_delay_sec, 0.0)
        compiling_after = max(record.run_duration_sec * 0.2, 0.0)
        dispatch_after = max(record.run_duration_sec * 0.45, 0.0)
        running_after = max(record.run_duration_sec * 0.6, 0.0)
        completion_after = max(record.run_duration_sec, 0.0)
        if record.batch_id:
            compiling_after *= 0.8
            dispatch_after *= 0.8
            running_after *= 0.8
            completion_after *= 0.8

        if len(record.updates) == 1 and elapsed >= scheduling_delay + compiling_after:
            self._append_update(
                record,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILED",
                progress=0.25,
                message="compiled",
            )
        if len(record.updates) <= 2 and elapsed >= scheduling_delay + dispatch_after:
            self._append_update(
                record,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="DISPATCHED",
                progress=0.45,
                message="dispatched",
            )
        if len(record.updates) <= 3 and elapsed >= scheduling_delay + running_after:
            self._append_update(
                record,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.7,
                message="running",
            )

        if record.cancel_requested:
            self._append_update(
                record,
                state=self._types_pb.JOB_STATE_CANCELLED,
                stage="CANCELLED",
                progress=1.0,
                message="cancelled by user request",
            )
        elif record.timeout_at is not None and now_dt >= record.timeout_at:
            self._append_update(
                record,
                state=self._types_pb.JOB_STATE_TIMEOUT,
                stage="TIMEOUT",
                progress=1.0,
                message=record.timeout_reason,
            )
        elif elapsed >= scheduling_delay + completion_after:
            if record.should_fail:
                self._append_update(
                    record,
                    state=self._types_pb.JOB_STATE_ERROR,
                    stage="ERROR",
                    progress=1.0,
                    message=record.error_summary,
                )
            else:
                self._append_update(
                    record,
                    state=self._types_pb.JOB_STATE_DONE,
                    stage="COMPLETED",
                    progress=1.0,
                    message="completed",
                )

        if record.updates[-1].state in {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}:
            self._finalize_terminal_state(record)
        else:
            self._store_timeline(record)

    def _build_job_record(self, request, *, job_id: str, created_at: Timestamp, trace_id: str | None) -> _JobRecord:
        metadata = dict(request.metadata)
        created_at_dt = created_at.ToDatetime().replace(tzinfo=timezone.utc)

        backend_error_kind = metadata.get("backend_error_kind", "").strip().lower()
        should_fail = request.target.startswith("emu:fail") or bool(backend_error_kind)
        error_code = ""
        error_summary = ""
        error_details_ref = ""

        runtime_error_map = {
            "timeout": ("RUNTIME_BACKEND_TIMEOUT", "backend execution timeout"),
            "unavailable": ("RUNTIME_BACKEND_UNAVAILABLE", "backend unavailable"),
            "invalid_program": ("RUNTIME_INVALID_PROGRAM", "backend rejected compiled program"),
        }
        if should_fail:
            error_code, error_summary = runtime_error_map.get(
                backend_error_kind,
                ("RUNTIME_BACKEND_EXECUTION_ERROR", "backend execution failed"),
            )

        results_metadata = {
            "version": "0.2",
            "backend": request.target or "sim:local",
            "qfs_compiled_aqo": f"qfs://jobs/{job_id}/compiled/circuit.aqo.json",
            "qfs_results_parquet": f"qfs://jobs/{job_id}/results.parquet",
            "qfs_metrics": f"qfs://jobs/{job_id}/results/metrics.json",
            "qfs_results_stream_prefix": f"qfs://jobs/{job_id}/results/streams/",
            "qfs_job_timeline": f"qfs://jobs/{job_id}/timeline.json",
            "trace_id": trace_id or "",
            "trace_ref": f"trace://{trace_id}" if trace_id else "",
            "timeline_version": "2.0.0",
        }
        dispatch_rationale = {
            "version": "2.0.0",
            "policy_version": metadata.get("dispatch_policy_version", "2.1.0"),
            "reason_codes": ["WEIGHTED_FAIRNESS", "DEVICE_SCORE", "SINGLE_DISPATCH"],
            "selected_backend": request.target or "sim:local",
            "selected_queue": f"priority-{int(request.priority)}",
            "attributes": {
                "priority": str(int(request.priority)),
                "target": request.target or "sim:local",
                "job_name": request.name,
                "batch_mode_enabled": str(self._batch_mode_enabled).lower(),
            },
            "timeline_ref": f"qfs://jobs/{job_id}/timeline.json",
            "logs_ref": f"qfs://jobs/{job_id}/logs/dispatch.log",
            "trace_id": trace_id or "",
            "trace_ref": f"trace://{trace_id}" if trace_id else "",
        }
        
        max_iters = 0
        if metadata.get("max_iters", "").strip():
            try:
                max_iters = max(int(metadata["max_iters"]), 0)
            except ValueError:
                max_iters = 0
        if max_iters > 0:
            simulated_history_len = max(2, max_iters)
            objective_history = [round(-1.0 - (0.08 * idx), 6) for idx in range(simulated_history_len)]
            results_metadata["objective_history"] = json.dumps(objective_history)

        counts = {} if should_fail else {"00": 512, "11": 512}
        
        if should_fail:
            error_details_ref = f"qfs://jobs/{job_id}/errors/runtime_error.json"
        try:
            run_duration_sec = max(float(metadata.get("simulate_runtime_sec", "0.0") or 0.0), 0.0)
        except ValueError:
            run_duration_sec = 0.0
        timeout_sec_raw = metadata.get("timeout_seconds", "").strip()
        timeout_at: datetime | None = None
        timeout_reason = "deadline exceeded"
        if timeout_sec_raw:
            try:
                timeout_sec = max(float(timeout_sec_raw), 0.0)
                timeout_at = created_at_dt + timedelta(seconds=timeout_sec)
            except ValueError:
                timeout_at = None

        updates = [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message=self._msg_with_trace("queued", trace_id),
                event_seq=1,
            )
        ]

        record = _JobRecord(
            job_id=job_id,
            created_at=created_at,
            created_at_dt=created_at_dt,
            updates=updates,
            counts=counts,
            results_metadata=results_metadata,
            results_parquet=None,
            completed_at=None,
            error_code=error_code,
            error_summary=error_summary,
            error_details_ref=error_details_ref,
            should_fail=should_fail,
            run_duration_sec=run_duration_sec,
            timeout_at=timeout_at,
            timeout_reason=timeout_reason,
            cancel_requested=False,
            finalized=False,
            temp_refs=[],
            trace_id=trace_id,
            max_iters=max_iters,
            dispatch_rationale=dispatch_rationale,
            batch_manifest_ref="",
            batch_id="",
            queue_delay_sec=0.0,
        )
        self._provision_temporary_artifacts(record)
        self._store_timeline(record)
        return record
    
    def _queue_key_for(self, record: _JobRecord) -> str:
        queue = record.dispatch_rationale.get("selected_queue", "priority-50")
        backend = record.dispatch_rationale.get("selected_backend", "sim:local")
        return f"{queue}|{backend}"

    def _assign_single_dispatch_delay(self, record: _JobRecord) -> None:
        slot = self._dispatch_slot_seq
        self._dispatch_slot_seq += 1
        record.queue_delay_sec = float(slot) * self._batch_dispatch_gap_sec

    def _inflight_batch_jobs(self) -> int:
        terminal_values = {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
        return sum(
            1
            for rec in self._jobs.values()
            if rec.batch_id and rec.updates and rec.updates[-1].state not in terminal_values
        )

    def _emit_batch_manifest(self, *, batch_id: str, members: list[_JobRecord], queue_key: str) -> str:
        manifest_ref = f"qfs://batches/{batch_id}/manifest.json"
        payload = {
            "version": "1.0.0",
            "schema_version": "batch_manifest.v1",
            "batch_id": batch_id,
            "queue_key": queue_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "jobs": [rec.job_id for rec in members],
            "size": len(members),
            "mode": "batch",
        }
        QFS_STORE.atomic_write_bytes(
            manifest_ref,
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        return manifest_ref

    def _apply_batch_assignment(self, members: list[_JobRecord], *, queue_key: str) -> None:
        if not members:
            return
        batch_id = f"batch_{uuid.uuid4().hex[:10]}"
        manifest_ref = self._emit_batch_manifest(batch_id=batch_id, members=members, queue_key=queue_key)
        slot = self._dispatch_slot_seq
        self._dispatch_slot_seq += 1
        for rec in members:
            rec.batch_id = batch_id
            rec.batch_manifest_ref = manifest_ref
            rec.queue_delay_sec = float(slot) * self._batch_dispatch_gap_sec
            rec.dispatch_rationale["reason_codes"] = ["WEIGHTED_FAIRNESS", "DEVICE_SCORE", "BATCH_EXECUTION_V1"]
            attrs = dict(rec.dispatch_rationale["attributes"])
            attrs["batch_id"] = batch_id
            attrs["batch_manifest_ref"] = manifest_ref
            attrs["batch_manifest_version"] = "1.0.0"
            attrs["batch_mode_enabled"] = "true"
            rec.dispatch_rationale["attributes"] = attrs
            rec.results_metadata["batch_manifest_ref"] = manifest_ref
            rec.results_metadata["batch_manifest_version"] = "1.0.0"

    def _try_batch_assignments(self) -> None:
        if not self._batch_mode_enabled:
            return
        if self._inflight_batch_jobs() >= self._batch_inflight_limit:
            return
        pending = [
            rec
            for rec in self._jobs.values()
            if not rec.batch_id and len(rec.updates) == 1 and rec.updates[-1].stage == "QUEUED"
        ]
        groups: dict[str, list[_JobRecord]] = {}
        for rec in pending:
            groups.setdefault(self._queue_key_for(rec), []).append(rec)

        now = datetime.now(timezone.utc)
        for queue_key, members in groups.items():
            members.sort(key=lambda item: item.created_at_dt)
            while members:
                if self._inflight_batch_jobs() >= self._batch_inflight_limit:
                    return
                oldest_wait = (now - members[0].created_at_dt).total_seconds()
                if len(members) < self._batch_size and oldest_wait < self._batch_wait_window_sec:
                    break
                batch_members = members[: self._batch_size]
                self._apply_batch_assignment(batch_members, queue_key=queue_key)
                members = members[self._batch_size :]

    def _assign_scheduler_slot(self, record: _JobRecord) -> None:
        if not self._batch_mode_enabled:
            self._assign_single_dispatch_delay(record)
            return
        self._try_batch_assignments()
        if not record.batch_id:
            self._assign_single_dispatch_delay(record)

    def SubmitJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.SubmitJob")
        enforce_authz(context, required_permission="jobs:submit")
        rc = new_request_context(context)
        log_request_start("JobService.SubmitJob", rc)

        violations = validate_submit_job(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        idem_key = self._idempotency_key(request)
        request_fingerprint = self._request_fingerprint(request)

        with self._lock:
            if idem_key:
                previous = self._idempotency.get(idem_key)
                if previous:
                    if previous.request_fingerprint != request_fingerprint:
                        context.abort(
                            grpc.StatusCode.INVALID_ARGUMENT,
                            f"idempotency key reuse with different payload: {idem_key}",
                        )
                    existing = self._jobs[previous.job_id]
                    self._advance_job(existing)
                    latest = existing.updates[-1]
                    rc.job_id = existing.job_id
                    log_request_end("JobService.SubmitJob", rc)
                    return self._job_pb.SubmitJobResponse(
                        job_id=existing.job_id,
                        status=self._types_pb.JobStatus(
                            job_id=existing.job_id,
                            state=latest.state,
                            stage=latest.stage,
                            progress=latest.progress,
                            message="accepted (idempotent replay)",
                            created_at=existing.created_at,
                            updated_at=latest.timestamp,
                        ),
                    )

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            rc.job_id = job_id
            now = _ts_now()
            trace_id = rc.trace_id or request.metadata.get("trace_id", "").strip() or None
            record = self._build_job_record(request, job_id=job_id, created_at=now, trace_id=trace_id)
            self._jobs[job_id] = record
            self._assign_scheduler_slot(record)
            if idem_key:
                self._idempotency[idem_key] = _IdempotencyRecord(
                    job_id=job_id, request_fingerprint=request_fingerprint
                )

        resp = self._job_pb.SubmitJobResponse(
            job_id=job_id,
            status=self._types_pb.JobStatus(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message=record.updates[0].message,
                created_at=now,
                updated_at=now,
            ),
        )

        log_request_end("JobService.SubmitJob", rc)
        return resp

    def GetJobStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobStatus")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobStatus", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
        with self._lock:
            self._advance_job(record)
            latest = record.updates[-1]
        created_at = record.created_at

        resp = self._job_pb.GetJobStatusResponse(
            status=self._types_pb.JobStatus(
                job_id=request.job_id,
                state=latest.state,
                stage=latest.stage,
                progress=latest.progress,
                message=latest.message,
                created_at=created_at,
                updated_at=latest.timestamp,
                error_code=record.error_code if latest.state == self._types_pb.JOB_STATE_ERROR else "",
                error_summary=record.error_summary if latest.state == self._types_pb.JOB_STATE_ERROR else "",
                error_details_ref=record.error_details_ref if latest.state == self._types_pb.JOB_STATE_ERROR else "",
            )
        )

        log_request_end("JobService.GetJobStatus", rc)
        return resp

    def CancelJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.CancelJob")
        enforce_authz(context, required_permission="jobs:cancel")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.CancelJob", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        accepted = False
        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
            self._advance_job(record)
            terminal_values = {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
            if record.updates[-1].state not in terminal_values and not record.cancel_requested:
                record.cancel_requested = True
                self._advance_job(record)
                accepted = True

        resp = self._job_pb.CancelJobResponse(accepted=accepted)
        log_request_end("JobService.CancelJob", rc)
        return resp

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.StreamJobUpdates")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.StreamJobUpdates", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        start_after_seq = int(request.last_event_seq)
        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
            self._advance_job(record)
            selected_updates = list(record.updates)

        for update in selected_updates:
            if int(update.event_seq) <= start_after_seq:
                continue
            yield self._job_pb.StreamJobUpdatesResponse(update=update)

        log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobResults")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobResults", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
        current_state = record.updates[-1].state
        if current_state in {
            self._types_pb.JOB_STATE_PENDING,
            self._types_pb.JOB_STATE_COMPILING,
            self._types_pb.JOB_STATE_RUNNING,
        }:
            context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                f"results are not ready yet for job_id={request.job_id}; current_state={self._types_pb.JobState.Name(current_state)}",
            )

        resp = self._job_pb.GetJobResultsResponse(
            job_id=request.job_id,
            state=current_state,
            counts=record.counts,
            metadata={
                **record.results_metadata,
                "qfs_results_parquet_bytes": str(len(record.results_parquet or b"")),
            },
            error_code=record.error_code,
            error_summary=record.error_summary,
            error_details_ref=record.error_details_ref,
            completed_at=record.completed_at or _ts_now(),
        )

        log_request_end("JobService.GetJobResults", rc)
        return resp
    
    def GetDispatchRationale(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetDispatchRationale")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetDispatchRationale", rc)

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"job_id not found: {request.job_id}")
            self._advance_job(record)
            rationale = dict(record.dispatch_rationale)

        resp = self._job_pb.GetDispatchRationaleResponse(
            rationale=self._job_pb.DispatchRationale(
                version=str(rationale["version"]),
                policy_version=str(rationale["policy_version"]),
                reason_codes=[str(code) for code in rationale["reason_codes"]],
                selected_backend=str(rationale["selected_backend"]),
                selected_queue=str(rationale["selected_queue"]),
                attributes={k: str(v) for k, v in dict(rationale["attributes"]).items()},
                timeline_ref=str(rationale["timeline_ref"]),
                logs_ref=str(rationale["logs_ref"]),
                trace_id=str(rationale["trace_id"]),
                trace_ref=str(rationale["trace_ref"]),
            )
        )

        log_request_end("JobService.GetDispatchRationale", rc)
        return resp


class DeviceService:
    """Implementation of eigen.api.v1.DeviceService."""

    def __init__(self, dev_pb, types_pb):
        self._dev_pb = dev_pb
        self._types_pb = types_pb

    def ListDevices(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.ListDevices")
        enforce_authz(context, required_permission="devices:list")
        rc = new_request_context(context)
        log_request_start("DeviceService.ListDevices", rc)

        # backend_type is optional
        resp = self._dev_pb.ListDevicesResponse(
            devices=[
                self._types_pb.DeviceInfo(
                    device_id="sim:local",
                    name="Local simulator",
                    backend_type="simulator",
                    status=self._types_pb.DEVICE_STATUS_ONLINE,
                    queue_depth=0,
                    estimated_wait_sec=0,
                    capabilities={"shots": "1024"},
                )
            ]
        )

        log_request_end("DeviceService.ListDevices", rc)
        return resp

    def GetDeviceDetails(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.GetDeviceDetails")
        enforce_authz(context, required_permission="devices:list")
        rc = new_request_context(context)
        log_request_start("DeviceService.GetDeviceDetails", rc)

        violations = validate_device_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.GetDeviceDetailsResponse(
            device=self._types_pb.DeviceInfo(
                device_id=request.device_id,
                name="Device",
                backend_type="simulator",
                status=self._types_pb.DEVICE_STATUS_ONLINE,
            )
        )

        log_request_end("DeviceService.GetDeviceDetails", rc)
        return resp

    def GetDeviceStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.GetDeviceStatus")
        enforce_authz(context, required_permission="devices:list")
        rc = new_request_context(context)
        log_request_start("DeviceService.GetDeviceStatus", rc)

        violations = validate_device_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.GetDeviceStatusResponse(
            device_id=request.device_id,
            status=self._types_pb.DEVICE_STATUS_ONLINE,
            queue_depth=0,
            estimated_wait_sec=0,
            metadata={},
        )

        log_request_end("DeviceService.GetDeviceStatus", rc)
        return resp

    def ReserveDevice(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.ReserveDevice")
        enforce_authz(context, required_permission="devices:reserve")
        rc = new_request_context(context)
        log_request_start("DeviceService.ReserveDevice", rc)

        violations = validate_reserve_device(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        resp = self._dev_pb.ReserveDeviceResponse(
            reservation_id=f"rsv_{uuid.uuid4().hex[:12]}",
            expires_at=_ts_now(),
        )

        log_request_end("DeviceService.ReserveDevice", rc)
        return resp
