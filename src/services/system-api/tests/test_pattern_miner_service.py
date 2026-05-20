from __future__ import annotations

import json
from pathlib import Path

from system_api.pattern_miner import PatternMinerService


def _dataset() -> list[dict[str, str]]:
    return [
        {"record_id": "r-2", "circuit_id": "c1", "backend_class": "sim"},
        {"record_id": "r-1", "circuit_id": "c1", "backend_class": "sim"},
        {"record_id": "r-3", "circuit_id": "c2", "backend_class": "qpu"},
    ]


def test_pattern_miner_ingest_is_idempotent_and_deterministic() -> None:
    service = PatternMinerService()
    first = service.ingest_snapshot(snapshot_id="s1", records=_dataset(), config_digest="cfg-a")
    second = service.ingest_snapshot(snapshot_id="s1", records=list(reversed(_dataset())), config_digest="cfg-a")

    assert first.created is True
    assert second.created is False
    assert first.idempotency_key == second.idempotency_key

    mined_first = service.mine_patterns(snapshot_id="s1")
    mined_second = service.mine_patterns(snapshot_id="s1")
    assert mined_first == mined_second


def test_recommendation_payload_has_versioned_contract_and_provenance_links() -> None:
    service = PatternMinerService()
    service.ingest_snapshot(snapshot_id="s1", records=_dataset(), config_digest="cfg-a")

    recommendation = service.get_recommendation(snapshot_id="s1", circuit_id="c1", backend_class="sim", min_confidence=0.1)
    assert recommendation["contract"] == "pattern_miner.recommendation"
    assert recommendation["version"] == "1.0.0"
    assert recommendation["recommendation"]["fallback_used"] is False
    assert recommendation["provenance"]["source_record_ids"] == ["r-1", "r-2"]
    assert recommendation["provenance"]["queryable_links"] == ["kb://records/r-1", "kb://records/r-2"]


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
    