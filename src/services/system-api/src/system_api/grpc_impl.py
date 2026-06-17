"""gRPC service implementations for System API (MVP skeleton)."""
from __future__ import annotations

import asyncio
import ast
import json
import logging
import os
import re
import time
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from datetime import timedelta
from hashlib import sha256
from io import BytesIO

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .job_store import JobStore
from .job_store import JobRecord as DurableJobRecord

from .security import _AUTH_ALLOW_ALL

# ----------------------------------------------------------------------
# JobEvent and JobEventStore – moved here because they are missing from
# job_store.py.  The definitions mirror the usage inside JobService.
# ----------------------------------------------------------------------

@dataclass
class JobEvent:
    event_id: str
    job_id: str
    tenant_id: str
    event_type: str
    timestamp_ms: int
    payload: dict

class JobEventStore:
    def __init__(self) -> None:
        self._events: dict[str, list[dict]] = {}

    def append(self, event: JobEvent) -> None:
        record = {
            "event_id": event.event_id,
            "job_id": event.job_id,
            "tenant_id": event.tenant_id,
            "event_type": event.event_type,
            "timestamp_ms": event.timestamp_ms,
            "payload": event.payload,
        }
        self._events.setdefault(event.job_id, []).append(record)

    def read(self, job_id: str) -> list[dict]:
        return self._events.get(job_id, [])

# ----------------------------------------------------------------------

logger = logging.getLogger(__name__)

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ModuleNotFoundError:  # pragma: no cover - optional for lightweight test environments
    pa = None
    pq = None

from .errors import FieldViolation, PublicErrorSpec, abort_invalid_argument, abort_payload_limit, abort_public, abort_with_error_info
from .lifecycle import apply_signal
from .scheduling import resolve_dag
from .kernel_client import KernelGatewayClient
from .observability import (
    append_security_audit_event,
    log_request_end,
    log_request_start,
    new_request_context,
    record_kb_fallback,
    record_public_api_contract_marker,
    record_submit_job_outcome,
    trace_id_from_traceparent,
)
from .qfs_store import QFS_STORE
from .security import (
    SecurityContext,
    auth_context,
    enforce_authn,
    enforce_authz,
    enforce_sandbox_policy,
    security_context,
    load_security_config,
)
from .validation import (
    validate_device_id,
    validate_job_id,
    validate_reserve_device,
    validate_submit_job,
)

from .job_store import JobStore, JobRecord

JOB_STORE = JobStore()

def _resolve_idempotency(request) -> str:
     return (
         getattr(request, "idempotency_key", None)
         or getattr(request, "client_request_id", None)
         or sha256(str(request).encode()).hexdigest()
     )

TERMINAL_JOB_STATES = {
    "JOB_STATE_DONE",
    "JOB_STATE_ERROR",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_TIMEOUT",
}

TOPOLOGY_CONTRACT_VERSION = "1.1.0"
TOPOLOGY_LINEAGE_VERSION = "1.1.0"
TENANT_ENVELOPE_CONTRACT_VERSION = "1.0.0"
PUBLIC_API_CONTRACT_VERSION = "1.0.0"
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def _metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


@dataclass(frozen=True)
class NormalizedPublicEnvelope:
    contract_version: str
    request_id: str
    idempotency_key: str
    traceparent: str
    tenant_id: str
    project_id: str
    client_version: str


def _stable_request_id(request) -> str:
    raw = request.SerializeToString(deterministic=True)
    return f"req_{sha256(raw).hexdigest()[:24]}"


def _synthetic_traceparent(seed: str) -> str:
    digest = sha256(seed.encode("utf-8")).hexdigest()
    trace_id = digest[:32]
    span_id = digest[32:48]
    return f"00-{trace_id}-{span_id}-01"


def _public_envelope(request, context: grpc.ServicerContext) -> NormalizedPublicEnvelope:

    envelope = getattr(request, "envelope", None)
    md = _metadata(context)
    _subject, _roles, auth_tenant = auth_context(context)
    contract_version = (
        getattr(envelope, "contract_version", "")
        or md.get("x-eigen-contract-version", "")
        or PUBLIC_API_CONTRACT_VERSION
    ).strip()
    if not _SEMVER_RE.match(contract_version):
        record_public_api_contract_marker(contract_version, "error")
        abort_with_error_info(
            context,
            grpc_code=grpc.StatusCode.INVALID_ARGUMENT,
            message=f"malformed public contract_version: {contract_version}",
            reason="EIGEN_PUBLIC_CONTRACT_VERSION_MALFORMED",
            domain="eigen.api.v1",
            metadata={"contract_version": contract_version},
        )
    if contract_version != PUBLIC_API_CONTRACT_VERSION:
        record_public_api_contract_marker(contract_version, "error")
        abort_with_error_info(
            context,
            grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
            message=f"unsupported public contract_version: {contract_version}",
            reason="EIGEN_PUBLIC_CONTRACT_VERSION_UNSUPPORTED",
            domain="eigen.api.v1",
            metadata={
                "contract_version": contract_version,
                "supported_contract_version": PUBLIC_API_CONTRACT_VERSION,
            },
        )

    request_id = (
        getattr(envelope, "request_id", "")
        or md.get("x-request-id", "")
        or _stable_request_id(request)
    ).strip()
    tenant_id = (
        auth_tenant
        or getattr(envelope, "tenant_id", "")
        or md.get("x-eigen-tenant", "")
        or "tenant-default"
    ).strip()
    project_id = (
        getattr(envelope, "project_id", "")
        or md.get("x-eigen-project", "")
        or md.get("x-project-id", "")
        or "project-default"
    ).strip()
    traceparent = (getattr(envelope, "traceparent", "") or md.get("traceparent", "")).strip()
    if not traceparent:
        traceparent = _synthetic_traceparent(request_id)

    return NormalizedPublicEnvelope(
        contract_version=contract_version,
        request_id=request_id,
        idempotency_key=(
            getattr(envelope, "idempotency_key", "")
            or md.get("x-idempotency-key", "")
            or md.get("x-eigen-idempotency-key", "")
        ).strip(),
        traceparent=traceparent,
        tenant_id=tenant_id or "tenant-default",
        project_id=project_id or "project-default",
        client_version=(getattr(envelope, "client_version", "") or md.get("x-client-version", "")).strip(),
    )


def _abort_job_not_found(context: grpc.ServicerContext, job_id: str) -> None:
    abort_public(
        context,
        PublicErrorSpec(
            grpc_code=grpc.StatusCode.NOT_FOUND,
            message=f"job_id not found: {job_id}",
            reason="EIGEN_PUBLIC_JOB_NOT_FOUND",
            retryable=False,
            resource_type="eigen.api.v1.Job",
            resource_name=job_id,
            detail="No job exists for the supplied job_id.",
        ),
    )


def _apply_public_envelope_context(rc, envelope: NormalizedPublicEnvelope) -> None:
    rc.request_id = envelope.request_id
    if envelope.traceparent and not rc.traceparent:
        rc.traceparent = envelope.traceparent
    if rc.trace_id is None and rc.traceparent:
        rc.trace_id = trace_id_from_traceparent(rc.traceparent)


def _public_contract_version_label(envelope: NormalizedPublicEnvelope | None) -> str:
    return envelope.contract_version if envelope is not None else PUBLIC_API_CONTRACT_VERSION


def _record_submit_public_marker(envelope: NormalizedPublicEnvelope | None, outcome: str) -> None:
    record_public_api_contract_marker(_public_contract_version_label(envelope), outcome)


def _envelope_value(envelope, field: str) -> str:
    return str(getattr(envelope, field, "") or "").strip() if envelope is not None else ""


def _ts_now() -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.now(timezone.utc))
    return ts


def _ts_from_unix(seconds: float) -> Timestamp:
    ts = Timestamp()
    ts.FromDatetime(datetime.fromtimestamp(seconds, tz=timezone.utc))
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
    topology: dict[str, str]
    batch_manifest_ref: str
    batch_id: str
    queue_delay_sec: float
    owner_subject: str
    owner_tenant: str
    owner_project: str
    tenant_quota_limit: int
    project_quota_limit: int


@dataclass
class _IdempotencyRecord:
    job_id: str
    request_fingerprint: str
    expires_at_unix: float
    tenant_id: str
    project_id: str

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "_IdempotencyRecord":
        return cls(
            job_id=str(payload["job_id"]),
            request_fingerprint=str(payload["request_fingerprint"]),
            expires_at_unix=float(payload["expires_at_unix"]),
            tenant_id=str(payload.get("tenant_id", "tenant-default")),
            project_id=str(payload.get("project_id", "project-default")),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "request_fingerprint": self.request_fingerprint,
            "expires_at_unix": self.expires_at_unix,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
        }


