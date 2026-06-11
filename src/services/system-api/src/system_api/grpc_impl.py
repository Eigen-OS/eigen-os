"""gRPC service implementations for System API (MVP skeleton)."""

from __future__ import annotations

import json
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
import pyarrow as pa
import pyarrow.parquet as pq

from .errors import FieldViolation, PublicErrorSpec, abort_invalid_argument, abort_payload_limit, abort_public, abort_with_error_info
from .lifecycle import apply_signal
from .scheduling import resolve_dag
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
from .knowledge_base import KnowledgeBaseService, KnowledgeBaseUnavailable
from .qfs_store import QFS_STORE
from .security import auth_context, enforce_authn, enforce_authz, enforce_sandbox_policy, security_context
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
    return NormalizedPublicEnvelope(
        contract_version=contract_version,
        request_id=request_id,
        idempotency_key=(
            getattr(envelope, "idempotency_key", "")
            or md.get("x-idempotency-key", "")
            or md.get("x-eigen-idempotency-key", "")
        ).strip(),
        traceparent=(getattr(envelope, "traceparent", "") or md.get("traceparent", "")).strip(),
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

    def __init__(self, job_pb, types_pb, kb_service: KnowledgeBaseService | None = None):
        self._job_pb = job_pb
        self._types_pb = types_pb
        self._reservation_store_path = Path(
            os.getenv("SYSTEM_API_RESERVATION_STORE_PATH", "/tmp/eigen-system-api-reservations.json")
        )
        self._reservation_qfs_root = os.getenv("SYSTEM_API_RESERVATION_QFS_ROOT", "qfs://reservations")
        self._reservations: dict[str, _ReservationRecord] = {}
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
        self._kb_service = kb_service
        self._jobs: dict[str, _JobRecord] = {}
        self._idempotency: dict[str, _IdempotencyRecord] = {}
        self._idempotency_ttl_sec = max(float(os.getenv("SYSTEM_API_IDEMPOTENCY_TTL_SECONDS", "86400")), 1.0)
        self._idempotency_store_path = Path(
            os.getenv("SYSTEM_API_IDEMPOTENCY_STORE_PATH", "/tmp/eigen-system-api-idempotency.json")
        )
        self._lock = threading.RLock()
        self._load_idempotency_records()
        self._batch_mode_enabled = os.getenv("EIGEN_BATCH_MODE", "1").strip() not in {"0", "false", "off"}
        self._batch_size = max(int(os.getenv("EIGEN_BATCH_SIZE", "4")), 2)
        self._batch_wait_window_sec = max(float(os.getenv("EIGEN_BATCH_WAIT_WINDOW_SEC", "0.2")), 0.0)
        self._batch_dispatch_gap_sec = max(float(os.getenv("EIGEN_BATCH_DISPATCH_GAP_SEC", "0.15")), 0.0)
        self._batch_inflight_limit = max(int(os.getenv("EIGEN_BATCH_INFLIGHT_LIMIT", "64")), self._batch_size)
        self._quota_per_target = max(int(os.getenv("EIGEN_SCHED_QUOTA_PER_TARGET", "8")), 1)
        self._starvation_threshold_sec = max(float(os.getenv("EIGEN_SCHED_STARVATION_SEC", "2.0")), 0.0)
        self._dispatch_slot_seq = 0

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

    def _mk_vqe_updates(self, *, job_id: str, trace_id: str | None, max_iters: int, topology: dict[str, str]) -> list:
        updates = [
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
                progress=0.2,
                message="compiling",
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
                    topology=topology,
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
                topology=topology,
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
                    topology=record.topology,
                )
            elif record.should_fail:
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
        sandbox_profile = metadata.get("sandbox_profile", "default").strip() or "default"
        sec = security_context(context=_DummyContext(metadata), method_name="JobService.SubmitJob") if False else None
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
            default_runtime_sec = 1.0
        try:
            run_duration_sec = max(float(metadata.get("simulate_runtime_sec", str(default_runtime_sec)) or default_runtime_sec), 0.0)
        except ValueError:
            run_duration_sec = default_runtime_sec

        results_metadata = {
            "version": "0.3",
            "backend": request.target or "sim:local",
            "qfs_compiled_aqo": f"qfs://jobs/{job_id}/compiled/circuit.aqo.json",
            "security_subject": owner_subject,
            "security_tenant": owner_tenant,
            "security_project": owner_project,
            "security_sandbox_profile": sandbox_profile,
            "security_policy_version": "1.0.0",
            "security_service_identity": "system-api",
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
                    "attributes": {"batch_mode_enabled": str(self._batch_mode_enabled).lower()},
                    "attributes": {
                        "batch_mode_enabled": str(self._batch_mode_enabled).lower(),
                        "worker_id": topology["worker_id"],
                    },
                },
                {
                    "step": 3,
                    "event": "BACKEND_SELECTED",
                    "outcome": request.target or "sim:local",
                    "attributes": {"reason_codes": "WEIGHTED_FAIRNESS,DEVICE_SCORE"},
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
            max_iters=max_iters,
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
        self._provision_temporary_artifacts(record)
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
        subject, roles, tenant = auth_context(context)
        if "*" in roles or "admin" in roles:
            return
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
        enforce_authn(context, method_name="JobService.SubmitJob")
        enforce_authz(context, required_permission="jobs:submit")
        rc = new_request_context(context)

        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.SubmitJob")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity
        rc.sandbox_profile = sec.sandbox_profile
        enforce_sandbox_policy(context, sandbox_profile=sec.sandbox_profile or "default")
        log_request_start("JobService.SubmitJob", rc)

        violations = validate_submit_job(request)
        if violations:
            if any("exceeds max allowed size" in violation.description for violation in violations):
                record_submit_job_outcome("limit")
                _record_submit_public_marker(envelope, "limit")
                abort_payload_limit(context, "payload limit exceeded", violations)
                _record_submit_public_marker(envelope, "error")
            abort_invalid_argument(context, "validation failed", violations)

        dag_nodes = sorted({request.name, *list(request.dependencies)})
        dag = resolve_dag(dag_nodes, {request.name: list(request.dependencies)})
        if not dag.ok:
            _record_submit_public_marker(envelope, "error")
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.INVALID_ARGUMENT,
                    message="dag resolution failed",
                    reason="EIGEN_PUBLIC_VALIDATION_FAILED",
                    retryable=False,
                    metadata={"reason_code": dag.reason_code},
                    violations=[
                        FieldViolation(
                            field="dependencies",
                            description=f"{dag.reason_code}: {dag.detail}",
                        )
                    ],
                ),
            )

        idem_key = self._idempotency_key(request, context, envelope)
        request_fingerprint = self._request_fingerprint(request, envelope)

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
                    existing = self._jobs.get(previous.job_id)
                    if existing is None:
                        now = _ts_now()
                        rc.job_id = previous.job_id
                        record_submit_job_outcome("replayed")
                        _record_submit_public_marker(envelope, "replayed")
                        log_request_end("JobService.SubmitJob", rc)
                        return self._job_pb.SubmitJobResponse(
                            job_id=previous.job_id,
                            status=self._types_pb.JobStatus(
                                job_id=previous.job_id,
                                state=self._types_pb.JOB_STATE_PENDING,
                                stage="QUEUED",
                                progress=0.0,
                                message="accepted (idempotent replay from persisted request record)",
                                created_at=now,
                                updated_at=now,
                            ),
                        )
                    self._advance_job(existing)
                    latest = existing.updates[-1]
                    rc.job_id = existing.job_id
                    record_submit_job_outcome("replayed")
                    _record_submit_public_marker(envelope, "replayed")
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
                            topology=self._mk_topology_pb(existing.topology),
                        ),
                    )

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            rc.job_id = job_id
            now = _ts_now()
            trace_id = rc.trace_id or request.metadata.get("trace_id", "").strip() or None
            owner_subject, _, _owner_tenant = auth_context(context)
            record = self._build_job_record(
                request,
                job_id=job_id,
                created_at=now,
                trace_id=trace_id,
                owner_subject=owner_subject,
                owner_tenant=envelope.tenant_id,
                owner_project=envelope.project_id,
            )
            self._jobs[job_id] = record
            self._assign_scheduler_slot(record)
            if idem_key:
                self._remember_idempotency_record(
                    key=idem_key,
                    job_id=job_id,
                    request_fingerprint=request_fingerprint,
                    envelope=envelope,
                )
            record_submit_job_outcome("accepted")
            _record_submit_public_marker(envelope, "accepted")

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
                topology=self._mk_topology_pb(record.topology),
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

        with self._lock:
            record = self._jobs.get(request.job_id)

        if record is None:
            _abort_job_not_found(context, request.job_id)
        with self._lock:
            self._enforce_job_access(context=context, record=record)
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
                topology=self._mk_topology_pb(record.topology),
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

        accepted = False
        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                _abort_job_not_found(context, request.job_id)
            self._enforce_job_access(context=context, record=record)
            self._advance_job(record)
            terminal_values = {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
            decision = apply_signal(
                current_stage=record.updates[-1].stage,
                signal="cancel",
                already_requested=record.cancel_requested,
            )
            if decision.accepted and record.updates[-1].state not in terminal_values:
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

        start_after_seq = int(request.last_event_seq)
        terminal_values = {getattr(self._types_pb, name) for name in TERMINAL_JOB_STATES}
        while True:
            with self._lock:
                record = self._jobs.get(request.job_id)
                if record is None:
                    _abort_job_not_found(context, request.job_id)
                self._enforce_job_access(context=context, record=record)
                self._advance_job(record)
                selected_updates = list(record.updates)
                done = selected_updates[-1].state in terminal_values

            for update in selected_updates:
                event_seq = int(update.event_seq)
                if event_seq <= start_after_seq:
                    continue
                start_after_seq = event_seq
                yield self._job_pb.StreamJobUpdatesResponse(update=update)

            if done:
                break
            if not context.is_active():
                break
            time.sleep(0.01)

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

        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is not None:
                self._enforce_job_access(context=context, record=record)
                self._advance_job(record)

        if record is None:
            _abort_job_not_found(context, request.job_id)
        current_state = record.updates[-1].state
        if current_state in {
            self._types_pb.JOB_STATE_PENDING,
            self._types_pb.JOB_STATE_COMPILING,
            self._types_pb.JOB_STATE_RUNNING,
        }:
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                    message="results are not ready yet",
                    reason="EIGEN_PUBLIC_RESULTS_NOT_READY",
                    retryable=True,
                    metadata={"current_state": self._types_pb.JobState.Name(current_state)},
                    retry_delay_seconds=1,
                    precondition_type="JOB_LIFECYCLE",
                    precondition_subject=request.job_id,
                    detail="Poll GetJobStatus until the job reaches a terminal state before reading results.",
                ),
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

        with self._lock:
            record = self._jobs.get(request.job_id)
            if record is None:
                abort_with_error_info(
                    context,
                    grpc_code=grpc.StatusCode.NOT_FOUND,
                    message=f"job_id not found: {request.job_id}",
                    reason="EIGEN_PUBLIC_EXPLAIN_DECISION_NOT_FOUND",
                    domain="eigen.api.v1.explain",
                    metadata={"job_id": request.job_id},
                )
            self._enforce_job_access(context=context, record=record)
            self._advance_job(record)
            rationale = dict(record.dispatch_rationale)
            attrs = dict(rationale["attributes"])
            attrs["queue_delay_ms"] = str(max(int(float(record.queue_delay_sec) * 1000), 0))
            attrs["dispatch_latency_ms"] = attrs.get("dispatch_latency_ms", "150")
            attrs["execution_time_ms"] = attrs.get("execution_time_ms", str(max(int(record.run_duration_sec * 1000), 0)))
            if "decision_lineage" not in attrs:
                attrs["decision_lineage"] = json.dumps(
                    rationale.get("lineage", []),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            rationale["attributes"] = attrs

        decision_payload = {
            "contract_version": PUBLIC_API_CONTRACT_VERSION,
            "record_id": f"decision:{record.job_id}",
            "job_id": record.job_id,
            "trace_id": str(rationale["trace_id"]),
            "request_id": rc.request_id,
            "tenant_id": record.owner_tenant,
            "project_id": record.owner_project,
            "component": "runtime",
            "model_version": str(rationale["policy_version"]),
            "policy_branch": str(rationale["attributes"].get("policy_branch", "baseline")),
            "selected_action": str(rationale["selected_backend"]),
            "fallback_used": any(str(code).endswith("FALLBACK") for code in rationale["reason_codes"]),
            "feature_snapshot": {
                "queue_delay_ms": str(max(int(float(record.queue_delay_sec) * 1000), 0)),
                "dispatch_latency_ms": str(rationale["attributes"].get("dispatch_latency_ms", "150")),
                "execution_time_ms": str(max(int(record.run_duration_sec * 1000), 0)),
                "selected_queue": str(rationale["selected_queue"]),
                "selected_backend": str(rationale["selected_backend"]),
            },
            "provenance": {
                "runtime_ref": str(rationale["timeline_ref"]),
                "checkpoint_ref": str(rationale["logs_ref"]),
                "compiler_ref": str(rationale["attributes"].get("compiler_ref", "")),
                "optimizer_ref": str(rationale["attributes"].get("optimizer_ref", "")),
            },
            "replay_bundle_ref": str(rationale["attributes"].get("replay_bundle_ref", f"qfs://jobs/{record.job_id}/kb/replay_bundle.json")),
            "request_hash": str(rationale["attributes"].get("request_hash", "")),
        }
        if self._kb_service is not None:
            try:
                self._kb_service.ingest_runtime_decision(decision_payload)
            except KnowledgeBaseUnavailable:
                record_kb_fallback("storage_unavailable")
            except Exception:
                record_kb_fallback("ingest_failed")

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
