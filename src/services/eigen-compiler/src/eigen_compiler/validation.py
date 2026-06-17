"""Request validation for eigen-compiler RPCs."""

from __future__ import annotations

from collections.abc import Iterable
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List

from .errors import FieldViolation

_SUPPORTED_LANGUAGES = {"eigen-lang"}
_SUPPORTED_DISTRIBUTED_TARGETS = {"cluster"}
_SUPPORTED_QUEUE_PROVIDERS = {"memory", "redis", "sqs"}
_SUPPORTED_TOPOLOGY_HINTS = {"data_parallel", "pipeline"}
_SUPPORTED_WORKLOAD_KINDS = {
    "QuantumJob",
    "HybridWorkflow",
    "DistributedJob",
    "BenchmarkJob",
    "PipelineJob",
    "ReplayJob",
}


_SUPPORTED_BACKEND_TARGETS = {
    "sim:local",
    "backend:quantum",
    "backend:cluster",
    "cluster:auto",
    "cluster:gpu",
    "cluster:quantum",
    "runtime:auto",
    "runtime:latency",
    "runtime:cost",
    "runtime:availability",
    "runtime:deterministic",
    "ibm:qpu",
    "aws:braket",
    "azure:quantum",
}

_PROFILE_ALLOWED_BACKEND_TARGET_CLASSES: dict[str, tuple[str, ...]] = {
    "QuantumJob": ("implicit", "simulator", "provider", "policy"),
    "HybridWorkflow": ("implicit", "simulator", "provider", "policy", "distributed"),
    "DistributedJob": ("distributed",),
    "BenchmarkJob": ("simulator", "provider", "policy", "distributed"),
    "PipelineJob": ("implicit", "simulator", "provider", "policy", "distributed"),
    "ReplayJob": ("implicit", "simulator", "provider", "policy", "distributed"),
}

_PROFILE_EMISSION_MODES: dict[str, tuple[str, ...]] = {
    "QuantumJob": ("aqo_json", "aqo_json+driver_metadata"),
    "HybridWorkflow": ("aqo_json", "aqo_json+driver_metadata", "aqo_json+runtime_metadata"),
    "DistributedJob": ("aqo_json+topology_metadata", "aqo_json+runtime_metadata"),
    "BenchmarkJob": ("aqo_json", "aqo_json+benchmark_metadata"),
    "PipelineJob": ("aqo_json", "aqo_json+handoff_metadata"),
    "ReplayJob": ("aqo_json", "aqo_json+replay_metadata"),
}


@dataclass(frozen=True)
class WorkloadProfile:
    kind: str
    required_semantic_checks: tuple[str, ...]
    allowed_rewrites: tuple[str, ...]
    forbidden_transformations: tuple[str, ...]
    target_expectations: tuple[str, ...]
    replay_or_benchmark_constraints: tuple[str, ...]
    observability_requirements: tuple[str, ...]


