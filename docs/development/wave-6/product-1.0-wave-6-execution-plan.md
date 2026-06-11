# Product 1.0 Wave 6 Execution Plan

**Wave:** Product 1.0 Wave 6 — Driver Manager and QDriver final contract  
**Status:** Planning baseline  
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`  
**Inventory:** `docs/development/product-1.0-contract-inventory.md`  
**Version policy:** `docs/development/product-1.0-version-policy.md`  
**Source of truth:** `docs/architecture/**`, `docs/reference/**`  
**Created:** 2026-06-12

---

## 1. Goal

Wave 6 makes provider execution safe, normalized, and replaceable by closing the remaining gap between the current Driver Manager skeleton and the final Product 1.0 QDriver contract. The wave must preserve the existing kernel-facing driver manager boundary while tightening the behavior expected from provider adapters, simulator parity, secrets handling, and observability.

Wave 6 is a **major internal contract alignment wave**. It may change driver-manager internals, provider-adapter lifecycle behavior, supported transport forms, and conformance expectations. It must not introduce silent provider-specific behavior into public contracts.

---

## 2. Normative source map

| Wave 6 area | Canonical source | Implementation surface | Primary evidence |
|---|---|---|---|
| Driver Manager architecture boundary | `docs/architecture/components/driver-manager.md` | `src/services/driver-manager`, kernel-facing gRPC service, driver registry | Driver-manager conformance tests, registry fixtures |
| QDriver v1 final contract | `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`; `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md` | `DriverManagerService`, `BaseDriver`, provider adapters | `src/services/driver-manager/tests/test_qdriver_v1_conformance.py` |
| Provider matrix and tolerance governance | `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`; `docs/adr/0031-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md` | provider matrix fixtures, parity policy, rollback governance | parity tests and tolerance-suite fixtures |
| Internal API transport shape | `docs/reference/api/grpc-internal.md` | `proto/eigen/internal/v1/driver_manager_service.proto`, generated bindings | proto lint / breaking checks |
| Security / secrets isolation | `docs/architecture/components/driver-manager.md`; `docs/reference/security/authz.md` if referenced by implementation | secret lifecycle, sandbox policy, provider config resolution | secret lifecycle tests, authz tests |
| Observability and audit trail | `docs/reference/orchestration-observability-contract.md`; `docs/reference/intelligent-runtime-observability-contract.md` | bounded logs, metrics, trace continuity | observability smoke / driver-manager metrics checks |

---

## 3. Wave scope

### In scope

1. Align the kernel-facing Driver Manager contract with the final QDriver v1 contract.
2. Preserve the simulator as the canonical reference backend for conformance and parity checks.
3. Normalize execution results, device status, and error semantics across provider adapters.
4. Make session pooling and lifecycle management explicit and testable.
5. Enforce sandbox/process isolation and secret handling for provider credentials.
6. Define tolerance profiles, rollback hooks, and parity gates for the official provider matrix.
7. Publish a planning-time compatibility story for existing MVP-style driver-manager behavior.
8. Keep observability and audit evidence bounded, structured, and replay-friendly.

### Out of scope

- Kernel lifecycle ownership changes already resolved in Wave 2.
- QFS lineage / checkpoint ownership changes already resolved in Wave 4.
- Resource Manager scheduling and multi-device dispatch changes already resolved in Wave 5.
- New public product surfaces unrelated to driver execution.

---

## 4. Work streams

### 4.1 Final QDriver contract alignment

- Reconcile the current `DriverManagerService` interface with the accepted QDriver v1 semantics.
- Add/maintain the canonical `docs/reference/api/qdriver.md` reference so the final contract is frozen on the docs surface.
- Document the accepted method set, capability negotiation, and unsupported-operation policy.
- Ensure the implementation does not leak provider-specific SDK details across the kernel boundary.
- Keep gRPC status mapping stable and deterministic.

### 4.2 Provider capability registry and device profiles

- Make device capabilities and profile metadata versioned and queryable.
- Keep snapshot ordering deterministic by device_id and driver name.
- Separate profile snapshot state from live session state.
- Define profile negotiation fallback behavior for unsupported profiles and simulator parity entries.
- Separate capability snapshot concerns from session/connection concerns.
- Treat simulator and official providers as matrix entries with explicit tolerance policy hooks.

### 4.3 Session pooling and lifecycle governance

- Define session creation, reuse, refresh, graceful shutdown, and restart behavior.
- Make calibration lifecycle semantics explicit.
- Keep the lifecycle transitions deterministic and testable.

### 4.4 Result normalization and error mapping

- Normalize counts, metadata, timing, and execution results into the canonical response shape.
- Map provider errors into stable Eigen OS error classes.
- Preserve retryability and precondition semantics in structured form.

### 4.5 Sandbox, secrets, and supply-chain isolation

- Ensure provider credentials are loaded only through the security/secrets module.
- Keep provider execution isolated from the public surface.
- Document the fail-closed behavior for secret retrieval and sandbox policy failures.

### 4.6 Simulator reference backend and parity gates

- Keep the simulator as the default reference backend for conformance and CI.
- Add parity fixtures for supported provider classes.
- Make tolerance profiles explicit and versioned.

### 4.7 Observability and release evidence

- Keep driver-manager metrics bounded.
- Preserve trace continuity from kernel to provider adapter.
- Publish release evidence for matrix coverage, parity, and rollback behavior.

---

## 5. Exit criteria

Wave 6 is ready to close only when:

1. The final QDriver contract is documented, implemented, and conformance-tested.
2. The simulator reference backend passes the canonical conformance suite.
3. Provider parity and tolerance policy are versioned and enforced in CI.
4. Secrets handling and sandbox isolation remain fail-closed.
5. Normalized results and errors are stable for identical inputs.
6. The inventory, manifest, compatibility report, release checklist, and exit evidence bundle are synchronized.
7. No undocumented provider-specific behavior remains in the canonical path.

---

## 6. Deliverables

- Wave 6 issue pack
- Wave 6 RFC / ADR gap analysis
- Wave 6 compatibility report
- Wave 6 release readiness checklist
- Wave 6 exit evidence bundle
- Canonical QDriver v1 reference: `docs/reference/api/qdriver.md`
- Inventory row and manifest row for the Driver Manager / QDriver final contract

---

## 7. Concrete implementation artifacts

The Wave 6 opening package is carried by:

- `docs/development/wave-6/README.md`
- `docs/development/wave-6/product-1.0-wave-6-execution-plan.md`
- `docs/development/wave-6/product-1.0-wave-6-issue-pack.md`
- `docs/development/wave-6/product-1.0-wave-6-rfc-adr-gap-analysis.md`
- `docs/development/wave-6/product-1.0-wave-6-compatibility-report.md`
- `docs/development/wave-6/product-1.0-wave-6-release-readiness-checklist.md`
- `docs/development/wave-6/product-1.0-wave-6-exit-evidence-bundle.md`
