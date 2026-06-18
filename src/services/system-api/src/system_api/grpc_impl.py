"""gRPC service implementations for System API (MVP skeleton)."""
from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .security import _AUTH_ALLOW_ALL

# ----------------------------------------------------------------------

logger = logging.getLogger(__name__)


from .errors import FieldViolation, PublicErrorSpec, abort_invalid_argument, abort_payload_limit, abort_public, abort_with_error_info
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


TERMINAL_JOB_STATES = {"JOB_STATE_DONE", "JOB_STATE_ERROR", "JOB_STATE_CANCELLED", "JOB_STATE_TIMEOUT"}
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
    topology: dict[str, str]


def _stable_request_id(request) -> str:
    raw = request.SerializeToString(deterministic=True)
    return f"req_{sha256(raw).hexdigest()[:24]}"


def _synthetic_traceparent(seed: str) -> str:
    digest = sha256(seed.encode("utf-8")).hexdigest()
    trace_id = digest[:32]
    span_id = digest[32:48]
    return f"00-{trace_id}-{span_id}-01"


def _normalized_topology(md: dict[str, str]) -> dict[str, str]:
    attempt_raw = md.get("topology_attempt", "1")
    try:
        attempt = int(attempt_raw)
    except (TypeError, ValueError):
        attempt = 1
    return {
        "contract_version": TOPOLOGY_CONTRACT_VERSION,
        "lineage_version": TOPOLOGY_LINEAGE_VERSION,
        "cluster_id": md.get("topology_cluster_id", "cluster-local"),
        "worker_id": md.get("topology_worker_id", "worker-local"),
        "partition_id": md.get("topology_partition_id", "partition-0"),
        "attempt": str(max(attempt, 1)),
    }


def _public_envelope(request, context: grpc.ServicerContext) -> NormalizedPublicEnvelope:

    envelope = getattr(request, "envelope", None)
    md = _metadata(context)
    request_md = {str(k).lower(): str(v) for k, v in dict(getattr(request, "metadata", {})).items()}
    combined_md = {**md, **request_md}
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
    topology = _normalized_topology(combined_md)
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
        topology=topology,
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


# -----------------------------------------------------------------------------
# Thin ingress layer
# -----------------------------------------------------------------------------

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


