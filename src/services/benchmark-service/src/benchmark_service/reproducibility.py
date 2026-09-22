from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import fmean, pstdev
from typing import Any

REPRODUCIBILITY_POLICY_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ReproducibilityPolicy:
    version: str
    min_runs: int
    max_relative_stddev_pct: float
    max_absolute_stddev: float


DEFAULT_REPRODUCIBILITY_POLICY = ReproducibilityPolicy(
    version=REPRODUCIBILITY_POLICY_VERSION,
    min_runs=3,
    max_relative_stddev_pct=2.0,
    max_absolute_stddev=0.005,
)


@dataclass(frozen=True, slots=True)
class DriftDiagnostic:
    code: str
    message: str
    field: str


@dataclass(frozen=True, slots=True)
class ReproducibilityReport:
    policy_version: str
    passed: bool
    run_count: int
    metadata_consistent: bool
    diagnostics: tuple[DriftDiagnostic, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "passed": self.passed,
            "run_count": self.run_count,
            "metadata_consistent": self.metadata_consistent,
            "diagnostics": [
                {"code": item.code, "message": item.message, "field": item.field}
                for item in self.diagnostics
            ],
        }


class ReproducibilityGate:
    """Evaluates deterministic snapshot metadata and bounded metric variance."""

    def __init__(self, *, policy: ReproducibilityPolicy = DEFAULT_REPRODUCIBILITY_POLICY) -> None:
        self._policy = policy

    def evaluate(self, runs: list[dict[str, Any]]) -> ReproducibilityReport:
        diagnostics: list[DriftDiagnostic] = []

        if len(runs) < self._policy.min_runs:
            diagnostics.append(
                DriftDiagnostic(
                    code="insufficient_runs",
                    field="runs",
                    message=f"expected at least {self._policy.min_runs} runs, got {len(runs)}",
                )
            )
            return ReproducibilityReport(
                policy_version=self._policy.version,
                passed=False,
                run_count=len(runs),
                metadata_consistent=False,
                diagnostics=tuple(diagnostics),
            )

        metadata_consistent = self._validate_metadata(runs, diagnostics)
        self._validate_metric_variance(runs, diagnostics)

        return ReproducibilityReport(
            policy_version=self._policy.version,
            passed=len(diagnostics) == 0,
            run_count=len(runs),
            metadata_consistent=metadata_consistent,
            diagnostics=tuple(diagnostics),
        )

    def _validate_metadata(self, runs: list[dict[str, Any]], diagnostics: list[DriftDiagnostic]) -> bool:
        first = runs[0]["snapshot"]
        expected_hash = first["request_hash"]
        expected_payload = first["payload"]
        metadata_consistent = True

        for index, run in enumerate(runs):
            snapshot = run["snapshot"]
            if snapshot["request_hash"] != expected_hash:
                metadata_consistent = False
                diagnostics.append(
                    DriftDiagnostic(
                        code="request_hash_mismatch",
                        field=f"runs[{index}].snapshot.request_hash",
                        message="run config hash diverged for identical config gate",
                    )
                )
            if snapshot["payload"] != expected_payload:
                metadata_consistent = False
                diagnostics.append(
                    DriftDiagnostic(
                        code="payload_mismatch",
                        field=f"runs[{index}].snapshot.payload",
                        message="run snapshot payload diverged for identical config gate",
                    )
                )

        return metadata_consistent

    def _validate_metric_variance(self, runs: list[dict[str, Any]], diagnostics: list[DriftDiagnostic]) -> None:
        metric_names = sorted(runs[0]["metrics"].keys())
        for name in metric_names:
            samples = [float(run["metrics"][name]) for run in runs]
            mean_value = fmean(samples)
            stddev_value = pstdev(samples)
            relative_stddev = math.inf
            if mean_value != 0:
                relative_stddev = abs(stddev_value / mean_value) * 100.0

            exceeds_absolute = stddev_value > self._policy.max_absolute_stddev
            exceeds_relative = relative_stddev > self._policy.max_relative_stddev_pct

            if exceeds_absolute and exceeds_relative:
                diagnostics.append(
                    DriftDiagnostic(
                        code="metric_variance_exceeded",
                        field=f"metrics.{name}",
                        message=(
                            f"stddev={stddev_value:.6f}, relative_stddev_pct={relative_stddev:.6f}, "
                            f"limits=({self._policy.max_absolute_stddev:.6f},"
                            f" {self._policy.max_relative_stddev_pct:.6f})"
                        ),
                    )
                )
                