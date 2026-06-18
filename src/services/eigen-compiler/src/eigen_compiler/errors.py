"""Structured gRPC error helpers for eigen-compiler."""

from __future__ import annotations

import json
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
    stage: str = ""
    rule: str = ""
    pass_name: str = ""


def annotate_violations(
    violations: Sequence[FieldViolation],
    *,
    stage: str,
    rule: str,
    pass_name: str,
) -> tuple[FieldViolation, ...]:
    annotated: list[FieldViolation] = []
    for violation in violations:
        annotated.append(
            FieldViolation(
                field=violation.field,
                description=violation.description,
                stage=violation.stage or stage,
                rule=violation.rule or rule,
                pass_name=violation.pass_name or pass_name,
            )
        )
    return tuple(annotated)


def _diagnostics_payload(violations: Sequence[FieldViolation]) -> list[dict[str, str]]:
    return [
        {
            "field": violation.field,
            "description": violation.description,
            "stage": violation.stage or "unknown",
            "rule": violation.rule or "unknown",
            "pass_name": violation.pass_name or "unknown",
        }
        for violation in violations
    ]


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
    diagnostics = tuple(violations)
    first_diagnostic = diagnostics[0] if diagnostics else FieldViolation(field="", description="")
    error_info = error_details_pb2.ErrorInfo(
        reason="EIGEN_COMPILER_VALIDATION_FAILED",
        domain="eigen.compiler",
        metadata={
            "stage": first_diagnostic.stage or "unknown",
            "rule": first_diagnostic.rule or "unknown",
            "pass_name": first_diagnostic.pass_name or "unknown",
            "diagnostics_json": json.dumps(
                _diagnostics_payload(diagnostics),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        },
    )

    st = status_pb2.Status(
        code=_grpc_code_int(grpc.StatusCode.INVALID_ARGUMENT),
        message=message,
    )
    st.details.add().Pack(bad_request)
    st.details.add().Pack(error_info)
    try:
        context.set_trailing_metadata((("grpc-status-details-bin", st.SerializeToString()),))
    except Exception as exc:
        logger.debug("failed to attach grpc status details metadata: %s", exc)
    context.abort(grpc.StatusCode.INVALID_ARGUMENT, message)
