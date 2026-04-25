# MVP-3 Security Audit — Kernel-Driver Execution Boundary

- **Date**: 2026-04-25
- **Scope**:
  - `src/rust/crates/eigen-kernel/src/rpc.rs`
  - `src/services/driver-manager/src/driver_manager/grpc_impl.py`
  - `src/services/driver-manager/src/driver_manager/simulator_driver.py`
- **Audit type**: manual code audit + boundary control checklist
- **Related artifacts**: RFC 0016, ADR 0007

## Objective

Verify that the kernel-to-driver execution handoff enforces strict validation, canonical error mapping, trace correlation, and constrained simulator execution without introducing arbitrary code execution paths.

## Checklist and findings

### 1) Request validation at boundary
- **Check**: kernel and driver-manager reject malformed job or payload fields before execution.
- **Result**: **PASS**.
- **Evidence**:
  - kernel validates required `name` / `job_id` fields on enqueue/status/results/cancel RPCs;
  - driver-manager validates `device_id`, `payload.format`, `payload.data`, and `shots > 0` before dispatch;
  - unsupported payload format is rejected with `UNIMPLEMENTED`.

### 2) Driver dispatch and device allowlisting
- **Check**: only registered devices are executable.
- **Result**: **PASS**.
- **Evidence**: driver-manager resolves target through registry and aborts with `FAILED_PRECONDITION` when device is unknown.

### 3) Canonical error mapping and deterministic failure signaling
- **Check**: simulator/runtime failures map to stable gRPC codes.
- **Result**: **PASS**.
- **Evidence**:
  - simulator raises explicit `DriverExecutionError` with canonical `INVALID_ARGUMENT`, `UNIMPLEMENTED`, `UNAVAILABLE`, `RESOURCE_EXHAUSTED` classes;
  - driver-manager surfaces these directly through gRPC abort;
  - kernel failure path terminalizes to `ERROR` with persisted diagnostic metadata.

### 4) Runtime execution safety (no arbitrary user code)
- **Check**: runtime executes structured AQO payload interpretation only.
- **Result**: **PASS**.
- **Evidence**:
  - simulator parses UTF-8 JSON payload and validates operation schema;
  - operation set is hard allowlisted (`RX`, `RY`, `RZ`, `CX`, `MEASURE`);
  - no dynamic import/eval/exec path in the driver execution pipeline.

### 5) Traceability and audit logging
- **Check**: cross-service correlation identifiers preserved.
- **Result**: **PASS**.
- **Evidence**:
  - kernel extracts and reinjects `traceparent` / `trace_id` to downstream RPC calls;
  - driver-manager logs `rpc_start`/`rpc_end` with `job_id` and trace fields.

## Residual risks and follow-ups

1. **In-memory payload size pressure**: AQO payload parsing remains memory-bound; add explicit payload byte limit enforcement at driver-manager boundary in post-MVP hardening.
2. **Metadata redaction policy**: current metadata is controlled but should add explicit denylist checks if new backend metadata fields are introduced.
3. **Timeout ownership clarity**: kernel-owned timeout terminalization is frozen for MVP-3; continue reviewing API-layer UX for long-running backends post-MVP.

## Conclusion

Audit outcome: **Kernel-Driver execution boundary is acceptable for MVP-3 release readiness** under current simulator-only scope and frozen runtime contracts.
