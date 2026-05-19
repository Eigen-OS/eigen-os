from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .compare_api import BenchmarkCompareApi

OPTIMIZER_EVAL_CONTRACT_VERSION = "1.0.0"
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
