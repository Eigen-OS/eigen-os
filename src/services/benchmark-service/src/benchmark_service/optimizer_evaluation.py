from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .compare_api import BenchmarkCompareApi

OPTIMIZER_EVAL_CONTRACT_VERSION = "1.5.0"
OPTIMIZER_BASELINE_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class TopologyEdge:
    source: str
    target: str
    fidelity: float


class TopologyAwareBaseline:
    """Deterministic topology-aware heuristic baseline for routing/placement cost."""

    def score(self, request: dict[str, Any]) -> dict[str, Any]:
        nodes = sorted(str(node) for node in request.get("nodes", []))
        edges = [
            TopologyEdge(
                source=str(edge["source"]),
                target=str(edge["target"]),
                fidelity=float(edge["fidelity"]),
            )
            for edge in request.get("edges", [])
        ]
        edge_penalty = sum(1.0 - min(max(edge.fidelity, 0.0), 1.0) for edge in edges)
        placement_cost = float(len(nodes)) + edge_penalty
        route_count = len(edges)
        return {
            "baseline_version": OPTIMIZER_BASELINE_VERSION,
            "placement_cost": round(placement_cost, 6),
            "route_count": route_count,
            "edge_penalty": round(edge_penalty, 6),
        }


class OptimizerEvaluationHarness:
    """Offline/online deterministic evaluation harness for Phase-8C promotion gates."""

    def __init__(self) -> None:
        self._compare_api = BenchmarkCompareApi()
        self._baseline = TopologyAwareBaseline()

    def _trace_context(self, fixture: dict[str, Any]) -> dict[str, str]:
        trace_context = dict(fixture.get("trace_context", {}))
        trace_id = str(trace_context.get("trace_id", ""))
        if not trace_id:
            trace_id = self._sha256_digest(
                {
                    "dataset_ref": fixture.get("dataset_ref"),
                    "dataset_hash": fixture.get("dataset_hash"),
                    "seed": int(fixture.get("seed", 0)),
                }
            )[:32]
        request_id = str(trace_context.get("request_id", "")) or f"optimizer-{int(fixture.get('seed', 0)):04d}"
        traceparent = str(trace_context.get("traceparent", "")) or f"00-{trace_id}-0000000000000000-01"
        return {
            "request_id": request_id,
            "trace_id": trace_id,
            "traceparent": traceparent,
        }

    def _decision_lineage(
        self,
        *,
        fixture: dict[str, Any],
        topology_request: dict[str, Any],
        baseline_snapshot: dict[str, Any],
        candidate_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
            "dataset_ref": fixture["dataset_ref"],
            "dataset_hash": fixture["dataset_hash"],
            "topology_hash": f"sha256:{self._sha256_digest(topology_request)}",
            "baseline_run_id": str(baseline_snapshot.get("run_id", "")),
            "candidate_run_id": str(candidate_snapshot.get("run_id", "")),
            "compare_policy_direction": str(fixture.get("compare_policy", {}).get("direction", "")),
        }

    def _sha256_digest(self, payload: Any) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    def _observability_bundle(
        self,
        *,
        fixture: dict[str, Any],
        trace_context: dict[str, str],
        confidence: float,
        fallback_used: bool,
        fallback_reason_code: str,
        fallback_reason: str,
        baseline_snapshot: dict[str, Any],
        candidate_snapshot: dict[str, Any],
        topology_request: dict[str, Any],
        observed_shadow_samples: int,
        min_shadow_samples: int,
    ) -> dict[str, Any]:
        baseline_metrics = {
            str(metric["name"]): float(metric["mean"])
            for metric in baseline_snapshot.get("metrics", [])
        }
        candidate_metrics = {
            str(metric["name"]): float(metric["mean"])
            for metric in candidate_snapshot.get("metrics", [])
        }
        runtime_ms = float(candidate_metrics.get("latency_ms", 0.0))
        baseline_fidelity = float(baseline_metrics.get("fidelity", 0.0))
        candidate_fidelity = float(candidate_metrics.get("fidelity", 0.0))
        return {
            "trace_context": trace_context,
            "decision_lineage": self._decision_lineage(
                fixture=fixture,
                topology_request=topology_request,
                baseline_snapshot=baseline_snapshot,
                candidate_snapshot=candidate_snapshot,
            ),
            "confidence_metadata": {
                "score": confidence,
                "minimum_confidence": float(fixture.get("compare_policy", {}).get("min_confidence", 0.0)),
                "source": "shadow_sample_coverage",
                "bounded": True,
            },
            "fallback_metadata": {
                "used": fallback_used,
                "reason_code": fallback_reason_code,
                "reason": fallback_reason,
            },
            "metric_bounds": {
                "confidence_score": {"min": 0.0, "max": 1.0},
                "predicted_error": {"min": 0.0, "max": 1.0},
                "observed_error": {"min": 0.0, "max": 1.0},
                "runtime_ms": {"min": 0.0, "max": max(0.0, runtime_ms)},
                "observed_shadow_samples": {
                    "min": 0,
                    "max": max(observed_shadow_samples, min_shadow_samples),
                },
                "baseline_fidelity": {
                    "min": 0.0,
                    "max": max(1.0, baseline_fidelity),
                },
                "candidate_fidelity": {
                    "min": 0.0,
                    "max": max(1.0, candidate_fidelity),
                },
            },
            "trace_fields": ["request_id", "trace_id", "traceparent"],
        }

    def evaluate_offline(self, fixture: dict[str, Any]) -> dict[str, Any]:
        baseline_snapshot = fixture["baseline_snapshot"]
        candidate_snapshot = fixture["candidate_snapshot"]
        compare_policy = fixture["compare_policy"]
        topology_request = fixture["topology"]

        baseline_heuristic = self._baseline.score(topology_request)
        comparison = self._compare_api.compare(
            {
                "baseline": baseline_snapshot,
                "candidate": candidate_snapshot,
                "policy": compare_policy,
                "cohort_filters": fixture.get("cohort_filters", {}),
            }
        )

        observed_shadow_samples = int(fixture.get("observed_shadow_samples", 0))
        min_shadow_samples = int(fixture.get("promotion_policy", {}).get("min_shadow_samples", 1))
        trace_context = self._trace_context(fixture)
        quality_signal = self._build_quality_signal(
            baseline_snapshot=baseline_snapshot,
            candidate_snapshot=candidate_snapshot,
            topology_request=topology_request,
            observed_shadow_samples=observed_shadow_samples,
            min_shadow_samples=min_shadow_samples,
        )
        confidence = float(quality_signal["confidence"])
        fallback_used = confidence < float(fixture.get("compare_policy", {}).get("min_confidence", 0.0)) or (
            observed_shadow_samples < min_shadow_samples
        )
        fallback_reason_code = (
            "EIGEN_OPT_CONFIDENCE_TOO_LOW"
            if confidence < float(fixture.get("compare_policy", {}).get("min_confidence", 0.0))
            else "EIGEN_OPT_UNSPECIFIED"
        )
        fallback_reason = (
            "Confidence below minimum policy threshold"
            if fallback_used and fallback_reason_code == "EIGEN_OPT_CONFIDENCE_TOO_LOW"
            else "Deterministic optimizer path remained within policy bounds"
        )
        explainability = self._observability_bundle(
            fixture=fixture,
            trace_context=trace_context,
            confidence=confidence,
            fallback_used=fallback_used,
            fallback_reason_code=fallback_reason_code,
            fallback_reason=fallback_reason,
            baseline_snapshot=baseline_snapshot,
            candidate_snapshot=candidate_snapshot,
            topology_request=topology_request,
            observed_shadow_samples=observed_shadow_samples,
            min_shadow_samples=min_shadow_samples,
        )

        return {
            "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
            "mode": "offline",
            "dataset_ref": fixture["dataset_ref"],
            "dataset_hash": fixture["dataset_hash"],
            "seed": int(fixture["seed"]),
            "baseline_heuristic": baseline_heuristic,
            "comparison": comparison["comparison"],
            "quality_signal": quality_signal,
            "explainability": explainability,
        }

    def _build_quality_signal(
        self,
        *,
        baseline_snapshot: dict[str, Any],
        candidate_snapshot: dict[str, Any],
        topology_request: dict[str, Any],
        observed_shadow_samples: int,
        min_shadow_samples: int,
    ) -> dict[str, Any]:
        baseline_metrics = {
            str(metric["name"]): float(metric["mean"])
            for metric in baseline_snapshot.get("metrics", [])
        }
        candidate_metrics = {
            str(metric["name"]): float(metric["mean"])
            for metric in candidate_snapshot.get("metrics", [])
        }
        fidelity = candidate_metrics.get("fidelity", 0.0)
        baseline_fidelity = baseline_metrics.get("fidelity")
        runtime_ms = candidate_metrics.get("latency_ms", 0.0)
        observed_error = None
        if baseline_fidelity is not None:
            observed_error = round(max(0.0, baseline_fidelity - fidelity), 6)

        confidence = 1.0 if observed_shadow_samples >= min_shadow_samples else 0.0
        baseline_heuristic = self._baseline.score(topology_request)
        predicted_error = round(max(0.0, 1.0 - fidelity), 6)
        metric_bounds = {
            "confidence_score": {"min": 0.0, "max": 1.0},
            "predicted_error": {"min": 0.0, "max": 1.0},
            "observed_error": {"min": 0.0, "max": 1.0},
            "runtime_ms": {"min": 0.0, "max": float(runtime_ms)},
            "observed_shadow_samples": {"min": 0, "max": max(observed_shadow_samples, min_shadow_samples)},
            "swap_count": {"min": 0, "max": int(baseline_heuristic["route_count"])},
        }
        return {
            "schema_version": "1.0.0",
            "swap_count": int(baseline_heuristic["route_count"]),
            "predicted_error": predicted_error,
            "observed_error": observed_error,
            "runtime_ms": float(runtime_ms),
            "confidence": confidence,
            "confidence_source": "shadow_sample_coverage",
            "metric_bounds": metric_bounds,
        }

    def evaluate_shadow(self, fixture: dict[str, Any]) -> dict[str, Any]:
        offline = self.evaluate_offline(fixture)
        summary = offline["comparison"]["summary"]
        gate_reasons: list[str] = []

        if summary["has_regression"]:
            gate_reasons.append("REGRESSION_VS_BASELINE_HEURISTIC")

        min_shadow_samples = int(fixture.get("promotion_policy", {}).get("min_shadow_samples", 1))
        observed_samples = int(fixture.get("observed_shadow_samples", 0))
        if observed_samples < min_shadow_samples:
            gate_reasons.append("INSUFFICIENT_SHADOW_SAMPLES")

        recommendation = "PROMOTE" if not gate_reasons else "BLOCK_PROMOTION"

        return {
            "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
            "mode": "shadow",
            "recommendation": recommendation,
            "gate_reasons": gate_reasons,
            "offline_bundle": offline,
        }

