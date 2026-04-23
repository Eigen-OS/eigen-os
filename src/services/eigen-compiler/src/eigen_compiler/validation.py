"""Request validation for eigen-compiler RPCs."""

from __future__ import annotations

import os
from typing import List

from .errors import FieldViolation

_SUPPORTED_LANGUAGES = {"eigen-lang"}

def _max_source_bytes() -> int:
    raw = os.getenv("EIGEN_COMPILER_MAX_SOURCE_BYTES", "262144")
    try:
        value = int(raw)
    except ValueError:
        return 262_144
    return max(1, value)


def _validate_input_oneof(req, *, source_field: str, source_ref_field: str) -> list[FieldViolation]:
    violations: list[FieldViolation] = []
    oneof = req.WhichOneof("input")
    if oneof is None:
        violations.append(FieldViolation(field="input", description="oneof input is required"))
        return violations

    if oneof == source_field and not getattr(req, source_field):
        violations.append(FieldViolation(field=source_field, description="source must be non-empty"))

    if oneof == source_ref_field and not getattr(req, source_ref_field):
        violations.append(
            FieldViolation(field=source_ref_field, description="source_ref must be non-empty")
        )
    return violations


def validate_compile_circuit(req) -> List[FieldViolation]:
    violations: list[FieldViolation] = []
    source_limit = _max_source_bytes()

    if not req.language:
        violations.append(FieldViolation(field="language", description="field is required"))
    elif req.language not in _SUPPORTED_LANGUAGES:
        violations.append(
            FieldViolation(field="language", description="unsupported language, expected eigen-lang")
        )

    violations.extend(_validate_input_oneof(req, source_field="source", source_ref_field="source_ref"))
    if req.WhichOneof("input") == "source" and len(req.source) > source_limit:
        violations.append(
            FieldViolation(
                field="source",
                description=f"source exceeds max allowed size ({source_limit} bytes)",
            )
        )
    return violations


def validate_compile_job(req) -> List[FieldViolation]:
    violations: list[FieldViolation] = []

    if not req.job_id:
        violations.append(FieldViolation(field="job_id", description="field is required"))

    violations.extend(validate_compile_circuit(req))
    return violations
