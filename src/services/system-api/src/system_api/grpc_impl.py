"""gRPC service implementations for System API (MVP skeleton)."""
from __future__ import annotations

import asyncio
import ast
import cmath
import json
import logging
import math
import os
import random
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

from .security import _AUTH_ALLOW_ALL

# ----------------------------------------------------------------------

logger = logging.getLogger(__name__)

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ModuleNotFoundError:  # pragma: no cover - optional for lightweight test environments
    pa = None
    pq = None

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
    if pa is None or pq is None:
        fallback_payload = {
            "job_id": job_id,
            "counts": ordered_counts,
            "metadata_json": ordered_metadata,
        }
        return json.dumps(fallback_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
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


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _literal_scalar(node: ast.AST) -> int | float | str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _literal_scalar(node.operand)
        if isinstance(value, (int, float)):
            return -value
    return None


def _collect_param_defaults(tree: ast.AST) -> dict[str, dict[str, object]]:
    params: dict[str, dict[str, object]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        target = node.targets[0].id
        if not isinstance(node.value, ast.Call) or _call_name(node.value.func) != "Param":
            continue
        if not node.value.args:
            continue
        name_arg = node.value.args[0]
        if not isinstance(name_arg, ast.Constant) or not isinstance(name_arg.value, str):
            continue
        default_value = _literal_scalar(node.value.args[1]) if len(node.value.args) > 1 else None
        params[target] = {"name": name_arg.value, "default": default_value}
    return params


def _resolve_int_expr(expr: ast.AST, *, context: str) -> int:
    value = _literal_scalar(expr)
    if isinstance(value, int):
        return value
    raise ValueError(f"{context} must be a literal integer")


def _resolve_theta_expr(expr: ast.AST, params: dict[str, dict[str, object]]) -> int | float | str:
    if isinstance(expr, ast.Name) and expr.id in params:
        default = params[expr.id].get("default")
        if isinstance(default, (int, float)):
            return float(default)
        raise ValueError(f"Param {params[expr.id]['name']} requires a numeric initial_value")
    scalar = _literal_scalar(expr)
    if isinstance(scalar, (int, float, str)):
        return scalar
    raise ValueError("theta must be a literal or Param reference")


def _simulate_aqo_counts(aqo_bytes: bytes, *, shots: int, seed: str) -> dict[str, int]:
    payload = json.loads(aqo_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("aqo payload must be a JSON object")

    qubits = payload.get("qubits")
    if not isinstance(qubits, int) or qubits <= 0:
        raise ValueError("aqo.qubits must be a positive integer")

    operations = payload.get("operations")
    if not isinstance(operations, list):
        raise ValueError("aqo.operations must be a list")

    state = [0j] * (1 << qubits)
    state[0] = 1 + 0j
    measure_map: list[tuple[int, int]] = []

    for idx, raw_op in enumerate(operations):
        if not isinstance(raw_op, dict):
            raise ValueError(f"operation[{idx}] must be an object")
        op = str(raw_op.get("op", "")).upper()
        q = raw_op.get("q")
        if not isinstance(q, list) or not all(isinstance(v, int) for v in q):
            raise ValueError(f"operation[{idx}].q must be an int list")
        if op in {"RX", "RY", "RZ"}:
            if len(q) != 1:
                raise ValueError(f"{op} requires one qubit")
            params = raw_op.get("params")
            if not isinstance(params, dict) or "theta" not in params:
                raise ValueError(f"operation[{idx}] missing theta")
            theta = params["theta"]
            if not isinstance(theta, (int, float)):
                raise ValueError(f"operation[{idx}] theta must be numeric")
            _apply_single_qubit_rotation(state, target=q[0], op=op, theta=float(theta))
        elif op == "CX":
            if len(q) != 2:
                raise ValueError("CX requires two qubits")
            _apply_cx(state, control=q[0], target=q[1])
        elif op == "MEASURE":
            c = raw_op.get("c")
            if not isinstance(c, list) or len(c) != len(q) or not all(isinstance(v, int) for v in c):
                raise ValueError(f"operation[{idx}].c must match q[]")
            for qidx, cidx in zip(q, c, strict=True):
                measure_map.append((qidx, cidx))
        else:
            raise ValueError(f"unsupported op: {op}")

    if not measure_map:
        measure_map = [(i, i) for i in range(qubits)]

    cwidth = max((c for _, c in measure_map), default=-1) + 1
    cwidth = max(cwidth, 1)

    probabilities = [abs(a) ** 2 for a in state]
    total = sum(probabilities)
    if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        probabilities = [p / total for p in probabilities]

    rnd = random.Random(seed)
    counts: dict[str, int] = {}
    for _ in range(max(int(shots), 0)):
        basis_state = rnd.choices(range(1 << qubits), weights=probabilities, k=1)[0]
        classical = [0] * cwidth
        for qidx, cidx in measure_map:
            classical[cidx] = (basis_state >> qidx) & 1
        bitstring = "".join(str(classical[i]) for i in range(cwidth - 1, -1, -1))
        counts[bitstring] = counts.get(bitstring, 0) + 1

    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _apply_single_qubit_rotation(state: list[complex], *, target: int, op: str, theta: float) -> None:
    c = math.cos(theta / 2)
    s = math.sin(theta / 2)
    if op == "RX":
        matrix = ((c, -1j * s), (-1j * s, c))
    elif op == "RY":
        matrix = ((c, -s), (s, c))
    elif op == "RZ":
        matrix = ((cmath.exp(-1j * theta / 2), 0j), (0j, cmath.exp(1j * theta / 2)))
    else:
        raise ValueError(f"unsupported rotation: {op}")

    step = 1 << target
    span = step << 1
    for base in range(0, len(state), span):
        for offset in range(step):
            i0 = base + offset
            i1 = i0 + step
            a0 = state[i0]
            a1 = state[i1]
            state[i0] = matrix[0][0] * a0 + matrix[0][1] * a1
            state[i1] = matrix[1][0] * a0 + matrix[1][1] * a1


def _apply_cx(state: list[complex], *, control: int, target: int) -> None:
    if control == target:
        raise ValueError("CX control and target must differ")

    control_mask = 1 << control
    target_mask = 1 << target
    for idx in range(len(state)):
        if (idx & control_mask) and not (idx & target_mask):
            swap_idx = idx | target_mask
            state[idx], state[swap_idx] = state[swap_idx], state[idx]


def _default_success_counts() -> dict[str, int]:
    # Canonical small-success result used by the local MVP executor and smoke tests.
    return {"00": 512, "11": 512}


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

class JobService:
    """Thin public ingress facade for eigen.api.v1.JobService.

    The execution boundary lives in Kernel/Core. This class only performs
    request validation, public-envelope normalization, trace propagation and
    response mapping.
    """

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
        self._jobs: dict[str, dict[str, object]] = {}
        self._load_idempotency_records()

    def _ensure_kernel(self) -> None:
        if getattr(self._kernel_client, "_closed", False):
            connect = getattr(self._kernel_client, "connect", None)
            if callable(connect):
                connect()

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
        tenant_id: str,
        project_id: str,
    ) -> None:
        self._idempotency[key] = _IdempotencyRecord(
            job_id=job_id,
            request_fingerprint=request_fingerprint,
            expires_at_unix=time.time() + self._idempotency_ttl_sec,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        self._persist_idempotency_records()

    @staticmethod
    def _idempotency_key(request, envelope: NormalizedPublicEnvelope) -> str:
        metadata = dict(getattr(request, "metadata", {}))
        return (
            envelope.idempotency_key
            or str(metadata.get("idempotency_key", "") or "").strip()
            or str(metadata.get("client_request_id", "") or "").strip()
            or str(metadata.get("x-idempotency-key", "") or "").strip()
        )

    @staticmethod
    def _request_fingerprint(request, envelope: NormalizedPublicEnvelope) -> str:
        metadata = {str(k): str(v) for k, v in sorted(dict(getattr(request, "metadata", {})).items())}
        compiler_options = {str(k): str(v) for k, v in sorted(dict(getattr(request, "compiler_options", {})).items())}
        program_kind = request.WhichOneof("program")
        program_digest = ""
        if program_kind == "eigen_lang":
            program_digest = sha256(bytes(request.eigen_lang.source)).hexdigest()
        elif program_kind == "qasm":
            program_digest = sha256(bytes(request.qasm.source)).hexdigest()
        elif program_kind == "aqo_ref":
            ref = str(getattr(request.aqo_ref, "qfs_ref", "") or "")
            program_digest = sha256(ref.encode("utf-8")).hexdigest()
        payload = {
            "job_name": getattr(request, "name", ""),
            "program_kind": program_kind,
            "program_digest": program_digest,
            "target": getattr(request, "target", ""),
            "priority": int(getattr(request, "priority", 0) or 0),
            "contract_version": envelope.contract_version,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "metadata": metadata,
            "compiler_options": compiler_options,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _remember_job(self, *, job_id: str, tenant_id: str, project_id: str, status) -> None:
        self._jobs[job_id] = {
            "owner_tenant": tenant_id,
            "owner_project": project_id,
            "status": status,
        }

    def _job_entry(self, job_id: str) -> dict[str, object] | None:
        return self._jobs.get(job_id)

    def _enforce_job_access(self, *, context: grpc.ServicerContext, job_id: str) -> None:
        entry = self._job_entry(job_id)
        if not entry:
            return
        _subject, _roles, tenant = auth_context(context)
        if tenant != entry.get("owner_tenant"):
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.PERMISSION_DENIED,
                    message="cross-tenant access denied",
                    reason="EIGEN_PUBLIC_PERMISSION_DENIED",
                    retryable=False,
                    metadata={"policy": "POLICY_DENY_TENANT_MISMATCH"},
                    precondition_type="AUTHORIZATION_POLICY",
                    precondition_subject=job_id,
                    detail="Caller tenant does not match the job owner tenant.",
                ),
            )

    @staticmethod
    def _public_envelope_dict(envelope: NormalizedPublicEnvelope) -> dict[str, str]:
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

    def _mk_topology_pb(self, topology: dict[str, str] | None):
        if not topology:
            return None
        return self._types_pb.TopologyEnvelope(
            contract_version=topology.get("contract_version", TOPOLOGY_CONTRACT_VERSION),
            lineage_version=topology.get("lineage_version", TOPOLOGY_LINEAGE_VERSION),
            cluster_id=topology.get("cluster_id", "cluster-local"),
            worker_id=topology.get("worker_id", "worker-local"),
            partition_id=topology.get("partition_id", "partition-0"),
            attempt=int(topology.get("attempt", 1)),
        )

    def _build_program_payload(self, request) -> tuple[bytes, str]:
        program_kind = request.WhichOneof("program")
        if program_kind == "eigen_lang":
            return bytes(request.eigen_lang.source), "eigen_lang_source"
        if program_kind == "qasm":
            return bytes(request.qasm.source), "qasm_text"
        if program_kind == "aqo_ref":
            ref = str(getattr(request.aqo_ref, "qfs_ref", "") or "")
            aqo_bytes = QFS_STORE.get_bytes(ref) if ref else None
            return (aqo_bytes or ref.encode("utf-8")), "aqo_ref"
        return (
            b"from eigen_lang import hybrid_program\n\n@hybrid_program()\ndef main():\n    return 0\n",
            "eigen_lang_source",
        )

    @staticmethod
    def _request_fingerprint(request, envelope: NormalizedPublicEnvelope) -> str:
        payload = {
            "job_name": getattr(request, "name", ""),
            "program_kind": request.WhichOneof("program"),
            "target": getattr(request, "target", ""),
            "priority": int(getattr(request, "priority", 0) or 0),
            "contract_version": envelope.contract_version,
            "tenant_id": envelope.tenant_id,
            "project_id": envelope.project_id,
            "metadata": {str(k): str(v) for k, v in sorted(dict(getattr(request, "metadata", {})).items())},
            "compiler_options": {str(k): str(v) for k, v in sorted(dict(getattr(request, "compiler_options", {})).items())},
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _normalize_env(self, request, context: grpc.ServicerContext, *, method_name: str) -> tuple[NormalizedPublicEnvelope, object]:
        envelope = _public_envelope(request, context)
        rc = new_request_context(context)
        _apply_public_envelope_context(rc, envelope)
        sec = security_context(context, method_name=method_name)
        rc.subject = sec.subject
        rc.roles = sec.roles
        rc.auth_mode = sec.auth_mode
        rc.policy_version = sec.policy_version
        rc.service_identity = sec.service_identity
        return envelope, rc

    def _call_kernel(self, fn, *args, **kwargs):
        self._ensure_kernel()
        return asyncio.run(fn(*args, **kwargs))

    async def _collect_kernel_updates(self, *, job_id: str, last_event_seq: int, envelope: NormalizedPublicEnvelope) -> list[dict]:
        updates: list[dict] = []
        async for update in self._kernel_client.stream_job_updates(
            job_id,
            last_event_seq,
            self._public_envelope_dict(envelope),
        ):
            updates.append(update)
        return updates

    def _build_submit_response(self, job_id: str, kernel_response: dict, *, message_override: str | None = None):
        status = self._job_status_from_kernel(job_id=job_id, kernel_response=kernel_response)
        if message_override is not None:
            status.message = message_override
        return self._job_pb.SubmitJobResponse(
            job_id=job_id,
            status=status,
        )

    def SubmitJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.SubmitJob")
        enforce_authz(context, required_permission="jobs:submit")
        violations = validate_submit_job(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        envelope, rc = self._normalize_env(request, context, method_name="JobService.SubmitJob")
        log_request_start("JobService.SubmitJob", rc)
        sec = security_context(context, method_name="JobService.SubmitJob")
        public_envelope = self._public_envelope_dict(envelope)
        public_envelope.update(
            {
                "auth_subject": sec.subject,
                "auth_role": ",".join(sec.roles) if sec.roles else "",
                "security_context": sec.policy_version,
            }
        )
        idem_key = self._idempotency_key(request, envelope)
        request_fingerprint = self._request_fingerprint(request, envelope)

        if idem_key:
            with self._lock:
                previous = self._get_idempotency_record(idem_key)
                if previous is not None:
                    if previous.request_fingerprint != request_fingerprint:
                        record_submit_job_outcome("conflict")
                        record_public_api_contract_marker(envelope.contract_version, "conflict")
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
                    cached = self._job_entry(previous.job_id)
                    if cached is not None and isinstance(cached.get("status"), self._types_pb.JobStatus.__class__):
                        record_submit_job_outcome("replayed")
                        record_public_api_contract_marker(envelope.contract_version, "replayed")
                        resp = self._job_pb.SubmitJobResponse(job_id=previous.job_id, status=self._job_pb.JobStatus())
                        resp.job_id = previous.job_id
                        resp.status.CopyFrom(cached["status"])
                        resp.status.message = "accepted (idempotent replay from persisted request record)"
                        log_request_end("JobService.SubmitJob", rc, request_id=rc.request_id, trace_id=rc.trace_id, traceparent=rc.traceparent, job_id=previous.job_id)
                        return resp
                    try:
                        kernel_status = self._call_kernel(
                            self._kernel_client.get_job_status,
                            previous.job_id,
                            public_envelope,
                        )
                    except grpc.RpcError as err:
                        if err.code() == grpc.StatusCode.NOT_FOUND:
                            _abort_job_not_found(context, previous.job_id)
                        context.abort(err.code(), err.details() or "kernel delegation failed")
                    except Exception as exc:  # pragma: no cover - kernel unavailable path
                        context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")
                    status = self._job_status_from_kernel(job_id=previous.job_id, kernel_response=kernel_status)
                    status.message = "accepted (idempotent replay from persisted request record)"
                    record_submit_job_outcome("replayed")
                    record_public_api_contract_marker(envelope.contract_version, "replayed")
                    resp = self._job_pb.SubmitJobResponse(job_id=previous.job_id, status=status)
                    with self._lock:
                        self._remember_job(job_id=previous.job_id, tenant_id=previous.tenant_id, project_id=previous.project_id, status=status)
                    log_request_end("JobService.SubmitJob", rc, request_id=rc.request_id, trace_id=rc.trace_id, traceparent=rc.traceparent, job_id=previous.job_id)
                    return resp

        program_bytes, program_format = self._build_program_payload(request)
        try:
            kernel_response = self._call_kernel(
                self._kernel_client.enqueue_job,
                name=request.name,
                program=program_bytes,
                program_format=program_format,
                target=request.target,
                priority=int(getattr(request, "priority", 0) or 0),
                compiler_options={str(k): str(v) for k, v in dict(getattr(request, "compiler_options", {})).items()},
                metadata_kvs={str(k): str(v) for k, v in dict(getattr(request, "metadata", {})).items()},
                public_envelope=public_envelope,
                workload=getattr(request, "workload", None),
            )
        except grpc.RpcError:
            raise
        except Exception as exc:  # pragma: no cover - kernel unavailable path
            context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")

        rc.job_id = kernel_response.get("job_id", "")
        status = self._job_status_from_kernel(job_id=rc.job_id, kernel_response=kernel_response)
        with self._lock:
            self._remember_job(job_id=rc.job_id, tenant_id=envelope.tenant_id, project_id=envelope.project_id, status=status)
            if idem_key:
                self._remember_idempotency_record(
                    key=idem_key,
                    job_id=rc.job_id,
                    request_fingerprint=request_fingerprint,
                    tenant_id=envelope.tenant_id,
                    project_id=envelope.project_id,
                )
        record_submit_job_outcome("accepted")
        record_public_api_contract_marker(envelope.contract_version, "accepted")
        log_request_end("JobService.SubmitJob", rc, request_id=rc.request_id, trace_id=rc.trace_id, traceparent=rc.traceparent, job_id=rc.job_id)
        return self._build_submit_response(rc.job_id, kernel_response)

    def GetJobStatus(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobStatus")
        enforce_authz(context, required_permission="jobs:read")
        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        envelope, rc = self._normalize_env(request, context, method_name="JobService.GetJobStatus")
        rc.job_id = request.job_id
        self._enforce_job_access(context=context, job_id=request.job_id)
        log_request_start("JobService.GetJobStatus", rc)
        try:
            kernel_response = self._call_kernel(
                self._kernel_client.get_job_status,
                request.job_id,
                self._public_envelope_dict(envelope),
            )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:
                _abort_job_not_found(context, request.job_id)
            context.abort(err.code(), err.details() or "kernel delegation failed")
        except Exception as exc:  # pragma: no cover - kernel unavailable path
            context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")

        status = self._job_status_from_kernel(job_id=request.job_id, kernel_response=kernel_response)
        with self._lock:
            entry = self._job_entry(request.job_id)
            if entry is not None:
                entry["status"] = status
        resp = self._job_pb.GetJobStatusResponse(status=status)
        log_request_end("JobService.GetJobStatus", rc)
        return resp

    def CancelJob(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.CancelJob")
        enforce_authz(context, required_permission="jobs:cancel")
        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        envelope, rc = self._normalize_env(request, context, method_name="JobService.CancelJob")
        rc.job_id = request.job_id
        self._enforce_job_access(context=context, job_id=request.job_id)
        log_request_start("JobService.CancelJob", rc)
        try:
            kernel_response = self._call_kernel(
                self._kernel_client.cancel_job,
                request.job_id,
                self._public_envelope_dict(envelope),
            )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:
                _abort_job_not_found(context, request.job_id)
            context.abort(err.code(), err.details() or "kernel delegation failed")
        except Exception as exc:  # pragma: no cover - kernel unavailable path
            context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")

        resp = self._job_pb.CancelJobResponse(accepted=bool(kernel_response.get("accepted", False)), reason_code=str(kernel_response.get("reason_code", "")))
        log_request_end("JobService.CancelJob", rc)
        return resp

    def StreamJobUpdates(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.StreamJobUpdates")
        enforce_authz(context, required_permission="jobs:read")
        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        envelope, rc = self._normalize_env(request, context, method_name="JobService.StreamJobUpdates")
        rc.job_id = request.job_id
        self._enforce_job_access(context=context, job_id=request.job_id)
        log_request_start("JobService.StreamJobUpdates", rc)
        try:
            updates = self._call_kernel(
                self._collect_kernel_updates,
                job_id=request.job_id,
                last_event_seq=int(getattr(request, "last_event_seq", 0) or 0),
                envelope=envelope,
            )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:
                _abort_job_not_found(context, request.job_id)
            context.abort(err.code(), err.details() or "kernel delegation failed")
        except Exception as exc:  # pragma: no cover - kernel unavailable path
            context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")

        for update in updates:
            yield self._job_pb.StreamJobUpdatesResponse(
                update=self._types_pb.JobUpdate(
                    job_id=update.get("job_id", request.job_id),
                    state=self._kernel_state_to_public_state(update.get("state", "TASK_STATE_PENDING")),
                    stage=update.get("stage", ""),
                    progress=float(update.get("progress", 0.0)),
                    message=update.get("message", ""),
                    event_seq=int(update.get("event_seq", 0)),
                    timestamp=update.get("timestamp") or _ts_now(),
                    topology=self._mk_topology_pb(update.get("topology")),
                )
            )
        log_request_end("JobService.StreamJobUpdates", rc)

    def GetJobResults(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetJobResults")
        enforce_authz(context, required_permission="jobs:read")
        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        envelope, rc = self._normalize_env(request, context, method_name="JobService.GetJobResults")
        rc.job_id = request.job_id
        self._enforce_job_access(context=context, job_id=request.job_id)
        log_request_start("JobService.GetJobResults", rc)
        try:
            kernel_response = self._call_kernel(
                self._kernel_client.get_job_results,
                request.job_id,
                self._public_envelope_dict(envelope),
            )
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
        except Exception as exc:  # pragma: no cover - kernel unavailable path
            context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")

        resp = self._job_pb.GetJobResultsResponse(
            job_id=kernel_response.get("job_id", request.job_id),
            state=self._kernel_state_to_public_state(kernel_response.get("state", "TASK_STATE_PENDING")),
            counts=dict(kernel_response.get("counts", {})),
            metadata=dict(kernel_response.get("metadata", {})),
            qfs_result_ref=kernel_response.get("qfs_result_ref", ""),
            completed_at=kernel_response.get("completed_at") or _ts_now(),
            error_code=kernel_response.get("error_code", ""),
            error_summary=kernel_response.get("error_summary", ""),
            error_details_ref=kernel_response.get("error_details_ref", ""),
        )
        with self._lock:
            entry = self._job_entry(request.job_id)
            if entry is not None:
                entry["status"] = self._job_status_from_kernel(job_id=request.job_id, kernel_response=kernel_response)
        log_request_end("JobService.GetJobResults", rc)
        return resp

    def GetDispatchRationale(self, request, context: grpc.ServicerContext):
        enforce_authn(context, method_name="JobService.GetDispatchRationale")
        enforce_authz(context, required_permission="jobs:read")
        violations = validate_job_id(request)
        if violations:
            abort_invalid_argument(context, "validation failed", violations)

        envelope, rc = self._normalize_env(request, context, method_name="JobService.GetDispatchRationale")
        rc.job_id = request.job_id
        self._enforce_job_access(context=context, job_id=request.job_id)
        log_request_start("JobService.GetDispatchRationale", rc)
        try:
            kernel_response = self._call_kernel(
                self._kernel_client.get_dispatch_rationale,
                request.job_id,
                self._public_envelope_dict(envelope),
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
        except Exception as exc:  # pragma: no cover - kernel unavailable path
            context.abort(grpc.StatusCode.UNAVAILABLE, f"kernel delegation failed: {exc}")

        resp = self._job_pb.GetDispatchRationaleResponse(
            rationale=self._job_pb.DispatchRationale(
                version=str(kernel_response.get("version", "")),
                policy_version=str(kernel_response.get("policy_version", "")),
                reason_codes=list(kernel_response.get("reason_codes", [])),
                selected_backend=str(kernel_response.get("selected_backend", "")),
                selected_queue=str(kernel_response.get("selected_queue", "")),
                attributes={k: str(v) for k, v in dict(kernel_response.get("attributes", {})).items()},
                timeline_ref=str(kernel_response.get("timeline_ref", "")),
                logs_ref=str(kernel_response.get("logs_ref", "")),
                trace_id=str(kernel_response.get("trace_id", "")),
                trace_ref=str(kernel_response.get("trace_ref", "")),
            )
        )
        log_request_end("JobService.GetDispatchRationale", rc)
        return resp

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

        return b'{"operations":[{"c":[0],"op":"MEASURE","q":[0]}],"qubits":1,"version":"1.0.0"}'

    def _compile_eigen_lang_source(self, source: bytes) -> bytes:
        try:
            tree = ast.parse(source.decode("utf-8"))
        except (UnicodeDecodeError, SyntaxError):
            return b'{"operations":[{"c":[0],"op":"MEASURE","q":[0]}],"qubits":1,"version":"1.0.0"}'

        params = _collect_param_defaults(tree)
        operations: list[dict[str, object]] = []
        qubits = 1

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            if name in {"rx", "ry", "rz"}:
                if not node.args:
                    raise ValueError(f"{name.upper()} requires a qubit index")
                q = _resolve_int_expr(node.args[0], context=f"{name.upper()} qubit index")
                theta_expr = next((kw.value for kw in node.keywords if kw.arg == "theta"), None)
                if theta_expr is None and len(node.args) > 1:
                    theta_expr = node.args[1]
                if theta_expr is None:
                    raise ValueError(f"{name.upper()} requires theta")
                theta = _resolve_theta_expr(theta_expr, params)
                operations.append({"op": name.upper(), "q": [q], "params": {"theta": theta}})
                qubits = max(qubits, q + 1)
            elif name in {"cx", "cnot"}:
                if len(node.args) < 2:
                    raise ValueError(f"{name.upper()} requires two qubit indices")
                q0 = _resolve_int_expr(node.args[0], context=f"{name.upper()} control index")
                q1 = _resolve_int_expr(node.args[1], context=f"{name.upper()} target index")
                operations.append({"op": "CX", "q": [q0, q1]})
                qubits = max(qubits, q0 + 1, q1 + 1)
            elif name == "measure":
                q = [_resolve_int_expr(arg, context="MEASURE qubit index") for arg in node.args]
                if not q:
                    raise ValueError("MEASURE requires at least one qubit")
                c_values = next((kw.value for kw in node.keywords if kw.arg == "c"), None)
                if c_values is not None:
                    if not isinstance(c_values, (ast.List, ast.Tuple)):
                        raise ValueError("MEASURE c must be a literal list")
                    c = [_resolve_int_expr(item, context="MEASURE classical index") for item in c_values.elts]
                else:
                    c = list(range(len(q)))
                operations.append({"op": "MEASURE", "q": q, "c": c})
                qubits = max(qubits, max(q) + 1, (max(c) + 1) if c else 0)
            elif name == "measure_all":
                q = list(range(qubits))
                operations.append({"op": "MEASURE", "q": q, "c": list(range(qubits))})

        if not operations:
            operations.append({"op": "MEASURE", "q": [0], "c": [0]})
        elif not any(op.get("op") == "MEASURE" for op in operations):
            operations.append({"op": "MEASURE", "q": list(range(qubits)), "c": list(range(qubits))})

        aqo: dict[str, object] = {"version": "1.0.0", "qubits": qubits, "operations": operations}
        if params:
            aqo["parameters"] = {params[name]["name"]: params[name]["default"] for name in sorted(params)}
        return json.dumps(aqo, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _provision_temporary_artifacts(self, record, request) -> None:
        compiled = record.results_metadata["qfs_compiled_aqo"]
        temp_prefix = f"qfs://jobs/{record.job_id}/tmp/"
        temp_refs = [f"{temp_prefix}request.json", f"{temp_prefix}compiled.tmp"]
        QFS_STORE.put_bytes(compiled, self._compiled_aqo_bytes_for_request(request))
        for temp_ref in temp_refs:
            QFS_STORE.put_bytes(temp_ref, b"tmp")
        record.temp_refs = temp_refs
