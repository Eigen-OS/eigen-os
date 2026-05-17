from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs" / "development" / "fixtures" / "phase8b" / "ci_gate_bundle_v1.json"


def _fail(reason_code: str, message: str, hint: str) -> str:
    return f"[{reason_code}] {message} | mitigation_hint={hint}"


def main() -> int:
    if not FIXTURE.exists():
        print(_fail(
            "P8B_GATE_FIXTURE_MISSING",
            f"missing fixture: {FIXTURE.relative_to(ROOT)}",
            "Add docs/development/fixtures/phase8b/ci_gate_bundle_v1.json and commit it as a versioned artifact.",
        ))
        return 1

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures: list[str] = []

    if payload.get("fixture_version") != "1.0.0":
        failures.append(_fail(
            "P8B_GATE_FIXTURE_VERSION_UNSUPPORTED",
            "fixture_version must be 1.0.0",
            "Regenerate fixture with the current schema version and update docs/changelog.",
        ))

    scale = payload.get("queue_scale", {})
    total_jobs = scale.get("jobs_total")
    min_jobs = scale.get("min_required")
    if total_jobs is None or min_jobs is None:
        failures.append(_fail(
            "P8B_GATE_SCALE_SCHEMA_INVALID",
            "queue_scale must include jobs_total and min_required",
            "Populate queue_scale with deterministic numeric fields.",
        ))
    elif total_jobs < min_jobs or min_jobs < 10_000:
        failures.append(_fail(
            "P8B_GATE_QUEUE_SCALE_BELOW_TARGET",
            f"queue scale target not met: jobs_total={total_jobs}, min_required={min_jobs}",
            "Increase synthetic queue load profile to >=10,000 jobs and refresh fixture evidence.",
        ))

    latency = payload.get("enqueue_latency_trend", {})
    p95_ms = latency.get("p95_ms")
    budget_ms = latency.get("budget_ms")
    profile = latency.get("profile")
    if p95_ms is None or budget_ms is None:
        failures.append(_fail(
            "P8B_GATE_LATENCY_SCHEMA_INVALID",
            "enqueue_latency_trend must include p95_ms and budget_ms",
            "Write deterministic latency trend fields into fixture.",
        ))
    elif p95_ms > budget_ms or budget_ms > 100:
        failures.append(_fail(
            "P8B_GATE_ENQUEUE_P95_REGRESSION",
            f"enqueue p95 exceeded envelope: p95_ms={p95_ms}, budget_ms={budget_ms}, profile={profile}",
            "Reduce enqueue hot-path latency or adjust benchmark environment noise before updating fixture.",
        ))

    integrity = payload.get("integrity", {})
    artifact_ok = integrity.get("artifact_suite_passed")
    checkpoint_ok = integrity.get("checkpoint_suite_passed")
    if artifact_ok is not True:
        failures.append(_fail(
            "P8B_GATE_ARTIFACT_INTEGRITY_FAILED",
            "artifact integrity suite marker is not true",
            "Run artifact integrity tests locally, fix drift/corruption, then refresh fixture marker.",
        ))
    if checkpoint_ok is not True:
        failures.append(_fail(
            "P8B_GATE_CHECKPOINT_INTEGRITY_FAILED",
            "checkpoint integrity suite marker is not true",
            "Run checkpoint envelope integrity tests, resolve checksum/schema issues, then refresh fixture marker.",
        ))

    if failures:
        print("[phase8b-gates] gate failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("[phase8b-gates] scale/latency/integrity fixture checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
