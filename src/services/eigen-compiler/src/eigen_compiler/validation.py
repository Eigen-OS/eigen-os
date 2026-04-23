"""Request validation for eigen-compiler RPCs."""

from __future__ import annotations

from typing import List

from .errors import FieldViolation

_SUPPORTED_LANGUAGES = {"eigen-lang"}


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

    if not req.language:
        violations.append(FieldViolation(field="language", description="field is required"))
    elif req.language not in _SUPPORTED_LANGUAGES:
        violations.append(
            FieldViolation(field="language", description="unsupported language, expected eigen-lang")
        )

    violations.extend(_validate_input_oneof(req, source_field="source", source_ref_field="source_ref"))
    return violations


def validate_compile_job(req) -> List[FieldViolation]:
    violations: list[FieldViolation] = []

    if not req.job_id:
        violations.append(FieldViolation(field="job_id", description="field is required"))

    violations.extend(validate_compile_circuit(req))
    return violations
