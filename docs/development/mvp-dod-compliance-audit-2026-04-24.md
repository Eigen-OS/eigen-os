# MVP DoD Compliance Audit — 2026-04-24

## Executive summary

Status at repository head: **MVP-compliant**.

- Core contract and test scaffolding are solid (public/internal proto, compiler conformance, simulator-based E2E smoke, QFS atomic writes).
- `SubmitJob` idempotency is now enforced in System API (preferred `client_request_id`, fallback `eigen_lang.sha256` key).
- API `v0.1` can be frozen for MVP with additive-only policy and Buf breaking checks in CI.

---

## 0) Global DoD

- ✅ Canonical protobuf/JobSpec source of truth (`proto/`, `docs/reference/jobspec.md`).
- ✅ Structured logging includes trace/job/device context hooks.
- ✅ `traceparent` propagation is implemented and has integration coverage in kernel.
- ✅ gRPC status codes + structured `google.rpc.BadRequest` details are used.
- ✅ Unit tests for validation/error mapping are present.
- ✅ Smoke integration tests are present in CI (`e2e-smoke-simulator`).

**Result:** ✅ Mostly compliant.

---

## 1) System API

### Must provide
- ✅ JobService: SubmitJob / GetJobStatus / GetJobResults / CancelJob / StreamJobUpdates
- ✅ DeviceService: ListDevices / GetDeviceStatus (and ReserveDevice kept)

### Must enforce
- ✅ auth/authz at boundary exists (`allow_all` + `static_token` modes documented in code).
- ✅ request size limits exist for source payload and jobspec-yaml metadata.
- ✅ idempotency strategy for SubmitJob is enforced (`client_request_id` + sha256 fallback).

### Must be testable
- ✅ e2e submit → watch → results on simulator.
- ✅ invalid job → INVALID_ARGUMENT with field violations.

**Result:** ✅ Compliant.

---

## 2) Kernel / QRTX

### Must provide
- ✅ Job lifecycle state machine implemented in `qrtx` with tests (including cancel path).
- ✅ Internal gRPC calls to Compiler + DriverManager are implemented in kernel pipeline.
- ✅ Aggregated device view is exposed through gateway RPC methods.

### Must enforce
- ✅ Strict stage boundaries are encoded via explicit state transitions.
- ✅ Retry boundary policy is fixed for MVP: retry only transient backend classes (`UNAVAILABLE` / `RESOURCE_EXHAUSTED`) when enabled by policy.

### Must be testable
- ✅ state machine tests (incl. cancel).
- ✅ integration with simulator driver path covered in kernel integration tests.

**Result:** ✅ Compliant.

---

## 3) Compiler

### Must provide
- ✅ AST-only compilation (no execution).
- ✅ Allowlist/forbidden constructs validation is implemented.
- ✅ Deterministic output for same input (`sort_keys=True` + deterministic test assertion).

### Must be testable
- ✅ Conformance suite includes `tests/golden/` and `tests/negative/`.
- ✅ Conformance suite runs on PRs via CI `python-components` job.
- ✅ Golden update process is documented.
- ✅ Invalid source maps to INVALID_ARGUMENT (+ field violations).

**Result:** ✅ Compliant.

---

## 4) Driver Manager

### Must provide
- ✅ DriverManagerService: ListDevices / GetDeviceStatus / ExecuteCircuit (+ optional CalibrateDevice).
- ✅ SimulatorDriver exists as golden driver.

### Must enforce
- ✅ Error normalization to canonical gRPC statuses.
- ✅ Canonical counts + bit ordering rule (`msb_first_by_classical_index`) enforced and tested.

### Must be testable
- ✅ Driver compliance tests exist.
- ✅ Error mapping tests exist.

**Result:** ✅ Compliant.

---

## 5) QFS (CircuitFS)

- ✅ Stable per-job path layout.
- ✅ Atomic writes implemented via temp file + persist.
- ✅ Store/retrieve tests exist.

**Result:** ✅ Compliant.

---

## 6) CLI / SDK

- ✅ commands: submit/status/results/watch.
- ✅ additional compile/visualize commands exist.
- ✅ packaging rule support present via jobspec parsing + sha256 flow.
- ✅ friendly gRPC-like error output present.
- ✅ e2e against mocked/public API path is covered by CLI tests and System API smoke tests.

**Result:** ✅ Compliant.

---

## 7) Observability

- ✅ `/metrics` exposed in System API and Driver Manager.
- ✅ trace propagation is verified end-to-end (kernel integration test).
- ✅ smoke tests for metrics and trace-related behavior exist.

**Result:** ✅ Compliant.

---

## Recommendation on API freeze (`v0.1`)

**Short answer:** yes, freeze API `0.1` now.

Recommended freeze policy for MVP closeout:

1. Freeze all existing field numbers and RPC signatures in `eigen.api.v1` and `eigen.internal.v1`.
2. Allow only additive changes (new optional fields/RPCs) after freeze.
3. Keep `buf lint` + `buf breaking` mandatory in CI (already configured).
4. Cut a tag/release note that marks this as “MVP contract baseline 0.1 (frozen)”.

---

## Verification commands run

- `PYTHONPATH=src/services/system-api/src pytest -q src/services/system-api/tests`
- `PYTHONPATH=src/services/eigen-compiler/src pytest -q src/services/eigen-compiler/tests`
- `PYTHONPATH=src/services/driver-manager/src pytest -q src/services/driver-manager/tests`
- `cargo test -q -p cli -p qrtx -p qfs --manifest-path src/rust/Cargo.toml`
- `cargo test -q -p eigen-kernel --manifest-path src/rust/Cargo.toml`