LEARNING_PIPELINE_POLICY_VERSION = "1.4.0"
DEFAULT_TRIGGER_CIRCUITS = 1000
ROLLBACK_RUNBOOK_REF = "docs/howto/intelligent-runtime-observability-runbook.md#rollback-decision-trace"
DEFAULT_CANARY_EVALUATION_WINDOW_MINUTES = 30
DEFAULT_CANARY_COHORT = "backend_class"
AUTO_ROLLBACK_SLO_MINUTES = 15


class ContinuousLearningPipeline:
    """Deterministic trigger/promotion/rollback policy bundle for Phase-8C."""

    def __init__(self) -> None:
        self._harness = OptimizerEvaluationHarness()

    def evaluate(self, fixture: dict[str, Any]) -> dict[str, Any]:
        trigger_policy = fixture.get("trigger_policy", {})
        threshold = int(trigger_policy.get("new_circuit_threshold", DEFAULT_TRIGGER_CIRCUITS))
        max_interval_minutes = int(trigger_policy.get("max_interval_minutes", 1440))
        observed_new_circuits = int(fixture.get("observed_new_circuits", 0))
        elapsed_minutes_since_last_train = int(fixture.get("elapsed_minutes_since_last_train", 0))
        manual_override = bool(fixture.get("manual_retrain_override", False))
        actor = str(fixture.get("trigger_actor", "continuous-learning-controller"))
        reason = str(fixture.get("trigger_reason", "scheduled-policy-evaluation"))

        trigger_rules = {
            "new_data_threshold": observed_new_circuits >= threshold,
            "time_cap_exceeded": elapsed_minutes_since_last_train >= max_interval_minutes,
            "manual_override": manual_override,
        }
        should_retrain = any(trigger_rules.values())
        trigger_event_id = self._sha256_digest(
            {
                "dataset_ref": fixture.get("dataset_ref"),
                "dataset_hash": fixture.get("dataset_hash"),
                "threshold": threshold,
                "max_interval_minutes": max_interval_minutes,
                "observed_new_circuits": observed_new_circuits,
                "elapsed_minutes_since_last_train": elapsed_minutes_since_last_train,
                "manual_override": manual_override,
                "actor": actor,
                "reason": reason,
            }
        )[:24]
        audit_events = [
            {
                "event_id": f"evt-{trigger_event_id}",
                "event_type": "RETRAIN_TRIGGER_EVALUATED",
                "actor": actor,
                "reason_code": reason,
                "rules": trigger_rules,
                "should_retrain": should_retrain,
            }
        ]

        if not should_retrain:
            return {
                "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
                "policy_version": LEARNING_PIPELINE_POLICY_VERSION,
                "trigger": {
                    "threshold": threshold,
                    "max_interval_minutes": max_interval_minutes,
                    "observed_new_circuits": observed_new_circuits,
                    "elapsed_minutes_since_last_train": elapsed_minutes_since_last_train,
                    "manual_override": manual_override,
                    "rules": trigger_rules,
                    "should_retrain": False,
                },
                "audit_events": audit_events,
                "artifact": None,
                "promotion": None,
                "rollback": None,
            }

        artifact_version = str(
            fixture.get("artifact_version")
            or f"phase8c-candidate-{observed_new_circuits:04d}"
        )
        lineage_hash = hashlib.sha256(
            f'{fixture["dataset_ref"]}|{fixture["dataset_hash"]}|{int(fixture["seed"])}|{artifact_version}'.encode("utf-8")
        ).hexdigest()

        dataset_snapshot_manifest = {
            "snapshot_ref": fixture["dataset_ref"],
            "snapshot_hash": fixture["dataset_hash"],
            "record_count": int(fixture.get("snapshot_record_count", observed_new_circuits)),
            "partition_spec": str(fixture.get("snapshot_partition_spec", "default")),
        }
        config_payload = fixture.get("training_config", {})
        config_digest = f"sha256:{self._sha256_digest(config_payload)}"
        model_artifact_hashes = {
            "weights": f"sha256:{self._sha256_digest({'artifact_version': artifact_version, 'kind': 'weights'})}",
            "metadata": f"sha256:{self._sha256_digest({'artifact_version': artifact_version, 'kind': 'metadata'})}",
            "eval_report": f"sha256:{self._sha256_digest({'artifact_version': artifact_version, 'kind': 'eval_report'})}",
        }

        canary_policy = fixture.get("canary_policy", {})
        cohort_dimension = str(canary_policy.get("cohort_dimension", DEFAULT_CANARY_COHORT))
        cohort_value = str(
            canary_policy.get("cohort_value")
            or fixture.get("cohort_filters", {}).get(cohort_dimension, "default")
        )
        evaluation_window_minutes = int(
            canary_policy.get("evaluation_window_minutes", DEFAULT_CANARY_EVALUATION_WINDOW_MINUTES)
        )

        artifact = {
            "artifact_version": artifact_version,
            "registry_entry_id": f"model-{artifact_version}",
            "lineage": {
                "dataset_ref": fixture["dataset_ref"],
                "dataset_hash": fixture["dataset_hash"],
                "seed": int(fixture["seed"]),
                "lineage_hash": f"sha256:{lineage_hash}",
            },
            "dataset_snapshot_manifest": dataset_snapshot_manifest,
            "training_config_digest": config_digest,
            "model_artifact_hashes": model_artifact_hashes,
            "reproduce": {
                "command": (
                    "python -m benchmark_service.reproduce_training "
                    f"--artifact-version {artifact_version} "
                    f"--dataset-manifest-hash {dataset_snapshot_manifest['snapshot_hash']} "
                    f"--config-digest {config_digest}"
                ),
                "expected_lineage_hash": f"sha256:{lineage_hash}",
            },
        }

        promotion = self._harness.evaluate_shadow(fixture)
        canary_decision = "PROMOTE" if promotion["recommendation"] == "PROMOTE" else "ROLLBACK"
        canary_reason_codes = [f"CANARY_{reason}" for reason in promotion["gate_reasons"]]
        if canary_decision == "PROMOTE":
            canary_reason_codes = ["CANARY_PROMOTION_APPROVED"]

        rollback = None
        if canary_decision == "ROLLBACK":
            rollback = {
                "action": "ROLLBACK_TO_STABLE",
                "reason_codes": sorted(canary_reason_codes),
                "runbook_ref": ROLLBACK_RUNBOOK_REF,
                "target_model_version": str(fixture.get("stable_model_version", "phase8c-stable-previous")),
                "slo_minutes": AUTO_ROLLBACK_SLO_MINUTES,
            }

        audit_events.append(
            {
                "event_id": f"evt-{self._sha256_digest({'artifact_version': artifact_version, 'event': 'MODEL_VERSION_PRODUCED'})[:24]}",
                "event_type": "MODEL_VERSION_PRODUCED",
                "actor": actor,
                "reason_code": reason,
                "linked_model_version": artifact_version,
                "digests": {
                    "lineage_hash": artifact["lineage"]["lineage_hash"],
                    "training_config_digest": config_digest,
                    "weights_hash": model_artifact_hashes["weights"],
                },
            }
        )

        return {
            "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
            "policy_version": LEARNING_PIPELINE_POLICY_VERSION,
            "trigger": {
                "threshold": threshold,
                "max_interval_minutes": max_interval_minutes,
                "observed_new_circuits": observed_new_circuits,
                "elapsed_minutes_since_last_train": elapsed_minutes_since_last_train,
                "manual_override": manual_override,
                "rules": trigger_rules,
                "should_retrain": True,
            },
            "audit_events": audit_events,
            "artifact": artifact,
            "promotion": promotion,
            "canary": {
                "cohort": {
                    "dimension": cohort_dimension,
                    "value": cohort_value,
                },
                "evaluation_window_minutes": evaluation_window_minutes,
                "decision": canary_decision,
                "reason_codes": sorted(canary_reason_codes),
                "auto_rollback_slo_minutes": AUTO_ROLLBACK_SLO_MINUTES,
            },
            "rollback": rollback,
        }

    def _sha256_digest(self, payload: Any) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()
