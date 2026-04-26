"""Pipeline stage latency aggregation helpers.

This module keeps in-memory sliding windows of per-stage durations and error counts,
then computes quantiles suitable for dashboards and alerting.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import DefaultDict


@dataclass(frozen=True)
class StageLatencyStats:
    """Computed latency and reliability metrics for a single stage."""

    stage: str
    sample_count: int
    error_count: int
    error_rate: float
    p50_seconds: float
    p95_seconds: float
    p99_seconds: float


class StageLatencyAggregator:
    """Aggregate pipeline stage latencies and errors in a bounded time window.

    Parameters
    ----------
    max_samples_per_stage:
        Maximum retained samples per stage in the rolling buffer.
    """

    def __init__(self, *, max_samples_per_stage: int = 4096) -> None:
        if max_samples_per_stage < 100:
            raise ValueError("max_samples_per_stage must be >= 100")
        self._max_samples = max_samples_per_stage
        self._latency_by_stage: DefaultDict[str, deque[float]] = defaultdict(lambda: deque(maxlen=self._max_samples))
        self._error_count_by_stage: DefaultDict[str, int] = defaultdict(int)
        self._lock = Lock()

    def observe(self, *, stage: str, latency_seconds: float, is_error: bool = False) -> None:
        """Record one stage execution sample."""
        if not stage or not stage.strip():
            raise ValueError("stage must be a non-empty string")
        if latency_seconds < 0:
            raise ValueError("latency_seconds must be >= 0")

        normalized_stage = stage.strip()
        with self._lock:
            self._latency_by_stage[normalized_stage].append(float(latency_seconds))
            if is_error:
                self._error_count_by_stage[normalized_stage] += 1

    def snapshot(self) -> dict[str, StageLatencyStats]:
        """Return quantiles and error rates for all stages."""
        with self._lock:
            stages = set(self._latency_by_stage.keys()) | set(self._error_count_by_stage.keys())
            result: dict[str, StageLatencyStats] = {}
            for stage in sorted(stages):
                samples = list(self._latency_by_stage.get(stage, ()))
                sample_count = len(samples)
                error_count = int(self._error_count_by_stage.get(stage, 0))
                if sample_count == 0:
                    result[stage] = StageLatencyStats(
                        stage=stage,
                        sample_count=0,
                        error_count=error_count,
                        error_rate=0.0,
                        p50_seconds=0.0,
                        p95_seconds=0.0,
                        p99_seconds=0.0,
                    )
                    continue

                p50 = _nearest_rank_quantile(samples, 0.50)
                p95 = _nearest_rank_quantile(samples, 0.95)
                p99 = _nearest_rank_quantile(samples, 0.99)
                result[stage] = StageLatencyStats(
                    stage=stage,
                    sample_count=sample_count,
                    error_count=error_count,
                    error_rate=error_count / sample_count,
                    p50_seconds=p50,
                    p95_seconds=p95,
                    p99_seconds=p99,
                )
            return result


def _nearest_rank_quantile(samples: list[float], quantile: float) -> float:
    if not samples:
        return 0.0
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    rank = max(1, min(n, int((n * quantile) + 0.999999)))
    return float(sorted_samples[rank - 1])
