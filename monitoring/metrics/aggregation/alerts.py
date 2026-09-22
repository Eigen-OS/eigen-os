"""Stage latency/error-rate SLO definitions and alert evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from monitoring.metrics.aggregation.aggregator import StageLatencyStats


@dataclass(frozen=True)
class StageSLO:
    stage: str
    max_p95_seconds: float
    max_p99_seconds: float
    max_error_rate: float
    min_samples: int = 50


@dataclass(frozen=True)
class AlertViolation:
    stage: str
    metric: str
    threshold: float
    actual: float
    severity: str
    message: str


class StageSLOAlertEvaluator:
    def __init__(self, slos: list[StageSLO]) -> None:
        if not slos:
            raise ValueError("at least one SLO must be configured")
        self._slos = {slo.stage: slo for slo in slos}

    def evaluate(self, stats_by_stage: dict[str, StageLatencyStats]) -> list[AlertViolation]:
        violations: list[AlertViolation] = []
        for stage, slo in self._slos.items():
            stats = stats_by_stage.get(stage)
            if stats is None or stats.sample_count < slo.min_samples:
                continue

            if stats.p95_seconds > slo.max_p95_seconds:
                violations.append(
                    AlertViolation(
                        stage=stage,
                        metric="p95_seconds",
                        threshold=slo.max_p95_seconds,
                        actual=stats.p95_seconds,
                        severity="warning",
                        message=f"Stage '{stage}' p95 latency {stats.p95_seconds:.3f}s exceeds {slo.max_p95_seconds:.3f}s",
                    )
                )
            if stats.p99_seconds > slo.max_p99_seconds:
                violations.append(
                    AlertViolation(
                        stage=stage,
                        metric="p99_seconds",
                        threshold=slo.max_p99_seconds,
                        actual=stats.p99_seconds,
                        severity="critical",
                        message=f"Stage '{stage}' p99 latency {stats.p99_seconds:.3f}s exceeds {slo.max_p99_seconds:.3f}s",
                    )
                )
            if stats.error_rate > slo.max_error_rate:
                violations.append(
                    AlertViolation(
                        stage=stage,
                        metric="error_rate",
                        threshold=slo.max_error_rate,
                        actual=stats.error_rate,
                        severity="critical",
                        message=f"Stage '{stage}' error rate {stats.error_rate:.2%} exceeds {slo.max_error_rate:.2%}",
                    )
                )
        return violations


def default_stage_slos() -> list[StageSLO]:
    """Baseline SLOs for runtime operators."""
    return [
        StageSLO(stage="queue", max_p95_seconds=0.5, max_p99_seconds=1.0, max_error_rate=0.005),
        StageSLO(stage="compile", max_p95_seconds=2.5, max_p99_seconds=4.0, max_error_rate=0.01),
        StageSLO(stage="schedule", max_p95_seconds=1.0, max_p99_seconds=2.0, max_error_rate=0.005),
        StageSLO(stage="execute", max_p95_seconds=8.0, max_p99_seconds=12.0, max_error_rate=0.02),
        StageSLO(stage="result", max_p95_seconds=1.5, max_p99_seconds=3.0, max_error_rate=0.01),
    ]
