<<<<<<< HEAD
# RFC 0002: System architecture boundaries and service graph (MVP)

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0003,0004,0006,0007

## Summary

Defines the MVP service decomposition and the mandatory inter-service edges from client to QPU and back.

## Motivation

The roadmap requires an MVP that runs an end-to-end VQE cycle via `eigen-cli submit --job job.yaml`. To reach that quickly, we must pin down what runs where, and which protocols connect services.

## Goals

- Establish a consistent client→API→kernel→compiler/driver-manager→backend→kernel→API→client path.
- Avoid circular dependencies and hidden coupling.
- Make future split/merge of services explicit.

## Non-Goals

- Final microservices topology for Phase 2+.
- High-availability deployment and multi-region concerns.

## Guide-level explanation

**MVP services:**
- `system-api` (Python): public gRPC/REST, authn/authz, request validation, observability boundary.
- `eigen-kernel` (Rust): QRTX scheduler + execution pipeline + QFS access.
- `eigen-compiler` (Python): CompilationService (Compile/Validate/Optimize).
- `driver-manager` (Python): DriverManagerService (List/Status/Execute/Calibrate) and plugin loading.

**Mandatory edges (sync RPC):**
1) Clients → system-api: `eigen_api.v1` gRPC.
2) system-api → eigen-kernel: internal gRPC (`kernel_api.v1`, defined in RFC 0004 Appendix A).
3) eigen-kernel → eigen-compiler: `CompilationService` gRPC.
4) eigen-kernel → driver-manager: `DriverManagerService` gRPC.
5) driver-manager → backend: vendor SDK/HTTP.
**Artifacts/results** are persisted by kernel into QFS and served back through system-api.

## Reference-level design

### Interfaces / APIs

Public gRPC (client-facing): RFC 0004.
Compiler gRPC: RFC 0004 (CompilationService).
Driver-manager gRPC: RFC 0006.
Kernel internal gRPC: RFC 0004 (Appendix A).

### Data model

JobSpec: RFC 0003. IR/AQO: RFC 0005.
Results: counts + metadata (RFC 0006).

### Error model

All inter-service calls must map errors to a common error envelope: `code`, `message`, `details` (protobuf Any) at the API boundary.

### Security & privacy

system-api is the only public ingress.
Kernel/Compiler/DriverManager are internal network only.
Auth context is propagated from system-api to kernel via metadata headers (trace + authz claims).

### Observability

Trace context propagated end-to-end.
system-api emits request metrics; kernel emits job lifecycle + execution metrics; driver-manager emits backend/driver metrics.

### Performance notes

MVP expects low concurrency; prioritize correctness and observability.
Hot path: kernel pipeline stage transitions; avoid blocking I/O in scheduler thread.

## Testing plan

Contract tests for RPC interfaces (golden protobuf messages).
Integration test: job.yaml → SubmitJob → DONE → GetJobResults.
Driver-manager simulated backend test.

## Rollout / Migration

Start with single-host docker-compose deployment.
Allow compiling/executing against simulator only.
Add real QPU drivers in Phase 2.

## Alternatives considered

- Collapsing compiler into system-api (rejected for MVP: kernel already models CompilerClient).
- Exposing kernel directly to clients (postponed: keep stable public boundary).

## Open questions

- Exact shape of `kernel_api.v1`? (defined in RFC 0004 Appendix A as minimal gateway)
- Which payload format for circuit to driver-manager? (bytes + format enum in RFC 0006)
=======
# RFC 0002: System architecture boundaries and service graph (MVP)

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0003,0004,0006,0007

## Summary

Defines the MVP service decomposition and the mandatory inter-service edges from client to QPU and back.

## Motivation

The roadmap requires an MVP that runs an end-to-end VQE cycle via `eigen-cli submit --job job.yaml`. To reach that quickly, we must pin down what runs where, and which protocols connect services.

## Goals

- Establish a consistent client→API→kernel→compiler/driver-manager→backend→kernel→API→client path.
- Avoid circular dependencies and hidden coupling.
- Make future split/merge of services explicit.

## Non-Goals

- Final microservices topology for Phase 2+.
- High-availability deployment and multi-region concerns.

## Guide-level explanation

**MVP services:**
- `system-api` (Python): public gRPC/REST, authn/authz, request validation, observability boundary.
- `eigen-kernel` (Rust): QRTX scheduler + execution pipeline + QFS access.
- `eigen-compiler` (Python): CompilationService (Compile/Validate/Optimize).
- `driver-manager` (Python): DriverManagerService (List/Status/Execute/Calibrate) and plugin loading.

**Mandatory edges (sync RPC):**
1) Clients → system-api: `eigen_api.v1` gRPC.
2) system-api → eigen-kernel: internal gRPC (`kernel_api.v1`, defined in RFC 0004 Appendix A).
3) eigen-kernel → eigen-compiler: `CompilationService` gRPC.
4) eigen-kernel → driver-manager: `DriverManagerService` gRPC.
5) driver-manager → backend: vendor SDK/HTTP.
**Artifacts/results** are persisted by kernel into QFS and served back through system-api.

## Reference-level design

### Interfaces / APIs

Public gRPC (client-facing): RFC 0004.
Compiler gRPC: RFC 0004 (CompilationService).
Driver-manager gRPC: RFC 0006.
Kernel internal gRPC: RFC 0004 (Appendix A).

### Data model

JobSpec: RFC 0003. IR/AQO: RFC 0005.
Results: counts + metadata (RFC 0006).

### Error model

All inter-service calls must map errors to a common error envelope: `code`, `message`, `details` (protobuf Any) at the API boundary.

### Security & privacy

system-api is the only public ingress.
Kernel/Compiler/DriverManager are internal network only.
Auth context is propagated from system-api to kernel via metadata headers (trace + authz claims).

### Observability

Trace context propagated end-to-end.
system-api emits request metrics; kernel emits job lifecycle + execution metrics; driver-manager emits backend/driver metrics.

### Performance notes

MVP expects low concurrency; prioritize correctness and observability.
Hot path: kernel pipeline stage transitions; avoid blocking I/O in scheduler thread.

## Testing plan

Contract tests for RPC interfaces (golden protobuf messages).
Integration test: job.yaml → SubmitJob → DONE → GetJobResults.
Driver-manager simulated backend test.

## Rollout / Migration

Start with single-host docker-compose deployment.
Allow compiling/executing against simulator only.
Add real QPU drivers in Phase 2.

## Alternatives considered

- Collapsing compiler into system-api (rejected for MVP: kernel already models CompilerClient).
- Exposing kernel directly to clients (postponed: keep stable public boundary).

## Open questions

- Exact shape of `kernel_api.v1`? (defined in RFC 0004 Appendix A as minimal gateway)
- Which payload format for circuit to driver-manager? (bytes + format enum in RFC 0006)
>>>>>>> ecdefb971cbcc1e10e3966753900fbc94b960cc2
