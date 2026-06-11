from __future__ import annotations

import json
from pathlib import Path

from driver_manager.rollback_governance import (
    REQUIRED_CONTROLS,
    REQUIRED_FAILURE_CLASSES,
    RollbackRehearsalEvidence,
    evaluate_rollback_safety,
)


def test_phase8d_rollback_rehearsal_fixture_is_complete() -> None:
    fixture = (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "development"
        / "fixtures"
        / "phase8d"
        / "rollback_rehearsal_matrix_v1.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    for provider in payload["providers"]:
        evidence = RollbackRehearsalEvidence(
            provider=provider["provider"],
            exercised_controls=tuple(provider["exercised_controls"]),
            covered_failure_classes=tuple(provider["covered_failure_classes"]),
            escalation_path_verified=provider["escalation_path_verified"],
        )
        ok, violations = evaluate_rollback_safety(evidence)
        assert ok, violations

    assert payload["artifact_version"] == "1.0.0"


def test_rollback_safety_fails_closed_when_controls_are_missing() -> None:
    evidence = RollbackRehearsalEvidence(
        provider="aws",
        exercised_controls=("adapter_pin",),
        covered_failure_classes=("provider_outage",),
        escalation_path_verified=False,
    )

    ok, violations = evaluate_rollback_safety(evidence)

    assert not ok
    assert any("controls missing required entries" in violation for violation in violations)
    assert any("failure_classes missing required entries" in violation for violation in violations)
    assert any("escalation_path" in violation for violation in violations)
    assert REQUIRED_CONTROLS
    assert REQUIRED_FAILURE_CLASSES

def test_session_restart_safety():
    registry = DriverRegistry()

    registry.invalidate_session(
        "simulator",
        "stable-session",
    )

    session = registry.get_or_create_session(
        "simulator",
        "stable-session",
    )

    assert session["state"] == "active"
