"""Error helpers for System API (MVP).

This module provides helpers to construct **structured** gRPC errors.

Contract:
- Use gRPC status codes for failures (no `success=false` fields).
- For validation failures: `INVALID_ARGUMENT` with `google.rpc.BadRequest`
  field violations (machine-readable).

References:
- docs/reference/error-model.md
- docs/reference/error-mapping.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import grpc
from google.rpc import error_details_pb2, status_pb2
from grpc_status import rpc_status


@dataclass(frozen=True)
class FieldViolation:
    field: str
    description: str


def _grpc_code_int(code: grpc.StatusCode) -> int:
    # grpc.StatusCode.value is a tuple: (int, 'NAME')
    return int(code.value[0])


@dataclass(frozen=True)
class PublicErrorSpec:
    """Canonical public error contract emitted at the API boundary."""

    grpc_code: grpc.StatusCode
    message: str
    reason: str
    retryable: bool
    domain: str = "eigen.api.v1"
    metadata: dict[str, str] | None = None
    violations: Sequence[FieldViolation] = ()
    retry_delay_seconds: int | None = None
    resource_type: str = ""
    resource_name: str = ""
    precondition_type: str = ""
    precondition_subject: str = ""
    quota_subject: str = ""
    request_id: str = ""
    detail: str = ""


def build_public_status(spec: PublicErrorSpec) -> status_pb2.Status:
    """Build deterministic google.rpc.Status details for public errors.

    Detail order is intentionally stable: ErrorInfo is always first so SDKs can
    extract reason/retryability uniformly, followed by scenario-specific detail
    messages required by docs/reference/error-model.md.
    """

    metadata = dict(spec.metadata or {})
    metadata["retryable"] = "true" if spec.retryable else "false"
    st = status_pb2.Status(code=_grpc_code_int(spec.grpc_code), message=spec.message)
    st.details.add().Pack(
        error_details_pb2.ErrorInfo(
            reason=spec.reason,
            domain=spec.domain,
            metadata={k: str(metadata[k]) for k in sorted(metadata)},
        )
    )
    if spec.violations:
        st.details.add().Pack(
            error_details_pb2.BadRequest(
                field_violations=[
                    error_details_pb2.BadRequest.FieldViolation(field=v.field, description=v.description)
                    for v in spec.violations
                ]
            )
        )
    if spec.retry_delay_seconds is not None:
        retry = error_details_pb2.RetryInfo()
        retry.retry_delay.seconds = int(spec.retry_delay_seconds)
        st.details.add().Pack(retry)
    if spec.resource_type or spec.resource_name:
        st.details.add().Pack(
            error_details_pb2.ResourceInfo(
                resource_type=spec.resource_type,
                resource_name=spec.resource_name,
                description=spec.detail,
            )
        )
    if spec.precondition_type or spec.precondition_subject:
        violation = error_details_pb2.PreconditionFailure.Violation(
            type=spec.precondition_type or spec.reason,
            subject=spec.precondition_subject,
            description=spec.detail or spec.message,
        )
        st.details.add().Pack(error_details_pb2.PreconditionFailure(violations=[violation]))
    if spec.quota_subject:
        violation = error_details_pb2.QuotaFailure.Violation(
            subject=spec.quota_subject,
            description=spec.detail or spec.message,
        )
        st.details.add().Pack(error_details_pb2.QuotaFailure(violations=[violation]))
    if spec.request_id:
        st.details.add().Pack(error_details_pb2.RequestInfo(request_id=spec.request_id))
    return st


def abort_public(context: grpc.ServicerContext, spec: PublicErrorSpec) -> None:
    """Abort RPC with canonical public google.rpc.Status details."""

    context.abort_with_status(rpc_status.to_status(build_public_status(spec)))


def abort_validation(
    context: grpc.ServicerContext,
    message: str,
    violations: Sequence[FieldViolation],
) -> None:
    abort_public(
        context,
        PublicErrorSpec(
            grpc_code=grpc.StatusCode.INVALID_ARGUMENT,
            message=message,
            reason="EIGEN_PUBLIC_VALIDATION_FAILED",
            retryable=False,
            metadata={"error_class": "validation"},
            violations=violations,
        ),
    )

def abort_payload_limit(
    context: grpc.ServicerContext,
    message: str,
    violations: Sequence[FieldViolation],
) -> None:
    abort_public(
        context,
        PublicErrorSpec(
            grpc_code=grpc.StatusCode.RESOURCE_EXHAUSTED,
            message=message,
            reason="EIGEN_PUBLIC_PAYLOAD_LIMIT_EXCEEDED",
            retryable=False,
            metadata={"limit_class": "payload"},
            violations=violations,
            quota_subject="request.payload",
            detail="Reduce request payload size and retry with a smaller request.",
        ),
    )

def abort_invalid_argument(
    context: grpc.ServicerContext,
    message: str,
    violations: Sequence[FieldViolation],
) -> None:
    """Abort the current RPC with INVALID_ARGUMENT + canonical public details."""

    abort_validation(context, message, violations)

def abort_with_error_info(
    context: grpc.ServicerContext,
    *,
    grpc_code: grpc.StatusCode,
    message: str,
    reason: str,
    domain: str,
    metadata: dict[str, str] | None = None,
) -> None:
    """Abort RPC with canonical public ErrorInfo details for stable parsing."""

    abort_public(
        context,
        PublicErrorSpec(
            grpc_code=grpc_code,
            message=message,
            reason=reason,
            domain=domain,
            retryable=grpc_code in {
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                grpc.StatusCode.ABORTED,
            },
            metadata=metadata,
            retry_delay_seconds=1
            if grpc_code in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.ABORTED}
            else None,
        ),
    )

def required_string(value: str, field: str) -> Iterable[FieldViolation]:
    if not value:
        yield FieldViolation(field=field, description="field is required")


def positive_int(value: int, field: str) -> Iterable[FieldViolation]:
    if value <= 0:
        yield FieldViolation(field=field, description="must be > 0")
