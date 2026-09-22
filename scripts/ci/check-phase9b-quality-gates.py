from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs" / "development" / "fixtures" / "phase9b" / "gnn_quality_gate_bundle_v1.json"
REPORT = ROOT / "artifacts" / "phase9b" / "gnn_quality_regression_report.json"


def _fail(code: str, message: str, hint: str) -> str:
    return f"[{code}] {message} | mitigation_hint={hint}"


def main() -> int:
    if not FIXTURE.exists():
        print(_fail("P9B_QUALITY_FIXTURE_MISSING", f"missing fixture: {FIXTURE.relative_to(ROOT)}", "Add versioned Phase-9B quality fixture."))
        return 1

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures: list[str] = []
    if payload.get("contract_version") != "1.3.0":
        failures.append(_fail("P9B_QUALITY_CONTRACT_UNSUPPORTED", "contract_version must be 1.3.0", "Regenerate quality bundle using contract v1.3.0."))

    quality = payload.get("quality_signal", {})
    required = ("schema_version", "swap_count", "predicted_error", "observed_error", "runtime_ms", "confidence")
    for field in required:
        if field not in quality:
            failures.append(_fail("P9B_QUALITY_SCHEMA_DRIFT", f"quality_signal missing required field '{field}'", "Restore required schema fields."))

    thresholds = payload.get("threshold_policy", {})
    max_runtime_ms = float(thresholds.get("max_runtime_ms", 0.0))
    max_predicted_error = float(thresholds.get("max_predicted_error", 0.0))
    min_confidence = float(thresholds.get("min_confidence", 0.0))

    runtime_ok = float(quality.get("runtime_ms", 0.0)) <= max_runtime_ms
    error_ok = float(quality.get("predicted_error", 1.0)) <= max_predicted_error
    confidence_ok = float(quality.get("confidence", 0.0)) >= min_confidence
    if not (runtime_ok and error_ok and confidence_ok):
        failures.append(_fail("P9B_QUALITY_NON_REGRESSION_FAILED", "quality signal breached threshold policy", "Block promotion and retrain or rollback candidate."))

    report = {
        "report_version": "1.0.0",
        "contract_version": payload.get("contract_version"),
        "schema_version": quality.get("schema_version"),
        "non_regression_passed": not failures,
        "checks": {
            "runtime_ok": runtime_ok,
            "predicted_error_ok": error_ok,
            "confidence_ok": confidence_ok,
        },
        "failures": failures,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if failures:
        print("[phase9b-quality-gates] gate failed:")
        for item in failures:
            print(f" - {item}")
        return 1

    print(f"[phase9b-quality-gates] passed; report={REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