@dataclass
class _ReservationRecord:
    reservation_id: str
    device_id: str
    purpose: str
    owner_subject: str
    owner_tenant: str
    owner_project: str
    request_hash: str
    ttl_seconds: int
    state: str
    created_at_unix: float
    updated_at_unix: float
    expires_at_unix: float

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> "_ReservationRecord":
        return cls(
            reservation_id=str(payload["reservation_id"]),
            device_id=str(payload["device_id"]),
            purpose=str(payload.get("purpose", "unspecified")),
            owner_subject=str(payload.get("owner_subject", "")),
            owner_tenant=str(payload.get("owner_tenant", "tenant-default")),
            owner_project=str(payload.get("owner_project", "project-default")),
            request_hash=str(payload.get("request_hash", "")),
            ttl_seconds=int(payload.get("ttl_seconds", 0)),
            state=str(payload.get("state", "ACTIVE")),
            created_at_unix=float(payload.get("created_at_unix", 0.0)),
            updated_at_unix=float(payload.get("updated_at_unix", 0.0)),
            expires_at_unix=float(payload.get("expires_at_unix", 0.0)),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "reservation_id": self.reservation_id,
            "device_id": self.device_id,
            "purpose": self.purpose,
            "owner_subject": self.owner_subject,
            "owner_tenant": self.owner_tenant,
            "owner_project": self.owner_project,
            "request_hash": self.request_hash,
            "ttl_seconds": self.ttl_seconds,
            "state": self.state,
            "created_at_unix": self.created_at_unix,
            "updated_at_unix": self.updated_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }


