from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark_service.run_api import (
    BENCHMARK_RUN_API_VERSION,
    BENCHMARK_RUN_HISTORY_VERSION,
    BenchmarkRunApi,
    BenchmarkRunRequestValidationError,
)
from benchmark_service.run_lifecycle import RUN_CONTRACT_VERSION, SNAPSHOT_VERSION

CONTRACT_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "benchmark_run_v1"


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((CONTRACT_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_benchmark_run_success_contract_fixture_is_stable() -> None:
    api = BenchmarkRunApi()
    request = _load_json("request.json")
    contract = _load_json("expected_contract.json")

    response = api.run(request)

    assert set(contract["request_required_fields"]).issubset(request.keys())
    assert set(contract["response_required_top_level_fields"]) == set(response.keys())
    assert set(contract["response_required_run_fields"]) == set(response["run"].keys())
    assert set(contract["response_required_snapshot_fields"]) == set(response["snapshot"].keys())

    assert response["api_version"] == BENCHMARK_RUN_API_VERSION
    assert response["run"]["state"] == "PENDING"
    assert response["run"]["state_contract_version"] == RUN_CONTRACT_VERSION
    assert response["snapshot"]["contract_version"] == RUN_CONTRACT_VERSION
    assert response["snapshot"]["snapshot_version"] == SNAPSHOT_VERSION
    assert response["snapshot"]["history_entry_version"] == BENCHMARK_RUN_HISTORY_VERSION


def test_benchmark_run_validation_errors_map_to_public_error_envelope() -> None:
    api = BenchmarkRunApi()
    contract = _load_json("expected_contract.json")

    try:
        api.run({"config": {}})
    except BenchmarkRunRequestValidationError as err:
        envelope = api.to_error_envelope(err)
    else:
        raise AssertionError("invalid request must fail")

    assert set(contract["error_required_top_level_fields"]) == set(envelope.keys())
    assert set(contract["error_required_fields"]) == set(envelope["error"].keys())
    assert envelope["error"]["code"] == "INVALID_ARGUMENT"

    detail = envelope["error"]["details"][0]
    assert set(contract["error_required_detail_fields"]) == set(detail.keys())
