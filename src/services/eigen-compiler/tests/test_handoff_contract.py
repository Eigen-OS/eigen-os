from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eigen_compiler.compiler import compile_eigen_lang


TEST_SOURCE = (
    b"from eigen_lang import hybrid_program\n\n"
    b"@hybrid_program(target=\"sim\", shots=1000)\n"
    b"def main():\n"
    b"    ry(0, theta=1.0)\n"
)

REQUEST_CONTEXT = {
    "request_id": "req-handoff-1",
    "trace_id": "trace-handoff-1",
    "traceparent": "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01",
    "deadline": "0:00:30",
    "retry_policy": "idempotent",
    "security_context": "mTLS",
    "tenant_id": "tenant-a",
    "project_id": "project-x",
}

ALLOWED_HANDFOFF_ENVELOPE_FIELDS = {
    "contract_version",
    "compiler_contract_version",
    "optimizer_contract_version",
    "aqo_version",
    "request_sha256",
    "source_sha256",
    "aqo_sha256",
    "source_precedence",
    "request_id",
    "trace_id",
    "traceparent",
    "source_ref",
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compile_sample(*, source: bytes = TEST_SOURCE, source_ref: str | None = None):
    return compile_eigen_lang(source, source_ref=source_ref, request_context=REQUEST_CONTEXT)


def _build_handoff_bundle(result, *, optimizer_contract_version: str = "1.0.0") -> dict[str, object]:
    aqo_json = json.loads(result.aqo_json.decode("utf-8"))
    envelope = {
        "contract_version": "1.0.0",
        "compiler_contract_version": result.metadata["compiler_contract_version"],
        "optimizer_contract_version": optimizer_contract_version,
        "aqo_version": result.metadata["aqo_version"],
        "request_sha256": result.metadata["request_sha256"],
        "source_sha256": result.metadata["source_sha256"],
        "aqo_sha256": result.metadata["aqo_sha256"],
        "source_precedence": result.metadata["source_precedence"],
        "request_id": result.metadata["request_id"],
        "trace_id": result.metadata["trace_id"],
        "traceparent": result.metadata["traceparent"],
        "source_ref": result.metadata.get("source_ref", ""),
    }
    compiler_metadata = {
        "request_id": result.metadata["request_id"],
        "trace_id": result.metadata["trace_id"],
        "traceparent": result.metadata["traceparent"],
        "deadline": result.metadata["deadline"],
        "retry_policy": result.metadata["retry_policy"],
        "security_context": result.metadata["security_context"],
        "tenant_id": result.metadata["tenant_id"],
        "project_id": result.metadata["project_id"],
        "compiler_contract_version": result.metadata["compiler_contract_version"],
        "aqo_version": result.metadata["aqo_version"],
        "source_precedence": result.metadata["source_precedence"],
        "source_sha256": result.metadata["source_sha256"],
        "aqo_sha256": result.metadata["aqo_sha256"],
        "request_sha256": result.metadata["request_sha256"],
        "compiler_passes_json": result.metadata["compiler_passes_json"],
        "decision_lineage_json": result.metadata["decision_lineage_json"],
        "observability_json": result.metadata["observability_json"],
        "explainability_json": result.metadata["explainability_json"],
    }
    return {"envelope": envelope, "input_aqo": aqo_json, "compiler_metadata": compiler_metadata}


def _validate_handoff_boundary(handoff: dict[str, object]) -> None:
    envelope = handoff["envelope"]
    unknown_envelope_fields = set(envelope) - ALLOWED_HANDFOFF_ENVELOPE_FIELDS
    if unknown_envelope_fields:
        raise ValueError(f"unsupported envelope fields: {sorted(unknown_envelope_fields)}")

    hidden_state_fields = {
        "model_version",
        "fallback_used",
        "fallback_reason",
        "fallback_reason_code",
        "confidence_score",
        "optimizer_digest",
        "candidate_budget",
        "timeout_ms",
        "graph_encoding",
    }
    forbidden = hidden_state_fields & set(handoff)
    if forbidden:
        raise ValueError(f"hidden state crossed compiler/optimizer boundary: {sorted(forbidden)}")


def _canonical_handoff_digest(handoff: dict[str, object]) -> str:
    return _sha256_hex(_canonical_json(handoff))


def test_handoff_schema_is_versioned_and_bounded() -> None:
    result = _compile_sample()
    handoff = _build_handoff_bundle(result)

    assert handoff["envelope"]["contract_version"] == "1.0.0"
    assert handoff["envelope"]["compiler_contract_version"] == "1.0.0"
    assert handoff["envelope"]["optimizer_contract_version"] == "1.0.0"
    assert handoff["envelope"]["aqo_version"] == "1.0.0"
    assert handoff["envelope"]["source_precedence"] == "source"
    assert set(handoff["envelope"]) == ALLOWED_HANDFOFF_ENVELOPE_FIELDS
    assert handoff["input_aqo"]["version"] == "1.0.0"
    assert handoff["input_aqo"]["operations"]
    assert result.metadata["workload_profile"] == "QuantumJob"

    pass_pipeline = json.loads(handoff["compiler_metadata"]["compiler_passes_json"])    
    decision_lineage = json.loads(handoff["compiler_metadata"]["decision_lineage_json"])
    observability = json.loads(handoff["compiler_metadata"]["observability_json"])
    explainability = json.loads(handoff["compiler_metadata"]["explainability_json"])
    
    assert pass_pipeline["version"] == "1.0.0"
    assert [item["name"] for item in pass_pipeline["passes"]] == [
        "lower_to_ir",
        "rewrite_ir",
        "validate_lowering",
        "canonicalize_aqo",
    ]
    assert pass_pipeline["passes"][0]["output"]["operations"] == [
        {"op": "RY", "params": {"theta": 1.0}, "q": [0]}
    ]
    assert pass_pipeline["passes"][1]["output"]["operations"][-1] == {"op": "MEASURE", "q": [0], "c": [0]}
    assert decision_lineage["workload_profile"] == "QuantumJob"

    assert decision_lineage["contract_version"] == "1.0.0"
    assert decision_lineage["compiler_contract_version"] == "1.0.0"
    assert decision_lineage["optimizer_contract_version"] == "1.0.0"
    assert decision_lineage["stage_order"] == [
        "parse",
        "semantic_validation",
        "annotate",
        "lower_to_ir",
        "lowering_validation",
        "eigen_dpda",
        "canonicalize_aqo",
        "emit",
    ]
    assert decision_lineage["trace_id"] == REQUEST_CONTEXT["trace_id"]
    assert observability["trace_fields"] == ["request_id", "trace_id", "traceparent"]
    assert observability["metric_bounds"]["labels_bounded"] is True
    assert observability["metric_bounds"]["request_ids_in_metrics"] is False
    assert explainability["decision"] == "compiler_to_optimizer_handoff"
    assert explainability["bounded_fields"] == [
        "request_id",
        "trace_id",
        "traceparent",
        "source_sha256",
        "aqo_sha256",
        "request_sha256",
    ]


def test_stable_identifier_propagation_across_boundary_is_deterministic() -> None:
    first = _compile_sample()
    second = _compile_sample()

    first_handoff = _build_handoff_bundle(first)
    second_handoff = _build_handoff_bundle(second)

    for key in ("request_id", "source_sha256", "aqo_sha256", "request_sha256", "source_precedence"):
        assert first.metadata[key] == second.metadata[key]
        assert first_handoff["envelope"][key] == second_handoff["envelope"][key]

    for key in ("compiler_passes_json", "decision_lineage_json", "observability_json", "explainability_json"):
        assert first.metadata[key] == second.metadata[key]
        assert first_handoff["compiler_metadata"][key] == second_handoff["compiler_metadata"][key]

    assert first_handoff == second_handoff
    assert _canonical_handoff_digest(first_handoff) == _canonical_handoff_digest(second_handoff)


def test_boundary_rejects_unsupported_fields() -> None:
    handoff = _build_handoff_bundle(_compile_sample())
    handoff["envelope"]["model_version"] = "must-not-cross"

    with pytest.raises(ValueError, match="unsupported envelope fields|hidden state crossed"):
        _validate_handoff_boundary(handoff)


def test_replay_determinism_fixture_preserves_source_precedence_and_handoff_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    qfs_root = tmp_path / "circuit_fs"
    program_path = qfs_root / "jobs" / "job-1" / "input" / "program.eigen.py"
    program_path.parent.mkdir(parents=True)
    program_path.write_bytes(TEST_SOURCE)
    monkeypatch.setenv("EIGEN_QFS_ROOT", str(qfs_root))

    first = compile_eigen_lang(
        TEST_SOURCE,
        source_ref="jobs/job-1/input/program.eigen.py",
        request_context=REQUEST_CONTEXT,
    )
    second = compile_eigen_lang(
        TEST_SOURCE,
        source_ref="jobs/job-1/input/program.eigen.py",
        request_context=REQUEST_CONTEXT,
    )

    first_handoff = _build_handoff_bundle(first)
    second_handoff = _build_handoff_bundle(second)

    assert first.metadata["source_precedence"] == "source"
    assert second.metadata["source_precedence"] == "source"
    assert first_handoff == second_handoff
    assert _canonical_handoff_digest(first_handoff) == _canonical_handoff_digest(second_handoff)
