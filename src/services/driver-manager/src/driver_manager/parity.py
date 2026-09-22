from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToleranceProfile:
    policy_version: str
    canonical_workload: str
    allowed_missing_keys: int
    max_latency_ratio: float
    max_noise_delta: float


@dataclass(frozen=True)
class ProviderObservation:
    provider: str
    counts: dict[str, int]
    latency_sec: float


def evaluate_tolerance(
    baseline: ProviderObservation,
    candidate: ProviderObservation,
    profile: ToleranceProfile,
) -> tuple[bool, list[str]]:
    violations: list[str] = []

    missing = set(baseline.counts) - set(candidate.counts)
    extra = set(candidate.counts) - set(baseline.counts)
    if len(missing) + len(extra) > profile.allowed_missing_keys:
        violations.append(
            f"result_shape mismatch: missing={sorted(missing)} extra={sorted(extra)} "
            f"allowed_missing_keys={profile.allowed_missing_keys}"
        )

    baseline_total = max(sum(baseline.counts.values()), 1)
    candidate_total = max(sum(candidate.counts.values()), 1)
    all_keys = set(baseline.counts) | set(candidate.counts)
    max_delta = 0.0
    for key in all_keys:
        b = baseline.counts.get(key, 0) / baseline_total
        c = candidate.counts.get(key, 0) / candidate_total
        max_delta = max(max_delta, abs(b - c))
    if max_delta > profile.max_noise_delta:
        violations.append(
            f"noise_delta exceeded: observed={max_delta:.6f} threshold={profile.max_noise_delta:.6f}"
        )

    latency_ratio = candidate.latency_sec / max(baseline.latency_sec, 1e-9)
    if latency_ratio > profile.max_latency_ratio:
        violations.append(
            f"latency_ratio exceeded: observed={latency_ratio:.3f} threshold={profile.max_latency_ratio:.3f}"
        )

    return not violations, violations
