"""JobSpec (job.yaml) parser for SubmitJobRequest canonical mapping.

Implements MVP-2 parser contract from RFC 0013 / ADR 0003.
"""

from __future__ import annotations

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


REQUIRED_FIELD_MATRIX: dict[str, bool] = {
    "apiVersion": True,
    "kind": True,
    "metadata": True,
    "metadata.name": True,
    "metadata.labels": False,
    "metadata.annotations": False,
    "spec": True,
    "spec.program": False,
    "spec.program_path": False,
    "spec.entrypoint": False,
    "spec.target": True,
    "spec.priority": False,
    "spec.compiler_options": False,
    "spec.metadata": False,
    "spec.dependencies": False,
}


@dataclass(frozen=True)
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


def parse_jobspec_to_submit_request(jobspec_path: Path) -> job_pb.SubmitJobRequest:
    """Parse job.yaml and map it to canonical SubmitJobRequest."""

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
        parsed = yaml.safe_load(raw.decode("utf-8"))
    except UnicodeDecodeError:
        parsed = None
        violations.append(FieldViolation(field="job.yaml", description="must be valid UTF-8"))
    except yaml.YAMLError:
        parsed = None
        violations.append(FieldViolation(field="job.yaml", description="must be valid YAML"))

    root = _require_dict(parsed, "job.yaml", violations)

    api_version = root.get("apiVersion", "")
    if api_version != "eigen.os/v0.1":
        violations.append(FieldViolation(field="apiVersion", description="must be eigen.os/v0.1"))

    kind = root.get("kind", "")
    if kind != "QuantumJob":
        violations.append(FieldViolation(field="kind", description="must be QuantumJob"))

    metadata = _require_dict(root.get("metadata"), "metadata", violations)
    name = metadata.get("name", "")
    if not isinstance(name, str) or not name.strip():
        violations.append(FieldViolation(field="metadata.name", description="field is required"))

    spec = _require_dict(root.get("spec"), "spec", violations)
    target = spec.get("target", "")
    if not isinstance(target, str) or not target.strip():
        violations.append(FieldViolation(field="spec.target", description="field is required"))

    priority = spec.get("priority", 50)
    if not isinstance(priority, int):
        violations.append(FieldViolation(field="spec.priority", description="must be int32"))
    elif priority < 0 or priority > 100:
        violations.append(FieldViolation(field="spec.priority", description="must be in range [0,100]"))

    entrypoint = spec.get("entrypoint", "main")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        violations.append(FieldViolation(field="spec.entrypoint", description="must be non-empty string"))

    source_bytes = b""
    program_inline = spec.get("program")
    program_path = spec.get("program_path")
    base_dir = jobspec_path.parent

    if program_inline is not None and program_path is not None:
        violations.append(
            FieldViolation(field="spec.program_path", description="cannot be set when spec.program is provided")
        )

    if isinstance(program_inline, str) and program_inline.strip():
        source_bytes = program_inline.encode("utf-8")
    else:
        ref = "program.eigen.py" if program_path is None else program_path
        if not isinstance(ref, str):
            violations.append(FieldViolation(field="spec.program_path", description="must be string"))
        else:
            resolved, err = _resolve_safe_path(base_dir, ref, "spec.program_path")
            if err:
                violations.append(err)
            elif resolved is not None:
                try:
                    source_bytes = resolved.read_bytes()
                except FileNotFoundError:
                    violations.append(FieldViolation(field="spec.program_path", description="file not found"))

    if source_bytes and len(source_bytes) > cfg.max_program_source_bytes:
        violations.append(
            FieldViolation(
                field="eigen_lang.source",
                description=f"source exceeds max allowed size ({cfg.max_program_source_bytes} bytes)",
            )
        )
    if not source_bytes:
        violations.append(FieldViolation(field="spec.program", description="program source is required"))

    def _string_map(field: str) -> dict[str, str]:
        raw_map = spec.get(field, {})
        if raw_map is None:
            return {}
        if not isinstance(raw_map, dict):
            violations.append(FieldViolation(field=f"spec.{field}", description="must be map<string,string>"))
            return {}
        out: dict[str, str] = {}
        for k, v in raw_map.items():
            if not isinstance(k, str) or not isinstance(v, str):
                violations.append(
                    FieldViolation(field=f"spec.{field}", description="must be map<string,string>")
                )
                return {}
            out[k] = v
        return out

    compiler_options = _string_map("compiler_options")
    submit_metadata = _string_map("metadata")

    dependencies_raw = spec.get("dependencies", [])
    dependencies: list[str] = []
    if dependencies_raw is None:
        dependencies_raw = []
    if not isinstance(dependencies_raw, list):
        violations.append(FieldViolation(field="spec.dependencies", description="must be list<string>"))
    else:
        for idx, item in enumerate(dependencies_raw):
            if not isinstance(item, str):
                violations.append(
                    FieldViolation(field=f"spec.dependencies[{idx}]", description="must be string")
                )
            else:
                dependencies.append(item)

    if violations:
        raise JobSpecValidationError(tuple(violations))

    return job_pb.SubmitJobRequest(
        name=name.strip(),
        target=target.strip(),
        priority=priority,
        compiler_options=compiler_options,
        metadata={**submit_metadata, "jobspec_yaml": raw.decode("utf-8")},
        dependencies=dependencies,
        eigen_lang=types_pb.EigenLangSource(
            source=source_bytes,
            entrypoint=entrypoint.strip(),
            sha256=sha256(source_bytes).hexdigest(),
        ),
    )
