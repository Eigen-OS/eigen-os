from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eigen_compiler.compiler import CompilerValidationError, _encode_aqo_payload, compile_eigen_lang
from eigen_compiler.validation import build_compiler_rule_catalog
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


def test_aqo_validation_rejects_unknown_top_level_field() -> None:
    with pytest.raises(CompilerValidationError):
        _encode_aqo_payload({"version": "1.0.0", "qubits": 1, "operations": [{"op": "H", "q": [0]}], "x": {}})


def test_aqo_validation_rejects_unknown_opcode_and_measurement_shape() -> None:
    with pytest.raises(CompilerValidationError):
        _encode_aqo_payload({"version": "1.0.0", "qubits": 1, "operations": [{"op": "FOO", "q": [0]}]})
    with pytest.raises(CompilerValidationError):
        _encode_aqo_payload({"version": "1.0.0", "qubits": 2, "operations": [{"op": "MEASURE", "q": [0, 1], "c": [0]}]})


def test_rule_catalog_exposes_named_semantic_and_lowering_rules() -> None:
    catalog = build_compiler_rule_catalog()
    names = {rule.name for rule in catalog.rules}
    assert "syntax.entrypoint.single" in names
    assert "policy.import.allowed" in names
    assert "lowering.rotation.theta_required" in names


def test_compile_errors_carry_named_rule_and_location() -> None:
    source = (
        b"import os\n"
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program()\n"
        b"def main():\n"
        b"    pass\n"
    )
    with pytest.raises(CompilerValidationError) as excinfo:
        compile_eigen_lang(source)
    assert any(v.rule == "policy.import.allowed" for v in excinfo.value.violations)
    assert any(v.location == "source" for v in excinfo.value.violations)


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


def test_metrics_expose_contract_marker() -> None:
    text = render_metrics_text()
    assert 'eigen_observability_contract_info{version="1.0.0"} 1' in text
    assert 'eigen_compiler_contract_info{version="1.0.0"} 1' in text