_WORKLOAD_PROFILE_CATALOG: dict[str, WorkloadProfile] = {
    "QuantumJob": WorkloadProfile(
        kind="QuantumJob",
        required_semantic_checks=(
            "compiler.semantic.ast_subset",
            "compiler.semantic.single_entrypoint",
            "compiler.profile.quantum.no_adaptive_markers",
        ),
        allowed_rewrites=(
            "compiler.rewrite.measure_normalization",
            "compiler.rewrite.constant_theta_projection",
        ),
        forbidden_transformations=(
            "compiler.rewrite.distributed_topology",
            "compiler.rewrite.benchmark_materialization",
            "compiler.rewrite.pipeline_handoff",
            "compiler.rewrite.replay_materialization",
        ),
        target_expectations=("sim:local", "backend:quantum"),
        replay_or_benchmark_constraints=("benchmark=false", "replay=false"),
        observability_requirements=("request_id", "trace_id", "traceparent"),
    ),
    "HybridWorkflow": WorkloadProfile(
        kind="HybridWorkflow",
        required_semantic_checks=(
            "compiler.semantic.ast_subset",
            "compiler.semantic.single_entrypoint",
            "compiler.profile.hybrid.allow_expectation_and_minimize",
        ),
        allowed_rewrites=(
            "compiler.rewrite.hybrid_annotation_projection",
            "compiler.rewrite.expectation_annotation_projection",
            "compiler.rewrite.measure_normalization",
        ),
        forbidden_transformations=(
            "compiler.rewrite.pipeline_handoff",
            "compiler.rewrite.replay_materialization",
        ),
        target_expectations=("sim:local", "backend:cluster"),
        replay_or_benchmark_constraints=("benchmark=false", "replay=false"),
        observability_requirements=("request_id", "trace_id", "traceparent"),
    ),
    "DistributedJob": WorkloadProfile(
        kind="DistributedJob",
        required_semantic_checks=(
            "compiler.semantic.ast_subset",
            "compiler.semantic.single_entrypoint",
            "compiler.profile.distributed.explicit_topology",
        ),
        allowed_rewrites=(
            "compiler.rewrite.distributed_topology_projection",
            "compiler.rewrite.partition_hint_projection",
        ),
        forbidden_transformations=(
            "compiler.rewrite.benchmark_materialization",
            "compiler.rewrite.pipeline_handoff",
            "compiler.rewrite.replay_materialization",
        ),
        target_expectations=("cluster:auto", "cluster:gpu", "cluster:quantum"),
        replay_or_benchmark_constraints=("distributed.enabled=true", "partition_count>=1"),
        observability_requirements=("request_id", "trace_id", "traceparent", "tenant_id", "project_id"),
    ),
    "BenchmarkJob": WorkloadProfile(
        kind="BenchmarkJob",
        required_semantic_checks=(
            "compiler.semantic.ast_subset",
            "compiler.semantic.single_entrypoint",
            "compiler.profile.benchmark.fixed_seed",
        ),
        allowed_rewrites=(),
        forbidden_transformations=(
            "compiler.rewrite.distributed_topology",
            "compiler.rewrite.pipeline_handoff",
            "compiler.rewrite.replay_materialization",
            "compiler.rewrite.adaptive_minimize",
        ),
        target_expectations=("explicit backend target",),
        replay_or_benchmark_constraints=("seed required", "target required"),
        observability_requirements=("request_id", "trace_id", "traceparent", "tenant_id", "project_id"),
    ),
    "PipelineJob": WorkloadProfile(
        kind="PipelineJob",
        required_semantic_checks=(
            "compiler.semantic.ast_subset",
            "compiler.semantic.single_entrypoint",
            "compiler.profile.pipeline.explicit_handoff",
        ),
        allowed_rewrites=("compiler.rewrite.pipeline_handoff_projection",),
        forbidden_transformations=(
            "compiler.rewrite.benchmark_materialization",
            "compiler.rewrite.replay_materialization",
        ),
        target_expectations=("source_ref required", "handoff_ref required"),
        replay_or_benchmark_constraints=("stage_id required",),
        observability_requirements=("request_id", "trace_id", "traceparent", "tenant_id", "project_id"),
    ),
    "ReplayJob": WorkloadProfile(
        kind="ReplayJob",
        required_semantic_checks=(
            "compiler.semantic.ast_subset",
            "compiler.semantic.single_entrypoint",
            "compiler.profile.replay.canonical_source_ref",
        ),
        allowed_rewrites=("compiler.rewrite.replay_lineage_projection",),
        forbidden_transformations=(
            "compiler.rewrite.adaptive_minimize",
            "compiler.rewrite.pipeline_handoff",
        ),
        target_expectations=("source_ref required",),
        replay_or_benchmark_constraints=("replay enabled", "source_ref required"),
        observability_requirements=("request_id", "trace_id", "traceparent", "tenant_id", "project_id"),
    ),
}


