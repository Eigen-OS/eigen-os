from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

BENCHMARK_COMPARE_API_VERSION = "1.0.0"
BENCHMARK_COMPARE_SCHEMA_VERSION = "1.0.0"
BENCHMARK_COMPARE_METHODOLOGY_VERSION = "1.0.0"

_ALLOWED_DIRECTIONS = {"lower_is_better", "higher_is_better"}


@dataclass(frozen=True, slots=True)
class CompareValidationError:
    code: str
    field: str
    message: str


class BenchmarkCompareRequestValidationError(ValueError):
    """Raised when /benchmarks/compare request validation fails."""

    def __init__(self, errors: list[CompareValidationError]) -> None:
        super().__init__("benchmark compare request validation failed")
        self.errors = errors


class BenchmarkCompareApi:
    """Contract surface for /benchmarks/compare deterministic comparison payloads."""

    def compare(self, request: dict[str, Any]) -> dict[str, Any]:
        errors = self._validate_request(request)
        if errors:
            raise BenchmarkCompareRequestValidationError(errors)

        baseline = request["baseline"]
        candidate = request["candidate"]
        policy = request["policy"]

        baseline_metrics = {item["name"]: item for item in baseline["metrics"]}
        candidate_metrics = {item["name"]: item for item in candidate["metrics"]}

        metric_names = sorted(set(baseline_metrics) & set(candidate_metrics))
        regressions: list[str] = []
        comparisons: list[dict[str, Any]] = []

        for name in metric_names:
            baseline_metric = baseline_metrics[name]
            candidate_metric = candidate_metrics[name]
            compared = self._compare_metric(
                name=name,
                baseline_metric=baseline_metric,
                candidate_metric=candidate_metric,
                policy=policy,
            )
            comparisons.append(compared)
            if compared["regression"]["is_regression"]:
                regressions.append(name)

        return {
            "api_version": BENCHMARK_COMPARE_API_VERSION,
            "comparison_schema_version": BENCHMARK_COMPARE_SCHEMA_VERSION,
            "comparison": {
                "baseline_run_id": baseline["run_id"],
                "candidate_run_id": candidate["run_id"],
                "cohort_filters": request.get("cohort_filters", {}),
                "policy": {
                    "direction": policy["direction"],
                    "regression_threshold_pct": float(policy["regression_threshold_pct"]),
                    "min_confidence": float(policy["min_confidence"]),
                },
                "methodology": {
                    "methodology_version": BENCHMARK_COMPARE_METHODOLOGY_VERSION,
                    "name": "normal_approximation_ztest",
                    "confidence_formula": "erf(|z|/sqrt(2))",
                    "delta_formula": "((candidate-baseline)/abs(baseline))*100",
                },
                "metrics": comparisons,
                "summary": {
                    "metric_count": len(comparisons),
                    "regression_count": len(regressions),
                    "has_regression": bool(regressions),
                    "regression_metrics": regressions,
                },
            },
        }

    def to_error_envelope(self, err: BenchmarkCompareRequestValidationError) -> dict[str, Any]:
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

    def _validate_request(self, request: dict[str, Any]) -> list[CompareValidationError]:
        errors: list[CompareValidationError] = []

        for side in ("baseline", "candidate"):
            payload = request.get(side)
            if not isinstance(payload, dict):
                errors.append(
                    CompareValidationError(
                        code="field_required",
                        field=side,
                        message=f"{side} is required and must be an object",
                    )
                )
                continue

            run_id = payload.get("run_id")
            if not isinstance(run_id, str) or not run_id.strip():
                errors.append(
                    CompareValidationError(
                        code="field_required",
                        field=f"{side}.run_id",
                        message=f"{side}.run_id is required and must be a non-empty string",
                    )
                )

            metrics = payload.get("metrics")
            if not isinstance(metrics, list) or not metrics:
                errors.append(
                    CompareValidationError(
                        code="field_required",
                        field=f"{side}.metrics",
                        message=f"{side}.metrics is required and must be a non-empty array",
                    )
                )
                continue

            for index, metric in enumerate(metrics):
                if not isinstance(metric, dict):
                    errors.append(
                        CompareValidationError(
                            code="invalid_type",
                            field=f"{side}.metrics[{index}]",
                            message="metric item must be an object",
                        )
                    )
                    continue

                if not isinstance(metric.get("name"), str) or not metric["name"].strip():
                    errors.append(
                        CompareValidationError(
                            code="field_required",
                            field=f"{side}.metrics[{index}].name",
                            message="metric name must be a non-empty string",
                        )
                    )

                for number_field in ("mean", "stddev"):
                    value = metric.get(number_field)
                    if not isinstance(value, (int, float)):
                        errors.append(
                            CompareValidationError(
                                code="field_required",
                                field=f"{side}.metrics[{index}].{number_field}",
                                message=f"{number_field} must be numeric",
                            )
                        )

                sample_size = metric.get("sample_size")
                if not isinstance(sample_size, int) or sample_size < 1:
                    errors.append(
                        CompareValidationError(
                            code="field_required",
                            field=f"{side}.metrics[{index}].sample_size",
                            message="sample_size must be an integer >= 1",
                        )
                    )

        policy = request.get("policy")
        if not isinstance(policy, dict):
            errors.append(
                CompareValidationError(
                    code="field_required",
                    field="policy",
                    message="policy is required and must be an object",
                )
            )
            return errors

        direction = policy.get("direction")
        if direction not in _ALLOWED_DIRECTIONS:
            errors.append(
                CompareValidationError(
                    code="invalid_value",
                    field="policy.direction",
                    message="policy.direction must be one of lower_is_better or higher_is_better",
                )
            )

        threshold = policy.get("regression_threshold_pct")
        if not isinstance(threshold, (int, float)) or threshold < 0:
            errors.append(
                CompareValidationError(
                    code="invalid_value",
                    field="policy.regression_threshold_pct",
                    message="policy.regression_threshold_pct must be numeric and >= 0",
                )
            )

        min_confidence = policy.get("min_confidence")
        if not isinstance(min_confidence, (int, float)) or not (0 <= min_confidence <= 1):
            errors.append(
                CompareValidationError(
                    code="invalid_value",
                    field="policy.min_confidence",
                    message="policy.min_confidence must be numeric in [0, 1]",
                )
            )

        return errors

    @staticmethod
    def _compare_metric(
        *,
        name: str,
        baseline_metric: dict[str, Any],
        candidate_metric: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        baseline_mean = float(baseline_metric["mean"])
        candidate_mean = float(candidate_metric["mean"])
        baseline_stddev = float(baseline_metric["stddev"])
        candidate_stddev = float(candidate_metric["stddev"])
        baseline_n = int(baseline_metric["sample_size"])
        candidate_n = int(candidate_metric["sample_size"])

        delta_abs = candidate_mean - baseline_mean
        delta_pct = None
        if baseline_mean != 0:
            delta_pct = (delta_abs / abs(baseline_mean)) * 100.0

        variance_term = (baseline_stddev**2 / baseline_n) + (candidate_stddev**2 / candidate_n)
        standard_error = math.sqrt(variance_term) if variance_term > 0 else 0.0
        z_score = 0.0 if standard_error == 0 else delta_abs / standard_error
        confidence = math.erf(abs(z_score) / math.sqrt(2.0))

        threshold = float(policy["regression_threshold_pct"])
        direction = str(policy["direction"])
        min_confidence = float(policy["min_confidence"])

        regression = False
        if delta_pct is not None and confidence >= min_confidence:
            if direction == "lower_is_better":
                regression = delta_pct > threshold
            else:
                regression = delta_pct < -threshold

        return {
            "name": name,
            "baseline": {
                "mean": baseline_mean,
                "stddev": baseline_stddev,
                "sample_size": baseline_n,
            },
            "candidate": {
                "mean": candidate_mean,
                "stddev": candidate_stddev,
                "sample_size": candidate_n,
            },
            "delta": {
                "absolute": delta_abs,
                "percent": delta_pct,
            },
            "statistical_metadata": {
                "z_score": z_score,
                "standard_error": standard_error,
                "confidence": confidence,
            },
            "regression": {
                "is_regression": regression,
                "threshold_pct": threshold,
                "direction": direction,
                "min_confidence": min_confidence,
            },
        }
