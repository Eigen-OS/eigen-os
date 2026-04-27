This document is a ready-to-use set of GitHub issues for the **Phase-3** stage of the roadmap.

**Context Sources:**
- `docs/roadmap.md` (Section: "Phase-3: Benchmarking Platform")
- `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase-3: Benchmarking Platform")
- `docs/development/phase-3-rfc-adr-gap-analysis.md`

---

## Versioning Rules (Mandatory for every Phase-3 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer for stable benchmark contracts:**
   - Benchmark run/compare/history DTOs use `MAJOR.MINOR.PATCH`.
2. **Breaking changes only via `MAJOR`:**
   - Any incompatible payload, state-machine, or comparison semantics change requires `MAJOR`.
3. **Backward-compatible additions via `MINOR`:**
   - Optional fields/metadata that do not break clients use `MINOR`.
4. **`PATCH` for fixes only:**
   - No changes to public benchmark semantics in `PATCH` releases.
5. **Mandatory version markers in artifacts:**
   - Run snapshots, comparison outputs, and history entries include explicit version fields.
6. **Deprecation policy:**
   - Fields cannot be removed before at least one `MINOR` release marks them deprecated.
7. **Changelog discipline:**
   - Every Phase-3 PR includes:
     - `Version impact`
     - `Compatibility`
     - `Migration notes` (if applicable).

---

## Milestone

- **Milestone:** `Phase-3 Benchmarking Platform`
- **Suggested labels:** `phase-3`, `benchmarking`, `dataset`, `api`, `cli`, `observability`, `quality`

---

## Issues

### P3-01 — Benchmark Service Core v1 (Run Lifecycle)

**Type:** Feature  
**Labels:** `phase-3`, `benchmarking`, `runtime`

**Problem** A dedicated run lifecycle is required for reproducible benchmark execution and auditability.

**Scope**
- `benchmark-service` skeleton and run state machine.
- Idempotent run start/retry semantics.
- Deterministic run snapshot persistence.

**Acceptance Criteria**
- Run state transitions are documented and tested.
- Duplicate run requests are idempotent.
- Every run stores immutable execution snapshot metadata.

**Versioning Constraints**
- Run lifecycle state contract carries explicit version.

---

### P3-02 — QSBench-Compatible Dataset Ingestion Pipeline

**Type:** Feature  
**Labels:** `phase-3`, `dataset`, `benchmarking`

**Problem** Benchmarks are not useful without standardized datasets and reproducible ingestion.

**Scope**
- Dataset manifest schema and validation.
- Ingestion flow with checksum/provenance verification.
- Dataset catalog registration.

**Acceptance Criteria**
- Invalid dataset bundles are rejected with structured errors.
- Dataset versions are queryable from the registry.
- Ingestion test fixtures cover positive and negative cases.

**Versioning Constraints**
- Dataset manifest schema changes follow SemVer discipline.

---

### P3-03 — Benchmark Run API (`/benchmarks/run`) and Contract Tests

**Type:** API  
**Labels:** `phase-3`, `api`, `benchmarking`

**Problem** A stable external contract is required for launching benchmark runs from tooling.

**Scope**
- Request/response schema for benchmark runs.
- Validation and error envelope mapping.
- API conformance fixtures + CI gate.

**Acceptance Criteria**
- API schema is documented in `docs/reference/`.
- Contract compatibility tests block breaking changes.
- Error model aligns with existing public API conventions.

**Versioning Constraints**
- Removing/changing required request fields without `MAJOR` is prohibited.

---

### P3-04 — Comparison API (`/benchmarks/compare`) with Statistical Metadata

**Type:** Feature / API  
**Labels:** `phase-3`, `api`, `analytics`

**Problem** Teams need reliable side-by-side comparison and regression detection between benchmark runs.

**Scope**
- Compare request model (`A vs B`, cohort filters).
- Output schema for deltas + confidence metadata.
- Baseline regression flags and threshold policies.

**Acceptance Criteria**
- Comparison output is deterministic for identical inputs.
- Regression flagging is test-covered with fixtures.
- Compare schema includes version + methodology metadata.

**Versioning Constraints**
- Changing delta semantics requires `MAJOR`.

---

### P3-05 — History API (`/benchmarks/history`) and Trend Queries

**Type:** Feature / API  
**Labels:** `phase-3`, `api`, `benchmarking`

**Problem** Operators and researchers need historical trend data for performance governance.

**Scope**
- Time-range and filterable history endpoint.
- Pagination and stable ordering guarantees.
- Trend-oriented aggregate fields.

**Acceptance Criteria**
- History endpoint supports deterministic pagination.
- Query filters are validated and documented.
- Integration tests cover trend and edge-case retrieval.

**Versioning Constraints**
- Pagination and ordering guarantees are part of the public contract.

---

### P3-06 — CLI UX: `eigen benchmark run/compare`

**Type:** DX / CLI  
**Labels:** `phase-3`, `cli`, `benchmarking`

**Problem** Phase-3 must be usable without writing custom client code.

**Scope**
- `eigen benchmark run` command.
- `eigen benchmark compare` command.
- JSON + human-readable output modes.

**Acceptance Criteria**
- CLI commands cover minimum end-to-end benchmark flow.
- Snapshot fixtures protect output compatibility.
- Help docs include reproducibility-focused examples.

**Versioning Constraints**
- CLI JSON output is treated as a stable contract.

---

### P3-07 — Benchmark Metrics, Dashboards, and Alerts Pack

**Type:** Observability  
**Labels:** `phase-3`, `observability`, `sre`

**Problem** Benchmark pipeline health must be observable and operable in production-like setups.

**Scope**
- Metrics: queue depth, run duration, success/failure rates, ingestion failures.
- Dashboard views for throughput and regression signals.
- Alerts and runbook entries for benchmark SLO breaches.

**Acceptance Criteria**
- Dashboard(s) exist for benchmark lifecycle visibility.
- Alert rules fire on stalled run/ingestion error conditions.
- Runbook includes concrete triage steps.

**Versioning Constraints**
- Metric names and labels are part of the observability contract.

---

### P3-08 — Reproducibility and Determinism Gate

**Type:** Quality  
**Labels:** `phase-3`, `quality`, `benchmarking`

**Problem** Benchmark results lose value if repeated runs with identical configs diverge unexpectedly.

**Scope**
- Reproducibility test suite.
- Deterministic config snapshot validation.
- CI quality gate for reproducibility drift.

**Acceptance Criteria**
- Identical run configs produce consistent metadata and bounded metric variance.
- CI blocks uncontrolled reproducibility regressions.
- Drift diagnostics are emitted when gate fails.

**Versioning Constraints**
- Reproducibility policy thresholds are versioned and documented.

---

### P3-09 — RFC Package for Phase-3 Contracts

**Type:** Architecture / Governance  
**Labels:** `phase-3`, `rfc`, `architecture`

**Problem** Phase-3 currently has implementation goals but lacks a dedicated RFC package for contract-level decisions.

**Scope**
- Create/accept RFCs for:
  1. benchmark run contract,
  2. dataset ingestion contract,
  3. comparison methodology + history contract.
- Link RFCs from roadmap/development docs.

**Acceptance Criteria**
- Required Phase-3 RFC set is merged and indexed.
- Each RFC includes compatibility and benchmarking/test plan sections.
- RFC statuses are explicit (`Draft`/`Accepted`/`Implemented`).

**Versioning Constraints**
- No Phase-3 contract is marked stable without an accepted RFC.

---

### P3-10 — ADR Package and Phase-3 Release Readiness Meta

**Type:** Meta / Release  
**Labels:** `phase-3`, `adr`, `release`, `quality`

**Problem** Accepted RFC outcomes must be operationalized in ADRs before Phase-3 closure.

**Scope**
- Add ADR(s) mirroring accepted and implemented Phase-3 RFC outcomes.
- Add release readiness checklist + compatibility report templates for Phase-3.
- Update ADR index and RFC pointer docs.

**Acceptance Criteria**
- Every implemented Phase-3 RFC has synchronized ADR coverage.
- `docs/adr/README.md` and `docs/rfcs-pointer.md` are updated.
- Release package docs exist and are linked from `docs/development/README.md`.

**Versioning Constraints**
- Phase-3 release cannot be marked `Ready` without signed compatibility and ADR synchronization check.

---
