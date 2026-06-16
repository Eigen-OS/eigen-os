"""JobSpec parser/normalizer for SubmitJobRequest canonical mapping.

Implements the Product 1.0 JobSpec contract from docs/reference/jobspec.md and
keeps documented v0.1 migration compatibility for MVP clients.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .errors import FieldViolation
from .proto_gen import ensure_generated
from .security import load_security_config

ensure_generated()
from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required for job.yaml parsing") from exc


JOBSPEC_VERSION = "1.0.0"
JOBSPEC_API_VERSION = "eigen.os/v1"
LEGACY_JOBSPEC_API_VERSION = "eigen.os/v0.1"
JOBSPEC_KIND = "QuantumJob"
JOBSPEC_WORKLOAD_KINDS = (
    "QuantumJob",
    "HybridWorkflow",
    "DistributedJob",
    "BenchmarkJob",
    "PipelineJob",
    "ReplayJob",
)
JOBSPEC_WORKLOAD_KIND_DEFAULT = "QuantumJob"
JOBSPEC_WORKLOAD_EXECUTION_PROFILES = {
    "QuantumJob": "quantum",
    "HybridWorkflow": "hybrid",
    "DistributedJob": "distributed",
    "BenchmarkJob": "benchmark",
    "PipelineJob": "pipeline",
    "ReplayJob": "replay",
}
JOBSPEC_WORKLOAD_ENUM_NAMES = {
    "QuantumJob": "WORKLOAD_FAMILY_KIND_QUANTUM_JOB",
    "HybridWorkflow": "WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW",
    "DistributedJob": "WORKLOAD_FAMILY_KIND_DISTRIBUTED_JOB",
    "BenchmarkJob": "WORKLOAD_FAMILY_KIND_BENCHMARK_JOB",
    "PipelineJob": "WORKLOAD_FAMILY_KIND_PIPELINE_JOB",
    "ReplayJob": "WORKLOAD_FAMILY_KIND_REPLAY_JOB",
}
ACCEPTED_API_VERSIONS = {JOBSPEC_API_VERSION, LEGACY_JOBSPEC_API_VERSION}

REQUIRED_FIELD_MATRIX: dict[str, bool] = {
    "apiVersion": True,
    "kind": True,
    "metadata": True,
    "metadata.name": True,
    "metadata.labels": False,
    "metadata.annotations": False,
    "spec": True,
    "spec.program": False,
    "spec.program.path": False,
    "spec.program.source": False,
    "spec.program_path": False,
    "spec.entrypoint": False,
    "spec.target": True,
    "spec.compiler": False,
    "spec.compiler_options": False,
    "spec.metadata": False,
    "spec.dependencies": False,
    "scheduling": False,
    "security": False,
    "observability": False,
}


@dataclass
class JobSpecValidationError(Exception):
    violations: tuple[FieldViolation, ...]


def _is_safe_relative_path(path_value: str) -> bool:
    path = Path(path_value)
    if path.is_absolute():
        return False
    return ".." not in path.parts


def _resolve_safe_path(base_dir: Path, ref: str, field: str) -> tuple[Path | None, FieldViolation | None]:
    if not ref:
        return None, FieldViolation(field=field, description="field is required")
    if not _is_safe_relative_path(ref):
        return None, FieldViolation(field=field, description="path traversal is not allowed")

    candidate = (base_dir / ref).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError:
        return None, FieldViolation(field=field, description="path traversal is not allowed")
    return candidate, None


def _require_dict(value: Any, field: str, violations: list[FieldViolation]) -> dict[str, Any]:
    if not isinstance(value, dict):
        violations.append(FieldViolation(field=field, description="must be a mapping"))
        return {}
    return value


def _string_map(raw_map: Any, field: str, violations: list[FieldViolation]) -> dict[str, str]:
    if raw_map is None:
        return {}
    if not isinstance(raw_map, dict):
        violations.append(FieldViolation(field=field, description="must be map<string,string>"))
        return {}
    out: dict[str, str] = {}
    for k, v in raw_map.items():
        if not isinstance(k, str) or not isinstance(v, str):
            violations.append(FieldViolation(field=field, description="must be map<string,string>"))
            return {}
        out[k] = v
    return out


def _normalize_workload_contract(
    workload_raw: Any,
    target: str,
    metadata: dict[str, str],
    annotations: dict[str, str],
    violations: list[FieldViolation],
) -> dict[str, Any]:
    workload_declared = workload_raw is not None
    if workload_raw is None:
        workload_raw = {}
    if not isinstance(workload_raw, dict):
        violations.append(FieldViolation(field="spec.workload", description="must be a mapping"))
        workload_raw = {}

    kind = workload_raw.get("kind") or workload_raw.get("workload_kind")

    if kind is None:
        if workload_declared:
            violations.append(FieldViolation(field="spec.workload.kind", description="field is required"))
        kind = JOBSPEC_WORKLOAD_KIND_DEFAULT
    elif not isinstance(kind, str) or not kind.strip():
        violations.append(FieldViolation(field="spec.workload.kind", description="field is required"))
        kind = JOBSPEC_WORKLOAD_KIND_DEFAULT
    elif kind not in JOBSPEC_WORKLOAD_KINDS:
        violations.append(
            FieldViolation(
                field="spec.workload.kind",
                description=f"must be one of {', '.join(JOBSPEC_WORKLOAD_KINDS)}",
            )
        )
        kind = JOBSPEC_WORKLOAD_KIND_DEFAULT

    execution_profile = workload_raw.get("execution_profile") or workload_raw.get("executionProfile")
    if execution_profile is None:
        execution_profile = JOBSPEC_WORKLOAD_EXECUTION_PROFILES[kind]
    elif not isinstance(execution_profile, str):
        violations.append(FieldViolation(field="spec.workload.execution_profile", description="must be string"))
        execution_profile = JOBSPEC_WORKLOAD_EXECUTION_PROFILES[kind]

    replayable = workload_raw.get("replayable")
    if replayable is None:
        replayable = kind != "QuantumJob"
    elif not isinstance(replayable, bool):
        violations.append(FieldViolation(field="spec.workload.replayable", description="must be boolean"))
        replayable = kind != "QuantumJob"

    def _require_subdict(value: Any, field: str) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            violations.append(FieldViolation(field=field, description="must be a mapping"))
            return {}
        return value

    artifact_lineage_raw = _require_subdict(
        workload_raw.get("artifact_lineage") or workload_raw.get("artifactLineage"),
        "spec.workload.artifact_lineage",
    )
    observability_raw = _require_subdict(
        workload_raw.get("observability"),
        "spec.workload.observability",
    )
    security_raw = _require_subdict(
        workload_raw.get("security"),
        "spec.workload.security",
    )

    def _string_field(raw: dict[str, Any], key: str, field: str) -> str:
        value = raw.get(key, "")
        if value is None:
            return ""
        if not isinstance(value, str):
            violations.append(FieldViolation(field=field, description="must be string"))
            return ""
        return value.strip()

    artifact_lineage = {
        "root_ref": _string_field(artifact_lineage_raw, "root_ref", "spec.workload.artifact_lineage.root_ref"),
        "parent_ref": _string_field(artifact_lineage_raw, "parent_ref", "spec.workload.artifact_lineage.parent_ref"),
        "policy_snapshot_ref": _string_field(
            artifact_lineage_raw, "policy_snapshot_ref", "spec.workload.artifact_lineage.policy_snapshot_ref"
        ),
        "execution_ref": _string_field(artifact_lineage_raw, "execution_ref", "spec.workload.artifact_lineage.execution_ref"),
    }
    observability = {
        "traceparent": _string_field(observability_raw, "traceparent", "spec.workload.observability.traceparent"),
        "trace_id": _string_field(observability_raw, "trace_id", "spec.workload.observability.trace_id"),
        "trace_ref": _string_field(observability_raw, "trace_ref", "spec.workload.observability.trace_ref"),
        "emit_metrics": observability_raw.get("emit_metrics", False),
    }
    if not isinstance(observability["emit_metrics"], bool):
        violations.append(FieldViolation(field="spec.workload.observability.emit_metrics", description="must be boolean"))
        observability["emit_metrics"] = False

    security = {
        "tenant_id": _string_field(security_raw, "tenant_id", "spec.workload.security.tenant_id"),
        "project_id": _string_field(security_raw, "project_id", "spec.workload.security.project_id"),
        "service_identity": _string_field(security_raw, "service_identity", "spec.workload.security.service_identity"),
        "policy_snapshot_ref": _string_field(
            security_raw, "policy_snapshot_ref", "spec.workload.security.policy_snapshot_ref"
        ),
        "fail_closed": security_raw.get("fail_closed", kind == "ReplayJob"),
    }
    if not isinstance(security["fail_closed"], bool):
        violations.append(FieldViolation(field="spec.workload.security.fail_closed", description="must be boolean"))
        security["fail_closed"] = kind == "ReplayJob"

    backend_target = workload_raw.get("backend_target") or workload_raw.get("backendTarget") or target
    if backend_target is None:
        backend_target = ""
    if not isinstance(backend_target, str):
        violations.append(FieldViolation(field="spec.workload.backend_target", description="must be string"))
        backend_target = target

    return {
        "kind": kind,
        "execution_profile": execution_profile,
        "replayable": replayable,
        "artifact_lineage": artifact_lineage,
        "observability": observability,
        "security": security,
        "backend_target": backend_target.strip() if isinstance(backend_target, str) else target,
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _extract_program(spec: dict[str, Any], violations: list[FieldViolation]) -> tuple[str | None, str | None]:
    program_inline: str | None = None
    program_path: str | None = None
    program = spec.get("program")

    if isinstance(program, dict):
        raw_source = program.get("source")
        raw_path = program.get("path")
        if raw_source is not None:
            if isinstance(raw_source, str):
                program_inline = raw_source
            else:
                violations.append(FieldViolation(field="spec.program.source", description="must be string"))
        if raw_path is not None:
            if isinstance(raw_path, str):
                program_path = raw_path
            else:
                violations.append(FieldViolation(field="spec.program.path", description="must be string"))
    elif isinstance(program, str):
        # v0.1 migration form: spec.program is inline source.
        program_inline = program
    elif program is not None:
        violations.append(FieldViolation(field="spec.program", description="must be mapping"))

    legacy_path = spec.get("program_path")
    if legacy_path is not None:
        if isinstance(legacy_path, str):
            if program_path is not None:
                violations.append(FieldViolation(field="spec.program_path", description="cannot be set with spec.program.path"))
            program_path = legacy_path
        else:
            violations.append(FieldViolation(field="spec.program_path", description="must be string"))

    if program_inline is not None and program_path is not None:
        violations.append(FieldViolation(field="spec.program", description="cannot set both source and path"))
    return program_inline, program_path


def normalize_jobspec(jobspec_path: Path) -> dict[str, Any]:
    """Return the byte-stable JobSpec 1.0 normalized payload dictionary."""

    cfg = load_security_config()
    raw = jobspec_path.read_bytes()
    violations: list[FieldViolation] = []

    if len(raw) > cfg.max_jobspec_yaml_bytes:
        violations.append(
            FieldViolation(
                field="job.yaml",
                description=f"jobspec yaml exceeds max allowed size ({cfg.max_jobspec_yaml_bytes} bytes)",
            )
        )

    try:
        raw_text = raw.decode("utf-8")
        parsed = yaml.safe_load(raw_text)
    except UnicodeDecodeError:
        raw_text = ""
        parsed = None
        violations.append(FieldViolation(field="job.yaml", description="must be valid UTF-8"))
    except yaml.YAMLError:
        raw_text = ""
        parsed = None
        violations.append(FieldViolation(field="job.yaml", description="must be valid YAML"))

    root = _require_dict(parsed, "job.yaml", violations)

    api_version = root.get("apiVersion", "")
    if api_version not in ACCEPTED_API_VERSIONS:
        violations.append(FieldViolation(field="apiVersion", description="must be eigen.os/v1"))

    kind = root.get("kind", "")
    if kind != JOBSPEC_KIND:
        violations.append(FieldViolation(field="kind", description="must be QuantumJob"))

    metadata = _require_dict(root.get("metadata"), "metadata", violations)
    name = metadata.get("name", "")
    if not isinstance(name, str) or not name.strip():
        violations.append(FieldViolation(field="metadata.name", description="field is required"))

    labels = _string_map(metadata.get("labels"), "metadata.labels", violations)
    annotations = _string_map(metadata.get("annotations"), "metadata.annotations", violations)

    spec = _require_dict(root.get("spec"), "spec", violations)
    target = spec.get("target", "")
    workload = _normalize_workload_contract(spec.get("workload"), target, metadata, annotations, violations)
    if not isinstance(target, str) or not target.strip():
        violations.append(FieldViolation(field="spec.target", description="field is required"))
    
    priority = spec.get("priority", 50)
    if not isinstance(priority, int):
        violations.append(FieldViolation(field="spec.priority", description="must be int32"))
        priority = 50
    elif priority < 0 or priority > 100:
        violations.append(FieldViolation(field="spec.priority", description="must be in range [0,100]"))

    entrypoint = spec.get("entrypoint", "main")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        violations.append(FieldViolation(field="spec.entrypoint", description="must be non-empty string"))
        entrypoint = "main"

    program_inline, program_path = _extract_program(spec, violations)
    base_dir = jobspec_path.parent
    source_bytes = b""
    normalized_program: dict[str, Any] = {"entrypoint": entrypoint.strip()}

    if isinstance(program_inline, str) and program_inline.strip():
        source_bytes = program_inline.encode("utf-8")
        normalized_program["source"] = program_inline
    else:
        ref = "program.eigen.py" if program_path is None else program_path
        resolved, err = _resolve_safe_path(base_dir, ref, "spec.program.path")
        if err:
            violations.append(err)
        elif resolved is not None:
            try:
                source_bytes = resolved.read_bytes()
                normalized_program["path"] = ref
            except FileNotFoundError:
                violations.append(FieldViolation(field="spec.program.path", description="file not found"))

    if source_bytes and len(source_bytes) > cfg.max_program_source_bytes:
        violations.append(
            FieldViolation(
                field="eigen_lang.source",
                description=f"source exceeds max allowed size ({cfg.max_program_source_bytes} bytes)",
            )
        )
    if not source_bytes:
        violations.append(FieldViolation(field="spec.program", description="program source is required"))

    source_digest = sha256(source_bytes).hexdigest() if source_bytes else ""
    normalized_program["sha256"] = source_digest

    compiler_options = _string_map(spec.get("compiler_options") or spec.get("compiler"), "spec.compiler", violations)
    submit_metadata = _string_map(spec.get("metadata"), "spec.metadata", violations)

    dependencies_raw = spec.get("dependencies", [])
    dependencies: list[str] = []
    if dependencies_raw is None:
        dependencies_raw = []
    if not isinstance(dependencies_raw, list):
        violations.append(FieldViolation(field="spec.dependencies", description="must be list<string>"))
    else:
        for idx, item in enumerate(dependencies_raw):
            if not isinstance(item, str):
                violations.append(FieldViolation(field=f"spec.dependencies[{idx}]", description="must be string"))
            else:
                dependencies.append(item)

    for section_name in ("scheduling", "security", "observability"):
        section = root.get(section_name, {})
        if section is None:
            section = {}
        if not isinstance(section, dict):
            violations.append(FieldViolation(field=section_name, description="must be a mapping"))

    if violations:
        raise JobSpecValidationError(tuple(violations))

    normalized = {
        "contract": "jobspec.normalized",
        "version": JOBSPEC_VERSION,
        "apiVersion": JOBSPEC_API_VERSION,
        "kind": JOBSPEC_KIND,
        "compatibility": {
            "input_apiVersion": api_version,
            "migration": "v0.1-inline-and-program_path" if api_version == LEGACY_JOBSPEC_API_VERSION else "none",
        },
        "metadata": {
            "name": name.strip(),
            "labels": labels,
            "annotations": annotations,
        },
        "spec": {
            "target": target.strip(),
            "priority": priority,
            "program": normalized_program,
            "compiler_options": compiler_options,
            "metadata": submit_metadata,
            "dependencies": dependencies,
            "workload": workload,
        },
        "scheduling": root.get("scheduling") or {},
        "security": root.get("security") or {},
        "observability": root.get("observability") or {},
    }
    normalized["digest"] = sha256(_canonical_json(normalized).encode("utf-8")).hexdigest()
    normalized["package"] = {
        "source_sha256": source_digest,
        "canonical_digest": normalized["digest"],
        "normalized_json_sha256": normalized["digest"],
    }
    return normalized


def canonical_jobspec_json(jobspec_path: Path) -> str:
    """Return byte-stable canonical JSON for the normalized JobSpec."""
    return _canonical_json(normalize_jobspec(jobspec_path))


def canonical_jobspec_digest(jobspec_path: Path) -> str:
    """Return the deterministic sha256 digest of the normalized JobSpec."""
    return normalize_jobspec(jobspec_path)["digest"]


def parse_jobspec_to_submit_request(jobspec_path: Path) -> job_pb.SubmitJobRequest:
    """Parse job.yaml and map it to canonical SubmitJobRequest."""

    normalized = normalize_jobspec(jobspec_path)
    program = normalized["spec"]["program"]
    source_bytes = program.get("source", "").encode("utf-8")
    if not source_bytes and "path" in program:
        resolved, _ = _resolve_safe_path(jobspec_path.parent, program["path"], "spec.program.path")
        source_bytes = resolved.read_bytes() if resolved else b""

    public_metadata = dict(normalized["spec"]["metadata"])
    # Internal envelope mapping: scheduler/security/observability become bounded
    # internal metadata hints. Raw internal-only fields are not exposed in the
    # public SubmitJobRequest schema.
    public_metadata.update(
        {
            "jobspec_yaml": jobspec_path.read_text(encoding="utf-8"),
            "jobspec_version": normalized["version"],
            "jobspec_digest": normalized["digest"],
            "source_sha256": program["sha256"],
            "jobspec_scheduling": _canonical_json(normalized["scheduling"]),
            "jobspec_security": _canonical_json(normalized["security"]),
            "jobspec_observability": _canonical_json(normalized["observability"]),
            "jobspec_workload": _canonical_json(normalized["spec"]["workload"]),
        }
    )

    workload = normalized["spec"]["workload"]
    workload_proto = job_pb.WorkloadContract(
        kind=job_pb.WorkloadFamilyKind.Value(JOBSPEC_WORKLOAD_ENUM_NAMES[workload["kind"]]),
        execution_profile=workload["execution_profile"],
        replayable=workload["replayable"],
    )

    return job_pb.SubmitJobRequest(
        name=normalized["metadata"]["name"],
        target=normalized["spec"]["target"],
        priority=normalized["spec"]["priority"],
        compiler_options=normalized["spec"]["compiler_options"],
        metadata=public_metadata,
        dependencies=normalized["spec"]["dependencies"],
        workload=workload_proto,
        eigen_lang=types_pb.EigenLangSource(
            source=source_bytes,
            entrypoint=program["entrypoint"],
            sha256=program["sha256"],
        ),
    )
