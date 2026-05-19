from __future__ import annotations

import json
from pathlib import Path

from driver_manager.parity import ToleranceProfile


def test_phase8d_tolerance_policy_fixture_is_versioned_and_valid() -> None:
    fixture = (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "development"
        / "fixtures"
        / "phase8d"
        / "provider_tolerance_policy_v1.json"
    )
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    profile = ToleranceProfile(
        policy_version=payload["policy_version"],
        canonical_workload=payload["canonical_workload"],
        allowed_missing_keys=payload["result_shape"]["allowed_missing_keys"],
        max_latency_ratio=payload["latency"]["max_ratio_vs_simulator"],
        max_noise_delta=payload["noise"]["max_probability_delta"],
    )

    assert profile.policy_version == "1.0.0"
    assert profile.canonical_workload == "phase8d_canonical_workload_v1"
    assert payload["official_targets"] == ["simulator", "ibm", "aws"]
