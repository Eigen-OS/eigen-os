from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs" / "development" / "fixtures" / "phase8c" / "ci_gate_bundle_v1.json"


def _fail(reason_code: str, message: str, hint: str) -> str:
    return f"[{reason_code}] {message} | mitigation_hint={hint}"


def main() -> int:
    if not FIXTURE.exists():
        print(_fail(
            "P8C_GATE_FIXTURE_MISSING",
            f"missing fixture: {FIXTURE.relative_to(ROOT)}",
            "Add docs/development/fixtures/phase8c/ci_gate_bundle_v1.json and commit it as a versioned artifact.",
        ))
        return 1

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures: list[str] = []

    if payload.get("fixture_version") != "1.0.0":
        failures.append(_fail(
            "P8C_GATE_FIXTURE_VERSION_UNSUPPORTED",
            "fixture_version must be 1.0.0",
            "Regenerate Phase-8C evidence bundle with schema v1.0.0 and update release notes.",
        ))

    trigger = payload.get("trigger", {})
    if trigger.get("auto_model_version_created") is not True:
        failures.append(_fail(
            "P8C_TRIGGER_AUTOVERSION_MISSING",
            "trigger gate did not report automatic model version creation",
            "Enable deterministic model version minting in trigger policy before promotion.",
        ))

    canary = payload.get("canary", {})
    baseline_non_regression = canary.get("baseline_non_regression")
    canary_reason = canary.get("reason_code")
    if baseline_non_regression is not True:
        failures.append(_fail(
            canary_reason or "P8C_CANARY_REGRESSION_DETECTED",
            "canary gate failed non-regression against baseline heuristic",
            "Block promotion, inspect compare bundle deltas, retrain or tune candidate model.",
        ))

    rollback = payload.get("rollback", {})
    rollback_safe = rollback.get("safety_ready")
    rollback_reason = rollback.get("reason_code")
    if rollback_safe is not True:
        failures.append(_fail(
            rollback_reason or "P8C_ROLLBACK_SAFETY_UNAVAILABLE",
            "rollback safety gate did not confirm stable target and runbook",
            "Publish rollback target/runbook linkage and verify restore drill before release.",
        ))

    reproducibility = payload.get("reproducibility", {})
    reproducibility_ok = reproducibility.get("hash_match")
    reproducibility_reason = reproducibility.get("reason_code")
    if reproducibility_ok is not True:
        failures.append(_fail(
            reproducibility_reason or "P8C_REPRODUCIBILITY_HASH_MISMATCH",
            "reproducibility hash gate failed",
            "Rebuild artifact from pinned dataset/seed and refresh deterministic lineage hash.",
        ))

    if failures:
        print("[phase8c-gates] gate failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("[phase8c-gates] trigger/canary/rollback/reproducibility fixture checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
