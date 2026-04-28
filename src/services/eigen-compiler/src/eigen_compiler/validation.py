"""Request validation for eigen-compiler RPCs."""

from __future__ import annotations

import os
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
