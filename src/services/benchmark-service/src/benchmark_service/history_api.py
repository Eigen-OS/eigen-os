from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import json
from typing import Any

from .run_lifecycle import BenchmarkRun, BenchmarkRunService, RunState

BENCHMARK_HISTORY_API_VERSION = "1.0.0"
BENCHMARK_HISTORY_QUERY_VERSION = "1.0.0"

_ORDERING_GUARANTEE = "created_at_desc_run_id_asc"
_ALLOWED_STATES = {state.value for state in RunState}


@dataclass(frozen=True, slots=True)
class HistoryValidationError:
    code: str
    field: str
    message: str


class BenchmarkHistoryRequestValidationError(ValueError):
    """Raised when /benchmarks/history request validation fails."""

    def __init__(self, errors: list[HistoryValidationError]) -> None:
        super().__init__("benchmark history request validation failed")
        self.errors = errors


class BenchmarkHistoryApi:
    """Contract surface for /benchmarks/history deterministic trend queries."""

    def __init__(self, run_service: BenchmarkRunService | None = None) -> None:
        self._run_service = run_service or BenchmarkRunService()

    def history(self, request: dict[str, Any]) -> dict[str, Any]:
        errors = self._validate_request(request)
        if errors:
            raise BenchmarkHistoryRequestValidationError(errors)

        time_range = request["time_range"]
        start_at = _parse_iso8601(str(time_range["start_at"]))
        end_at = _parse_iso8601(str(time_range["end_at"]))
        filters = request.get("filters", {})
        page_size = int(request.get("page_size", 50))
        page_token = request.get("page_token")

        sorted_runs = self._sorted_runs(start_at=start_at, end_at=end_at, filters=filters)
        windowed_runs, next_page_token = _slice_with_cursor(
            runs=sorted_runs,
            page_size=page_size,
            page_token=page_token,
        )

        return {
            "api_version": BENCHMARK_HISTORY_API_VERSION,
            "query_version": BENCHMARK_HISTORY_QUERY_VERSION,
            "query": {
                "time_range": {
                    "start_at": start_at.isoformat(),
                    "end_at": end_at.isoformat(),
                },
                "filters": {
                    "states": sorted(filters.get("states", [])),
                    "dataset": filters.get("dataset"),
                },
            },
            "pagination": {
                "page_size": page_size,
                "ordering": _ORDERING_GUARANTEE,
                "next_page_token": next_page_token,
                "has_more": next_page_token is not None,
            },
            "trend": _build_trend(sorted_runs),
            "entries": [self._to_history_entry(run) for run in windowed_runs],
        }

    def to_error_envelope(self, err: BenchmarkHistoryRequestValidationError) -> dict[str, Any]:
        return {
            "error": {
                "code": "INVALID_ARGUMENT",
                "message": str(err),
                "details": [
                    {
                        "code": item.code,
                        "field": item.field,
                        "message": item.message,
                    }
                    for item in err.errors
                ],
            }
        }

    def _validate_request(self, request: dict[str, Any]) -> list[HistoryValidationError]:
        errors: list[HistoryValidationError] = []

        time_range = request.get("time_range")
        if not isinstance(time_range, dict):
            errors.append(
                HistoryValidationError(
                    code="field_required",
                    field="time_range",
                    message="time_range is required and must be an object",
                )
            )
            return errors

        start_at_raw = time_range.get("start_at")
        end_at_raw = time_range.get("end_at")
        start_at = None
        end_at = None

        if not isinstance(start_at_raw, str):
            errors.append(
                HistoryValidationError(
                    code="field_required",
                    field="time_range.start_at",
                    message="time_range.start_at is required and must be an ISO-8601 string",
                )
            )
        else:
            try:
                start_at = _parse_iso8601(start_at_raw)
            except ValueError:
                errors.append(
                    HistoryValidationError(
                        code="invalid_value",
                        field="time_range.start_at",
                        message="time_range.start_at must be a valid ISO-8601 datetime",
                    )
                )

        if not isinstance(end_at_raw, str):
            errors.append(
                HistoryValidationError(
                    code="field_required",
                    field="time_range.end_at",
                    message="time_range.end_at is required and must be an ISO-8601 string",
                )
            )
        else:
            try:
                end_at = _parse_iso8601(end_at_raw)
            except ValueError:
                errors.append(
                    HistoryValidationError(
                        code="invalid_value",
                        field="time_range.end_at",
                        message="time_range.end_at must be a valid ISO-8601 datetime",
                    )
                )

        if start_at is not None and end_at is not None and start_at > end_at:
            errors.append(
                HistoryValidationError(
                    code="invalid_value",
                    field="time_range",
                    message="time_range.start_at must be <= time_range.end_at",
                )
            )

        filters = request.get("filters", {})
        if filters is not None and not isinstance(filters, dict):
            errors.append(
                HistoryValidationError(
                    code="invalid_type",
                    field="filters",
                    message="filters must be an object when provided",
                )
            )
            filters = {}

        states = filters.get("states", []) if isinstance(filters, dict) else []
        if states is not None:
            if not isinstance(states, list) or not all(isinstance(item, str) for item in states):
                errors.append(
                    HistoryValidationError(
                        code="invalid_type",
                        field="filters.states",
                        message="filters.states must be an array of state strings",
                    )
                )
            else:
                invalid_states = sorted({state for state in states if state not in _ALLOWED_STATES})
                if invalid_states:
                    errors.append(
                        HistoryValidationError(
                            code="invalid_value",
                            field="filters.states",
                            message=f"unsupported states: {','.join(invalid_states)}",
                        )
                    )

        dataset = filters.get("dataset") if isinstance(filters, dict) else None
        if dataset is not None and (not isinstance(dataset, str) or not dataset.strip()):
            errors.append(
                HistoryValidationError(
                    code="invalid_value",
                    field="filters.dataset",
                    message="filters.dataset must be a non-empty string when provided",
                )
            )

        page_size = request.get("page_size", 50)
        if not isinstance(page_size, int) or not (1 <= page_size <= 100):
            errors.append(
                HistoryValidationError(
                    code="invalid_value",
                    field="page_size",
                    message="page_size must be an integer in [1, 100]",
                )
            )

        page_token = request.get("page_token")
        if page_token is not None:
            if not isinstance(page_token, str) or not page_token.strip():
                errors.append(
                    HistoryValidationError(
                        code="invalid_value",
                        field="page_token",
                        message="page_token must be a non-empty string when provided",
                    )
                )
            else:
                try:
                    _decode_cursor(page_token)
                except ValueError:
                    errors.append(
                        HistoryValidationError(
                            code="invalid_value",
                            field="page_token",
                            message="page_token is malformed",
                        )
                    )

        return errors

    def _sorted_runs(self, *, start_at: datetime, end_at: datetime, filters: dict[str, Any]) -> list[BenchmarkRun]:
        states = set(filters.get("states", []))
        dataset_filter = filters.get("dataset")
        selected: list[BenchmarkRun] = []

        for run in self._run_service.list_runs():
            created = _parse_iso8601(run.snapshot.created_at)
            if created < start_at or created > end_at:
                continue

            if states and run.state.value not in states:
                continue

            payload = json.loads(run.snapshot.payload)
            dataset = payload.get("dataset")
            if dataset_filter is not None and dataset != dataset_filter:
                continue

            selected.append(run)

        selected.sort(key=lambda item: (-_parse_iso8601(item.snapshot.created_at).timestamp(), item.run_id))
        return selected

    @staticmethod
    def _to_history_entry(run: BenchmarkRun) -> dict[str, Any]:
        payload = json.loads(run.snapshot.payload)
        return {
            "history_entry_version": run.snapshot.snapshot_version,
            "run_id": run.run_id,
            "parent_run_id": run.parent_run_id,
            "state": run.state.value,
            "state_contract_version": run.state_contract_version,
            "idempotency_key": run.idempotency_key,
            "created_at": run.snapshot.created_at,
            "request_hash": run.snapshot.request_hash,
            "dataset": payload.get("dataset"),
        }


