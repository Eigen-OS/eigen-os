"""Structured gRPC error helpers for driver-manager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import grpc
from google.rpc import error_details_pb2, status_pb2
from grpc_status import rpc_status


@dataclass(frozen=True)
class FieldViolation:
    field: str
    description: str


def _grpc_code_int(code: grpc.StatusCode) -> int:
    return int(code.value[0])


def abort_invalid_argument(
    context: grpc.ServicerContext,
    message: str,
    violations: Sequence[FieldViolation],
) -> None:
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
