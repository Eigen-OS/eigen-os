# Product 1.0 Wave 7a Exit Evidence Bundle

**Status:** Wave 7a closure evidence draft
**Scope:** Optimizer service wiring, model registry, deterministic fallback, optimization traces, intelligent-runtime observability, and compatibility evidence
**Created:** 2026-06-12

---

## 1. Evidence index

| Evidence ID | Requirement | Command / artifact | Expected result | Actual result | Owner | Link |
|---|---|---|---|---|---|---|
| W7A-E01 | Optimizer service wiring through Kernel/QRTX | `src/rust/crates/eigen-kernel/src/rpc.rs`; `proto/eigen/internal/v1/optimizer_service.proto`; `src/services/system-api/tests/fixtures/contracts/optimizer_v1/service_contract_v1_0_0.json`; `src/services/system-api/tests/test_optimizer_contract_fixture.py` | Production path exists, preserves stable trace context, and keeps the frozen contract shape | Completed | GNN Optimizer + Kernel/QRTX | `docs/development/wave-7a/product-1.0-wave-7a-compatibility-report.md` |
| W7A-E02 | Model registry and promotion policy | Registry/policy fixture tests | Promotion is versioned and explicit | Completed | GNN Optimizer + Architecture | `docs/development/wave-7a/product-1.0-wave-7a-compatibility-report.md` |
| W7A-E03 | Deterministic fallback and confidence threshold behavior | `src/services/benchmark-service/tests/test_optimizer_evaluation_harness.py` | Unavailable/low-confidence paths use the documented fallback | Completed | GNN Optimizer + Reliability | `src/services/benchmark-service/tests/test_optimizer_evaluation_harness.py` |
| W7A-E04 | Optimization candidate traces and observability | `monitoring/metrics/prometheus/exporter.py`; `monitoring/dashboards/intelligent_runtime_dashboard.json`; `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`; `monitoring/metrics/tests/test_wave5_observability_conformance.py` | Candidate telemetry is present with bounded labels and trace continuity | Completed | Observability | `docs/development/wave-7a/product-1.0-wave-7a-compatibility-report.md` |
| W7A-E05 | Quality regression gates | `src/services/benchmark-service/tests/test_optimizer_evaluation_harness.py`; `scripts/ci/check-phase9b-gates.sh` | Fixed fixture regressions block release and preserve bounded evidence | Completed | GNN Optimizer + Release Governance | `docs/development/wave-7a/product-1.0-wave-7a-release-readiness-checklist.md` |
| W7A-E06 | Inventory/manifest synchronization and closure readiness | Docs review | No unresolved TBD values remain | Pending | Architecture/Governance | TBD |

---

## 2. Required evidence record format

- Exact commands run: `cd src/services/benchmark-service && PYTHONPATH=src pytest -q tests/test_optimizer_evaluation_harness.py`
- Commit SHA: record the closure commit SHA in the final release PR before merge
- Generated artifact paths: `docs/development/wave-7a/product-1.0-wave-7a-compatibility-report.md`; `docs/development/wave-7a/product-1.0-wave-7a-release-readiness-checklist.md`
- Fixture paths: `src/services/benchmark-service/tests/fixtures/optimizer_evaluation/offline_online_fixture.json`
- Pass/fail output summary: fixed fixture passes the gate when the regression is detected and the rollback recommendation stays blocked
- Known limitations: the extracted workspace snapshot is not a git checkout, so the closure commit SHA must be filled in by the release commit process

---

## 3. Wave 8 handoff

Wave 8 may start after the Wave 7a closure commit. The optimizer output is then considered a governed input to the knowledge/learning layer rather than fixture-only output.
