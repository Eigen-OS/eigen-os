"""Request validation for System API (MVP).

Validation rules are intentionally minimal and focus on **required fields**.

All validation failures MUST be reported as:
- gRPC status: INVALID_ARGUMENT
- Details: google.rpc.BadRequest.FieldViolation entries

See docs/reference/error-model.md.
"""

from __future__ import annotations

from typing import List

from .errors import FieldViolation, positive_int, required_string


def validate_submit_job(req) -> List[FieldViolation]:
    violations: List[FieldViolation] = []

    violations.extend(required_string(req.name, "name"))
    violations.extend(required_string(req.target, "target"))

    program = req.WhichOneof("program")
    if program is None:
        violations.append(FieldViolation(field="program", description="oneof program is required"))
    else:
        # A tiny bit of sanity validation for program payload.
        if program == "eigen_lang":
            violations.extend(required_string(req.eigen_lang.entrypoint, "eigen_lang.entrypoint"))
            if not req.eigen_lang.source:
                violations.append(
                    FieldViolation(field="eigen_lang.source", description="source must be non-empty")
                )
        elif program == "qasm":
            if not req.qasm.source:
                violations.append(FieldViolation(field="qasm.source", description="source must be non-empty"))
            violations.extend(required_string(req.qasm.version, "qasm.version"))
        elif program == "aqo_ref":
            violations.extend(required_string(req.aqo_ref.qfs_ref, "aqo_ref.qfs_ref"))

    return violations


def validate_job_id(req, field_name: str = "job_id") -> List[FieldViolation]:
    return list(required_string(getattr(req, field_name, ""), field_name))


def validate_device_id(req, field_name: str = "device_id") -> List[FieldViolation]:
    return list(required_string(getattr(req, field_name, ""), field_name))


def validate_reserve_device(req) -> List[FieldViolation]:
    violations: List[FieldViolation] = []
    violations.extend(required_string(req.device_id, "device_id"))
    violations.extend(positive_int(req.ttl_seconds, "ttl_seconds"))
    return violations
