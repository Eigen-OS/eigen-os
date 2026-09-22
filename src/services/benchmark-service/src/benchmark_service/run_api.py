from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .run_lifecycle import BENCHMARK_PROFILE_KIND, BenchmarkRunService, BenchmarkRunSnapshot, RunState

BENCHMARK_RUN_API_VERSION = "1.0.0"
BENCHMARK_RUN_HISTORY_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ApiValidationError:
    code: str
    field: str
    message: str


class BenchmarkRunRequestValidationError(ValueError):
    """Raised when /benchmarks/run request validation fails."""

    def __init__(self, errors: list[ApiValidationError]) -> None:
        super().__init__("benchmark run request validation failed")
        self.errors = errors


class BenchmarkRunApi:
    """Contract surface for /benchmarks/run endpoint payloads."""

    def __init__(self, run_service: BenchmarkRunService | None = None, kb_sink=None) -> None:
        self._run_service = run_service or BenchmarkRunService(kb_sink=kb_sink)

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        errors = self._validate_request(request)
        if errors:
            raise BenchmarkRunRequestValidationError(errors)

        run = self._run_service.start_run(
            idempotency_key=request["idempotency_key"],
            config=request["config"],
        )
        return self._to_success_response(run)

    def to_error_envelope(self, err: BenchmarkRunRequestValidationError) -> dict[str, Any]:
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

    def _validate_request(self, request: dict[str, Any]) -> list[ApiValidationError]:
        errors: list[ApiValidationError] = []

        idempotency_key = request.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            errors.append(
                ApiValidationError(
                    code="field_required",
                    field="idempotency_key",
                    message="idempotency_key is required and must be a non-empty string",
                )
            )

        config = request.get("config")
        if not isinstance(config, dict) or not config:
            errors.append(
                ApiValidationError(
                    code="field_required",
                    field="config",
                    message="config is required and must be a non-empty object",
                )
            )
            return errors

        for field in ("dataset", "dataset_version", "backend", "seed"):
            value = config.get(field)
            if field == "seed":
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(
                        ApiValidationError(
                            code="field_required",
                            field=f"config.{field}",
                            message="config.seed is required and must be an integer seed",
                        )
                    )
                continue

            if not isinstance(value, str) or not value.strip():
                errors.append(
                    ApiValidationError(
                        code="field_required",
                        field=f"config.{field}",
                        message=f"config.{field} is required and must be a non-empty string",
                    )
                )

        target = config.get("target")
        if target is not None and (not isinstance(target, str) or not target.strip()):
            errors.append(
                ApiValidationError(
                    code="invalid_value",
                    field="config.target",
                    message="config.target must be a non-empty string when provided",
                )
            )
        if isinstance(target, str) and isinstance(config.get("backend"), str) and target.strip() != config["backend"].strip():
            errors.append(
                ApiValidationError(
                    code="failed_precondition",
                    field="config.target",
                    message="config.target must match config.backend when explicitly set",
                )
            )

        return errors

    @staticmethod
    def _to_success_response(run: Any) -> dict[str, Any]:
        snapshot: BenchmarkRunSnapshot = run.snapshot
        return {
            "api_version": BENCHMARK_RUN_API_VERSION,
            "run": {
                "run_id": run.run_id,
                "workload_kind": BENCHMARK_PROFILE_KIND,
                "state": _run_state_value(run.state),
                "state_contract_version": run.state_contract_version,
                "parent_run_id": run.parent_run_id,
                "idempotency_key": run.idempotency_key,
            },
            "snapshot": {
                "contract_version": snapshot.contract_version,
                "snapshot_version": snapshot.snapshot_version,
                "history_entry_version": BENCHMARK_RUN_HISTORY_VERSION,
                "run_id": snapshot.run_id,
                "request_hash": snapshot.request_hash,
                "created_at": snapshot.created_at,
                "payload": snapshot.payload,
                "measurement_digest": snapshot.measurement_digest,
                "execution_context": snapshot.execution_context,
                "artifacts": snapshot.artifacts,
            },
            "execution_context": snapshot.execution_context,
            "artifacts": snapshot.artifacts,
        }


def _run_state_value(state: RunState | str) -> str:
    if isinstance(state, RunState):
        return state.value
    return str(state)
