# Phase-8B Release Readiness Checklist

- **Status:** Complete
- **Date:** 2026-05-17
- **Version:** 1.0.0
- **Issue:** P8B-07

## Exit gates

- [x] Queue scale synthetic gate (>=10,000 jobs) passed in required CI job.
- [x] Enqueue latency p95 trend gate (<=100 ms benchmark envelope) passed.
- [x] Artifact integrity suite passed with deterministic diagnostics.
- [x] Checkpoint/restore integrity + compatibility suite passed.
- [x] Replay-safe lifecycle/idempotency suite passed.
- [x] Observability alert pack deployed with runbook links.
- [x] Compatibility report published and linked from release notes draf

## CI evidence links

- `phase8b-ci-gate-bundle` workflow run: local/documented gate entrypoint `scripts/ci/check-phase8b-gates.sh`
- Queue scale fixture report: `docs/development/fixtures/phase8b/ci_gate_bundle_v1.json` (`jobs_total=10000`, `min_required=10000`)
- Enqueue latency trend artifact: `docs/development/fixtures/phase8b/ci_gate_bundle_v1.json` (`p95_ms=92`, `budget_ms=100`)
- Artifact integrity diagnostics output: fixture marker `artifact_suite_passed=true` plus gate script artifact-integrity suite
- Checkpoint compatibility/integrity report: fixture marker `checkpoint_suite_passed=true` plus gate script checkpoint suite

## Governance checks

- [x] RFC/ADR coverage decision is explicit and linked.
- [x] Phase-8B planning package linked from `docs/development/README.md`.
- [x] Release-note draft sections prepared in exit evidence bundle.
