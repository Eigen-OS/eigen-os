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


def abort_invalid_argument(
    context: grpc.ServicerContext,
    message: str,
    violations: Sequence[FieldViolation],
) -> None:
    """Abort the current RPC with INVALID_ARGUMENT + BadRequest details."""

    bad_request = error_details_pb2.BadRequest(
        field_violations=[
            error_details_pb2.BadRequest.FieldViolation(
                field=v.field,
                description=v.description,
            )
            for v in violations
        ]
    )

    st = status_pb2.Status(
        code=_grpc_code_int(grpc.StatusCode.INVALID_ARGUMENT),
        message=message,
    )
    st.details.add().Pack(bad_request)

    context.abort_with_status(rpc_status.to_status(st))


def required_string(value: str, field: str) -> Iterable[FieldViolation]:
    if not value:
        yield FieldViolation(field=field, description="field is required")


def positive_int(value: int, field: str) -> Iterable[FieldViolation]:
    if value <= 0:
        yield FieldViolation(field=field, description="must be > 0")
