# Product 1.0 Wave 2 Exit Evidence Bundle

**Status:** Draft evidence template for Wave 2 closure
**Scope:** Kernel/QRTX lifecycle authority, internal API conformance, state replay, System API delegation, orchestration DAG, cancellation/deadline/retry behavior, observability, and migration evidence
**Created:** 2026-06-02

---

## 1. Evidence index

| Evidence ID | Requirement | Command / artifact | Expected result | Actual result | Owner | Link |
|---|---|---|---|---|---|---|
| W2-E01 | Internal KernelGateway proto/reference/state-machine coverage | `python3 scripts/ci/check-docs-links.py`; `python3 scripts/ci/check-product-1-0-manifest.py`; Product 1.0 internal coverage matrix | Matrix has no unexplained gaps; manifest/inventory mappings resolve | TBD | Kernel/QRTX + Architecture | `docs/reference/api/grpc-internal.md`; `proto/eigen/internal/v1/kernel_gateway.proto`; `docs/development/product-1.0-contract-inventory.md` |
| W2-E02 | Durable/replayable kernel state and transition validation | Kernel state-store unit/integration tests | Replay/restart reconstructs state or fixture limitation is explicit; invalid transitions fail canonically | TBD | Kernel/QRTX + Runtime Reliability | `src/rust/crates/eigen-kernel/tests/` |
| W2-E03 | System API delegates lifecycle to Kernel/QRTX while preserving Wave 1 public behavior | `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_public_envelope_versioning.py`; `PYTHONPATH=src/services/system-api/src pytest src/services/system-api/tests/test_idempotency.py`; delegation integration tests | Public behavior remains compatible; lifecycle state is kernel-owned | TBD | System API + Kernel/QRTX | `src/services/system-api/tests/`; `src/rust/crates/eigen-kernel/tests/` |
| W2-E04 | Orchestration DAG submit-to-results and failed-stage paths | Kernel orchestration integration tests | DAG records deterministic stages and terminal states | TBD | Kernel/QRTX | `src/rust/crates/eigen-kernel/tests/` |
| W2-E05 | Deadline propagation and cancellation fan-out | Kernel cancellation/deadline integration tests | Queued/compiling/executing/finalizing cancellations and timeouts are deterministic | TBD | Kernel/QRTX + Driver Manager + Resource Manager | `src/rust/crates/eigen-kernel/tests/`; `src/services/driver-manager/tests/`; `src/rust/crates/resource-manager/tests/` |
| W2-E06 | Retry governance and canonical retryability | Kernel retry/failure taxonomy tests | Retryable, non-retryable, exhausted, and deadline-interrupted retries match canonical errors | TBD | Kernel/QRTX + Reliability | `docs/reference/error-model.md`; `docs/reference/error-mapping.md`; `src/rust/crates/eigen-kernel/tests/` |
| W2-E07 | Orchestration observability and trace continuity | Kernel/observability smoke tests; Prometheus fixture output | Contract markers, bounded labels, and trace continuity are present | TBD | Observability + Kernel/QRTX | `docs/reference/orchestration-observability-contract.md`; `docs/reference/cluster-runtime-observability-contract.md` |
| W2-E08 | Compatibility report, migration notes, and closure readiness | `python3 scripts/ci/check-product-1-0-wave2-planning.py`; Wave 2 closure validation command or manual governance review | Planning package is structurally complete; no unresolved completed-issue `TBD`; all MAJOR/breaking changes have migration notes and evidence | TBD | Architecture/Governance + Tech Writing | `docs/development/product-1.0-wave-2-compatibility-report.md`; `docs/development/product-1.0-wave-2-release-readiness-checklist.md` |

---

## 2. Required evidence record format

Each completed evidence item must include or point to:

- exact command(s) run,
- repository commit SHA recorded by the closure commit,
- generated proto/schema artifact paths when applicable,
- fixture paths and fixture digests when applicable,
- pass/fail output summary,
- known limitations,
- migration-note link for breaking behavior,
- release-note draft link,
- owner sign-off or review link.

---

## 3. Known limitations template

Known limitations for Wave 2 closure must be recorded here before release. Examples that require explicit acceptance if present:

- state-store implementation is fixture-backed rather than production-durable;
- event subscription supports polling but not replay cursors;
- downstream compiler/optimizer/driver/QFS adapters are placeholders pending later waves;
- split/merge execution is modeled but not fully implemented;
- selected orchestration metrics are deferred to resource/scheduler waves with compatibility rationale.

Current known limitations: `TBD`.

---

## 4. Wave 2 acceptance mapping

| Acceptance criterion | Evidence IDs | Status |
|---|---|---|
| Internal KernelGateway/reference coverage is reconciled | W2-E01 | Pending |
| Kernel owns lifecycle state and transition validation | W2-E02 | Pending |
| System API delegates lifecycle while public behavior remains compatible | W2-E03 | Pending |
| Orchestration DAG is deterministic and replay-safe | W2-E04 | Pending |
| Cancellation and deadlines propagate through lifecycle stages | W2-E05 | Pending |
| Retries are bounded and tied to canonical retryability | W2-E06 | Pending |
| Orchestration metrics and trace continuity are observable | W2-E07 | Pending |
| Compatibility, migration, and readiness evidence is complete | W2-E08 | Pending |

---

## 5. Closure statement

Wave 2 is not closed until every evidence row has an actual result, owner, and reproducible artifact link; W2-01 through W2-08 acceptance criteria map to objective evidence; public Wave 1 regression evidence is present; and every breaking internal change has migration notes.
