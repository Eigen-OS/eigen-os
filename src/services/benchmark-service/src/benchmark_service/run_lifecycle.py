from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any

RUN_CONTRACT_VERSION = "1.0.0"
SNAPSHOT_VERSION = "1.0.0"


class RunState(str, Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.PENDING: {RunState.PREPARING, RunState.CANCELLED},
    RunState.PREPARING: {RunState.RUNNING, RunState.FAILED, RunState.CANCELLED},
    RunState.RUNNING: {RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED},
    RunState.SUCCEEDED: set(),
    RunState.FAILED: set(),
    RunState.CANCELLED: set(),
}


class RunTransitionError(ValueError):
    """Raised when a transition violates run lifecycle contract v1."""


@dataclass(frozen=True, slots=True)
class BenchmarkRunSnapshot:
    contract_version: str
    snapshot_version: str
    run_id: str
    request_hash: str
    created_at: str
    payload: str


@dataclass(slots=True)
class BenchmarkRun:
    run_id: str
    parent_run_id: str | None
    state: RunState
    state_contract_version: str
    idempotency_key: str
    snapshot: BenchmarkRunSnapshot


class BenchmarkRunService:
    """In-memory benchmark run lifecycle core with idempotent start/retry."""

    def __init__(self) -> None:
        self._runs: dict[str, BenchmarkRun] = {}
        self._start_index: dict[str, str] = {}
        self._retry_index: dict[tuple[str, str], str] = {}

    def start_run(self, *, idempotency_key: str, config: dict[str, Any]) -> BenchmarkRun:
        existing_run_id = self._start_index.get(idempotency_key)
        if existing_run_id is not None:
            return self._runs[existing_run_id]

        run_id = self._stable_run_id("start", idempotency_key, config)
        run = self._create_run(run_id=run_id, parent_run_id=None, idempotency_key=idempotency_key, config=config)
        self._runs[run_id] = run
        self._start_index[idempotency_key] = run_id
        return run

    def retry_run(self, *, run_id: str, retry_key: str) -> BenchmarkRun:
        source_run = self._runs[run_id]
        if source_run.state not in {RunState.FAILED, RunState.CANCELLED}:
            raise RunTransitionError(f"retry is allowed only from FAILED/CANCELLED, got {source_run.state}")

        key = (run_id, retry_key)
        existing_retry = self._retry_index.get(key)
        if existing_retry is not None:
            return self._runs[existing_retry]

        retry_config = {
            "retry_of": run_id,
            "source_snapshot_hash": source_run.snapshot.request_hash,
            "retry_key": retry_key,
        }
        retry_run_id = self._stable_run_id("retry", retry_key, retry_config)
        retry_run = self._create_run(
            run_id=retry_run_id,
            parent_run_id=run_id,
            idempotency_key=retry_key,
            config=retry_config,
        )
        self._runs[retry_run_id] = retry_run
        self._retry_index[key] = retry_run_id
        return retry_run

    def transition(self, *, run_id: str, new_state: RunState) -> BenchmarkRun:
        run = self._runs[run_id]
        allowed_targets = ALLOWED_TRANSITIONS[run.state]
        if new_state not in allowed_targets:
            raise RunTransitionError(f"transition {run.state} -> {new_state} is forbidden in {RUN_CONTRACT_VERSION}")
        run.state = new_state
        return run

    def get_run(self, run_id: str) -> BenchmarkRun:
        return self._runs[run_id]

    def _create_run(
        self,
        *,
        run_id: str,
        parent_run_id: str | None,
        idempotency_key: str,
        config: dict[str, Any],
    ) -> BenchmarkRun:
        canonical_payload = json.dumps(config, sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        snapshot = BenchmarkRunSnapshot(
            contract_version=RUN_CONTRACT_VERSION,
            snapshot_version=SNAPSHOT_VERSION,
            run_id=run_id,
            request_hash=request_hash,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            payload=canonical_payload,
        )
        return BenchmarkRun(
            run_id=run_id,
            parent_run_id=parent_run_id,
            state=RunState.PENDING,
            state_contract_version=RUN_CONTRACT_VERSION,
            idempotency_key=idempotency_key,
            snapshot=snapshot,
        )

    @staticmethod
    def _stable_run_id(scope: str, key: str, payload: dict[str, Any]) -> str:
        normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{scope}:{key}:{normalized_payload}".encode("utf-8")).hexdigest()
        return f"run_{digest[:16]}"
