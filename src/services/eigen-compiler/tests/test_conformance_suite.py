from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eigen_compiler.compiler import CompilerValidationError, _encode_aqo_payload, compile_eigen_lang
from eigen_compiler.grpc_impl import render_metrics_text
from eigen_compiler.proto_gen import ensure_generated

ensure_generated()

GOLDEN_ROOT = Path(__file__).parent / "golden"


def _normalize_aqo(aqo: dict[str, object]) -> dict[str, object]:
    normalized = json.loads(json.dumps(aqo))
    normalized["version"] = "1.0.0"
    if isinstance(normalized.get("parameters"), list):
        normalized["parameters"] = {
            item["name"]: item.get("default", item["name"])
            for item in normalized["parameters"]
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
    return normalized


@pytest.mark.parametrize("case_dir", sorted(GOLDEN_ROOT.iterdir()), ids=lambda p: p.name)
def test_golden_cases_match_expected_aqo(case_dir: Path) -> None:
    source = (case_dir / "program.eigen.py").read_bytes()
    expected = json.loads((case_dir / "expected.aqo.json").read_text(encoding="utf-8"))

    first = compile_eigen_lang(source).aqo_json
    second = compile_eigen_lang(source).aqo_json
    assert first == second

    actual = json.loads(first.decode("utf-8"))
    assert _normalize_aqo(actual) == _normalize_aqo(expected)


def test_aqo_is_canonical_and_hash_stable() -> None:
    source = b'from eigen_lang import hybrid_program\n@hybrid_program(target="sim")\ndef main():\n    ry(0, theta=1.0)\n'
    compiled = compile_eigen_lang(source)
    payload = json.loads(compiled.aqo_json.decode("utf-8"))
    assert compiled.aqo_json == json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert compiled.metadata["aqo_sha256"] == hashlib.sha256(compiled.aqo_json).hexdigest()


def test_compile_preserves_annotations_and_topology() -> None:
    source = b'from eigen_lang import Param, ExpectationValue, hybrid_program, minimize\n@hybrid_program(target="sim")\ndef main():\n    theta = Param("theta")\n    ry(0, theta=theta)\n    minimize(ExpectationValue("a", "b"), [0.1])\n'
    compiled = json.loads(
        compile_eigen_lang(
            source,
            options={
                "distributed.enabled": "true",
                "distributed.target": "cluster",
                "distributed.partition_count": "4",
                "distributed.queue_provider": "memory",
                "distributed.topology_hint": "pipeline",
            },
        ).aqo_json.decode("utf-8")
    )
    assert compiled["annotations"]["expectation"] == {"kind": "ExpectationValue"}
    assert compiled["annotations"]["hybrid_plan_marker"] == {"kind": "minimize", "expanded_by": "kernel"}
    assert compiled["topology"]["partition_count"] == 4


def test_compile_exposes_compiler_diagnostics_payload() -> None:
    source = b'from eigen_lang import Param, ExpectationValue, hybrid_program, minimize\n@hybrid_program(target="sim")\ndef main():\n    theta = Param("theta")\n    ry(0, theta=theta)\n    minimize(ExpectationValue("a", "b"), [0.1])\n'
    compiled = compile_eigen_lang(
        source,
        options={
            "distributed.enabled": "true",
            "distributed.target": "cluster",
            "distributed.partition_count": "4",
            "distributed.queue_provider": "memory",
            "distributed.topology_hint": "pipeline",
        },
    )
    diagnostics = json.loads(compiled.metadata["compiler_diagnostics_json"])
    assert diagnostics["contract_version"] == "1.0.0"
    assert diagnostics["stage_order"] == ["parse", "validate_ast", "annotate", "lower_to_ir", "eigen_dpda", "canonicalize_aqo", "emit"]
    assert diagnostics["backend_contract"]["backend_target_class"] == "distributed"
    assert diagnostics["explainability"]["decision"] == "compiler_to_optimizer_handoff"


def test_compile_exposes_backend_contract_and_target_classification() -> None:
    source = (
        b"from eigen_lang import Param, ExpectationValue, hybrid_program, minimize\n"
        b"@hybrid_program(target=\"sim\")\n"
        b"def main():\n"
        b"    theta = Param(\"theta\")\n"
        b"    ry(0, theta=theta)\n"
        b"    minimize(ExpectationValue(\"a\", \"b\"), [0.1])\n"
    )
    compiled = compile_eigen_lang(
        source,
        options={
            "distributed.enabled": "true",
            "distributed.target": "cluster",
            "distributed.partition_count": "4",
            "distributed.queue_provider": "memory",
            "distributed.topology_hint": "pipeline",
        },
    )

    workload_profile = json.loads(compiled.metadata["workload_profile_json"])
    backend_contract = json.loads(compiled.metadata["backend_contract_json"])

    assert workload_profile["backend_targets"]
    assert workload_profile["emission_modes"]
    assert backend_contract["contract_version"] == "1.0.0"
    assert backend_contract["workload_profile"] == "DistributedJob"
    assert backend_contract["backend_target_class"] == "distributed"
    assert backend_contract["target_resolution"] == "distributed"
    assert backend_contract["selected_emission_mode"] == "aqo_json+topology_metadata"
    assert backend_contract["backend_specific_decisions"] == {
        "distributed.enabled": True,
        "distributed.target": "cluster",
        "requires_explicit_target": True,
        "core_ir_backend_agnostic": True,
    }


def test_aqo_validation_rejects_unknown_top_level_field() -> None:
    with pytest.raises(CompilerValidationError):
        _encode_aqo_payload({"version": "1.0.0", "qubits": 1, "operations": [{"op": "H", "q": [0]}], "x": {}})


def test_aqo_validation_rejects_unknown_opcode_and_measurement_shape() -> None:
    with pytest.raises(CompilerValidationError):
        _encode_aqo_payload({"version": "1.0.0", "qubits": 1, "operations": [{"op": "FOO", "q": [0]}]})
    with pytest.raises(CompilerValidationError):
        _encode_aqo_payload({"version": "1.0.0", "qubits": 2, "operations": [{"op": "MEASURE", "q": [0, 1], "c": [0]}]})


def test_source_ref_is_resolved_from_qfs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = b'from eigen_lang import hybrid_program\n@hybrid_program(target="sim")\ndef main():\n    ry(0, theta=1.0)\n'
    qfs_root = tmp_path / "circuit_fs"
    path = qfs_root / "jobs" / "job-1" / "input" / "program.eigen.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(source)
    monkeypatch.setenv("EIGEN_QFS_ROOT", str(qfs_root))

    from_ref = compile_eigen_lang(b"", source_ref="jobs/job-1/input/program.eigen.py")
    direct = compile_eigen_lang(source)
    assert from_ref.aqo_json == direct.aqo_json
    assert from_ref.metadata["source_precedence"] == "source_ref"


def test_compile_rejects_backend_target_mismatch() -> None:
    source = b'from eigen_lang import hybrid_program\n@hybrid_program(target="sim")\ndef main():\n    ry(0, theta=1.0)\n'
    with pytest.raises(CompilerValidationError) as excinfo:
        compile_eigen_lang(
            source,
            options={
                "spec.workload.kind": "DistributedJob",
                "distributed.enabled": "true",
                "distributed.target": "cluster",
                "distributed.partition_count": "2",
                "spec.workload.backend_target": "sim:local",
            },
        )
    assert excinfo.value.violations
    assert excinfo.value.violations[0].stage == "eigen_dpda"
    assert excinfo.value.violations[0].rule in {
        "compiler.profile.distributed.target_mismatch",
        "compiler.profile.validation",
    }
    descriptions = [violation.description for violation in excinfo.value.violations]
    assert any("DistributedJob requires a distributed backend target" in desc for desc in descriptions)

def test_compile_exposes_deterministic_pass_pipeline() -> None:
    source = (
        b"from eigen_lang import hybrid_program\n"
        b"@hybrid_program(target=\"sim\")\n"
        b"def main():\n"
        b"    ry(0, theta=1.0)\n"
    )

    compiled = compile_eigen_lang(source)
    pass_pipeline = json.loads(compiled.metadata["compiler_passes_json"])

    assert pass_pipeline["version"] == "1.0.0"
    assert [item["name"] for item in pass_pipeline["passes"]] == [
        "lower_to_ir",
        "rewrite_ir",
        "validate_lowering",
        "canonicalize_aqo",
    ]
    assert pass_pipeline["passes"][0]["output"]["operations"] == [
        {"op": "RY", "q": [0], "params": {"theta": 1.0}}
    ]
    assert pass_pipeline["passes"][1]["output"]["operations"][-1] == {"op": "MEASURE", "q": [0], "c": [0]}
    assert pass_pipeline["passes"][2]["output"] == {"status": "valid", "aqo_version": "1.0.0"}


def test_metrics_expose_contract_marker() -> None:
    text = render_metrics_text()
    assert 'eigen_observability_contract_info{version="1.0.0"} 1' in text
    assert 'eigen_compiler_contract_info{version="1.0.0"} 1' in text
