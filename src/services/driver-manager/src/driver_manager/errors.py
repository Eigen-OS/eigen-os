"""Structured gRPC error helpers for driver-manager.

Includes Eigen backend error normalization envelope used for operator diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import grpc
from google.protobuf import duration_pb2
from google.rpc import error_details_pb2, status_pb2
from grpc_status import rpc_status
import uuid


@dataclass(frozen=True)
class FieldViolation:
    field: str
    description: str


class ErrorTaxonomy(str, Enum):
    PROVIDER = "provider"
    NETWORK = "network"
    AUTH = "auth"
    QUOTA = "quota"
    RUNTIME = "runtime"
    INTERNAL = "internal"


@dataclass(frozen=True)
class NormalizedError:
    grpc_code: grpc.StatusCode
    eigen_code: str
    message: str
    taxonomy: ErrorTaxonomy
    remediation: str


def _grpc_code_int(code: grpc.StatusCode) -> int:
    return int(code.value[0])


def _correlation_id(context: grpc.ServicerContext) -> str:
    md = {k.lower(): v for (k, v) in (context.invocation_metadata() or [])}
    return md.get("x-correlation-id") or md.get("x-request-id") or str(uuid.uuid4())


def _retry_delay_for(code: grpc.StatusCode) -> duration_pb2.Duration | None:
    if code == grpc.StatusCode.UNAVAILABLE:
        delay = 1
    elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        delay = 5
    elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
        delay = 2
    else:
        return None

    return duration_pb2.Duration(seconds=delay)


def _add_retry_info(status: status_pb2.Status, code: grpc.StatusCode) -> None:
    retry_delay = _retry_delay_for(code)
    if retry_delay is None:
        return
    retry_info = error_details_pb2.RetryInfo(retry_delay=retry_delay)
    status.details.add().Pack(retry_info)


def _add_precondition_failure(status: status_pb2.Status, *, provider: str, job_id: str) -> None:
    precondition = error_details_pb2.PreconditionFailure(
        violations=[
            error_details_pb2.PreconditionFailure.Violation(
                type="STATE",
                subject=provider or "driver_manager",
                description=job_id or "backend precondition failure",
            )
        ]
    )
    status.details.add().Pack(precondition)


def abort_normalized(
    context: grpc.ServicerContext,
    *,
    normalized: NormalizedError,
    violations: Sequence[FieldViolation] = (),
    job_id: str = "",
    provider: str = "",
) -> None:
    corr = _correlation_id(context)
    md = {k.lower(): v for (k, v) in (context.invocation_metadata() or [])}
    trace_id = md.get("trace_id", "")

    st = status_pb2.Status(code=_grpc_code_int(normalized.grpc_code), message=normalized.message)

    if violations:
        bad_request = error_details_pb2.BadRequest(
            field_violations=[
                error_details_pb2.BadRequest.FieldViolation(field=v.field, description=v.description) for v in violations
            ]
        )
        st.details.add().Pack(bad_request)

    metadata = {
        "taxonomy": normalized.taxonomy.value,
        "remediation": normalized.remediation,
        "correlation_id": corr,
        "job_id": job_id,
        "provider": provider,
        "job_timeline": f"qfs://jobs/{job_id}/timeline.json" if job_id else "",
        "trace": f"trace://{trace_id}" if trace_id else "",
        "retryable": "true" if normalized.grpc_code in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.DEADLINE_EXCEEDED} else "false",
        "precondition": "true" if normalized.grpc_code == grpc.StatusCode.FAILED_PRECONDITION else "false",
    }
    
    info = error_details_pb2.ErrorInfo(
        reason=normalized.eigen_code,
        domain="eigen.driver_manager",
        metadata=metadata,
    )
    st.details.add().Pack(info)
    _add_retry_info(st, normalized.grpc_code)
    if normalized.grpc_code == grpc.StatusCode.FAILED_PRECONDITION:
        _add_precondition_failure(st, provider=provider, job_id=job_id)

    if job_id:
        resource = error_details_pb2.ResourceInfo(resource_type="job", resource_name=job_id, owner="eigen")
        st.details.add().Pack(resource)

    context.abort_with_status(rpc_status.to_status(st))


def abort_invalid_argument(
    context: grpc.ServicerContext,
    message: str,
    violations: Sequence[FieldViolation],
) -> None:
    abort_normalized(
        context,
        normalized=NormalizedError(
            grpc_code=grpc.StatusCode.INVALID_ARGUMENT,
            eigen_code="EIGEN_INVALID_ARGUMENT",
            message=message,
            taxonomy=ErrorTaxonomy.INTERNAL,
            remediation="Fix request fields according to the API contract and retry.",
        ),
        violations=violations,
    )

def map_backend_error(code: grpc.StatusCode, message: str) -> NormalizedError:
    msg = message or "backend execution failed"
    if code == grpc.StatusCode.UNAUTHENTICATED:
        return NormalizedError(code, "EIGEN_BACKEND_AUTH", msg, ErrorTaxonomy.AUTH, "Refresh backend credentials/token and retry.")
    if code == grpc.StatusCode.PERMISSION_DENIED:
        return NormalizedError(code, "EIGEN_BACKEND_AUTHZ", msg, ErrorTaxonomy.AUTH, "Verify backend access policy for this tenant/device.")
    if code == grpc.StatusCode.UNAVAILABLE:
        return NormalizedError(code, "EIGEN_BACKEND_UNAVAILABLE", msg, ErrorTaxonomy.NETWORK, "Retry with exponential backoff; verify provider status.")
    if code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        return NormalizedError(code, "EIGEN_BACKEND_QUOTA", msg, ErrorTaxonomy.QUOTA, "Reduce load/shots or wait for quota reset then retry.")
    if code == grpc.StatusCode.DEADLINE_EXCEEDED:
        return NormalizedError(code, "EIGEN_BACKEND_TIMEOUT", msg, ErrorTaxonomy.NETWORK, "Retry after reducing workload or increasing the deadline.")
    if code == grpc.StatusCode.FAILED_PRECONDITION:
        return NormalizedError(code, "EIGEN_BACKEND_PRECONDITION", msg, ErrorTaxonomy.RUNTIME, "Refresh state or satisfy the backend precondition before retrying.")
    if code == grpc.StatusCode.UNIMPLEMENTED:
        return NormalizedError(code, "EIGEN_BACKEND_PROVIDER", msg, ErrorTaxonomy.PROVIDER, "Use a supported backend capability or payload format.")
    if code == grpc.StatusCode.INVALID_ARGUMENT:
        return NormalizedError(code, "EIGEN_BACKEND_INVALID_ARGUMENT", msg, ErrorTaxonomy.PROVIDER, "Correct backend-specific payload parameters.")
    return NormalizedError(grpc.StatusCode.INTERNAL, "EIGEN_BACKEND_INTERNAL", msg, ErrorTaxonomy.INTERNAL, "Collect correlation id and contact Eigen operators.")
