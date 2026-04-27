from __future__ import annotations

import json
from pathlib import Path

from benchmark_service.compare_api import (
    BENCHMARK_COMPARE_API_VERSION,
    BENCHMARK_COMPARE_METHODOLOGY_VERSION,
    BENCHMARK_COMPARE_SCHEMA_VERSION,
    BenchmarkCompareApi,
    BenchmarkCompareRequestValidationError,
)

CONTRACT_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "benchmark_compare_v1"


def _load_json(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_benchmark_compare_success_contract_fixture_is_stable() -> None:
    api = BenchmarkCompareApi()
    request = _load_json("request.json")
    contract = _load_json("expected_contract.json")

    response = api.compare(request)

    assert set(contract["request_required_fields"]).issubset(request.keys())
    assert set(contract["response_required_top_level_fields"]) == set(response.keys())
    assert set(contract["response_required_comparison_fields"]) == set(response["comparison"].keys())

    for metric in response["comparison"]["metrics"]:
        assert set(contract["response_required_metric_fields"]) == set(metric.keys())

    assert response["api_version"] == BENCHMARK_COMPARE_API_VERSION
    assert response["comparison_schema_version"] == BENCHMARK_COMPARE_SCHEMA_VERSION
    assert (
        response["comparison"]["methodology"]["methodology_version"] == BENCHMARK_COMPARE_METHODOLOGY_VERSION
    )


def test_benchmark_compare_is_deterministic_for_identical_inputs() -> None:
    api = BenchmarkCompareApi()
    request = _load_json("request.json")

    first = api.compare(request)
    second = api.compare(request)

    assert first == second


def test_benchmark_compare_regression_flagging_is_fixture_covered() -> None:
    api = BenchmarkCompareApi()
    request = _load_json("regression_request.json")

    response = api.compare(request)
    by_name = {item["name"]: item for item in response["comparison"]["metrics"]}

    assert by_name["energy_j"]["regression"]["is_regression"] is True
    assert by_name["fidelity"]["regression"]["is_regression"] is False
    assert response["comparison"]["summary"]["regression_count"] == 1
    assert response["comparison"]["summary"]["regression_metrics"] == ["energy_j"]


def test_benchmark_compare_validation_errors_map_to_public_error_envelope() -> None:
    api = BenchmarkCompareApi()
    contract = _load_json("expected_contract.json")

    try:
        api.compare({"baseline": {}, "candidate": {}, "policy": {}})
    except BenchmarkCompareRequestValidationError as err:
        envelope = api.to_error_envelope(err)
    else:
        raise AssertionError("invalid request must fail")

    assert set(contract["error_required_top_level_fields"]) == set(envelope.keys())
    assert set(contract["error_required_fields"]) == set(envelope["error"].keys())
    assert envelope["error"]["code"] == "INVALID_ARGUMENT"

    detail = envelope["error"]["details"][0]
    assert set(contract["error_required_detail_fields"]) == set(detail.keys())