def _slice_with_cursor(
    *,
    runs: list[BenchmarkRun],
    page_size: int,
    page_token: str | None,
) -> tuple[list[BenchmarkRun], str | None]:
    start_index = 0
    if page_token:
        cursor = _decode_cursor(page_token)
        for index, run in enumerate(runs):
            if run.snapshot.created_at == cursor["created_at"] and run.run_id == cursor["run_id"]:
                start_index = index + 1
                break

    page = runs[start_index : start_index + page_size]
    if (start_index + page_size) >= len(runs):
        return page, None

    last = page[-1]
    return page, _encode_cursor(created_at=last.snapshot.created_at, run_id=last.run_id)


def _build_trend(runs: list[BenchmarkRun]) -> dict[str, Any]:
    state_counts: dict[str, int] = {state: 0 for state in sorted(_ALLOWED_STATES)}
    by_day: dict[str, dict[str, int]] = {}

    for run in runs:
        state_name = run.state.value
        state_counts[state_name] += 1

        day = _parse_iso8601(run.snapshot.created_at).date().isoformat()
        bucket = by_day.setdefault(
            day,
            {
                "run_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "cancelled_count": 0,
            },
        )
        bucket["run_count"] += 1
        if state_name == RunState.SUCCEEDED.value:
            bucket["success_count"] += 1
        elif state_name == RunState.FAILED.value:
            bucket["failure_count"] += 1
        elif state_name == RunState.CANCELLED.value:
            bucket["cancelled_count"] += 1

    total = len(runs)
    terminal_count = (
        state_counts[RunState.SUCCEEDED.value]
        + state_counts[RunState.FAILED.value]
        + state_counts[RunState.CANCELLED.value]
    )
    success_rate = None
    if terminal_count > 0:
        success_rate = state_counts[RunState.SUCCEEDED.value] / terminal_count

    return {
        "total_runs": total,
        "terminal_runs": terminal_count,
        "success_rate": success_rate,
        "state_counts": state_counts,
        "daily": [
            {
                "date": day,
                **counts,
            }
            for day, counts in sorted(by_day.items())
        ],
    }


def _parse_iso8601(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _encode_cursor(*, created_at: str, run_id: str) -> str:
    raw = json.dumps({"created_at": created_at, "run_id": run_id}, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def _decode_cursor(page_token: str) -> dict[str, str]:
    try:
        decoded = base64.urlsafe_b64decode(page_token.encode("utf-8") + b"===").decode("utf-8")
        payload = json.loads(decoded)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid page token") from exc

    if not isinstance(payload, dict):
        raise ValueError("invalid page token")

    created_at = payload.get("created_at")
    run_id = payload.get("run_id")
    if not isinstance(created_at, str) or not isinstance(run_id, str):
        raise ValueError("invalid page token")

    _parse_iso8601(created_at)
    return {"created_at": created_at, "run_id": run_id}
