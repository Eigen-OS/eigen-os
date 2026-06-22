from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuro_symbolic_service.pattern_miner import PatternMinerService


def _dataset(
    *,
    tenant_id: str = "tenant-a",
    project_id: str = "project-a",
    prefix: str = "",
) -> list[dict[str, str]]:
    return [
        {
            "record_id": f"{prefix}r-2",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "circuit_id": "c1",
            "backend_class": "sim",
            "pattern_family": "alpha",
            "schema_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "aqo_version": "aqo-1.0",
            "optimizer_version": "opt-1.0",
            "policy_mode": "deterministic",
            "policy_digest": "policy-1",
            "semantic_hash": "semantic-alpha",
            "aqo_hash": "aqo-alpha",
        },
        {
            "record_id": f"{prefix}r-1",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "circuit_id": "c1",
            "backend_class": "sim",
            "pattern_family": "alpha",
            "schema_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "aqo_version": "aqo-1.0",
            "optimizer_version": "opt-1.0",
            "policy_mode": "deterministic",
            "policy_digest": "policy-1",
            "semantic_hash": "semantic-alpha",
            "aqo_hash": "aqo-alpha",
        },
        {
            "record_id": f"{prefix}r-3",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "circuit_id": "c1",
            "backend_class": "sim",
            "pattern_family": "beta",
            "schema_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "aqo_version": "aqo-1.0",
            "optimizer_version": "opt-1.0",
            "policy_mode": "deterministic",
            "policy_digest": "policy-1",
            "semantic_hash": "semantic-beta",
            "aqo_hash": "aqo-beta",
        },
        {
            "record_id": f"{prefix}r-4",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "circuit_id": "c1",
            "backend_class": "sim",
            "pattern_family": "gamma",
            "schema_version": "1.0.0",
            "compiler_version": "compiler-2.0",
            "aqo_version": "aqo-1.0",
            "optimizer_version": "opt-1.0",
            "policy_mode": "deterministic",
            "policy_digest": "policy-1",
            "semantic_hash": "semantic-gamma",
            "aqo_hash": "aqo-gamma",
        },
        {
            "record_id": f"{prefix}r-5",
            "tenant_id": tenant_id,
            "project_id": project_id,
            "circuit_id": "c2",
            "backend_class": "qpu",
            "pattern_family": "delta",
            "schema_version": "1.0.0",
            "compiler_version": "compiler-1.0",
            "aqo_version": "aqo-1.0",
            "optimizer_version": "opt-1.0",
            "policy_mode": "deterministic",
            "policy_digest": "policy-1",
            "semantic_hash": "semantic-delta",
            "aqo_hash": "aqo-delta",
        },
    ]


def test_pattern_miner_ingest_is_idempotent_and_deterministic() -> None:
    service = PatternMinerService()
    first = service.ingest_snapshot(snapshot_id="s1", records=_dataset(tenant_id="tenant-a", project_id="project-a"), config_digest="cfg-a", tenant_id="tenant-a", project_id="project-a")
    second = service.ingest_snapshot(snapshot_id="s1", records=list(reversed(_dataset(tenant_id="tenant-a", project_id="project-a"))), config_digest="cfg-a", tenant_id="tenant-a", project_id="project-a")

    assert first.created is True
    assert second.created is False
    assert first.idempotency_key == second.idempotency_key

    mined_first = service.mine_patterns(snapshot_id="s1", tenant_id="tenant-a", project_id="project-a")
    mined_second = service.mine_patterns(snapshot_id="s1", tenant_id="tenant-a", project_id="project-a")
    assert mined_first == mined_second
    assert mined_first["patterns"][0]["provenance"]["source"]["snapshot_id"] == "s1"
    assert mined_first["patterns"][0]["provenance"]["validation_status"]["state"] == "catalogued"


def test_recommendation_payload_has_versioned_contract_and_provenance_links() -> None:
    service = PatternMinerService()
    service.ingest_snapshot(
        snapshot_id="s1",
        records=_dataset(tenant_id="tenant-a", project_id="project-a"),
        config_digest="cfg-a",
    )
    recommendation = service.get_recommendation(snapshot_id="s1", tenant_id="tenant-a", project_id="project-a", circuit_id="c1", backend_class="sim", min_confidence=0.1)

    recommendation = service.get_recommendation(snapshot_id="s1", tenant_id="tenant-a", project_id="project-a", circuit_id="c1", backend_class="sim", min_confidence=0.1)
    assert recommendation["contract"] == "pattern_miner.recommendation"
    assert recommendation["version"] == "1.0.0"
    assert recommendation["recommendation"]["fallback_used"] is False
    assert recommendation["provenance"]["source_record_ids"] == ["r-1", "r-2"]
    assert recommendation["provenance"]["queryable_links"] == ["kb://records/r-1", "kb://records/r-2"]


