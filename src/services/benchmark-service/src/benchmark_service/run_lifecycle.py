from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Callable
from enum import Enum
import hashlib
import json
from typing import Any

RUN_CONTRACT_VERSION = "1.0.0"
SNAPSHOT_VERSION = "1.0.0"
BENCHMARK_PROFILE_KIND = "BenchmarkJob"
BENCHMARK_TELEMETRY_SCOPE = "benchmark"
BENCHMARK_ARTIFACT_PREFIX = "qfs://benchmarks"


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
    measurement_digest: str
    created_at: str
    payload: str
    execution_context: dict[str, Any]
    artifacts: dict[str, Any]


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

    def __init__(self, *, now_fn: Callable[[], datetime] | None = None, kb_sink: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._runs: dict[str, BenchmarkRun] = {}
        self._start_index: dict[str, str] = {}
        self._retry_index: dict[tuple[str, str], str] = {}
        self._now_fn = now_fn or (lambda: datetime.now(tz=timezone.utc))
        self._kb_sink = kb_sink

    def start_run(self, *, idempotency_key: str, config: dict[str, Any]) -> BenchmarkRun:
        existing_run_id = self._start_index.get(idempotency_key)
        if existing_run_id is not None:
            return self._runs[existing_run_id]

        run_id = self._stable_run_id("start", idempotency_key, config)
        run = self._create_run(run_id=run_id, parent_run_id=None, idempotency_key=idempotency_key, config=config)
        self._runs[run_id] = run
        self._start_index[idempotency_key] = run_id
        self._emit_kb_record(run, kind="start", source_run_id=None, retry_key=None)
        return run

    def retry_run(self, *, run_id: str, retry_key: str) -> BenchmarkRun:
        source_run = self._runs[run_id]
        if source_run.state not in {RunState.FAILED, RunState.CANCELLED}:
            raise RunTransitionError(f"retry is allowed only from FAILED/CANCELLED, got {source_run.state}")

        key = (run_id, retry_key)
        existing_retry = self._retry_index.get(key)
        if existing_retry is not None:
            return self._runs[existing_retry]

        source_context = source_run.snapshot.execution_context
        retry_config = {
            "dataset": source_context["dataset"],
            "dataset_version": source_context["dataset_version"],
            "backend": source_context["backend"],
            "target": source_context["target"],
            "seed": source_context["seed"],
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
        self._emit_kb_record(retry_run, kind="retry", source_run_id=run_id, retry_key=retry_key)
        return retry_run

    def transition(self, *, run_id: str, new_state: RunState) -> BenchmarkRun:
        run = self._runs[run_id]
        allowed_targets = ALLOWED_TRANSITIONS[run.state]
        if new_state not in allowed_targets:
            raise RunTransitionError(f"transition {run.state} -> {new_state} is forbidden in {RUN_CONTRACT_VERSION}")
        run.state = new_state
        self._emit_kb_record(run, kind="transition", source_run_id=run_id, retry_key=None)
        return run

    def get_run(self, run_id: str) -> BenchmarkRun:
        return self._runs[run_id]

    def list_runs(self) -> list[BenchmarkRun]:
        return list(self._runs.values())

    def _create_run(
        self,
        *,
        run_id: str,
        parent_run_id: str | None,
        idempotency_key: str,
        config: dict[str, Any],
    ) -> BenchmarkRun:
        target = str(config.get("target") or config.get("backend") or "")
        execution_context = {
            "profile_kind": BENCHMARK_PROFILE_KIND,
            "profile_version": RUN_CONTRACT_VERSION,
            "dataset": str(config.get("dataset", "")),
            "dataset_version": str(config.get("dataset_version", "")),
            "backend": str(config.get("backend", "")),
            "target": target,
            "seed": int(config.get("seed", 0)),
            "selection_policy": "backend_locked" if target == str(config.get("backend", "")) else "explicit_target",
            "trace_scope": BENCHMARK_TELEMETRY_SCOPE,
            "telemetry_scope": BENCHMARK_TELEMETRY_SCOPE,
        }
        canonical_payload = json.dumps(
            {
                "dataset": execution_context["dataset"],
                "dataset_version": execution_context["dataset_version"],
                "backend": execution_context["backend"],
                "target": execution_context["target"],
                "seed": execution_context["seed"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        request_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        measurement_digest = hashlib.sha256(
            json.dumps(execution_context, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        artifacts = {
            "metrics_artifact_ref": f"{BENCHMARK_ARTIFACT_PREFIX}/{run_id}/metrics/summary.json",
            "metrics_artifact_digest": measurement_digest,
            "lineage_ref": f"{BENCHMARK_ARTIFACT_PREFIX}/{run_id}/lineage.json",
            "telemetry_ref": f"{BENCHMARK_ARTIFACT_PREFIX}/{run_id}/telemetry/isolated.jsonl",
            "normalized_metrics": {
                "dataset": execution_context["dataset"],
                "dataset_version": execution_context["dataset_version"],
                "backend": execution_context["backend"],
                "target": execution_context["target"],
                "seed": execution_context["seed"],
                "request_hash": request_hash,
            },
        }
        snapshot = BenchmarkRunSnapshot(
            contract_version=RUN_CONTRACT_VERSION,
            snapshot_version=SNAPSHOT_VERSION,
            run_id=run_id,
            request_hash=request_hash,
            measurement_digest=measurement_digest,
            created_at=self._now_fn().astimezone(timezone.utc).isoformat(),
            payload=canonical_payload,
            execution_context=execution_context,
            artifacts=artifacts,
        )
        run = BenchmarkRun(
            run_id=run_id,
            parent_run_id=parent_run_id,
            state=RunState.PENDING,
            state_contract_version=RUN_CONTRACT_VERSION,
            idempotency_key=idempotency_key,
            snapshot=snapshot,
        )
        return run

    @staticmethod
    def _stable_run_id(scope: str, key: str, payload: dict[str, Any]) -> str:
        normalized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(f"{scope}:{key}:{normalized_payload}".encode("utf-8")).hexdigest()
        return f"run_{digest[:16]}"

    def _emit_kb_record(self, run: BenchmarkRun, *, kind: str, source_run_id: str | None, retry_key: str | None) -> None:
        if self._kb_sink is None:
            return
        
        source_measurement_digest = run.snapshot.measurement_digest
        if source_run_id is not None and source_run_id in self._runs:
            source_measurement_digest = self._runs[source_run_id].snapshot.measurement_digest

        payload = {
            "contract_version": RUN_CONTRACT_VERSION,
            "record_id": f"benchmark:{run.run_id}",
            "run_id": run.run_id,
            "job_id": run.run_id,
            "parent_run_id": run.parent_run_id or source_run_id,
            "idempotency_key": run.idempotency_key,
            "state": run.state.value,
            "request_hash": run.snapshot.request_hash,
            "measurement_digest": source_measurement_digest,
            "created_at": run.snapshot.created_at,
            "trace_id": f"trace_{run.run_id[:8]}",
            "trace_scope": BENCHMARK_TELEMETRY_SCOPE,
            "tenant_id": "tenant-default",
            "project_id": "project-default",
            "replay_bundle_ref": f"{BENCHMARK_ARTIFACT_PREFIX}/{run.run_id}/replay_bundle.json",
            "attributes": {
                "kind": kind,
                "scope": BENCHMARK_TELEMETRY_SCOPE,
                "source_run_id": source_run_id or "",
                "retry_key": retry_key or "",
                "request_hash": run.snapshot.request_hash,
                "measurement_digest": run.snapshot.measurement_digest,
                "state": run.state.value,
                "workload_kind": BENCHMARK_PROFILE_KIND,
            },
            "provenance": {
                "runtime_ref": f"{BENCHMARK_ARTIFACT_PREFIX}/{run.run_id}/runtime.json",
                "checkpoint_ref": f"{BENCHMARK_ARTIFACT_PREFIX}/{run.run_id}/checkpoint.json",
                "compiler_ref": "",
                "optimizer_ref": "",
            },
            "lineage": {
                "model_version": RUN_CONTRACT_VERSION,
                "training_set_hash": run.snapshot.request_hash,
                "evaluation_bundle_hash": source_measurement_digest,
                "promotion_policy_version": RUN_CONTRACT_VERSION,
                "promotion_outcome": run.state.value,
            },
            "execution_context": run.snapshot.execution_context,
            "artifacts": run.snapshot.artifacts,
        }
        self._kb_sink(payload)
        