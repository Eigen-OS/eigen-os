# MVP Definition of Done — by service

> This is a **delivery control** document.  

---

## 0) Global DoD (applies to all services)
- [ ] Uses canonical protobuf/JobSpec (source of truth, no copies).
- [ ] Logs include `{trace_id, job_id, device_id}` where applicable.
- [ ] Propagates `traceparent` through outbound calls.
- [ ] Uses gRPC status codes (no `success=false`) and optional structured error details.
- [ ] Has unit tests for validation + error mapping.
- [ ] Has a minimal “smoke” integration test in CI.

---

## 1) System API
### Must provide
- [ ] JobService: SubmitJob / GetJobStatus / GetJobResults / CancelJob / StreamJobUpdates
- [ ] DeviceService: ListDevices / GetDeviceStatus (ReserveDevice only if kept)
- [ ] (Optional) CompilationService: CompileCircuit (if kept public)

### Must enforce
- [ ] auth/authz at boundary (even if allow‑all, document it)
- [ ] request size limits
- [ ] idempotency strategy for SubmitJob

### Must be testable
- [ ] e2e: submit → watch → results on simulator
- [ ] invalid job → INVALID_ARGUMENT + field violations

---

## 2) Kernel / QRTX
### Must provide
- [ ] Job lifecycle state machine
- [ ] Internal gRPC to Compiler + DriverManager
- [ ] Aggregated device view for DeviceService

### Must enforce
- [ ] strict stage boundaries
- [ ] retry boundaries (only UNAVAILABLE/RESOURCE_EXHAUSTED if enabled)

### Must be testable
- [ ] state machine tests (incl. cancel)
- [ ] integration with simulator driver

---

## 3) Compiler
### Must provide
- [ ] AST-only compilation (no exec)
- [ ] allowlist validation (MVP subset)
- [ ] deterministic output for same input

### Must be testable
- [ ] golden tests source→AQO
- [ ] invalid source→INVALID_ARGUMENT

---

## 4) Driver Manager
### Must provide
- [ ] DriverManagerService: ListDevices / GetDeviceStatus / ExecuteCircuit
- [ ] SimulatorDriver as golden driver

### Must enforce
- [ ] error normalization (vendor→canonical)
- [ ] canonical counts format + bit ordering rule

### Must be testable
- [ ] driver compliance tests
- [ ] error mapping tests

---

## 5) QFS (CircuitFS)
- [ ] stable path layout per job_id
- [ ] atomic results write
- [ ] store/retrieve tests

---

## 6) CLI / SDK
- [ ] commands: submit/status/results/watch
- [ ] packaging rule: job.yaml + program.eigen.py + sha256 + entrypoint
- [ ] friendly error output
- [ ] e2e against local stack (or mocked API)

---

## 7) Observability
- [ ] `/metrics` exposed
- [ ] trace propagation verified end-to-end
- [ ] smoke tests for metrics and trace propagation

