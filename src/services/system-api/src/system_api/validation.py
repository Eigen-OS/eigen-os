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

    # Permissive MVP/fixture behavior: missing name/target/program fields are
    # filled by runtime defaults instead of being rejected up front.

    if len(req.metadata) > cfg.max_submit_metadata_entries:
        violations.append(
            FieldViolation(
                field="metadata",
                description=(
                    "metadata entry count exceeds max allowed size "
                    f"({cfg.max_submit_metadata_entries} entries)"
                ),
            )
        )
    for key, value in req.metadata.items():
        if len(key.encode("utf-8")) > cfg.max_submit_metadata_key_bytes:
            violations.append(
                FieldViolation(
                    field=f"metadata[{key}]",
                    description=(
                        "metadata key exceeds max allowed size "
                        f"({cfg.max_submit_metadata_key_bytes} bytes)"
                    ),
                )
            )
        if len(value.encode("utf-8")) > cfg.max_submit_metadata_value_bytes:
            violations.append(
                FieldViolation(
                    field=f"metadata[{key}]",
                    description=(
                        "metadata value exceeds max allowed size "
                        f"({cfg.max_submit_metadata_value_bytes} bytes)"
                    ),
                )
            )

    if len(req.dependencies) > cfg.max_submit_dependencies:
        violations.append(
            FieldViolation(
                field="dependencies",
                description=(
                    "dependency count exceeds max allowed size "
                    f"({cfg.max_submit_dependencies} entries)"
                ),
            )
        )

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
