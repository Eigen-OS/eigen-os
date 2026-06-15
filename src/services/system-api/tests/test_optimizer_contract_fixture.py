from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path


ALLOWED_CLASSIFICATION_LABELS = {
    "Advisory",
    "Optimization",
    "Recommendation",
    "Informational",
}


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _load_fixture() -> dict[str, object]:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "contracts"
        / "optimizer_v1"
        / "service_contract_v1_0_0.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _replay_digest(example: dict[str, object]) -> str:
    request = example["request"]
    response = example["response"]
    selected_candidate = response["candidates"][0]
    return _sha256_hex(
        _canonical_json(
            {
                "request": request,
                "selected_candidate": selected_candidate,
                "selected_candidate_id": response["selected_candidate_id"],
                "confidence_score": response["confidence_score"],
                "fallback": {
                    "used": response["fallback_used"],
                    "reason_code": response["fallback_reason_code"],
                },
            }
        )
    )


def _validate_classification_label(label: str) -> str:
    normalized = label.strip()
    if normalized not in ALLOWED_CLASSIFICATION_LABELS:
        raise ValueError(f"unknown model output classification label: {label}")
    return normalized


def test_optimizer_contract_fixture_is_frozen_v1() -> None:
    payload = _load_fixture()

    assert payload["contract"] == "optimizer_service"
    assert payload["version"] == "1.0.0"
    assert payload["request"]["deterministic_defaults"] == {
        "candidate_budget": 1,
        "timeout_ms": 100,
        "trace_context": {},
    }
    assert payload["request"]["graph_encoding"]["canonical_format"] == "aqo-json"
    assert payload["request"]["graph_encoding"]["encoding_version"] == "aqo-graph-v1"
    assert payload["response"]["fallback_contract"] == {
        "fallback_used": True,
        "requires_fallback_reason": True,
        "requires_fallback_reason_code": True,
    }
    assert payload["response"]["metric_bounds"]["confidence_score"] == {"min": 0.0, "max": 1.0}
    assert payload["response"]["decision_lineage"]["optimizer"]["fallback_used"] is False
    assert payload["response"]["classification_label"] == "Optimization"
    assert payload["examples"]["replay"]["response"]["classification_label"] == "Optimization"
    assert payload["examples"]["fallback"]["response"]["classification_label"] == "Advisory"
    assert payload["reason_codes"] == [
        "EIGEN_OPT_INVALID_AQO",
        "EIGEN_OPT_TOPOLOGY_MISSING",
        "EIGEN_OPT_MODEL_UNAVAILABLE",
        "EIGEN_OPT_TIMEOUT",
        "EIGEN_OPT_INTERNAL",
        "EIGEN_OPT_FEATURE_EXTRACTION_FAILED",
        "EIGEN_OPT_CONFIDENCE_TOO_LOW",
        "EIGEN_OPT_UNSUPPORTED_BACKEND",
        "EIGEN_OPT_POLICY_REJECTED",
    ]


def test_optimizer_graph_encoding_round_trip_is_canonical_v1() -> None:
    payload = _load_fixture()
    graph_encoding = payload["request"]["graph_encoding"]
    canonical_graph = graph_encoding["canonical_graph"]
    canonical_bytes = _canonical_json(canonical_graph)

    assert _canonical_json(json.loads(canonical_bytes)) == canonical_bytes
    assert graph_encoding["canonical_sha256"] == _sha256_hex(canonical_bytes)
    assert graph_encoding["round_trip_stability"] is True
    assert payload["request"]["trace_context"]["traceparent"].startswith("00-")


def test_optimizer_deterministic_replay_is_stable_v1() -> None:
    payload = _load_fixture()
    replay = payload["examples"]["replay"]

    first_digest = replay["response"]["optimizer_digest"]
    second_digest = _replay_digest(replay)

    assert first_digest == second_digest
    assert replay["response"]["selected_candidate_id"] == replay["response"]["candidates"][0]["candidate_id"]
    assert replay["response"]["candidates"][0]["rank"] == 1
    assert replay["response"]["candidates"][0]["selected"] is True
    assert replay["response"]["candidates"][0]["score"]["total_score"] > replay["response"]["candidates"][1]["score"]["total_score"]
    assert replay["response"]["candidates"][0]["confidence"] == replay["response"]["confidence_score"]
    assert replay["response"]["decision_lineage"]["trace_context"]["traceparent"] == replay["request"]["trace_context"]["traceparent"]


def test_optimizer_fallback_path_fixture_requires_reason_code_v1() -> None:
    payload = _load_fixture()
    fallback = payload["examples"]["fallback"]

    assert fallback["response"]["fallback_used"] is True
    assert fallback["response"]["fallback_reason_code"] == "EIGEN_OPT_FEATURE_EXTRACTION_FAILED"
    assert fallback["response"]["fallback_reason"]
    assert fallback["response"]["decision_lineage"]["optimizer"]["fallback_used"] is True
    assert fallback["response"]["metric_bounds"]["confidence_score"] == {"min": 0.0, "max": 1.0}
    assert fallback["response"]["selected_candidate_id"] == "fallback-0"
    assert fallback["response"]["candidates"][0]["rank"] == 1
    assert fallback["response"]["candidates"][0]["selected"] is True


def test_optimizer_confidence_and_explainability_fixture_are_bounded_v1() -> None:
    payload = _load_fixture()
    replay = payload["examples"]["replay"]
    confidence = replay["response"]["confidence_score"]
    digest = replay["response"]["optimizer_digest"]

    assert 0.0 <= confidence <= 1.0
    assert replay["response"]["metric_bounds"]["confidence_score"] == {"min": 0.0, "max": 1.0}
    assert len(digest) == 64
    assert digest == _replay_digest(replay)
    assert replay["response"]["candidates"][0]["confidence"] == confidence
    assert payload["response"]["ranking"]["selected_candidate_id"] == replay["response"]["selected_candidate_id"]
    assert payload["response"]["ranking"]["ordered_candidate_ids"] == [
        candidate["candidate_id"] for candidate in replay["response"]["candidates"]
    ]


def test_optimizer_classification_label_validation_is_strict_v1() -> None:
    for label in sorted(ALLOWED_CLASSIFICATION_LABELS):
        assert _validate_classification_label(label) == label

    try:
        _validate_classification_label("Unknown")
    except ValueError:
        pass
    else:  # pragma: no cover - defensive branch
        raise AssertionError("unknown classification labels must be rejected")
