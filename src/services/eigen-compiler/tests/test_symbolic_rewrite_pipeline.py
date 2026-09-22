from __future__ import annotations

import ast
from types import SimpleNamespace

from eigen_compiler import SymbolicRewritePipeline
from eigen_compiler.compiler import CompileRequestContext, CompilationResult, CompilerPassPipeline, DistributedCompileConfig


def _patch_pipeline_dependencies(monkeypatch):
    import eigen_compiler.symbolic_rewrite as sr

    monkeypatch.setattr(sr, "_normalize_options", lambda options: {"spec.workload.kind": "QuantumJob"})
    monkeypatch.setattr(sr, "_normalize_request_context", lambda request_context: CompileRequestContext())
    monkeypatch.setattr(sr, "_resolve_source_bytes", lambda source, source_ref: (source, "inline"))
    monkeypatch.setattr(sr, "_parse_python_source", lambda source: ast.parse("from eigen_lang import *\n"))
    monkeypatch.setattr(sr, "_enforce_resource_limits", lambda tree: ())
    monkeypatch.setattr(sr, "_reject_forbidden_imports", lambda tree: ())
    monkeypatch.setattr(sr, "_reject_forbidden_calls", lambda tree: ())
    monkeypatch.setattr(sr, "_reject_dynamic_control_flow", lambda tree: ())
    monkeypatch.setattr(sr, "_validate_single_entrypoint", lambda tree: ())
    monkeypatch.setattr(sr, "_collect_params", lambda tree: ({}, ()))
    monkeypatch.setattr(sr, "_collect_observable_bindings", lambda tree: ({}, ()))
    monkeypatch.setattr(sr, "_collect_expectation_annotation", lambda tree, bindings: None)
    monkeypatch.setattr(sr, "_collect_operations", lambda tree, params: ([{"op": "H", "q": [0]}], 1))
    monkeypatch.setattr(
        sr,
        "_distributed_compile_config",
        lambda options: DistributedCompileConfig(enabled=False, target=None, partition_count=None, queue_provider=None, topology_hint=None),
    )
    monkeypatch.setattr(
        sr,
        "resolve_workload_profile",
        lambda options, has_expectation, has_minimize: (SimpleNamespace(kind="QuantumJob"), ()),
    )
    monkeypatch.setattr(sr, "validate_workload_profile", lambda *args, **kwargs: ())
    monkeypatch.setattr(sr, "workload_profile_payload", lambda workload_profile: {"kind": workload_profile.kind})
    monkeypatch.setattr(sr, "backend_contract_payload", lambda workload_profile, options: {"kind": workload_profile.kind})
    monkeypatch.setattr(sr, "_canonical_json_text", lambda payload: "{\"kind\":\"QuantumJob\"}")
    monkeypatch.setattr(sr, "_canonical_json_bytes", lambda payload: b'{"kind":"QuantumJob"}')
    monkeypatch.setattr(
        sr,
        "_build_aqo_payload",
        lambda **kwargs: {"version": "1.0.0", "qubits": kwargs["qubits"], "operations": kwargs["operations"]},
    )
    monkeypatch.setattr(sr, "_validate_lowering_payload", lambda aqo: aqo)
    monkeypatch.setattr(
        sr,
        "_build_compiler_pass_pipeline",
        lambda **kwargs: CompilerPassPipeline(
            records=(),
            aqo={"version": "1.0.0", "qubits": kwargs["qubits"], "operations": kwargs["operations"]},
        ),
    )
    monkeypatch.setattr(
        sr,
        "_compiler_replay_bundle",
        lambda **kwargs: ({
            "snapshot_id": "snapshot-sha",
            "model_snapshot": {"model_version": "dpda-model-v1", "model_snapshot_id": "dpda-model-v1", "model_snapshot_digest": "model-digest"},
            "knowledge_base_snapshot": {"kb_version": "1.0.0", "kb_snapshot_id": "1.0.0", "kb_snapshot_digest": "kb-digest"},
            "policy_snapshot": {"policy_mode": "deterministic", "policy_snapshot_version": "policy-2026-06-15", "policy_snapshot_id": "policy-2026-06-15", "policy_digest": "policy-digest"},
        }, "bundle-sha"),
    )


def test_symbolic_rewrite_pipeline_exposes_stages_and_logs_them(monkeypatch):
    _patch_pipeline_dependencies(monkeypatch)

    events: list[tuple[str, str]] = []

    def observer(stage: str, elapsed_seconds: float, outcome: str) -> None:
        events.append((stage, outcome))

    pipeline = SymbolicRewritePipeline(observer=observer)

    state = pipeline.parse(b"from eigen_lang import *\n", request_context={"request_id": "req-1"})
    state = pipeline.normalize(state)
    state = pipeline.generate_candidates(state)
    state = pipeline.check_legality(state)
    state = pipeline.rewrite(state)
    result = pipeline.emit_aqo(state)

    assert isinstance(result, CompilationResult)
    assert result.aqo_json == b'{"kind":"QuantumJob"}'
    assert [stage for stage, outcome in events] == [
        "parse",
        "normalize",
        "candidate_generation",
        "legality_check",
        "rewrite",
        "emit_aqo",
    ]
    assert all(outcome == "success" for _, outcome in events)


def test_symbolic_rewrite_pipeline_compile_runs_all_stages(monkeypatch):
    _patch_pipeline_dependencies(monkeypatch)

    stage_calls: list[str] = []

    def observer(stage: str, elapsed_seconds: float, outcome: str) -> None:
        stage_calls.append(stage)

    pipeline = SymbolicRewritePipeline(observer=observer)
    result = pipeline.compile(b"from eigen_lang import *\n")

    assert isinstance(result, CompilationResult)
    assert stage_calls == [
        "parse",
        "normalize",
        "candidate_generation",
        "legality_check",
        "rewrite",
        "emit_aqo",
    ]