class JobService:
    """Thin public ingress facade for eigen.api.v1.JobService."""

    def __init__(self, job_pb, types_pb, kernel_client: KernelGatewayClient | None = None):
        self._job_pb = job_pb
        self._types_pb = types_pb
        self._kernel_client = kernel_client or KernelGatewayClient()
        self._lock = threading.RLock()
        self._idempotency_store_path = Path(
            os.getenv("SYSTEM_API_IDEMPOTENCY_STORE_PATH", "/tmp/eigen-system-api-idempotency.json")
        )
        self._idempotency_ttl_sec = max(float(os.getenv("SYSTEM_API_IDEMPOTENCY_TTL_SECONDS", "86400")), 1.0)
        self._idempotency: dict[str, _IdempotencyRecord] = {}
        self._load_idempotency_records()

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    @staticmethod
    def _default_program_payload() -> tuple[bytes, str]:
        return (
            b"from eigen_lang import hybrid_program\n\n@hybrid_program()\ndef main():\n    return 0\n",
            "eigen_lang_source",
        )

    @staticmethod
    def _build_program_payload(request) -> tuple[bytes, str]:
        program_kind = request.WhichOneof("program")
        if program_kind == "eigen_lang":
            return bytes(request.eigen_lang.source), "eigen_lang_source"
        if program_kind == "qasm":
            return bytes(request.qasm.source), "qasm_text"
        if program_kind == "aqo_ref":
            ref = str(getattr(request.aqo_ref, "qfs_ref", "") or "")
            return ref.encode("utf-8"), "aqo_ref"
        program_bytes, program_format = JobService._default_program_payload()
        return program_bytes, program_format


    def _kernel_call(self, context: grpc.ServicerContext, func, *, not_found_reason: str | None = None, **kwargs):
        try:
            return self._run(func(**kwargs))
        except grpc.RpcError as exc:
            code = exc.code() if hasattr(exc, "code") else grpc.StatusCode.INTERNAL
            details = exc.details() if hasattr(exc, "details") else "kernel gateway error"
            if not_found_reason and code == grpc.StatusCode.NOT_FOUND:
                abort_public(
                    context,
                    PublicErrorSpec(
                        grpc_code=grpc.StatusCode.NOT_FOUND,
                        message=details,
                        reason=not_found_reason,
                        retryable=False,
                        detail=details,
                    ),
                )
            context.abort(code, details)

    def _retry_dispatch_rationale(self, request, context: grpc.ServicerContext, envelope: NormalizedPublicEnvelope):
        deadline = time.time() + float(os.getenv("SYSTEM_API_DISPATCH_RATIONALE_WAIT_SECONDS", "30"))
        last_exc: grpc.RpcError | None = None
        while True:
            try:
                return self._run(
                    self._kernel_client.get_dispatch_rationale(
                        job_id=request.job_id,
                        public_envelope=self._public_envelope_dict(envelope),
                    )
                )
            except grpc.RpcError as exc:
                last_exc = exc
                code = exc.code() if hasattr(exc, "code") else grpc.StatusCode.INTERNAL
                details = exc.details() if hasattr(exc, "details") else "kernel gateway error"
                if code == grpc.StatusCode.NOT_FOUND:
                    abort_public(
                        context,
                        PublicErrorSpec(
                            grpc_code=grpc.StatusCode.NOT_FOUND,
                            message=details,
                            reason="EIGEN_PUBLIC_EXPLAIN_DECISION_NOT_FOUND",
                            retryable=False,
                            detail=details,
                        ),
                    )
                if code != grpc.StatusCode.FAILED_PRECONDITION or time.time() >= deadline:
                    context.abort(code, details)
                try:
                    status = self._run(
                        self._kernel_client.get_job_status(
                            job_id=request.job_id,
                            public_envelope=self._public_envelope_dict(envelope),
                        )
                    )
                except grpc.RpcError:
                    time.sleep(0.1)
                    continue
                if status.get("state") in {"TASK_STATE_DONE", "TASK_STATE_ERROR", "TASK_STATE_CANCELLED", "TASK_STATE_TIMEOUT"}:
                    time.sleep(0.05)
                else:
                    time.sleep(0.1)
        if last_exc is not None:
            raise last_exc

    @staticmethod
    def _normalized_name(request) -> str:
        return (getattr(request, "name", "") or "job").strip() or "job"

    @staticmethod
    def _normalized_target(request) -> str:
        return (getattr(request, "target", "") or "sim:local").strip() or "sim:local"

    def _public_envelope_dict(self, envelope: NormalizedPublicEnvelope) -> dict[str, object]:
        return {
            "contract_version": envelope.contract_version,
            "request_id": envelope.request_id,
            "idempotency_key": envelope.idempotency_key,
            "traceparent": envelope.traceparent,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "client_version": envelope.client_version,
            "trace_id": trace_id_from_traceparent(envelope.traceparent) if envelope.traceparent else "",
            "topology": dict(envelope.topology),
        }

    def _kernel_state_to_public_enum(self, state: str):
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
        if state in mapping:
            return mapping[state]
        if state.startswith("JOB_STATE_"):
            return getattr(self._types_pb, state, self._types_pb.JOB_STATE_PENDING)
        return getattr(self._types_pb, f"JOB_STATE_{state}", self._types_pb.JOB_STATE_PENDING)

    def _mk_topology_pb(self, topology: dict[str, object] | None):
        if not topology:
            return self._types_pb.TopologyEnvelope(
                contract_version=TOPOLOGY_CONTRACT_VERSION,
                lineage_version=TOPOLOGY_LINEAGE_VERSION,
                cluster_id="cluster-local",
                worker_id="worker-local",
                partition_id="partition-0",
                attempt=1,
            )
        return self._types_pb.TopologyEnvelope(
            contract_version=str(topology.get("contract_version", TOPOLOGY_CONTRACT_VERSION)),
            lineage_version=str(topology.get("lineage_version", TOPOLOGY_LINEAGE_VERSION)),
            cluster_id=str(topology.get("cluster_id", "cluster-local")),
            worker_id=str(topology.get("worker_id", "worker-local")),
            partition_id=str(topology.get("partition_id", "partition-0")),
            attempt=int(topology.get("attempt", 1) or 1),
        )


    def _status_from_kernel(self, job_id: str, kernel_response: dict):
        return self._types_pb.JobStatus(
            job_id=job_id,
            state=self._kernel_state_to_public_enum(kernel_response.get("state", "TASK_STATE_PENDING")),
            stage=kernel_response.get("stage", ""),
            progress=float(kernel_response.get("progress", 0.0)),
            message=kernel_response.get("message", ""),
            created_at=kernel_response.get("created_at") or _ts_now(),
            updated_at=kernel_response.get("updated_at") or kernel_response.get("created_at") or _ts_now(),
            error_code=kernel_response.get("error_code", ""),
            error_summary=kernel_response.get("error_summary", ""),
            error_details_ref=kernel_response.get("error_details_ref", ""),
            topology=self._mk_topology_pb(kernel_response.get("topology")),
        )
    

    def _update_from_kernel(self, job_id: str, kernel_update: dict):
        return self._types_pb.JobUpdate(
            job_id=job_id,
            state=self._kernel_state_to_public_enum(kernel_update.get("state", "TASK_STATE_PENDING")),
            stage=kernel_update.get("stage", ""),
            progress=float(kernel_update.get("progress", 0.0)),
            message=kernel_update.get("message", ""),
            event_seq=int(kernel_update.get("event_seq", 0)),
            timestamp=kernel_update.get("timestamp") or _ts_now(),
            topology=self._mk_topology_pb(kernel_update.get("topology")),
        )

    def _rationale_from_kernel(self, kernel_rationale: dict):
        attributes = dict(kernel_rationale.get("attributes", {}))
        topology = dict(kernel_rationale.get("topology", {}))
        if topology:
            attributes.setdefault(
                "topology_contract_version",
                str(topology.get("contract_version", TOPOLOGY_CONTRACT_VERSION)),
            )
        return self._job_pb.DispatchRationale(
            version=kernel_rationale.get("version", ""),
            policy_version=kernel_rationale.get("policy_version", ""),
            reason_codes=list(kernel_rationale.get("reason_codes", [])),
            selected_backend=kernel_rationale.get("selected_backend", ""),
            selected_queue=kernel_rationale.get("selected_queue", ""),
            attributes=attributes,
            timeline_ref=kernel_rationale.get("timeline_ref", ""),
            logs_ref=kernel_rationale.get("logs_ref", ""),
            trace_id=kernel_rationale.get("trace_id", ""),
            trace_ref=kernel_rationale.get("trace_ref", ""),
        )

    def _load_idempotency_records(self) -> None:
        if not self._idempotency_store_path.exists():
            return
        try:
            payload = json.loads(self._idempotency_store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        records = payload.get("records", {}) if isinstance(payload, dict) else {}
        if not isinstance(records, dict):
            return
        now = time.time()
        for idem_key, raw in records.items():
            if not isinstance(raw, dict):
                continue
            try:
                record = _IdempotencyRecord.from_json(raw)
            except (KeyError, TypeError, ValueError):
                continue
            if record.expires_at_unix <= now:
                continue
            self._idempotency[str(idem_key)] = record

    def _persist_idempotency_records(self) -> None:
        payload = {
            "version": "1.0.0",
            "records": {key: record.to_json() for key, record in sorted(self._idempotency.items())},
         }
        self._idempotency_store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._idempotency_store_path.with_suffix(self._idempotency_store_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        tmp.replace(self._idempotency_store_path)


    def _sweep_expired_idempotency(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        changed = False
        for key, record in list(self._idempotency.items()):
            if record.expires_at_unix <= now:
                self._idempotency.pop(key, None)
                changed = True
        if changed:
            self._persist_idempotency_records()

    def _idempotency_key(self, request, envelope: NormalizedPublicEnvelope) -> tuple[str, bool]:
        metadata = dict(getattr(request, "metadata", {}))
        explicit = (
            envelope.idempotency_key
            or str(metadata.get("idempotency_key", "") or "").strip()
            or str(metadata.get("client_request_id", "") or "").strip()
            or str(metadata.get("x-idempotency-key", "") or "").strip()
        )
        if explicit:
            return explicit, True
        return self._request_fingerprint(request, envelope), False

    def _request_fingerprint(self, request, envelope: NormalizedPublicEnvelope) -> str:
        metadata = {str(k): str(v) for k, v in sorted(dict(getattr(request, "metadata", {})).items())}
        compiler_options = {str(k): str(v) for k, v in sorted(dict(getattr(request, "compiler_options", {})).items())}
        program_kind = request.WhichOneof("program")
        if program_kind == "eigen_lang":
            program_digest = sha256(bytes(request.eigen_lang.source)).hexdigest()
        elif program_kind == "qasm":
            program_digest = sha256(bytes(request.qasm.source)).hexdigest()
        elif program_kind == "aqo_ref":
            ref = str(getattr(request.aqo_ref, "qfs_ref", "") or "")
            program_kind = "aqo_ref"
            program_digest = sha256(ref.encode("utf-8")).hexdigest()
        else:
            program_bytes, _ = self._default_program_payload()
            program_kind = "eigen_lang"
            program_digest = sha256(program_bytes).hexdigest()

        payload = {
            "name": self._normalized_name(request),
            "target": self._normalized_target(request),
            "program_kind": program_kind,
            "program_digest": program_digest,
            "metadata": metadata,
            "compiler_options": compiler_options,
            "contract_version": envelope.contract_version,
            "request_id": envelope.request_id,
            "idempotency_key": envelope.idempotency_key,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "client_version": envelope.client_version,
            "traceparent": envelope.traceparent,
            "trace_id": trace_id_from_traceparent(envelope.traceparent) if envelope.traceparent else "",
            "topology": dict(envelope.topology),
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def SubmitJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.SubmitJob")
        enforce_authz(context, required_permission="jobs:submit")
        rc = new_request_context(context)
        log_request_start("JobService.SubmitJob", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.SubmitJob")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity

        violations = validate_submit_job(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        name = self._normalized_name(request)
        target = self._normalized_target(request)

        program, program_format = self._build_program_payload(request)
        job_idempotency_key, explicit_key = self._idempotency_key(request, envelope)
        request_fingerprint = self._request_fingerprint(request, envelope)

        with self._lock:
            self._sweep_expired_idempotency()
            existing = self._idempotency.get(job_idempotency_key)
            if existing is not None:
                if existing.request_fingerprint != request_fingerprint:
                    abort_public(
                        context,
                        PublicErrorSpec(
                            grpc_code=grpc.StatusCode.FAILED_PRECONDITION,
                            message="idempotency key already used with different payload",
                            reason="EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT",
                            retryable=False,
                            metadata={"idempotency_key": job_idempotency_key, "job_id": existing.job_id},
                            precondition_type="IDEMPOTENCY_CONFLICT",
                            precondition_subject=job_idempotency_key,
                            detail="SubmitJob idempotency key cannot be reused with a different payload.",
                        ),
                    )
                replayed = True
                job_id = existing.job_id
            else:
                replayed = False
                job_id = ""

        if replayed:
            status = self._kernel_call(
                context,
                self._kernel_client.get_job_status,
                job_id=job_id,
                public_envelope=self._public_envelope_dict(envelope),
                not_found_reason="EIGEN_PUBLIC_JOB_NOT_FOUND",
            )
            resp_status = self._status_from_kernel(job_id, status)
            resp_status.message = "accepted (idempotent replay from persisted request record)"
            record_public_api_contract_marker(envelope.contract_version, "replayed")
            record_submit_job_outcome("replayed")
            log_request_end("JobService.SubmitJob", rc)
            return self._job_pb.SubmitJobResponse(job_id=job_id, status=resp_status)

        kernel_response = self._kernel_call(
            context,
            self._kernel_client.enqueue_job,
            name=name,
            program=program,
            program_format=program_format,
            target=target,
            priority=int(getattr(request, "priority", 0) or 0),
            compiler_options=dict(getattr(request, "compiler_options", {})),
            metadata_kvs=dict(getattr(request, "metadata", {})),
            public_envelope=self._public_envelope_dict(envelope),
            workload=getattr(request, "workload", None),
        )
        job_id = kernel_response["job_id"]
        status = self._types_pb.JobStatus(
            job_id=job_id,
            state=self._kernel_state_to_public_enum(kernel_response.get("state", "TASK_STATE_PENDING")),
            message=kernel_response.get("message", "accepted"),
            created_at=kernel_response.get("created_at") or _ts_now(),
            updated_at=kernel_response.get("updated_at") or kernel_response.get("created_at") or _ts_now(),
            topology=self._mk_topology_pb(kernel_response.get("topology")),
        )
        resp = self._job_pb.SubmitJobResponse(job_id=job_id, status=status)
        with self._lock:
            self._idempotency[job_idempotency_key] = _IdempotencyRecord(
                job_id=job_id,
                request_fingerprint=request_fingerprint,
                expires_at_unix=time.time() + self._idempotency_ttl_sec,
                tenant_id=envelope.tenant_id,
                project_id=envelope.project_id,
            )
            self._persist_idempotency_records()
        record_public_api_contract_marker(envelope.contract_version, "accepted")
        record_submit_job_outcome("accepted")
        log_request_end("JobService.SubmitJob", rc)
        return resp

    def GetJobStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobStatus")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
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

        kernel_response = self._kernel_call(
            context,
            self._kernel_client.get_job_status,
            job_id=request.job_id,
            public_envelope=self._public_envelope_dict(envelope),
            not_found_reason="EIGEN_PUBLIC_JOB_NOT_FOUND",
        )
        resp = self._job_pb.GetJobStatusResponse(
            status=self._status_from_kernel(request.job_id, kernel_response)
        )
        log_request_end("JobService.GetJobStatus", rc)
        return resp

    def CancelJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.CancelJob")
        enforce_authz(context, required_permission="jobs:submit")
        rc = new_request_context(context)
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
        accepted = self._kernel_call(
            context,
            self._kernel_client.cancel_job,
            job_id=request.job_id,
            public_envelope=self._public_envelope_dict(envelope),
            not_found_reason="EIGEN_PUBLIC_JOB_NOT_FOUND",
        )
        log_request_end("JobService.CancelJob", rc)
        return self._job_pb.CancelJobResponse(accepted=bool(accepted.get("accepted", False)))

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.StreamJobUpdates")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
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

        async def _collect():
            items = []
            async for kernel_update in self._kernel_client.stream_job_updates(
                job_id=request.job_id,
                last_event_seq=int(getattr(request, "last_event_seq", 0) or 0),
                public_envelope=self._public_envelope_dict(envelope),
            ):
                items.append(kernel_update)
            return items

        try:
            last_emitted_seq = int(getattr(request, "last_event_seq", 0) or 0)
            for kernel_update in self._run(_collect()):
                event_seq = int(kernel_update.get("event_seq", 0))
                if event_seq <= last_emitted_seq:
                    continue
                last_emitted_seq = event_seq
                yield self._job_pb.StreamJobUpdatesResponse(
                    update=self._update_from_kernel(request.job_id, kernel_update)
                )
        except grpc.RpcError as exc:
            context.abort(exc.code() if hasattr(exc, "code") else grpc.StatusCode.INTERNAL, exc.details() if hasattr(exc, "details") else "kernel gateway error")
        finally:
            log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobResults")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
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

        kernel_response = self._kernel_call(
            context,
            self._kernel_client.get_job_results,
            job_id=request.job_id,
            public_envelope=self._public_envelope_dict(envelope),
            not_found_reason="EIGEN_PUBLIC_JOB_NOT_FOUND",
        )
        resp = self._job_pb.GetJobResultsResponse(
            job_id=kernel_response.get("job_id", request.job_id),
            state=self._kernel_state_to_public_enum(kernel_response.get("state", "TASK_STATE_PENDING")),
            counts=dict(kernel_response.get("counts", {})),
            metadata=dict(kernel_response.get("metadata", {})),
            error_code=kernel_response.get("error_code", ""),
            error_summary=kernel_response.get("error_summary", ""),
            error_details_ref=kernel_response.get("error_details_ref", ""),
            completed_at=kernel_response.get("completed_at") or _ts_now(),
        )
        log_request_end("JobService.GetJobResults", rc)
        return resp

    def GetDispatchRationale(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetDispatchRationale")
        enforce_authz(context, required_permission="jobs:read")
        rc = new_request_context(context)
        log_request_start("JobService.GetDispatchRationale", rc)
        envelope = _public_envelope(request, context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name="JobService.GetDispatchRationale")
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity
        if not getattr(request, "job_id", ""):
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.INVALID_ARGUMENT,
                    message="job_id is required",
                    reason="EIGEN_PUBLIC_EXPLAIN_INVALID_REQUEST",
                    retryable=False,
                    detail="job_id must be provided for dispatch rationale lookup.",
                ),
            )
        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        try:
            kernel_response = self._retry_dispatch_rationale(request, context, envelope)
        except grpc.RpcError as exc:
            code = exc.code() if hasattr(exc, "code") else grpc.StatusCode.INTERNAL
            details = exc.details() if hasattr(exc, "details") else "kernel gateway error"
            if code == grpc.StatusCode.NOT_FOUND:
                abort_public(
                    context,
                    PublicErrorSpec(
                        grpc_code=grpc.StatusCode.NOT_FOUND,
                        message=details,
                        reason="EIGEN_PUBLIC_EXPLAIN_DECISION_NOT_FOUND",
                        retryable=False,
                        detail=details,
                    ),
                )
            context.abort(code, details)
        resp = self._job_pb.GetDispatchRationaleResponse(
            rationale=self._rationale_from_kernel(kernel_response)
        )
        log_request_end("JobService.GetDispatchRationale", rc)
        return resp
        