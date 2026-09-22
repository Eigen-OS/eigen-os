from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


REQUIRED_CONTROLS = ("adapter_pin", "adapter_quarantine", "matrix_demotion")
REQUIRED_FAILURE_CLASSES = ("provider_outage", "provider_degradation", "auth_failure", "quota_failure")


@dataclass(frozen=True)
class RollbackRehearsalEvidence:
    provider: str
    exercised_controls: tuple[str, ...]
    covered_failure_classes: tuple[str, ...]
    escalation_path_verified: bool


def evaluate_rollback_safety(evidence: RollbackRehearsalEvidence) -> tuple[bool, list[str]]:
    violations: list[str] = []

    if not evidence.provider:
        violations.append("provider must be non-empty")

    _validate_required(
        field_name="controls",
        required=REQUIRED_CONTROLS,
        observed=evidence.exercised_controls,
        violations=violations,
    )
    _validate_required(
        field_name="failure_classes",
        required=REQUIRED_FAILURE_CLASSES,
        observed=evidence.covered_failure_classes,
        violations=violations,
    )

    if not evidence.escalation_path_verified:
        violations.append("escalation_path must be verified")

    return (len(violations) == 0, violations)


def _validate_required(
    *,
    field_name: str,
    required: Iterable[str],
    observed: Iterable[str],
    violations: list[str],
) -> None:
    observed_set = set(observed)
    missing = sorted(item for item in required if item not in observed_set)
    if missing:
        violations.append(f"{field_name} missing required entries: {', '.join(missing)}")