def test_get_pattern_returns_canonical_template_and_separates_candidates() -> None:
    service = PatternMinerService()
    service.ingest_snapshot(snapshot_id="s1", records=_dataset(tenant_id="tenant-a", project_id="project-a"), config_digest="cfg-a", tenant_id="tenant-a", project_id="project-a")

    result = service.get_pattern(
        snapshot_id="s1",
        tenant_id="tenant-a",
        project_id="project-a",
        circuit_id="c1",
        backend_class="sim",
        semantic_hash="semantic-alpha",
        aqo_hash="aqo-alpha",
        schema_version="1.0.0",
        compiler_version="compiler-1.0",
        aqo_version="aqo-1.0",
        optimizer_version="opt-1.0",
        policy_mode="deterministic",
        policy_digest="policy-1",
        seed=7,
        query_mode="structural",
        candidate_budget=8,
        deterministic=True,
    )

    assert result["contract"] == "pattern_miner.pattern"
    assert result["version"] == "1.0.0"
    assert result["diagnostics"]["fallback_used"] is False
    assert result["diagnostics"]["compatibility_signature"] == result["canonical_pattern"]["compatibility_signature"]
    assert result["canonical_pattern"]["pattern_kind"] == "canonical"
    assert result["canonical_pattern"]["pattern_family"] == "alpha"
    assert result["canonical_pattern"]["selected"] is True
    assert result["candidate_patterns"][0]["selected"] is True
    assert result["candidate_patterns"][0]["pattern_family"] == "alpha"
    assert result["candidate_patterns"][0]["rank"] == 1
    assert result["candidate_patterns"][0]["provenance"]["source"]["snapshot_id"] == "s1"
    assert result["candidate_patterns"][0]["provenance"]["version"]["contract_version"] == "1.0.0"
    assert result["candidate_patterns"][0]["provenance"]["compilation_context"]["query_mode"] == "structural"
    assert result["candidate_patterns"][0]["provenance"]["validation_status"]["state"] == "selected"
    assert result["candidate_patterns"][0]["provenance"]["validation_status"]["selected"] is True
    assert result["canonical_pattern"]["provenance"]["validation_status"]["state"] == "canonical"
    assert result["explanation_pattern"]["provenance"]["validation_status"]["state"] == "explanation"
    assert len(result["candidate_patterns"]) <= 8
    assert any(
        candidate["pattern_family"] == "beta"
        for candidate in result["candidate_patterns"]
    )
    assert any(
        candidate["pattern_family"] == "gamma" and "COMPILER_MISMATCH" in candidate["incompatibility_reasons"]
        for candidate in result["candidate_patterns"]
    )
    assert result["explanation_pattern"]["canonical_pattern_id"] == result["canonical_pattern"]["pattern_id"]
    assert result["explanation_pattern"]["pattern_kind"] == "explanation"


def test_get_pattern_returns_diagnostics_when_no_canonical_pattern_exists() -> None:
    service = PatternMinerService()
    service.ingest_snapshot(snapshot_id="s1", records=_dataset(tenant_id="tenant-a", project_id="project-a"), config_digest="cfg-a")

    result = service.get_pattern(
        snapshot_id="s1",
        tenant_id="tenant-a",
        project_id="project-a",
        circuit_id="c1",
        backend_class="sim",
        semantic_hash="semantic-alpha",
        aqo_hash="aqo-alpha",
        schema_version="1.0.0",
        compiler_version="compiler-9.9",
        aqo_version="aqo-1.0",
        optimizer_version="opt-1.0",
        policy_mode="deterministic",
        policy_digest="policy-1",
        seed=7,
        query_mode="structural",
        candidate_budget=8,
        deterministic=True,
    )

    assert result["canonical_pattern"] is None
    assert result["diagnostics"]["fallback_used"] is True
    assert result["diagnostics"]["fallback_reason"] == "NO_CANONICAL_PATTERN"
    assert "COMPILER_MISMATCH" in result["diagnostics"]["incompatibility_reason_codes"]
    assert all(candidate["selected"] is False for candidate in result["candidate_patterns"])
    assert result["candidate_patterns"][0]["provenance"]["validation_status"]["state"] == "incompatible"
    assert result["candidate_patterns"][0]["provenance"]["validation_status"]["selected"] is False
    assert result["explanation_pattern"]["provenance"]["validation_status"]["state"] == "explanation"
    assert result["explanation_pattern"]["canonical_pattern_id"] == ""
    assert result["candidate_patterns"][0]["pattern_kind"] == "candidate"


