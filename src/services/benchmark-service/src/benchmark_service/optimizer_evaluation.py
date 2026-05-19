from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compare_api import BenchmarkCompareApi

OPTIMIZER_EVAL_CONTRACT_VERSION = "1.2.0"
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

        return {
            "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
            "mode": "offline",
            "dataset_ref": fixture["dataset_ref"],
            "dataset_hash": fixture["dataset_hash"],
            "seed": int(fixture["seed"]),
            "baseline_heuristic": baseline_heuristic,
            "comparison": comparison["comparison"],
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

LEARNING_PIPELINE_POLICY_VERSION = "1.2.0"
DEFAULT_TRIGGER_CIRCUITS = 1000
ROLLBACK_RUNBOOK_REF = "docs/howto/intelligent-runtime-observability-runbook.md"


class ContinuousLearningPipeline:
    """Deterministic trigger/promotion/rollback policy bundle for Phase-8C."""

    def __init__(self) -> None:
        self._harness = OptimizerEvaluationHarness()

    def evaluate(self, fixture: dict[str, Any]) -> dict[str, Any]:
        trigger_policy = fixture.get("trigger_policy", {})
        threshold = int(trigger_policy.get("new_circuit_threshold", DEFAULT_TRIGGER_CIRCUITS))
        observed_new_circuits = int(fixture.get("observed_new_circuits", 0))
        should_retrain = observed_new_circuits >= threshold

        if not should_retrain:
            return {
                "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
                "policy_version": LEARNING_PIPELINE_POLICY_VERSION,
                "trigger": {
                    "threshold": threshold,
                    "observed_new_circuits": observed_new_circuits,
                    "should_retrain": False,
                },
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

        artifact = {
            "artifact_version": artifact_version,
            "lineage": {
                "dataset_ref": fixture["dataset_ref"],
                "dataset_hash": fixture["dataset_hash"],
                "seed": int(fixture["seed"]),
                "lineage_hash": f"sha256:{lineage_hash}",
            },
        }

        promotion = self._harness.evaluate_shadow(fixture)

        rollback = None
        if promotion["recommendation"] != "PROMOTE":
            rollback_reasons = [
                f"CANARY_{reason}"
                for reason in promotion["gate_reasons"]
                if reason in {"REGRESSION_VS_BASELINE_HEURISTIC", "INSUFFICIENT_SHADOW_SAMPLES"}
            ]
            if rollback_reasons:
                rollback = {
                    "action": "ROLLBACK_TO_STABLE",
                    "reason_codes": sorted(rollback_reasons),
                    "runbook_ref": ROLLBACK_RUNBOOK_REF,
                }

        return {
            "contract_version": OPTIMIZER_EVAL_CONTRACT_VERSION,
            "policy_version": LEARNING_PIPELINE_POLICY_VERSION,
            "trigger": {
                "threshold": threshold,
                "observed_new_circuits": observed_new_circuits,
                "should_retrain": True,
            },
            "artifact": artifact,
            "promotion": promotion,
            "rollback": rollback,
        }
