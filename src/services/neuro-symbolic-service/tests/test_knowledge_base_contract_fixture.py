from __future__ import annotations

import json
from pathlib import Path


def test_knowledge_base_error_model_fixture_is_frozen_v1() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "knowledge_base_v1"
        / "error_model_v1_0_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "knowledge_base_api"
    assert payload["version"] == "1.0.0"
    assert payload["reason_codes"] == [
        "KB_INVALID_ARGUMENT",
        "KB_NOT_FOUND",
        "KB_INDEX_UNAVAILABLE",
        "KB_RATE_LIMITED",
        "KB_INTERNAL",
    ]
    assert payload["deprecation_policy"] == {
        "min_supported_minor_releases": 2,
        "min_supported_days": 90,
    }

def test_knowledge_base_immutability_anonymization_index_profile_fixture_v1_2_0() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "knowledge_base_v1"
        / "immutability_anonymization_index_profile_contract_v1_2_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "knowledge_base.immutability_anonymization_index_profile"
    assert payload["version"] == "1.2.0"
    assert payload["semver_impact"] == "MINOR"

    immutability = payload["immutability"]
    assert immutability["append_only"] is True
    assert immutability["record_types"] == ["Circuit", "Pattern", "Task"]
    assert immutability["mutation_block_reason_code"] == "KB_IMMUTABILITY_VIOLATION"

    anonymization = payload["anonymization"]
    assert anonymization["algorithm"] == "HMAC-SHA256"
    assert anonymization["runtime_reversible_mapping_allowed"] is False
    assert anonymization["salt_rotation_policy"] == {
        "rotation_period_days": 30,
        "overlap_acceptance_days": 14,
        "max_runtime_salt_epochs": 2,
    }

    slos = payload["index_profile"]["latency_slo_ms_p95"]
    assert slos == {
        "structural_search": 100,
        "vector_search": 180,
        "hybrid_search": 220,
    }

    assert payload["compatibility"]["breaking"] is False

def test_knowledge_base_provenance_lineage_replay_bundle_fixture_v1_0_0() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "knowledge_base_v1"
        / "provenance_lineage_replay_bundle_v1_0_0.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["contract"] == "knowledge_base.provenance_lineage_replay_bundle"
    assert payload["version"] == "1.0.0"
    assert payload["record"]["provenance"]["compiler_ref"] == "compiler://v1"
    assert payload["decision_log"]["selected_action"] == "backend-alpha"
    assert payload["privacy"]["anonymized_attributes"] == ["user_id", "project_id", "client_ip"]
    