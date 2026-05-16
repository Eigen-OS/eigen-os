from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs" / "development" / "fixtures" / "phase8a" / "probe_trends_v1.json"

REQUIRED_PROBES = {
    "compile_latency_ms": lambda p: p["p95"] <= p["budget_ms"],
    "scheduler_enqueue_p95_ms": lambda p: p["p95"] <= p["budget_ms"],
    "kb_indexed_query_latency_ms": lambda p: p["p95"] <= p["budget_ms"],
    "dataset_ingestion_seconds": lambda p: p["duration"] <= p["max_seconds"],
}


def main() -> int:
    if not FIXTURE.exists():
        print(f"[phase8a-probes] missing fixture: {FIXTURE.relative_to(ROOT)}")
        return 1

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures: list[str] = []

    if payload.get("fixture_version") != "1.0.0":
        failures.append("fixture_version must be 1.0.0")

    probes = payload.get("probes", {})
    for name, predicate in REQUIRED_PROBES.items():
        probe = probes.get(name)
        if probe is None:
            failures.append(f"missing required probe '{name}'")
            continue
        try:
            if not predicate(probe):
                failures.append(f"probe '{name}' exceeded budget: {probe}")
        except KeyError as exc:
            failures.append(f"probe '{name}' missing required key: {exc}")

    if failures:
        print("[phase8a-probes] gate failed:")
        for failure in failures:
            print(f" - {failure}")
        print("[phase8a-probes] update docs/development/fixtures/phase8a/probe_trends_v1.json with versioned deterministic probe values.")
        return 1

    print("[phase8a-probes] all probe fixtures are present and within deterministic budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