def test_get_pattern_rejects_cross_scope_access_and_mixed_snapshot_ingest() -> None:
    service = PatternMinerService()
    service.ingest_snapshot(snapshot_id="s1", records=_dataset(tenant_id="tenant-a", project_id="project-a"), config_digest="cfg-a", tenant_id="tenant-a", project_id="project-a")

    mixed_records = _dataset(tenant_id="tenant-a", project_id="project-a") + _dataset(
        tenant_id="tenant-b",
        project_id="project-b",
        prefix="foreign-",
    )
    with pytest.raises(ValueError):
        service.ingest_snapshot(
            snapshot_id="mixed",
            records=mixed_records,
            config_digest="cfg-mixed",
        )

    with pytest.raises(PermissionError):
        service.get_pattern(
            snapshot_id="s1",
            tenant_id="tenant-b",
            project_id="project-b",
            circuit_id="c1",
            backend_class="sim",
            semantic_hash="semantic-alpha",
            aqo_hash="aqo-alpha",
            schema_version="1.0.0",
            compiler_version="compiler-1.0",
            aqo_version="aqo-1.0",
            optimizer_version="opt-1.0",
            policy_mode="deterministic",
            policy_digest="policy-1",
            seed=7,
            query_mode="structural",
            candidate_budget=8,
            deterministic=True,
        )


def test_pattern_retrieval_outputs_stay_within_tenant_project_scope() -> None:
    service = PatternMinerService()
    service.ingest_snapshot(snapshot_id="tenant-a-s1", records=_dataset(tenant_id="tenant-a", project_id="project-a"), config_digest="cfg-a", tenant_id="tenant-a", project_id="project-a")
    service.ingest_snapshot(snapshot_id="tenant-b-s1", records=_dataset(tenant_id="tenant-b", project_id="project-b", prefix="foreign-"), config_digest="cfg-b", tenant_id="tenant-b", project_id="project-b")

    result = service.get_pattern(
        snapshot_id="tenant-a-s1",
        tenant_id="tenant-a",
        project_id="project-a",
        circuit_id="c1",
        backend_class="sim",
        semantic_hash="semantic-alpha",
        aqo_hash="aqo-alpha",
        schema_version="1.0.0",
        compiler_version="compiler-1.0",
        aqo_version="aqo-1.0",
        optimizer_version="opt-1.0",
        policy_mode="deterministic",
        policy_digest="policy-1",
        seed=7,
        query_mode="structural",
        candidate_budget=8,
        deterministic=True,
    )

    assert result["tenant_id"] == "tenant-a"
    assert result["project_id"] == "project-a"
    assert all(not record_id.startswith("foreign-") for candidate in result["candidate_patterns"] for record_id in candidate["source_record_ids"])
    assert "tenant-b" not in json.dumps(result)
    assert "project-b" not in json.dumps(result)

    recommendation = service.get_recommendation(
        snapshot_id="tenant-a-s1",
        tenant_id="tenant-a",
        project_id="project-a",
        circuit_id="c1",
        backend_class="sim",
        min_confidence=0.1,
    )
    assert recommendation["tenant_id"] == "tenant-a"
    assert recommendation["project_id"] == "project-a"
    assert all(not rid.startswith("foreign-") for rid in recommendation["provenance"]["source_record_ids"])
    assert "tenant-b" not in json.dumps(recommendation)
    assert "project-b" not in json.dumps(recommendation)


def test_pattern_miner_recommendation_contract_fixture_v1_0_0() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "pattern_miner_recommendation_v1"
        / "recommendation_contract_v1_0_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "pattern_miner.recommendation"
    assert payload["version"] == "1.0.0"
    assert payload["semver_impact"] == "MINOR"
    assert payload["determinism"] == {
        "idempotent_ingest": True,
        "cadence_seconds": 300,
        "reproducible_for_same_snapshot_and_config_digest": True,
    }
    assert payload["compatibility"]["breaking"] is False
