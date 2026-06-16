"""Structured gRPC error helpers for eigen-compiler."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import grpc

logger = logging.getLogger(__name__)

try:
    from google.rpc import error_details_pb2, status_pb2
    from grpc_status import rpc_status
except ModuleNotFoundError:  # pragma: no cover - exercised in lean test envs
    error_details_pb2 = None
    status_pb2 = None
    rpc_status = None


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
    if error_details_pb2 is None or status_pb2 is None or rpc_status is None:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, message)
        return

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
    try:
        context.set_trailing_metadata((("grpc-status-details-bin", st.SerializeToString()),))
    except Exception as exc:
        logger.debug("failed to attach grpc status details metadata: %s", exc)
    context.abort(grpc.StatusCode.INVALID_ARGUMENT, message)
