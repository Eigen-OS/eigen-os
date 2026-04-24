# MVP Definition of Done — by service

> This is a **delivery control** document.  

---

## 0) Global DoD (applies to all services)
- [x] Uses canonical protobuf/JobSpec (source of truth, no copies).
- [x] Logs include `{trace_id, job_id, device_id}` where applicable.
- [x] Propagates `traceparent` through outbound calls.
- [x] Uses gRPC status codes (no `success=false`) and optional structured error details.
- [x] Has unit tests for validation + error mapping.
- [x] Has a minimal “smoke” integration test in CI.

---

## 1) System API
### Must provide
- [x] JobService: SubmitJob / GetJobStatus / GetJobResults / CancelJob / StreamJobUpdates
- [x] DeviceService: ListDevices / GetDeviceStatus (ReserveDevice only if kept)
- [x] (Optional) CompilationService: CompileCircuit (kept internal for MVP)

### Must enforce
- [x] auth/authz at boundary (allow‑all + static token mode documented in service config)
- [x] request size limits
- [x] idempotency strategy for SubmitJob

### Must be testable
- [x] e2e: submit → watch → results on simulator
- [x] invalid job → INVALID_ARGUMENT + field violations

---

## 2) Kernel / QRTX
### Must provide
- [x] Job lifecycle state machine
- [x] Internal gRPC to Compiler + DriverManager
- [x] Aggregated device view for DeviceService

### Must enforce
- [x] strict stage boundaries
- [x] retry boundaries (only UNAVAILABLE/RESOURCE_EXHAUSTED if enabled)

### Must be testable
- [x] state machine tests (incl. cancel)
- [x] integration with simulator driver

---

## 3) Compiler
### Must provide
- [x] AST-only compilation (no exec)
- [x] allowlist validation (MVP subset)
- [x] deterministic output for same input

### Must be testable
- [x] conformance suite with golden fixtures (`tests/golden/`) and negative fixtures (`tests/negative/`)
- [x] conformance suite runs on every PR in CI
- [x] golden changes follow explicit documented update process
- [x] invalid source→INVALID_ARGUMENT

---

## 4) Driver Manager
### Must provide
- [x] DriverManagerService: ListDevices / GetDeviceStatus / ExecuteCircuit
- [x] SimulatorDriver as golden driver

### Must enforce
- [x] error normalization (vendor→canonical)
- [x] canonical counts format + bit ordering rule

### Must be testable
- [x] driver compliance tests
- [x] error mapping tests

---

## 5) QFS (CircuitFS)
- [x] stable path layout per job_id
- [x] atomic results write
- [x] store/retrieve tests

---

## 6) CLI / SDK
- [x] commands: submit/status/results/watch
- [x] packaging rule: job.yaml + program.eigen.py + sha256 + entrypoint
- [x] friendly error output
- [x] e2e against local stack (or mocked API)

---

## 7) Observability
- [x] `/metrics` exposed
- [x] trace propagation verified end-to-end
- [x] smoke tests for metrics and trace propagation