class JobService:
    """Implementation of eigen.api.v1.JobService."""

    def __init__(self, job_pb, types_pb):
        self._job_pb = job_pb
        self._types_pb = types_pb
        self._idempotency: dict[str, _IdempotencyRecord] = {}
        self._idempotency_ttl_sec = max(float(os.getenv("SYSTEM_API_IDEMPOTENCY_TTL_SECONDS", "86400")), 1.0)
        self._idempotency_store_path = Path(
            os.getenv("SYSTEM_API_IDEMPOTENCY_STORE_PATH", "/tmp/eigen-system-api-idempotency.json")
        )
        self._lock = threading.RLock()
        self._job_store = JOB_STORE
        self._event_store = JobEventStore()
        self._jobs: dict[str, _JobRecord] = {}

        self._batch_mode_enabled = os.getenv("EIGEN_BATCH_MODE", "1").strip() not in {"0", "false", "off"}
        self._batch_size = max(int(os.getenv("EIGEN_BATCH_SIZE", "4")), 2)
        self._batch_wait_window_sec = max(float(os.getenv("EIGEN_BATCH_WAIT_WINDOW_SEC", "0.2")), 0.0)
        self._batch_dispatch_gap_sec = max(float(os.getenv("EIGEN_BATCH_DISPATCH_GAP_SEC", "0.15")), 0.0)
        self._batch_inflight_limit = max(int(os.getenv("EIGEN_BATCH_INFLIGHT_LIMIT", "64")), self._batch_size)
        self._quota_per_target = max(int(os.getenv("EIGEN_SCHED_QUOTA_PER_TARGET", "8")), 1)
        self._starvation_threshold_sec = max(float(os.getenv("EIGEN_SCHED_STARVATION_SEC", "2.0")), 0.0)
        self._dispatch_slot_seq = 0
        self._kernel_client = KernelGatewayClient()
        self._load_idempotency_records()

    # =========================================================
    # SINGLE WRITE PATH
    # =========================================================

    def _persist_job(self, job: _JobRecord, idem_key: str | None = None):
        """All writes go through this single path."""
        job_id = job.job_id
        # 1. Update kernel cache
        self._jobs[job_id] = job
        # 2. Update idempotency mapping
        if idem_key:
            self._idempotency[idem_key] = _IdempotencyRecord(
                job_id=job_id,
                request_fingerprint="",  # placeholder
                expires_at_unix=time.time() + self._idempotency_ttl_sec,
                tenant_id=job.owner_tenant,
                project_id=job.owner_project,
            )
        # 3. Durable write
        durable_record = DurableJobRecord(
            job_id=job_id,
            tenant_id=getattr(job, "owner_tenant", "unknown"),
            name=getattr(job, "name", ""),
            state=getattr(job, "state", "UNKNOWN"),
            created_at_unix_ms=int(job.created_at.timestamp() * 1000) if hasattr(job, "created_at") else int(time.time() * 1000),
            updated_at_unix_ms=int(time.time() * 1000),
            idempotency_key=idem_key,
        )
        self._job_store.upsert(durable_record)
        # 4. Event sourcing
        event = JobEvent(
            event_id=str(uuid.uuid4()),
            job_id=job_id,
            tenant_id=job.owner_tenant,
            event_type="JOB_STATE_CHANGED",
            timestamp_ms=int(time.time() * 1000),
            payload={"state": getattr(job, "state", "UNKNOWN")},
        )
        self._event_store.append(event)

    def _rebuild_from_events(self, job_id: str):
        events = self._event_store.read(job_id)
        if not events:
            return None
        state = None
        tenant = None
        name = None
        for e in events:
            if e["event_type"] in {"JOB_CREATED", "JOB_STATE_CHANGED"}:
                tenant = e["tenant_id"] or tenant
                name = e["payload"].get("name", name)
                state = e["payload"]["state"]
        job = _JobRecord(
            job_id=job_id,
            owner_tenant=tenant,
            name=name,
            state=state,
            created_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def _assert_consistency(self):
        for job_id, job in self._jobs.items():
            durable = self._job_store.get(job_id)
            if durable and durable.state != getattr(job, "state", None):
                print(f"[WARN] state drift detected: {job_id}")

    def _kernel_endpoint_configured(self) -> bool:
        return bool(
            os.environ.get("EIGEN_KERNEL_ADDR")
            or os.environ.get("KERNEL_ENDPOINT")
            or os.environ.get("KERNEL_GRPC_ENDPOINT")
        )

    def _public_envelope_dict(self, envelope: NormalizedPublicEnvelope) -> dict[str, str]:
        return {
            "contract_version": envelope.contract_version,
            "request_id": envelope.request_id,
            "idempotency_key": envelope.idempotency_key,
            "traceparent": envelope.traceparent,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "client_version": envelope.client_version,
        }

    def _kernel_state_to_public_state(self, kernel_state: str):
        mapping = {
            "TASK_STATE_PENDING": self._types_pb.JOB_STATE_PENDING,
            "TASK_STATE_COMPILING": self._types_pb.JOB_STATE_COMPILING,
            "TASK_STATE_OPTIMIZING": self._types_pb.JOB_STATE_COMPILING,
            "TASK_STATE_QUEUED": self._types_pb.JOB_STATE_QUEUED,
            "TASK_STATE_RUNNING": self._types_pb.JOB_STATE_RUNNING,
            "TASK_STATE_DONE": self._types_pb.JOB_STATE_DONE,
            "TASK_STATE_ERROR": self._types_pb.JOB_STATE_ERROR,
            "TASK_STATE_CANCELLED": self._types_pb.JOB_STATE_CANCELLED,
            "TASK_STATE_TIMEOUT": self._types_pb.JOB_STATE_TIMEOUT,
        }
        return mapping.get(kernel_state, self._types_pb.JOB_STATE_PENDING)

    def _job_status_from_kernel(self, *, job_id: str, kernel_response: dict, created_at: Timestamp | None = None):
        created_at_ts = created_at or kernel_response.get("created_at") or _ts_now()
        updated_at_ts = kernel_response.get("updated_at") or created_at_ts
        return self._types_pb.JobStatus(
            job_id=job_id,
            state=self._kernel_state_to_public_state(kernel_response.get("state", "TASK_STATE_PENDING")),
            stage=kernel_response.get("stage", ""),
            progress=float(kernel_response.get("progress", 0.0)),
            message=kernel_response.get("message", ""),
            created_at=created_at_ts,
            updated_at=updated_at_ts,
            error_code=kernel_response.get("error_code", ""),
            error_summary=kernel_response.get("error_summary", ""),
            error_details_ref=kernel_response.get("error_details_ref", ""),
            topology=self._mk_topology_pb(kernel_response.get("topology")),
        )

    def _job_status_from_record(self, record: _JobRecord, *, message_override: str | None = None):
        latest = record.updates[-1]
        terminal_state = latest.state in {
            getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES
        }
        return self._types_pb.JobStatus(
            job_id=record.job_id,
            state=latest.state,
            stage=latest.stage,
            progress=float(latest.progress),
            message=message_override if message_override is not None else latest.message,
            created_at=record.created_at,
            updated_at=record.completed_at or latest.timestamp or record.created_at,
            error_code=record.error_code if terminal_state else "",
            error_summary=record.error_summary if terminal_state else "",
            error_details_ref=record.error_details_ref if terminal_state else "",
            topology=self._mk_topology_pb(record.topology),
        )

    def _dispatch_rationale_from_record(self, record: _JobRecord):
        return self._job_pb.DispatchRationale(
            version=str(record.dispatch_rationale.get("version", "")),
            policy_version=str(record.dispatch_rationale.get("policy_version", "")),
            reason_codes=list(record.dispatch_rationale.get("reason_codes", [])),
            selected_backend=str(record.dispatch_rationale.get("selected_backend", "")),
            selected_queue=str(record.dispatch_rationale.get("selected_queue", "")),
            attributes={k: str(v) for k, v in dict(record.dispatch_rationale.get("attributes", {})).items()},
            timeline_ref=str(record.dispatch_rationale.get("timeline_ref", "")),
            logs_ref=str(record.dispatch_rationale.get("logs_ref", "")),
            trace_id=str(record.dispatch_rationale.get("trace_id", record.trace_id or "")),
            trace_ref=str(record.dispatch_rationale.get("trace_ref", f"trace://{record.trace_id}" if record.trace_id else "")),
        )

    def _get_local_job_record(self, job_id: str) -> _JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            self._advance_job(record)
            return record

    def _resolve_job(self, job_id: str):
        with self._lock:
            record = self._jobs.get(job_id)
            if record is not None:
                return self._job_pb.SubmitJobResponse(job_id=job_id, status=self._job_status_from_record(record))

            idem_record = next((rec for rec in self._idempotency.values() if rec.job_id == job_id), None)
            if idem_record is None:
                return None

            now = _ts_now()
            return self._job_pb.SubmitJobResponse(
                job_id=job_id,
                status=self._types_pb.JobStatus(
                    job_id=job_id,
                    state=self._types_pb.JOB_STATE_PENDING,
                    stage="QUEUED",
                    progress=0.0,
                    message="accepted (idempotent replay from persisted request record)",
                    created_at=now,
                    updated_at=now,
                ),
            )

    def _kernel_public_response(self, envelope: NormalizedPublicEnvelope) -> dict[str, str]:
        return {
            "contract_version": envelope.contract_version,
            "request_id": envelope.request_id,
            "idempotency_key": envelope.idempotency_key,
            "traceparent": envelope.traceparent,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "client_version": envelope.client_version,
        }

    def _load_idempotency_records(self) -> None:
        if not self._idempotency_store_path.exists():
            return
        try:
            payload = json.loads(self._idempotency_store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        now = time.time()
        records = payload.get("records", {}) if isinstance(payload, dict) else {}
        if not isinstance(records, dict):
            return
        for key, raw in records.items():
            if not isinstance(raw, dict):
                continue
            try:
                record = _IdempotencyRecord.from_json(raw)
            except (KeyError, TypeError, ValueError):
                continue
            if record.expires_at_unix > now:
                self._idempotency[str(key)] = record

    def _persist_idempotency_records(self) -> None:
        now = time.time()
        self._idempotency = {
            key: record
            for key, record in self._idempotency.items()
            if record.expires_at_unix > now
        }
        payload = {
            "version": "1.0.0",
            "ttl_seconds": self._idempotency_ttl_sec,
            "records": {
                key: record.to_json()
                for key, record in sorted(self._idempotency.items())
            },
        }
        self._idempotency_store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._idempotency_store_path.with_suffix(self._idempotency_store_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self._idempotency_store_path)

    def _get_idempotency_record(self, key: str) -> _IdempotencyRecord | None:
        record = self._idempotency.get(key)
        if record is None:
            return None
        if record.expires_at_unix <= time.time():
            self._idempotency.pop(key, None)
            self._persist_idempotency_records()
            return None
        return record

    def _remember_idempotency_record(
        self,
        *,
        key: str,
        job_id: str,
        request_fingerprint: str,
        envelope: NormalizedPublicEnvelope,
    ) -> None:
        self._idempotency[key] = _IdempotencyRecord(
            job_id=job_id,
            request_fingerprint=request_fingerprint,
            expires_at_unix=time.time() + self._idempotency_ttl_sec,
            tenant_id=envelope.tenant_id,
            project_id=envelope.project_id,
        )
        self._persist_idempotency_records()

    def _request_fingerprint(
        self, request, envelope: NormalizedPublicEnvelope
    ) -> str:
        payload = {
            "contract_version": envelope.contract_version,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "name": request.name,
            "target": request.target,
            "priority": int(request.priority),
            "compiler_options": sorted(request.compiler_options.items()),
            "dependencies": list(request.dependencies),
            "metadata": sorted((k, v) for k, v in request.metadata.items() if k not in {"trace_id"}),
            "program": request.WhichOneof("program") or "",
            "reservation_id": getattr(request, "reservation_id", ""),
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

    def _idempotency_key(
        self,
        request,
        _context: grpc.ServicerContext,
        envelope: NormalizedPublicEnvelope,
    ) -> str | None:
        tenant_id = (
            envelope.tenant_id or request.metadata.get("tenant_id", "tenant-default")
        ).strip() or "tenant-default"
        key = (
            envelope.idempotency_key or request.metadata.get("client_request_id", "")
        ).strip()
        if key:
            return ":".join(("tenant", tenant_id, "idempotency", key))
        if request.WhichOneof("program") == "eigen_lang":
            digest = request.eigen_lang.sha256.strip()
            if digest:
                return ":".join(
                    (
                        "tenant",
                        tenant_id,
                        "eigen_lang.sha256",
                        digest,
                        request.eigen_lang.entrypoint,
                        request.target,
                    )
                )
        return None

    def _msg_with_trace(self, message: str, trace_id: str | None) -> str:
        return f"{message} trace_id={trace_id}" if trace_id else message

    def _mk_update(
        self,
        *,
        job_id: str,
        state: int,
        stage: str,
        progress: float,
        message: str,
        event_seq: int,
        topology: dict[str, str] | None = None,
    ):
        return self._types_pb.JobUpdate(
            job_id=job_id,
            state=state,
            stage=stage,
            progress=progress,
            message=message,
            event_seq=event_seq,
            timestamp=_ts_now(),
            topology=self._mk_topology_pb(topology),
        )

    def _mk_topology_pb(self, topology: dict[str, str] | None):
        if not topology:
            return None
        return self._types_pb.TopologyEnvelope(
            contract_version=topology["contract_version"],
            lineage_version=topology["lineage_version"],
            cluster_id=topology["cluster_id"],
            worker_id=topology["worker_id"],
            partition_id=topology["partition_id"],
            attempt=int(topology["attempt"]),
        )

    def _mk_default_updates(self, job_id: str, trace_id: str | None, topology: dict[str, str]) -> list:
        return [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message="pending",
                event_seq=1,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILED",
                progress=0.25,
                message=self._msg_with_trace("compiled", trace_id),
                event_seq=2,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="DISPATCHED",
                progress=0.35,
                message=self._msg_with_trace("dispatched", trace_id),
                event_seq=3,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.7,
                message=self._msg_with_trace("running", trace_id),
                event_seq=4,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_DONE,
                stage="COMPLETED",
                progress=1.0,
                message=self._msg_with_trace("completed", trace_id),
                event_seq=5,
                topology=topology,
            ),
        ]

    def _mk_error_updates(self, *, job_id: str, summary: str, trace_id: str | None, topology: dict[str, str]) -> list:
        return [
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_PENDING,
                stage="QUEUED",
                progress=0.0,
                message=self._msg_with_trace("queued", trace_id),
                event_seq=1,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_COMPILING,
                stage="COMPILED",
                progress=0.25,
                message=self._msg_with_trace("compiled", trace_id),
                event_seq=2,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="DISPATCHED",
                progress=0.45,
                message=self._msg_with_trace("dispatched", trace_id),
                event_seq=3,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_RUNNING,
                stage="RUNNING",
                progress=0.6,
                message="dispatching_to_backend",
                event_seq=4,
                topology=topology,
            ),
            self._mk_update(
                job_id=job_id,
                state=self._types_pb.JOB_STATE_ERROR,
                stage="ERROR",
                progress=1.0,
                message=summary,
                event_seq=5,
                topology=topology,
            ),
        ]

    
    def _append_update(self, record: _JobRecord, *, state: int, stage: str, progress: float, message: str) -> None:
        record.updates.append(
            self._mk_update(
                job_id=record.job_id,
                state=state,
                stage=stage,
                progress=progress,
                message=self._msg_with_trace(message, record.trace_id),
                event_seq=len(record.updates) + 1,
                topology=record.topology,
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

    def _compiled_aqo_bytes_for_request(self, request) -> bytes:
        program = request.WhichOneof("program")
        if program == "aqo_ref":
            ref = request.aqo_ref.qfs_ref
            aqo_bytes = QFS_STORE.get_bytes(ref)
            if aqo_bytes:
                return aqo_bytes

        if program == "eigen_lang":
            source = bytes(request.eigen_lang.source)
            if source:
                aqo_bytes = self._compile_eigen_lang_source(source)
                if aqo_bytes:
                    return aqo_bytes

        # Never persist an empty AQO shell: keep the artifact canonical and non-empty
        # even if we could not compile or dereference the original payload yet.
        return b"{\"version\":\"1.0.0\",\"qubits\":1,\"operations\":[{\"op\":\"MEASURE\",\"q\":[0],\"c\":[0]}]}"

    def _compile_eigen_lang_source(self, source: bytes) -> bytes:
        try:
            tree = ast.parse(source.decode("utf-8"))
        except (UnicodeDecodeError, SyntaxError):
            return b"{\"version\":\"1.0.0\",\"qubits\":1,\"operations\":[{\"op\":\"MEASURE\",\"q\":[0],\"c\":[0]}]}"

        def _call_name(node):
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return node.attr
            return None

        def _literal_scalar(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
                return node.value
            return None

        operations: list[dict[str, object]] = []
        qubits = 1
        gate_ops = {"rx": "RX", "ry": "RY", "rz": "RZ"}

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            if name in gate_ops:
                op: dict[str, object] = {"op": gate_ops[name], "q": [0]}
                theta_expr = next((kw.value for kw in node.keywords if kw.arg == "theta"), None)
                theta_value = _literal_scalar(theta_expr) if theta_expr is not None else None
                if isinstance(theta_value, (int, float)):
                    op["params"] = {"theta": float(theta_value)}
                elif isinstance(theta_value, str):
                    op["params"] = {"theta": theta_value}
                operations.append(op)
            elif name == "cx":
                operations.append({"op": "CX", "q": [0, 1]})
                qubits = max(qubits, 2)

        if not operations:
            operations.append({"op": "MEASURE", "q": [0], "c": [0]})
        else:
            operations.append({"op": "MEASURE", "q": list(range(qubits)), "c": list(range(qubits))})

        aqo = {"version": "1.0.0", "qubits": qubits, "operations": operations}
        return json.dumps(aqo, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _provision_temporary_artifacts(self, record: _JobRecord, request) -> None:
        compiled = record.results_metadata["qfs_compiled_aqo"]
        temp_prefix = f"qfs://jobs/{record.job_id}/tmp/"
        temp_refs = [
            f"{temp_prefix}request.json",
            f"{temp_prefix}compiled.tmp",
        ]
        QFS_STORE.put_bytes(compiled, self._compiled_aqo_bytes_for_request(request))
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
            if record.should_fail:
                record.updates = self._mk_error_updates(
                    job_id=record.job_id,
                    summary=record.error_summary,
                    trace_id=record.trace_id,
                    topology=record.topology,
                )
            else:
                record.updates = self._mk_default_updates(record.job_id, record.trace_id, record.topology)
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

    def _build_job_record(
        self,
        request,
        *,
        job_id: str,
        created_at: Timestamp,
        trace_id: str | None,
        request_id: str,
        traceparent: str,
        security: SecurityContext,
        owner_subject: str,
        owner_tenant: str,
        owner_project: str,
    ) -> _JobRecord:
        metadata = dict(request.metadata)
        tenant_envelope = request.tenant
        tenant_id = (tenant_envelope.tenant_id or metadata.get("tenant_id") or owner_tenant or "tenant-default").strip() or "tenant-default"
        project_id = (
            tenant_envelope.project_id
            or metadata.get("project_id")
            or owner_project
            or "project-default"
        ).strip() or "project-default"
        sandbox_profile = metadata.get("sandbox_profile", security.sandbox_profile or "default").strip() or (security.sandbox_profile or "default")
        tenant_quota_limit = int(tenant_envelope.tenant_max_queued_jobs or os.getenv("EIGEN_SCHED_TENANT_QUOTA_MAX_QUEUED", "16"))
        project_quota_limit = int(tenant_envelope.project_max_queued_jobs or os.getenv("EIGEN_SCHED_PROJECT_QUOTA_MAX_QUEUED", "8"))
        created_at_dt = created_at.ToDatetime().replace(tzinfo=timezone.utc)
        attempt = 1
        try:
            attempt = max(int(metadata.get("topology_attempt", "1")), 1)
        except ValueError:
            attempt = 1
        topology = {
            "contract_version": TOPOLOGY_CONTRACT_VERSION,
            "lineage_version": TOPOLOGY_LINEAGE_VERSION,
            "cluster_id": metadata.get("topology_cluster_id", "cluster-local"),
            "worker_id": metadata.get("topology_worker_id", f"worker-{job_id[-6:]}"),
            "partition_id": metadata.get("topology_partition_id", "partition-0"),
            "attempt": str(attempt),
        }

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
        default_runtime_sec = 0.0
        if request.target.startswith("emu:real"):
            default_runtime_sec = 0.0
        try:
            run_duration_sec = max(float(metadata.get("simulate_runtime_sec", str(default_runtime_sec)) or default_runtime_sec), 0.0)
        except ValueError:
            run_duration_sec = default_runtime_sec

        security_roles = ",".join(sorted(security.roles))
        normalized_security_context = {
            "subject": security.subject,
            "roles": sorted(security.roles),
            "tenant": security.tenant or owner_tenant,
            "auth_mode": security.auth_mode,
            "policy_version": security.policy_version,
            "service_identity": security.service_identity or "system-api",
            "service_role": security.service_role or "",
            "sandbox_profile": security.sandbox_profile or sandbox_profile,
            "request_id": request_id,
            "traceparent": traceparent,
            "trace_id": trace_id or "",
        }

        results_metadata = {
            "version": "0.3",
            "backend": request.target or "sim:local",
            "qfs_compiled_aqo": f"qfs://jobs/{job_id}/compiled/circuit.aqo.json",
            "security_subject": security.subject,
            "security_roles": security_roles,
            "security_tenant": security.tenant or owner_tenant,
            "security_project": owner_project,
            "security_sandbox_profile": security.sandbox_profile or sandbox_profile,
            "security_policy_version": security.policy_version,
            "security_service_identity": security.service_identity or "system-api",
            "security_service_role": security.service_role or "",
            "security_context": json.dumps(normalized_security_context, sort_keys=True, separators=(",", ":")),
            "request_id": request_id,
            "traceparent": traceparent,
            "qfs_results_parquet": f"qfs://jobs/{job_id}/results.parquet",
            "qfs_metrics": f"qfs://jobs/{job_id}/results/metrics.json",
            "qfs_results_stream_prefix": f"qfs://jobs/{job_id}/results/streams/",
            "qfs_job_timeline": f"qfs://jobs/{job_id}/timeline.json",
            "trace_id": trace_id or "",
            "trace_ref": f"trace://{trace_id}" if trace_id else "",
            "timeline_version": "2.0.0",
            "topology_contract_version": topology["contract_version"],
            "topology_lineage_version": topology["lineage_version"],
            "topology_cluster_id": topology["cluster_id"],
            "topology_worker_id": topology["worker_id"],
            "topology_partition_id": topology["partition_id"],
            "topology_attempt": topology["attempt"],
            "topology_envelope_ref": f"qfs://jobs/{job_id}/topology/envelope.json",
            "tenant_envelope_contract_version": TENANT_ENVELOPE_CONTRACT_VERSION,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "tenant_max_queued_jobs": str(max(tenant_quota_limit, 1)),
            "project_max_queued_jobs": str(max(project_quota_limit, 1)),
        }
        noise_score = metadata.get("noise_score", "").strip()
        noise_threshold = metadata.get("noise_threshold", "").strip() or "0.03"
        topology_telemetry = metadata.get("topology_telemetry", "").strip().lower() in {"1", "true", "yes", "on"}
        topology_fallback = metadata.get("topology_fallback", "").strip() or "cluster-local/default"
        noise_fallback = "NOISE_TELEMETRY_MISSING"
        if noise_score:
            noise_fallback = "NO_FALLBACK"
        topology_fallback_reason = "TOPOLOGY_TELEMETRY_MISSING"
        if topology_telemetry:
            topology_fallback_reason = "NO_FALLBACK"
        dispatch_rationale = {
            "version": "2.3.0",
            "policy_version": metadata.get("dispatch_policy_version", "2.2.0"),
            "reason_codes": ["WEIGHTED_FAIRNESS", "DEVICE_SCORE", "PRIORITY_QUOTA", "SINGLE_DISPATCH"],
            "selected_backend": request.target or "sim:local",
            "selected_queue": f"priority-{int(request.priority)}",
            "attributes": {
                "priority": str(int(request.priority)),
                "target": request.target or "sim:local",
                "job_name": request.name,
                "traceparent": traceparent,
                "batch_mode_enabled": str(self._batch_mode_enabled).lower(),
                "policy_branch": "single_dispatch",
                "fallback_reason": f"{topology_fallback_reason}|{noise_fallback}",
                "artifact_version": "1.2.0",
                "topology_contract_version": topology["contract_version"],
                "topology_hook_status": "present" if topology_telemetry else "fallback",
                "topology_fallback_target": topology_fallback,
                "noise_hook_status": "present" if noise_score else "fallback",
                "noise_score": noise_score or "unavailable",
                "noise_threshold": noise_threshold,
                "tenant_envelope_contract_version": TENANT_ENVELOPE_CONTRACT_VERSION,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "tenant_quota_limit": str(max(tenant_quota_limit, 1)),
                "project_quota_limit": str(max(project_quota_limit, 1)),
            },
            "lineage": [
                {
                    "step": 1,
                    "event": "QUEUE_CLASSIFIED",
                    "outcome": f"priority-{int(request.priority)}",
                    "attributes": {
                        "queue": f"priority-{int(request.priority)}",
                        "target": request.target or "sim:local",
                        "cluster_id": topology["cluster_id"],
                        "partition_id": topology["partition_id"],
                    },
                },
                {
                    "step": 2,
                    "event": "DISPATCH_MODE_SELECTED",
                    "outcome": "single_dispatch",
                    "attributes": {
                        "batch_mode_enabled": str(self._batch_mode_enabled).lower(),
                        "worker_id": topology["worker_id"],
                    },
                },
                {
                    "step": 3,
                    "event": "BACKEND_SELECTED",
                    "outcome": request.target or "sim:local",
                    "attributes": {
                        "reason_codes": "WEIGHTED_FAIRNESS,DEVICE_SCORE",
                        "attempt": topology["attempt"],
                    },
                },
            ],
            "timeline_ref": f"qfs://jobs/{job_id}/timeline.json",
            "logs_ref": f"qfs://jobs/{job_id}/logs/dispatch.log",
            "trace_id": trace_id or "",
            "trace_ref": f"trace://{trace_id}" if trace_id else "",
        }

        counts = {} if should_fail else {"00": 512, "11": 512}

        if should_fail:
            error_details_ref = f"qfs://jobs/{job_id}/errors/runtime_error.json"
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
                topology=topology,
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
            max_iters=0,
            dispatch_rationale=dispatch_rationale,
            topology=topology,
            batch_manifest_ref="",
            batch_id="",
            queue_delay_sec=0.0,
            owner_subject=owner_subject,
            owner_tenant=tenant_id,
            owner_project=project_id,
            tenant_quota_limit=max(tenant_quota_limit, 1),
            project_quota_limit=max(project_quota_limit, 1),
        )
        self._provision_temporary_artifacts(record, request)
        QFS_STORE.atomic_write_bytes(
            results_metadata["topology_envelope_ref"],
            json.dumps(topology, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        self._store_timeline(record)
        return record

    def _queue_key_for(self, record: _JobRecord) -> str:
        queue = record.dispatch_rationale.get("selected_queue", "priority-50")
        backend = record.dispatch_rationale.get("selected_backend", "sim:local")
        return f"{queue}|{backend}"

    def _assign_single_dispatch_delay(self, record: _JobRecord) -> None:
        slot = self._dispatch_slot_seq
        self._dispatch_slot_seq += 1
        record.queue_delay_sec += float(slot) * self._batch_dispatch_gap_sec

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
        batch_delay_sec = float(slot) * self._batch_dispatch_gap_sec
        existing_delays = [max(rec.queue_delay_sec, 0.0) for rec in members if rec.queue_delay_sec > 0]
        if existing_delays:
            batch_delay_sec = min(batch_delay_sec, min(existing_delays))
        for rec in members:
            rec.batch_id = batch_id
            rec.batch_manifest_ref = manifest_ref
            rec.queue_delay_sec = batch_delay_sec
            rec.dispatch_rationale["reason_codes"] = ["WEIGHTED_FAIRNESS", "DEVICE_SCORE", "BATCH_EXECUTION_V1"]
            attrs = dict(rec.dispatch_rationale["attributes"])
            attrs["policy_branch"] = "batch_dispatch"
            attrs["fallback_reason"] = "QUEUE_BATCHED"
            attrs["batch_id"] = batch_id
            attrs["batch_manifest_ref"] = manifest_ref
            attrs["batch_manifest_version"] = "1.0.0"
            attrs["batch_mode_enabled"] = "true"
            rec.dispatch_rationale["attributes"] = attrs
            lineage = [
                {
                    "step": 1,
                    "event": "QUEUE_CLASSIFIED",
                    "outcome": str(rec.dispatch_rationale["selected_queue"]),
                    "attributes": {"queue_key": queue_key},
                },
                {
                    "step": 2,
                    "event": "BATCH_ELIGIBILITY",
                    "outcome": "eligible",
                    "attributes": {"batch_wait_window_sec": f"{self._batch_wait_window_sec:.3f}"},
                },
                {
                    "step": 3,
                    "event": "BATCH_ASSIGNED",
                    "outcome": batch_id,
                    "attributes": {"batch_manifest_ref": manifest_ref},
                },
            ]
            attrs["decision_lineage"] = json.dumps(lineage, sort_keys=True, separators=(",", ":"))
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
        queued_for_target = sum(
            1
            for rec in self._jobs.values()
            if rec.job_id != record.job_id
            if rec.dispatch_rationale.get("selected_backend", "sim:local")
            == record.dispatch_rationale.get("selected_backend", "sim:local")
            and rec.updates
            and rec.updates[-1].stage == "QUEUED"
        )
        age_sec = (datetime.now(timezone.utc) - record.created_at_dt).total_seconds()
        if queued_for_target >= self._quota_per_target:
            penalty_slots = max(queued_for_target - self._quota_per_target + 1, 1)
            record.queue_delay_sec += float(penalty_slots) * self._batch_dispatch_gap_sec
            record.dispatch_rationale["reason_codes"].append("TARGET_QUOTA_DELAY")
            record.dispatch_rationale["attributes"]["quota_state"] = "throttled"
            record.dispatch_rationale["attributes"]["quota_penalty_slots"] = str(penalty_slots)
        else:
            record.dispatch_rationale["attributes"]["quota_state"] = "eligible"
            record.dispatch_rationale["attributes"]["quota_penalty_slots"] = "0"

        queued_for_tenant = sum(
            1
            for rec in self._jobs.values()
            if rec.job_id != record.job_id
            and rec.owner_tenant == record.owner_tenant
            and rec.updates
            and rec.updates[-1].stage == "QUEUED"
        )
        if queued_for_tenant >= record.tenant_quota_limit:
            record.dispatch_rationale["reason_codes"].append("TENANT_BASELINE_QUOTA_DELAY")
            record.dispatch_rationale["attributes"]["tenant_quota_state"] = "throttled"
        else:
            record.dispatch_rationale["attributes"]["tenant_quota_state"] = "eligible"
        queued_for_project = sum(
            1
            for rec in self._jobs.values()
            if rec.job_id != record.job_id
            and rec.owner_tenant == record.owner_tenant
            and rec.owner_project == record.owner_project
            and rec.updates
            and rec.updates[-1].stage == "QUEUED"
        )
        if queued_for_project >= record.project_quota_limit:
            record.dispatch_rationale["reason_codes"].append("PROJECT_BASELINE_QUOTA_DELAY")
            record.dispatch_rationale["attributes"]["project_quota_state"] = "throttled"
        else:
            record.dispatch_rationale["attributes"]["project_quota_state"] = "eligible"
        if age_sec >= self._starvation_threshold_sec:
            record.queue_delay_sec = 0.0
            record.dispatch_rationale["reason_codes"].append("STARVATION_PROTECTION")
            record.dispatch_rationale["attributes"]["starvation_guard"] = "promoted"
        else:
            record.dispatch_rationale["attributes"]["starvation_guard"] = "none"
        if not self._batch_mode_enabled:
            self._assign_single_dispatch_delay(record)
            return
        self._try_batch_assignments()
        if not record.batch_id:
            self._assign_single_dispatch_delay(record)

    def _enforce_job_access(self, *, context: grpc.ServicerContext, record: _JobRecord) -> None:
        cfg = load_security_config()
        if cfg.auth_mode == "allow_all":
            return
        cfg = load_security_config()
        if cfg.auth_mode == _AUTH_ALLOW_ALL:
            return
        subject, roles, tenant = auth_context(context)
        if tenant != record.owner_tenant:
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.PERMISSION_DENIED,
                    message="cross-tenant access denied",
                    reason="EIGEN_PUBLIC_PERMISSION_DENIED",
                    retryable=False,
                    metadata={"policy": "POLICY_DENY_TENANT_MISMATCH"},
                    precondition_type="AUTHORIZATION_POLICY",
                    precondition_subject=record.job_id,
                    detail="Caller tenant does not match the job owner tenant.",
                ),
            )

    def SubmitJob(self, request, context: grpc.ServicerContext):
        envelope = _public_envelope(request, context)
        enforce_authn(context, method_name="JobService.SubmitJob")
        enforce_authz(context, required_permission="jobs:submit")

        subject, roles, tenant = auth_context(context)
        rc = new_request_context(context)
        log_request_start("JobService.SubmitJob", rc)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.SubmitJob")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        idem_key = self._idempotency_key(request, context, envelope)
        request_fingerprint = self._request_fingerprint(request, envelope)
        topology_metadata = dict(request.metadata)
        try:
            topology_attempt = max(int(topology_metadata.get("topology_attempt", "1")), 1)
        except ValueError:
            topology_attempt = 1
        topology = {
            "contract_version": TOPOLOGY_CONTRACT_VERSION,
            "lineage_version": TOPOLOGY_LINEAGE_VERSION,
            "cluster_id": topology_metadata.get("topology_cluster_id", "cluster-local"),
            "worker_id": topology_metadata.get("topology_worker_id", f"worker-{request.name[-6:] or 'local'}"),
            "partition_id": topology_metadata.get("topology_partition_id", "partition-0"),
            "attempt": str(topology_attempt),
        }
        public_envelope = self._public_envelope_dict(envelope)
        public_envelope["topology"] = topology
        created_at = _ts_now()
        kernel_public_envelope = dict(public_envelope)
        expired_idem_record = False
        if idem_key:
            raw_idem_record = self._idempotency.get(idem_key)
            if raw_idem_record is not None and raw_idem_record.expires_at_unix <= time.time():
                expired_idem_record = True

        with self._lock:
            if idem_key:
                previous = self._get_idempotency_record(idem_key)
                if previous:
                    if previous.request_fingerprint != request_fingerprint:
                        record_submit_job_outcome("conflict")
                        _record_submit_public_marker(envelope, "conflict")
                        abort_public(
                            context,
                            PublicErrorSpec(
                                grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                                message="idempotency key reuse with different normalized payload",
                                reason="EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT",
                                retryable=False,
                                metadata={"idempotency_scope": "tenant"},
                                precondition_type="IDEMPOTENCY_CONFLICT",
                                precondition_subject=idem_key,
                                detail="Reuse the key only with the same normalized request payload or choose a new key.",
                            ),
                        )
                    record_submit_job_outcome("replayed")
                    _record_submit_public_marker(envelope, "replayed")
                    existing_job = self._resolve_job(previous.job_id)
                    if existing_job:
                        return existing_job

                    existing = self._jobs.get(previous.job_id)
                    if existing:
                        job = existing
                        job.job_id = existing.job_id
                        self._persist_job(job, idem_key=idem_key)
                        if self._kernel_endpoint_configured():
                            try:
                                kernel_status = asyncio.run(
                                    self._kernel_client.get_job_status(previous.job_id, self._public_envelope_dict(envelope))
                                )
                            except grpc.RpcError as err:
                                if err.code() == grpc.StatusCode.NOT_FOUND:
                                    _abort_job_not_found(context, previous.job_id)
                                context.abort(err.code(), err.details() or "kernel delegation failed")
                            status = self._job_status_from_kernel(job_id=previous.job_id, kernel_response=kernel_status)
                            log_request_end(
                                "JobService.SubmitJob",
                                rc,
                                request_id=rc.request_id,
                                trace_id=(request.metadata.get("trace_id", "").strip() or rc.trace_id),
                                traceparent=rc.traceparent or envelope.traceparent or "",
                                job_id=previous.job_id,
                            )
                            return self._job_pb.SubmitJobResponse(job_id=previous.job_id, status=status)
                        record = self._jobs.get(previous.job_id)
                        if record is None:
                            record = self._build_job_record(
                                request,
                                job_id=previous.job_id,
                                created_at=created_at,
                                trace_id=(request.metadata.get("trace_id", "").strip() or rc.trace_id),
                                request_id=rc.request_id,
                                traceparent=rc.traceparent or envelope.traceparent or "",
                                security=sec,
                                owner_subject=sec.subject,
                                owner_tenant=sec.tenant or envelope.tenant_id,
                                owner_project=envelope.project_id,
                            )
                            self._jobs[previous.job_id] = record
                            status = self._job_status_from_record(
                                record,
                                message_override="accepted (idempotent replay from persisted request record)",
                            )
                        else:
                            self._advance_job(record)
                            status = self._job_status_from_record(record)

                        log_request_end(
                            "JobService.SubmitJob",
                            rc,
                            request_id=rc.request_id,
                            trace_id=(request.metadata.get("trace_id", "").strip() or rc.trace_id),
                            traceparent=rc.traceparent or envelope.traceparent or "",
                            job_id=previous.job_id,
                        )
                        return self._job_pb.SubmitJobResponse(job_id=previous.job_id, status=status)

        if expired_idem_record:
            kernel_public_envelope.pop("idempotency_key", None)

        try:
            program_kind = request.WhichOneof("program")
            if program_kind == "eigen_lang":
                program_bytes = bytes(request.eigen_lang.source)
                program_format = "eigen_lang_source"
            elif program_kind == "qasm":
                program_bytes = bytes(request.qasm.source)
                program_format = "qasm_text"
            elif program_kind == "aqo_ref":
                program_bytes = request.aqo_ref.qfs_ref.encode("utf-8")
                program_format = "aqo_ref"
            else:
                program_bytes = b""
                program_format = "unknown"

            job_id = f"job-{uuid.uuid4().hex[:16]}"
            record = self._build_job_record(
                request,
                job_id=job_id,
                created_at=created_at,
                trace_id=(request.metadata.get("trace_id", "").strip() or rc.trace_id),
                request_id=rc.request_id,
                traceparent=rc.traceparent or envelope.traceparent or "",
                security=sec,
                owner_subject=sec.subject,
                owner_tenant=sec.tenant or envelope.tenant_id,
                owner_project=envelope.project_id,
            )
            self._jobs[job_id] = record
        except Exception:
            _record_submit_public_marker(envelope, "error")
            raise

        kernel_endpoint = (
            os.environ.get("EIGEN_KERNEL_ADDR")
            or os.environ.get("KERNEL_ENDPOINT")
            or os.environ.get("KERNEL_GRPC_ENDPOINT")
        )
        if kernel_endpoint:
            try:
                asyncio.run(
                    self._kernel_client.enqueue_job(
                        name=request.name,
                        program=program_bytes,
                        program_format=program_format,
                        target=request.target,
                        priority=int(request.priority),
                        compiler_options=dict(request.compiler_options),
                        metadata_kvs=dict(request.metadata),
                        public_envelope=public_envelope,
                        workload=request.workload,
                    )
                )
            except Exception as exc:
                logger.warning("Kernel delegation unavailable for SubmitJob; using local lifecycle record: %s", exc)

        rc.job_id = job_id
        if idem_key:
            self._remember_idempotency_record(
                key=idem_key,
                job_id=job_id,
                request_fingerprint=request_fingerprint,
                envelope=envelope,
            )

        record_submit_job_outcome("accepted")
        _record_submit_public_marker(envelope, "accepted")
        status = self._job_status_from_record(record)

        resp = self._job_pb.SubmitJobResponse(job_id=job_id, status=status)

        log_request_end(
            "JobService.SubmitJob",
            rc,
            request_id=rc.request_id,
            trace_id=rc.trace_id,
            traceparent=rc.traceparent or envelope.traceparent or "",
            job_id=job_id,
        )
        return resp

    def GetJobStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobStatus")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobStatus", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.GetJobStatus")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        record = self._get_local_job_record(request.job_id)
        if record is not None:
            self._enforce_job_access(context=context, record=record)

        if self._kernel_endpoint_configured():
            try:
                kernel_response = asyncio.run(
                    self._kernel_client.get_job_status(request.job_id, self._public_envelope_dict(envelope))
                )
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.NOT_FOUND:
                    record = self._get_local_job_record(request.job_id)
                    if record is not None:
                        self._enforce_job_access(context=context, record=record)
                        resp = self._job_pb.GetJobStatusResponse(
                            status=self._job_status_from_record(record)
                        )
                        log_request_end("JobService.GetJobStatus", rc)
                        return resp
                    _abort_job_not_found(context, request.job_id)
                context.abort(err.code(), err.details() or "kernel delegation failed")

            resp = self._job_pb.GetJobStatusResponse(
                status=self._job_status_from_kernel(job_id=request.job_id, kernel_response=kernel_response)
            )
            log_request_end("JobService.GetJobStatus", rc)
            return resp

        record = self._get_local_job_record(request.job_id)
        if record is not None:
            self._enforce_job_access(context=context, record=record)
            resp = self._job_pb.GetJobStatusResponse(status=self._job_status_from_record(record))
            log_request_end("JobService.GetJobStatus", rc)
            return resp

        _abort_job_not_found(context, request.job_id)

    def CancelJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.CancelJob")
        enforce_authz(context, required_permission="jobs:cancel")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.CancelJob", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.CancelJob")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        if self._kernel_endpoint_configured():
            try:
                kernel_response = asyncio.run(
                    self._kernel_client.cancel_job(request.job_id, self._public_envelope_dict(envelope))
                )
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.NOT_FOUND:
                    _abort_job_not_found(context, request.job_id)
                context.abort(err.code(), err.details() or "kernel delegation failed")

            resp = self._job_pb.CancelJobResponse(accepted=bool(kernel_response.get("accepted", False)))
            log_request_end("JobService.CancelJob", rc)
            return resp

        record = self._get_local_job_record(request.job_id)
        if record is not None:
            current_stage = record.updates[-1].stage if record.updates else "QUEUED"
            decision = apply_signal(
                current_stage=current_stage,
                signal="cancel",
                already_requested=record.cancel_requested,
            )
            if decision.accepted:
                record.cancel_requested = True
                record.cancel_reason = "user-request"
                record.cancellation_fanout_ref = f"qfs://jobs/{record.job_id}/control/cancellation.json"
                self._append_update(
                    record,
                    state=self._types_pb.JOB_STATE_CANCELLED,
                    stage="CANCELLED",
                    progress=1.0,
                    message="cancelled by user request",
                )
                self._finalize_terminal_state(record)
            resp = self._job_pb.CancelJobResponse(accepted=decision.accepted)
            log_request_end("JobService.CancelJob", rc)
            return resp

        try:
            kernel_response = asyncio.run(self._kernel_client.cancel_job(request.job_id, self._public_envelope_dict(envelope)))
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:
                _abort_job_not_found(context, request.job_id)
            context.abort(err.code(), err.details() or "kernel delegation failed")

        resp = self._job_pb.CancelJobResponse(accepted=bool(kernel_response.get("accepted", False)))
        log_request_end("JobService.CancelJob", rc)
        return resp

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.StreamJobUpdates")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.StreamJobUpdates", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.StreamJobUpdates")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        if os.getenv("SYSTEM_API_DEBUG") == "1":
            self._assert_consistency()

        record = self._get_local_job_record(request.job_id)
        if record is not None:
            last_event_seq = int(request.last_event_seq)
            for update in record.updates:
                if int(update.event_seq) <= last_event_seq:
                    continue
                yield self._job_pb.StreamJobUpdatesResponse(
                    update=self._types_pb.JobUpdate(
                        job_id=update.job_id,
                        state=update.state,
                        stage=update.stage,
                        progress=float(update.progress),
                        message=update.message,
                        event_seq=int(update.event_seq),
                        timestamp=update.timestamp,
                        topology=update.topology,
                    )
                )
            log_request_end("JobService.StreamJobUpdates", rc)
            return
        
        if self._kernel_endpoint_configured():
            try:
                updates = asyncio.run(
                    self._collect_kernel_updates(
                        job_id=request.job_id,
                        last_event_seq=int(request.last_event_seq),
                        envelope=envelope,
                    )
                )
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.NOT_FOUND:
                    _abort_job_not_found(context, request.job_id)
                context.abort(err.code(), err.details() or "kernel delegation failed")

            for update in updates:
                yield self._job_pb.StreamJobUpdatesResponse(
                    update=self._types_pb.JobUpdate(
                        job_id=update["job_id"],
                        state=update["state"],
                        stage=update["stage"],
                        progress=float(update["progress"]),
                        message=update["message"],
                        event_seq=int(update["event_seq"]),
                        timestamp=update["timestamp"],
                        topology=self._mk_topology_pb(update.get("topology")),
                    )
                )
            log_request_end("JobService.StreamJobUpdates", rc)
            return

        _abort_job_not_found(context, request.job_id)

        try:
            updates = asyncio.run(
                self._collect_kernel_updates(
                    job_id=request.job_id,
                    last_event_seq=int(request.last_event_seq),
                    envelope=envelope,
                )
            )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:
                _abort_job_not_found(context, request.job_id)
            context.abort(err.code(), err.details() or "kernel delegation failed")

        for update in updates:
            yield self._job_pb.StreamJobUpdatesResponse(
                update=self._types_pb.JobUpdate(
                    job_id=update["job_id"],
                    state=update["state"],
                    stage=update["stage"],
                    progress=float(update["progress"]),
                    message=update["message"],
                    event_seq=int(update["event_seq"]),
                    timestamp=update["timestamp"],
                    topology=self._mk_topology_pb(update.get("topology")),
                )
            )

        log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobResults")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetJobResults", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.GetJobResults")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        if self._kernel_endpoint_configured():
            try:
                kernel_response = asyncio.run(
                    self._kernel_client.get_job_results(request.job_id, self._public_envelope_dict(envelope))
                )
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.NOT_FOUND:
                    record = self._get_local_job_record(request.job_id)
                    if record is not None:
                        self._enforce_job_access(context=context, record=record)
                        latest = record.updates[-1]
                        terminal_state = latest.state in {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
                        if not terminal_state:
                            abort_public(
                                context,
                                PublicErrorSpec(
                                    grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                                    message="results are not ready yet",
                                    reason="EIGEN_PUBLIC_RESULTS_NOT_READY",
                                    retryable=True,
                                    metadata={"current_state": "TASK_STATE_PENDING"},
                                    retry_delay_seconds=1,
                                    precondition_type="JOB_LIFECYCLE",
                                    precondition_subject=request.job_id,
                                    detail="Poll GetJobStatus until the job reaches a terminal state before reading results.",
                                ),
                            )
                        metadata = dict(record.results_metadata)
                        metadata.setdefault("qfs_results_parquet_bytes", str(len(record.results_parquet or b"")))
                        metadata.setdefault("qfs_result_ref", record.results_metadata.get("qfs_results_parquet", ""))
                        resp = self._job_pb.GetJobResultsResponse(
                            job_id=record.job_id,
                            state=latest.state,
                            counts=dict(record.counts),
                            metadata=metadata,
                            error_code=record.error_code,
                            error_summary=record.error_summary,
                            error_details_ref=record.error_details_ref,
                            completed_at=record.completed_at or latest.timestamp or _ts_now(),
                        )
                        log_request_end("JobService.GetJobResults", rc)
                        return resp
                    _abort_job_not_found(context, request.job_id)
                if err.code() == grpc.StatusCode.FAILED_PRECONDITION:
                    context.abort(err.code(), err.details() or "kernel delegation failed")

            resp = self._job_pb.GetJobResultsResponse(
                job_id=kernel_response.get("job_id", request.job_id),
                state=self._kernel_state_to_public_state(kernel_response.get("state", "TASK_STATE_PENDING")),
                counts=kernel_response.get("counts", {}),
                metadata=kernel_response.get("metadata", {}),
                qfs_result_ref=kernel_response.get("qfs_result_ref", ""),
                completed_at=kernel_response.get("completed_at") or _ts_now(),
                error_code=kernel_response.get("error_code", ""),
                error_summary=kernel_response.get("error_summary", ""),
                error_details_ref=kernel_response.get("error_details_ref", ""),
            )
            log_request_end("JobService.GetJobResults", rc)
            return resp
        
        if self._kernel_endpoint_configured():
            try:
                kernel_response = asyncio.run(self._kernel_client.get_job_results(request.job_id, self._public_envelope_dict(envelope)))
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.NOT_FOUND:
                    _abort_job_not_found(context, request.job_id)
                if err.code() == grpc.StatusCode.FAILED_PRECONDITION:
                    abort_public(
                        context,
                        PublicErrorSpec(
                            grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                            message="results are not ready yet",
                            reason="EIGEN_PUBLIC_RESULTS_NOT_READY",
                            retryable=True,
                            metadata={"current_state": "TASK_STATE_PENDING"},
                            retry_delay_seconds=1,
                            precondition_type="JOB_LIFECYCLE",
                            precondition_subject=request.job_id,
                            detail="Poll GetJobStatus until the job reaches a terminal state before reading results.",
                        ),
                    )
                context.abort(err.code(), err.details() or "kernel delegation failed")

            state = kernel_response.get("state", "TASK_STATE_UNSPECIFIED")
            counts = dict(kernel_response.get("counts", {}))
            metadata = dict(kernel_response.get("metadata", {}))
            if kernel_response.get("qfs_result_ref"):
                metadata.setdefault("qfs_result_ref", kernel_response["qfs_result_ref"])

            resp = self._job_pb.GetJobResultsResponse(
                job_id=request.job_id,
                state=self._kernel_state_to_public_state(state),
                counts=counts,
                metadata=metadata,
                error_code=kernel_response.get("error_code", ""),
                error_summary=kernel_response.get("error_summary", ""),
                error_details_ref=kernel_response.get("error_details_ref", ""),
                completed_at=kernel_response.get("completed_at") or _ts_now(),
            )
            log_request_end("JobService.GetJobResults", rc)
            return resp

        record = self._get_local_job_record(request.job_id)
        if record is not None:
            self._enforce_job_access(context=context, record=record)
            latest = record.updates[-1]
            terminal_state = latest.state in {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
            if not terminal_state:
                abort_public(
                    context,
                    PublicErrorSpec(
                        grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                        message="results are not ready yet",
                        reason="EIGEN_PUBLIC_RESULTS_NOT_READY",
                        retryable=True,
                        metadata={"current_state": "TASK_STATE_PENDING"},
                        retry_delay_seconds=1,
                        precondition_type="JOB_LIFECYCLE",
                        precondition_subject=request.job_id,
                        detail="Poll GetJobStatus until the job reaches a terminal state before reading results.",
                    ),
                )

            metadata = dict(record.results_metadata)
            metadata.setdefault("qfs_results_parquet_bytes", str(len(record.results_parquet or b"")))
            metadata.setdefault("qfs_result_ref", record.results_metadata.get("qfs_results_parquet", ""))

            resp = self._job_pb.GetJobResultsResponse(
                job_id=record.job_id,
                state=latest.state,
                counts=dict(record.counts),
                metadata=metadata,
                error_code=record.error_code,
                error_summary=record.error_summary,
                error_details_ref=record.error_details_ref,
                completed_at=record.completed_at or latest.timestamp or _ts_now(),
            )
            log_request_end("JobService.GetJobResults", rc)
            return resp
        
        _abort_job_not_found(context, request.job_id)


    def GetDispatchRationale(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetDispatchRationale")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        rc.job_id = request.job_id
        log_request_start("JobService.GetDispatchRationale", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.GetDispatchRationale")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_job_id(request)
        if violations:
            abort_with_error_info(
                context,
                grpc_code=grpc.StatusCode.INVALID_ARGUMENT,
                message="validation failed",
                reason="EIGEN_PUBLIC_EXPLAIN_INVALID_REQUEST",
                domain="eigen.api.v1.explain",
                metadata={"field": ",".join(v.field for v in violations)},
            )

        record = self._get_local_job_record(request.job_id)
        if record is not None:
            resp = self._job_pb.GetDispatchRationaleResponse(
                rationale=self._dispatch_rationale_from_record(record)
            )
            log_request_end("JobService.GetDispatchRationale", rc)
            return resp
        
        if self._kernel_endpoint_configured():
            try:
                kernel_response = asyncio.run(
                    self._kernel_client.get_dispatch_rationale(request.job_id, self._public_envelope_dict(envelope))
                )
            except grpc.RpcError as err:
                if err.code() == grpc.StatusCode.NOT_FOUND:
                    abort_with_error_info(
                        context,
                        grpc_code=grpc.StatusCode.NOT_FOUND,
                        message=f"job_id not found: {request.job_id}",
                        reason="EIGEN_PUBLIC_EXPLAIN_DECISION_NOT_FOUND",
                        domain="eigen.api.v1.explain",
                        metadata={"job_id": request.job_id},
                    )
                context.abort(err.code(), err.details() or "kernel delegation failed")

            resp = self._job_pb.GetDispatchRationaleResponse(
                rationale=self._job_pb.DispatchRationale(
                    version=kernel_response.get("version", ""),
                    policy_version=kernel_response.get("policy_version", ""),
                    reason_codes=list(kernel_response.get("reason_codes", [])),
                    selected_backend=kernel_response.get("selected_backend", ""),
                    selected_queue=kernel_response.get("selected_queue", ""),
                    attributes={k: str(v) for k, v in dict(kernel_response.get("attributes", {})).items()},
                    timeline_ref=kernel_response.get("timeline_ref", ""),
                    logs_ref=kernel_response.get("logs_ref", ""),
                    trace_id=kernel_response.get("trace_id", ""),
                    trace_ref=kernel_response.get("trace_ref", ""),
                )
            )
            log_request_end("JobService.GetDispatchRationale", rc)
            return resp

        abort_with_error_info(
            context,
            grpc_code=grpc.StatusCode.NOT_FOUND,
            message=f"job_id not found: {request.job_id}",
            reason="EIGEN_PUBLIC_EXPLAIN_DECISION_NOT_FOUND",
            domain="eigen.api.v1.explain",
            metadata={"job_id": request.job_id},
        )

    async def _collect_kernel_updates(self, *, job_id: str, last_event_seq: int, envelope: NormalizedPublicEnvelope) -> list[dict]:
        updates: list[dict] = []
        async for update in self._kernel_client.stream_job_updates(job_id, last_event_seq, self._public_envelope_dict(envelope)):
            updates.append(update)
        return updates


class DeviceService:
    """Implementation of eigen.api.v1.DeviceService."""

    def __init__(self, dev_pb, types_pb):
        self._dev_pb = dev_pb
        self._types_pb = types_pb
        self._reservation_store_path = Path(
            os.getenv("SYSTEM_API_RESERVATION_STORE_PATH", "/tmp/eigen-system-api-reservations.json")
        )
        self._reservation_qfs_root = os.getenv("SYSTEM_API_RESERVATION_QFS_ROOT", "qfs://reservations")
        self._reservations: dict[str, _ReservationRecord] = {}
        self._lock = threading.RLock()
        self._load_reservation_records()

    def _reservation_binding_key(
        self,
        *,
        device_id: str,
        purpose: str,
        owner_subject: str,
        owner_tenant: str,
        owner_project: str,
    ) -> str:
        payload = {
            "device_id": device_id,
            "purpose": purpose,
            "owner_subject": owner_subject,
            "owner_tenant": owner_tenant,
            "owner_project": owner_project,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _reservation_request_hash(
        self,
        *,
        device_id: str,
        purpose: str,
        ttl_seconds: int,
        owner_subject: str,
        owner_tenant: str,
        owner_project: str,
    ) -> str:
        payload = {
            "device_id": device_id,
            "purpose": purpose,
            "ttl_seconds": ttl_seconds,
            "owner_subject": owner_subject,
            "owner_tenant": owner_tenant,
            "owner_project": owner_project,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _reservation_id_for(self, binding_key: str) -> str:
        return f"rsv_{binding_key[:12]}"

    def _reservation_artifact_ref(self, reservation_id: str) -> str:
        return f"{self._reservation_qfs_root}/{reservation_id}/reservation.json"

    def _write_reservation_artifact(self, record: _ReservationRecord) -> None:
        QFS_STORE.atomic_write_bytes(
            self._reservation_artifact_ref(record.reservation_id),
            json.dumps(
                {
                    "version": "1.0.0",
                    "reservation": record.to_json(),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )

    def _load_reservation_records(self) -> None:
        if not self._reservation_store_path.exists():
            return
        try:
            payload = json.loads(self._reservation_store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        records = payload.get("reservations", {}) if isinstance(payload, dict) else {}
        if not isinstance(records, dict):
            return
        for raw in records.values():
            if not isinstance(raw, dict):
                continue
            try:
                record = _ReservationRecord.from_json(raw)
            except (KeyError, TypeError, ValueError):
                continue
            self._reservations[record.reservation_id] = record
        self._sweep_expired_reservations(time.time())
        self._persist_reservation_records()

    def _persist_reservation_records(self) -> None:
        payload = {
            "version": "1.0.0",
            "reservations": {
                reservation_id: record.to_json()
                for reservation_id, record in sorted(self._reservations.items())
            },
        }
        self._reservation_store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._reservation_store_path.with_suffix(self._reservation_store_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self._reservation_store_path)

    def _sweep_expired_reservations(self, now_unix: float) -> None:
        changed = False
        for record in self._reservations.values():
            if record.state == "ACTIVE" and now_unix >= record.expires_at_unix:
                record.state = "EXPIRED"
                record.updated_at_unix = now_unix
                changed = True
        if changed:
            self._persist_reservation_records()

    def ListDevices(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="DeviceService.ListDevices")
        enforce_authz(context, required_permission="devices:list")
        rc = new_request_context(context)
        log_request_start("DeviceService.ListDevices", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.ListDevices")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

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
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="DeviceService.GetDeviceDetails")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

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
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="DeviceService.GetDeviceStatus")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

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
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="DeviceService.ReserveDevice")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_reserve_device(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        owner_subject, _, owner_tenant = auth_context(context)
        owner_project = envelope.project_id or "project-default"
        purpose = (request.purpose or "unspecified").strip() or "unspecified"
        now_unix = time.time()
        ttl_seconds = int(request.ttl_seconds)
        device_id = request.device_id.strip()
        binding_key = self._reservation_binding_key(
            device_id=device_id,
            purpose=purpose,
            owner_subject=owner_subject,
            owner_tenant=owner_tenant or "tenant-default",
            owner_project=owner_project,
        )
        request_hash = self._reservation_request_hash(
            device_id=device_id,
            purpose=purpose,
            ttl_seconds=ttl_seconds,
            owner_subject=owner_subject,
            owner_tenant=owner_tenant or "tenant-default",
            owner_project=owner_project,
        )

        with self._lock:
            self._sweep_expired_reservations(now_unix)
            active = next(
                (
                    record
                    for record in self._reservations.values()
                    if record.device_id == device_id and record.state == "ACTIVE"
                ),
                None,
            )

            if active is not None and active.reservation_id != self._reservation_id_for(binding_key):
                abort_public(
                    context,
                    PublicErrorSpec(
                        grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                        message="device already has an active reservation",
                        reason="EIGEN_PUBLIC_RESERVATION_CONFLICT",
                        retryable=False,
                        metadata={
                            "device_id": device_id,
                            "active_reservation_id": active.reservation_id,
                            "active_purpose": active.purpose,
                        },
                        precondition_type="RESERVATION_CONFLICT",
                        precondition_subject=device_id,
                        detail="Release or let the active reservation expire before reserving the device again.",
                    ),
                )

            reservation_id = self._reservation_id_for(binding_key)
            record = self._reservations.get(reservation_id)
            if record is None:
                record = _ReservationRecord(
                    reservation_id=reservation_id,
                    device_id=device_id,
                    purpose=purpose,
                    owner_subject=owner_subject,
                    owner_tenant=owner_tenant or "tenant-default",
                    owner_project=owner_project,
                    request_hash=request_hash,
                    ttl_seconds=ttl_seconds,
                    state="ACTIVE",
                    created_at_unix=now_unix,
                    updated_at_unix=now_unix,
                    expires_at_unix=now_unix + ttl_seconds,
                )
                self._reservations[reservation_id] = record
            else:
                record.device_id = device_id
                record.purpose = purpose
                record.owner_subject = owner_subject
                record.owner_tenant = owner_tenant or "tenant-default"
                record.owner_project = owner_project
                record.request_hash = request_hash
                record.ttl_seconds = ttl_seconds
                record.state = "ACTIVE"
                record.updated_at_unix = now_unix
                record.expires_at_unix = now_unix + ttl_seconds

            self._persist_reservation_records()
            self._write_reservation_artifact(record)

        resp = self._dev_pb.ReserveDeviceResponse(
            reservation_id=record.reservation_id,
            expires_at=_ts_from_unix(record.expires_at_unix),
        )

        log_request_end("DeviceService.ReserveDevice", rc)
        return resp
