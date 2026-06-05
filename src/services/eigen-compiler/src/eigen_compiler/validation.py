"""Request validation for eigen-compiler RPCs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from .errors import FieldViolation

_SUPPORTED_LANGUAGES = {"eigen-lang"}
_SUPPORTED_DISTRIBUTED_TARGETS = {"cluster"}
_SUPPORTED_QUEUE_PROVIDERS = {"memory", "redis", "sqs"}
_SUPPORTED_TOPOLOGY_HINTS = {"data_parallel", "pipeline"}

def _max_source_bytes() -> int:
    raw = os.getenv("EIGEN_COMPILER_MAX_SOURCE_BYTES", "262144")
    try:
        value = int(raw)
    except ValueError:
        return 262_144
    return max(1, value)


def _validate_source_inputs(req) -> list[FieldViolation]:
    violations: list[FieldViolation] = []
    source_present = bool(req.source)
    source_ref_present = bool(req.source_ref)

    if not source_present and not source_ref_present:
        violations.append(
            FieldViolation(field="input", description="input or source_ref is required")
        )
        return violations

    if source_ref_present:
        normalized = req.source_ref
        for prefix in ("qfs://", "circuitfs://"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break
        ref_path = Path(normalized)
        if any(part == ".." for part in ref_path.parts):
            violations.append(
                FieldViolation(
                    field="source_ref",
                    description="source_ref must not contain path traversal segments",
                )
            )

    if source_ref_present and not req.source_ref:
        violations.append(
            FieldViolation(field="source_ref", description="source_ref must be non-empty")
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

    violations.extend(_validate_source_inputs(req))

    if req.source and len(req.source) > source_limit:
        violations.append(
            FieldViolation(
                field="source",
                description=f"source exceeds max allowed size ({source_limit} bytes)",
            )
        )

    if req.HasField("request_metadata"):
        md = req.request_metadata
        required = {
            "request_metadata.request_id": md.request_id,
            "request_metadata.trace_id": md.trace_id,
            "request_metadata.traceparent": md.traceparent,
            "request_metadata.deadline": md.deadline,
            "request_metadata.retry_policy": md.retry_policy,
            "request_metadata.security_context": md.security_context,
            "request_metadata.tenant_id": md.tenant_id,
            "request_metadata.project_id": md.project_id,
        }
        for field, value in required.items():
            if not value:
                violations.append(FieldViolation(field=field, description="field is required"))

    violations.extend(_validate_distributed_options(req.options))
    return violations


def validate_compile_job(req) -> List[FieldViolation]:
    violations: list[FieldViolation] = []

    if not req.job_id:
        violations.append(FieldViolation(field="job_id", description="field is required"))

    violations.extend(validate_compile_circuit(req))
    return violations


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _validate_distributed_options(options: dict[str, str]) -> list[FieldViolation]:
    violations: list[FieldViolation] = []
    enabled_raw = options.get("distributed.enabled", "false")
    enabled = _parse_bool(enabled_raw)
    if enabled is None:
        violations.append(
            FieldViolation(
                field="options.distributed.enabled",
                description="distributed.enabled must be a boolean",
            )
        )
        return violations

    target = options.get("distributed.target")
    if target and target not in _SUPPORTED_DISTRIBUTED_TARGETS:
        violations.append(
            FieldViolation(
                field="options.distributed.target",
                description="unsupported distributed target, expected cluster",
            )
        )

    partition_count_raw = options.get("distributed.partition_count")
    partition_count: int | None = None
    if partition_count_raw:
        try:
            partition_count = int(partition_count_raw)
        except ValueError:
            violations.append(
                FieldViolation(
                    field="options.distributed.partition_count",
                    description="distributed.partition_count must be an integer",
                )
            )
        else:
            if partition_count < 1:
                violations.append(
                    FieldViolation(
                        field="options.distributed.partition_count",
                        description="distributed.partition_count must be >= 1",
                    )
                )

    queue_provider = options.get("distributed.queue_provider")
    if queue_provider and queue_provider not in _SUPPORTED_QUEUE_PROVIDERS:
        violations.append(
            FieldViolation(
                field="options.distributed.queue_provider",
                description="unsupported queue provider, expected one of: memory, redis, sqs",
            )
        )

    topology_hint = options.get("distributed.topology_hint")
    if topology_hint and topology_hint not in _SUPPORTED_TOPOLOGY_HINTS:
        violations.append(
            FieldViolation(
                field="options.distributed.topology_hint",
                description="unsupported topology hint, expected one of: data_parallel, pipeline",
            )
        )

    if not enabled:
        for key in (
            "distributed.target",
            "distributed.partition_count",
            "distributed.queue_provider",
            "distributed.topology_hint",
        ):
            if key in options:
                violations.append(
                    FieldViolation(
                        field=f"options.{key}",
                        description=f"{key} requires distributed.enabled=true",
                    )
                )
    elif target is None:
        violations.append(
            FieldViolation(
                field="options.distributed.target",
                description="distributed.target is required when distributed.enabled=true",
            )
        )

    return violations