def _normalize_options(options: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in sorted((options or {}).items()):
        normalized[str(key)] = str(value)
    return normalized


def _first_option(options: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = options.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _profile_violation(rule: str, field: str, description: str) -> FieldViolation:
    return FieldViolation(field=field, description=f"{rule}: {description}")


def _backend_target_class(target: str | None) -> str:
    if not target:
        return "implicit"
    if target == "sim:local":
        return "simulator"
    if target in {"cluster:auto", "cluster:gpu", "cluster:quantum"}:
        return "distributed"
    if target in {"backend:quantum", "ibm:qpu", "aws:braket", "azure:quantum"}:
        return "provider"
    if target in {"backend:cluster", "runtime:auto", "runtime:latency", "runtime:cost", "runtime:availability", "runtime:deterministic"}:
        return "policy"
    return "unknown"


def _resolve_backend_target(normalized: dict[str, str]) -> tuple[str, str, str]:
    explicit = _first_option(normalized, "spec.workload.backend_target", "target", "runtime.target")
    distributed_enabled = _parse_bool(normalized.get("distributed.enabled", "false")) is True
    distributed_target = _first_option(normalized, "distributed.target")

    if explicit:
        return explicit, _backend_target_class(explicit), "explicit"
    if distributed_enabled or distributed_target is not None:
        return distributed_target or "cluster", "distributed", "distributed"
    return "", "implicit", "implicit"


def _profile_backend_targets(profile_kind: str) -> tuple[str, ...]:
    if profile_kind == "DistributedJob":
        return ("cluster:auto", "cluster:gpu", "cluster:quantum")
    if profile_kind in {"QuantumJob", "HybridWorkflow", "BenchmarkJob", "PipelineJob", "ReplayJob"}:
        return (
            "sim:local",
            "backend:quantum",
            "backend:cluster",
            "cluster:auto",
            "cluster:gpu",
            "cluster:quantum",
            "runtime:auto",
            "runtime:latency",
            "runtime:cost",
            "runtime:availability",
            "runtime:deterministic",
            "ibm:qpu",
            "aws:braket",
            "azure:quantum",
        )
    return ()


def backend_contract_payload(profile: WorkloadProfile, options: dict[str, str] | None) -> dict[str, object]:
    normalized = _normalize_options(options)
    declared_backend_target, backend_target_class, target_resolution = _resolve_backend_target(normalized)
    distributed_enabled = _parse_bool(normalized.get("distributed.enabled", "false")) is True
    distributed_target = _first_option(normalized, "distributed.target")
    emission_mode = (
        "aqo_json+topology_metadata"
        if backend_target_class == "distributed"
        else "aqo_json+driver_metadata"
        if backend_target_class == "provider"
        else "aqo_json+policy_metadata"
        if backend_target_class == "policy"
        else "aqo_json"
    )
    return {
        "contract_version": "1.0.0",
        "workload_profile": profile.kind,
        "declared_backend_target": declared_backend_target,
        "backend_target_class": backend_target_class,
        "target_resolution": target_resolution,
        "allowed_backend_target_classes": (
            ["implicit", "simulator", "provider", "policy", "distributed"]
            if profile.kind != "DistributedJob"
            else ["distributed"]
        ),
        "allowed_backend_targets": list(_profile_backend_targets(profile.kind)),
        "allowed_emission_modes": list(_profile_emission_modes(profile.kind)),
        "selected_emission_mode": emission_mode,
        "backend_specific_decisions": {
            "distributed.enabled": distributed_enabled,
            "distributed.target": distributed_target or "",
            "requires_explicit_target": profile.kind in {"BenchmarkJob", "DistributedJob"},
            "core_ir_backend_agnostic": True,
        },
    }


def _profile_emission_modes(profile_kind: str) -> tuple[str, ...]:
    if profile_kind == "DistributedJob":
        return ("aqo_json+topology_metadata", "aqo_json+runtime_metadata")
    if profile_kind == "BenchmarkJob":
        return ("aqo_json", "aqo_json+benchmark_metadata")
    if profile_kind == "PipelineJob":
        return ("aqo_json", "aqo_json+handoff_metadata")
    if profile_kind == "ReplayJob":
        return ("aqo_json", "aqo_json+replay_metadata")
    if profile_kind == "HybridWorkflow":
        return ("aqo_json", "aqo_json+driver_metadata", "aqo_json+runtime_metadata")
    return ("aqo_json", "aqo_json+driver_metadata")


def _backend_contract_payload(profile: WorkloadProfile, options: dict[str, str] | None) -> dict[str, object]:
    normalized = _normalize_options(options)
    declared_backend_target, backend_target_class, target_resolution = _resolve_backend_target(normalized)
    distributed_enabled = _parse_bool(normalized.get("distributed.enabled", "false")) is True
    distributed_target = _first_option(normalized, "distributed.target")
    emission_mode = (
        "aqo_json+topology_metadata"
        if backend_target_class == "distributed"
        else "aqo_json+driver_metadata"
        if backend_target_class == "provider"
        else "aqo_json+policy_metadata"
        if backend_target_class == "policy"
        else "aqo_json"
    )
    return {
        "contract_version": "1.0.0",
        "workload_profile": profile.kind,
        "declared_backend_target": declared_backend_target,
        "backend_target_class": backend_target_class,
        "target_resolution": target_resolution,
        "allowed_backend_target_classes": list(_PROFILE_ALLOWED_BACKEND_TARGET_CLASSES.get(profile.kind, ())),
        "allowed_backend_targets": list(_profile_backend_targets(profile.kind)),
        "allowed_emission_modes": list(_profile_emission_modes(profile.kind)),
        "selected_emission_mode": emission_mode,
        "backend_specific_decisions": {
            "distributed.enabled": distributed_enabled,
            "distributed.target": distributed_target or "",
            "requires_explicit_target": profile.kind in {"BenchmarkJob", "DistributedJob"},
            "core_ir_backend_agnostic": True,
        },
    }


def workload_profile_payload(profile: WorkloadProfile) -> dict[str, object]:
    return {
        "kind": profile.kind,
        "required_semantic_checks": list(profile.required_semantic_checks),
        "allowed_rewrites": list(profile.allowed_rewrites),
        "forbidden_transformations": list(profile.forbidden_transformations),
        "target_expectations": list(profile.target_expectations),
        "replay_or_benchmark_constraints": list(profile.replay_or_benchmark_constraints),
        "observability_requirements": list(profile.observability_requirements),
        "backend_targets": list(_profile_backend_targets(profile.kind)),
        "emission_modes": list(_profile_emission_modes(profile.kind)),
    }


def resolve_workload_profile(
    options: dict[str, str] | None,
    *,
    has_expectation: bool,
    has_minimize: bool,
) -> tuple[WorkloadProfile, tuple[FieldViolation, ...]]:
    normalized = _normalize_options(options)
    selection_violations: list[FieldViolation] = []

    explicit_kind = _first_option(normalized, "spec.workload.kind", "workload.kind")
    if explicit_kind:
        if explicit_kind not in _SUPPORTED_WORKLOAD_KINDS:
            selection_violations.append(
                _profile_violation(
                    "compiler.profile.selection.unknown",
                    "options.spec.workload.kind",
                    f"unsupported workload profile '{explicit_kind}'",
                )
            )
            return _WORKLOAD_PROFILE_CATALOG["QuantumJob"], tuple(selection_violations)
        return _WORKLOAD_PROFILE_CATALOG[explicit_kind], ()

    runtime_mode = _first_option(normalized, "runtime.mode", "spec.runtime.mode") or ""
    if runtime_mode == "distributed" or _parse_bool(normalized.get("distributed.enabled", "false")) is True:
        return _WORKLOAD_PROFILE_CATALOG["DistributedJob"], ()
    if runtime_mode == "benchmark" or _first_option(
        normalized, "spec.workload.seed", "workload.seed", "benchmark.seed"
    ) is not None:
        return _WORKLOAD_PROFILE_CATALOG["BenchmarkJob"], ()
    if runtime_mode == "pipeline" or _first_option(
        normalized, "spec.workload.pipeline.handoff_ref", "workload.pipeline.handoff_ref"
    ) is not None:
        return _WORKLOAD_PROFILE_CATALOG["PipelineJob"], ()
    if runtime_mode == "replay" or _parse_bool(
        _first_option(normalized, "spec.workload.replay.enabled", "workload.replay.enabled") or "false"
    ) is True:
        return _WORKLOAD_PROFILE_CATALOG["ReplayJob"], ()
    if runtime_mode == "hybrid" or has_expectation or has_minimize:
        return _WORKLOAD_PROFILE_CATALOG["HybridWorkflow"], ()
    return _WORKLOAD_PROFILE_CATALOG["QuantumJob"], ()


def validate_workload_profile(
    profile: WorkloadProfile,
    options: dict[str, str] | None,
    *,
    source_ref_present: bool,
    has_expectation: bool,
    has_minimize: bool,
) -> tuple[FieldViolation, ...]:
    normalized = _normalize_options(options)
    violations: list[FieldViolation] = []

    def add(rule: str, field: str, description: str) -> None:
        violations.append(
            FieldViolation(
                field=field,
                description=description,
                stage="eigen_dpda",
                rule=rule,
                pass_name="eigen_dpda",
            )
        )

    distributed_enabled = _parse_bool(normalized.get("distributed.enabled", "false")) is True
    seed_value = _first_option(normalized, "spec.workload.seed", "workload.seed", "benchmark.seed")
    backend_target = _first_option(normalized, "spec.workload.backend_target", "target", "runtime.target")
    declared_backend_target, backend_target_class, _target_resolution = _resolve_backend_target(normalized)
    pipeline_handoff_ref = _first_option(
        normalized, "spec.workload.pipeline.handoff_ref", "workload.pipeline.handoff_ref"
    )
    pipeline_stage_id = _first_option(normalized, "spec.workload.pipeline.stage_id", "workload.pipeline.stage_id")
    replay_enabled = _parse_bool(_first_option(normalized, "spec.workload.replay.enabled", "workload.replay.enabled") or "false") is True

    if profile.kind == "QuantumJob":
        if distributed_enabled or any(
            key in normalized
            for key in (
                "distributed.target",
                "distributed.partition_count",
                "distributed.queue_provider",
                "distributed.topology_hint",
            )
        ):
            add(
                "compiler.profile.quantum.no_distributed_options",
                "options.distributed.enabled",
                "QuantumJob forbids distributed compilation options",
            )
        if seed_value is not None:
            add(
                "compiler.profile.quantum.no_benchmark_metadata",
                "options.spec.workload.seed",
                "QuantumJob forbids benchmark seed metadata",
            )
        if pipeline_handoff_ref is not None or pipeline_stage_id is not None:
            add(
                "compiler.profile.quantum.no_pipeline_handoff",
                "options.spec.workload.pipeline.handoff_ref",
                "QuantumJob forbids pipeline handoff references",
            )
        if replay_enabled:
            add(
                "compiler.profile.quantum.no_replay_marker",
                "options.spec.workload.replay.enabled",
                "QuantumJob forbids replay markers",
            )
        if has_expectation or has_minimize:
            add(
                "compiler.profile.quantum.no_hybrid_markers",
                "source",
                "QuantumJob cannot be used with ExpectationValue or minimize markers",
            )
        if backend_target_class == "distributed":
            add(
                "compiler.backend.quantum.no_distributed_target",
                "options.spec.workload.backend_target",
                "QuantumJob cannot target distributed cluster backends",
            )

    elif profile.kind == "HybridWorkflow":
        if distributed_enabled or any(
            key in normalized
            for key in (
                "distributed.target",
                "distributed.partition_count",
                "distributed.queue_provider",
                "distributed.topology_hint",
            )
        ):
            add(
                "compiler.profile.hybrid.no_distributed_options",
                "options.distributed.enabled",
                "HybridWorkflow forbids distributed compilation options",
            )
        if seed_value is not None:
            add(
                "compiler.profile.hybrid.no_benchmark_metadata",
                "options.spec.workload.seed",
                "HybridWorkflow does not accept benchmark seed metadata",
            )
        if pipeline_handoff_ref is not None or pipeline_stage_id is not None:
            add(
                "compiler.profile.hybrid.no_pipeline_handoff",
                "options.spec.workload.pipeline.handoff_ref",
                "HybridWorkflow does not accept pipeline handoff references",
            )
        if replay_enabled:
            add(
                "compiler.profile.hybrid.no_replay_marker",
                "options.spec.workload.replay.enabled",
                "HybridWorkflow does not accept replay markers",
            )

    elif profile.kind == "DistributedJob":
        if not distributed_enabled:
            add(
                "compiler.profile.distributed.requires_enabled",
                "options.distributed.enabled",
                "DistributedJob requires distributed.enabled=true",
            )
        if _first_option(normalized, "distributed.target") is None:
            add(
                "compiler.profile.distributed.requires_target",
                "options.distributed.target",
                "DistributedJob requires distributed.target",
            )
        partition_count = _first_option(normalized, "distributed.partition_count")
        if partition_count is None:
            add(
                "compiler.profile.distributed.requires_partition_count",
                "options.distributed.partition_count",
                "DistributedJob requires distributed.partition_count",
            )
        else:
            try:
                if int(partition_count) < 1:
                    raise ValueError
            except ValueError:
                add(
                    "compiler.profile.distributed.invalid_partition_count",
                    "options.distributed.partition_count",
                    "distributed.partition_count must be a positive integer",
                )

    elif profile.kind == "BenchmarkJob":
        if seed_value is None:
            add(
                "compiler.profile.benchmark.requires_seed",
                "options.spec.workload.seed",
                "BenchmarkJob requires spec.workload.seed",
            )
        if seed_value is not None:
            try:
                int(seed_value)
            except ValueError:
                add(
                    "compiler.profile.benchmark.invalid_seed",
                    "options.spec.workload.seed",
                    "BenchmarkJob seed must be an integer",
                )
        if backend_target is None and backend_target_class == "implicit":
            add(
                "compiler.profile.benchmark.requires_backend_target",
                "options.spec.workload.backend_target",
                "BenchmarkJob requires an explicit backend target",
            )
        elif backend_target_class == "unknown":
            add(
                "compiler.backend.unknown_target",
                "options.spec.workload.backend_target",
                f"unsupported backend target '{declared_backend_target}'",
            )
        if backend_target is None:
            add(
                "compiler.profile.benchmark.requires_backend_target",
                "options.spec.workload.backend_target",
                "BenchmarkJob requires an explicit backend target",
            )
        if distributed_enabled:
            add(
                "compiler.profile.benchmark.no_distributed_options",
                "options.distributed.enabled",
                "BenchmarkJob forbids distributed compilation",
            )
        if has_minimize:
            add(
                "compiler.profile.benchmark.no_adaptive_rewrite",
                "source",
                "BenchmarkJob forbids minimize-based adaptive rewrites",
            )

    elif profile.kind == "PipelineJob":
        if pipeline_handoff_ref is None:
            add(
                "compiler.profile.pipeline.requires_handoff_ref",
                "options.spec.workload.pipeline.handoff_ref",
                "PipelineJob requires spec.workload.pipeline.handoff_ref",
            )
        if pipeline_stage_id is None:
            add(
                "compiler.profile.pipeline.requires_stage_id",
                "options.spec.workload.pipeline.stage_id",
                "PipelineJob requires spec.workload.pipeline.stage_id",
            )
        if not source_ref_present:
            add(
                "compiler.profile.pipeline.requires_source_ref",
                "source_ref",
                "PipelineJob requires source_ref so the handoff lineage can be reconstructed",
            )
        if has_minimize:
            add(
                "compiler.profile.pipeline.no_adaptive_rewrite",
                "source",
                "PipelineJob forbids minimize-based adaptive rewrites",
            )
        if declared_backend_target and backend_target_class == "unknown":
            add(
                "compiler.backend.unknown_target",
                "options.spec.workload.backend_target",
                f"unsupported backend target '{declared_backend_target}'",
            )

    elif profile.kind == "ReplayJob":
        if not replay_enabled:
            add(
                "compiler.profile.replay.requires_enabled",
                "options.spec.workload.replay.enabled",
                "ReplayJob requires spec.workload.replay.enabled=true",
            )
        if not source_ref_present:
            add(
                "compiler.profile.replay.requires_source_ref",
                "source_ref",
                "ReplayJob requires source_ref so canonical inputs can be replayed",
            )
        if has_minimize:
            add(
                "compiler.profile.replay.no_adaptive_rewrite",
                "source",
                "ReplayJob forbids minimize-based adaptive rewrites",
            )

        if profile.kind == "DistributedJob" and backend_target_class != "distributed":
            add(
                "compiler.profile.distributed.target_mismatch",
                "options.spec.workload.backend_target",
                f"DistributedJob requires a distributed backend target, got '{declared_backend_target or 'implicit'}'",
            )
        if declared_backend_target and backend_target_class == "unknown":
            add(
                "compiler.backend.unknown_target",
                "options.spec.workload.backend_target",
                f"unsupported backend target '{declared_backend_target}'",
            )

    if profile.kind == "DistributedJob" and declared_backend_target and backend_target_class != "distributed":
        add(
            "compiler.backend.distributed.target_mismatch",
            "options.spec.workload.backend_target",
            f"DistributedJob requires a distributed backend target, got '{declared_backend_target}'",
        )
        if declared_backend_target and backend_target_class == "unknown":
            add(
                "compiler.backend.unknown_target",
                "options.spec.workload.backend_target",
                f"unsupported backend target '{declared_backend_target}'",
            )

    return tuple(violations)


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
