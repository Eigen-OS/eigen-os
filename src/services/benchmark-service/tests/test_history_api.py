from __future__ import annotations

from datetime import datetime, timezone

from benchmark_service.history_api import (
    BENCHMARK_HISTORY_API_VERSION,
    BENCHMARK_HISTORY_QUERY_VERSION,
    BenchmarkHistoryApi,
    BenchmarkHistoryRequestValidationError,
)
from benchmark_service.run_lifecycle import BenchmarkRunService, RunState


def _clock(sequence: list[str]):
    items = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in sequence]

    def _next() -> datetime:
        if not items:
            raise AssertionError("clock sequence exhausted")
        return items.pop(0).astimezone(timezone.utc)

    return _next


def test_history_endpoint_supports_deterministic_pagination_and_ordering() -> None:
    service = BenchmarkRunService(
        now_fn=_clock(
            [
                "2026-04-20T09:00:00Z",
                "2026-04-20T10:00:00Z",
                "2026-04-20T11:00:00Z",
            ]
        )
    )
    run_a = service.start_run(idempotency_key="a", config={"dataset": "d1"})
    run_b = service.start_run(idempotency_key="b", config={"dataset": "d1"})
    run_c = service.start_run(idempotency_key="c", config={"dataset": "d1"})

    service.transition(run_id=run_a.run_id, new_state=RunState.PREPARING)
    service.transition(run_id=run_a.run_id, new_state=RunState.RUNNING)
    service.transition(run_id=run_a.run_id, new_state=RunState.SUCCEEDED)

    service.transition(run_id=run_b.run_id, new_state=RunState.PREPARING)
    service.transition(run_id=run_b.run_id, new_state=RunState.FAILED)

    api = BenchmarkHistoryApi(run_service=service)
    request = {
        "time_range": {
            "start_at": "2026-04-20T00:00:00Z",
            "end_at": "2026-04-21T00:00:00Z",
        },
        "filters": {"dataset": "d1"},
        "page_size": 2,
    }

    first_page = api.history(request)
    second_page = api.history({**request, "page_token": first_page["pagination"]["next_page_token"]})

    assert first_page["api_version"] == BENCHMARK_HISTORY_API_VERSION
    assert first_page["query_version"] == BENCHMARK_HISTORY_QUERY_VERSION
    assert first_page["pagination"]["ordering"] == "created_at_desc_run_id_asc"
    assert [entry["run_id"] for entry in first_page["entries"]] == [run_c.run_id, run_b.run_id]
    assert [entry["run_id"] for entry in second_page["entries"]] == [run_a.run_id]
    assert second_page["pagination"]["has_more"] is False


def test_history_endpoint_applies_filters_and_returns_trend_aggregates() -> None:
    service = BenchmarkRunService(
        now_fn=_clock(
            [
                "2026-04-20T09:00:00Z",
                "2026-04-20T11:00:00Z",
                "2026-04-21T07:00:00Z",
            ]
        )
    )

    run_success = service.start_run(idempotency_key="success", config={"dataset": "chem-v1"})
    run_failed = service.start_run(idempotency_key="failed", config={"dataset": "chem-v1"})
    run_other = service.start_run(idempotency_key="other", config={"dataset": "ml-v2"})

    for run_id in (run_success.run_id, run_failed.run_id, run_other.run_id):
        service.transition(run_id=run_id, new_state=RunState.PREPARING)

    service.transition(run_id=run_success.run_id, new_state=RunState.RUNNING)
    service.transition(run_id=run_success.run_id, new_state=RunState.SUCCEEDED)
    service.transition(run_id=run_failed.run_id, new_state=RunState.FAILED)
    service.transition(run_id=run_other.run_id, new_state=RunState.CANCELLED)

    api = BenchmarkHistoryApi(run_service=service)
    response = api.history(
        {
            "time_range": {
                "start_at": "2026-04-20T00:00:00Z",
                "end_at": "2026-04-22T00:00:00Z",
            },
            "filters": {"states": ["SUCCEEDED", "FAILED"], "dataset": "chem-v1"},
            "page_size": 10,
        }
    )

    assert [entry["run_id"] for entry in response["entries"]] == [run_failed.run_id, run_success.run_id]
    assert response["trend"]["total_runs"] == 2
    assert response["trend"]["terminal_runs"] == 2
    assert response["trend"]["state_counts"]["SUCCEEDED"] == 1
    assert response["trend"]["state_counts"]["FAILED"] == 1
    assert response["trend"]["success_rate"] == 0.5
    assert response["trend"]["daily"] == [
        {
            "date": "2026-04-20",
            "run_count": 2,
            "success_count": 1,
            "failure_count": 1,
            "cancelled_count": 0,
        }
    ]


def test_history_endpoint_validation_errors_map_to_public_error_envelope() -> None:
    api = BenchmarkHistoryApi()

    try:
        api.history(
            {
                "time_range": {
                    "start_at": "2026-05-01T00:00:00Z",
                    "end_at": "2026-04-01T00:00:00Z",
                },
                "filters": {"states": ["BROKEN"]},
                "page_size": 0,
                "page_token": "not-a-token",
            }
        )
    except BenchmarkHistoryRequestValidationError as err:
        envelope = api.to_error_envelope(err)
    else:
        raise AssertionError("invalid request must fail")

    assert envelope["error"]["code"] == "INVALID_ARGUMENT"
    fields = {detail["field"] for detail in envelope["error"]["details"]}
    assert "time_range" in fields
    assert "filters.states" in fields
    assert "page_size" in fields
    assert "page_token" in fields
