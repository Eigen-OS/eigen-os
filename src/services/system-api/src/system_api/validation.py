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
from .security import load_security_config

_JOBSPEC_YAML_KEYS = {"jobspec_yaml", "job_yaml", "job.spec.yaml"}


def validate_submit_job(req) -> List[FieldViolation]:
    violations: List[FieldViolation] = []
    cfg = load_security_config()

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
            elif len(req.eigen_lang.source) > cfg.max_program_source_bytes:
                violations.append(
                    FieldViolation(
                        field="eigen_lang.source",
                        description=(
                            "source exceeds max allowed size "
                            f"({cfg.max_program_source_bytes} bytes)"
                        ),
                    )
                )
        elif program == "qasm":
            if not req.qasm.source:
                violations.append(FieldViolation(field="qasm.source", description="source must be non-empty"))
            elif len(req.qasm.source) > cfg.max_program_source_bytes:
                violations.append(
                    FieldViolation(
                        field="qasm.source",
                        description=(
                            "source exceeds max allowed size "
                            f"({cfg.max_program_source_bytes} bytes)"
                        ),
                    )
                )
            violations.extend(required_string(req.qasm.version, "qasm.version"))
        elif program == "aqo_ref":
            violations.extend(required_string(req.aqo_ref.qfs_ref, "aqo_ref.qfs_ref"))

    for key in _JOBSPEC_YAML_KEYS:
        yaml_payload = req.metadata.get(key, "")
        if len(yaml_payload.encode("utf-8")) > cfg.max_jobspec_yaml_bytes:
            violations.append(
                FieldViolation(
                    field=f"metadata[{key}]",
                    description=(
                        "jobspec yaml exceeds max allowed size "
                        f"({cfg.max_jobspec_yaml_bytes} bytes)"
                    ),
                )
            )
            break
        
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
