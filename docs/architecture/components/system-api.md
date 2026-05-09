# System API

- Phase: MVP (срез состояния на 2026-05-09)

## Responsibility

The **System API** remains the **sole public ingress** for Eigen OS in MVP and currently provides:

1. **Public gRPC interface (implemented)**: exposes `JobService` and `DeviceService` and runs on `SYSTEM_API_GRPC_BIND` (default `0.0.0.0:50051`).
2. **Authentication & Authorization (implemented in MVP form)**: supports `allow_all` and `static_token` modes, plus coarse RBAC/permission checks.
3. **Request validation (implemented)**: validates job/device requests and returns canonical gRPC errors.
4. **Forwarding/execution shim (partially implemented)**: public API behavior is implemented, but direct forwarding to a real Kernel gRPC gateway is not the active path in this service implementation (current behavior is in-process simulated runtime state machine).
5. **Observability boundary (implemented)**: structured logs, request tracing context extraction, and Prometheus `/metrics` endpoint.
6. **Security context propagation (partially implemented)**: `x-eigen-*` and `traceparent` are consumed at boundary; full mandatory propagation contract to all downstream internal gRPC hops is defined by RFC/ADR, but this component currently does not yet act as a strict proxy to internal services for every request path.

### TODO (Responsibility)

- [ ] Replace in-process runtime emulation with strict gateway behavior to Kernel/Compiler for job lifecycle paths while preserving current public contract.
- [ ] Enforce end-to-end propagation guarantees for `x-eigen-sub`, `x-eigen-roles`, `x-eigen-tenant`, `traceparent` on all internal calls, not only at ingress parsing level.

## Interfaces

### Public gRPC API (implemented)

Defined in `proto/eigen/api/v1/*.proto` and served by `system-api`:

- **JobService**: `SubmitJob`, `GetJobStatus`, `CancelJob`, `StreamJobUpdates`, `GetJobResults`, `GetDispatchRationale`.
- **DeviceService**: `ListDevices`, `GetDeviceDetails`, `GetDeviceStatus`, `ReserveDevice`.

Notes:
- `GetDispatchRationale` is additive relative to the original MVP RFC 0004 surface.
- `StreamJobUpdates` currently streams from local job update state (poll/advance model), matching MVP semantics directionally.

### Public REST API (not implemented)

- **Status**: No production REST adapter (FastAPI/Flask public `/api/v1/*`) is wired in current service runtime.

### TODO (Public REST API)

- [ ] Implement REST adapter (`/api/v1/jobs`, `/api/v1/devices`) with generated gRPC translation and keep parity tests against gRPC responses.

### Internal gRPC clients (partially implemented vs RFC target)

RFC 0004 and architecture docs define System API as thin gateway to Kernel/Compiler internal gRPC.

Current state:
- **Kernel Gateway client**: not used as universal execution path by current `system-api` service implementation.
- **Compiler client**: not exposed as dedicated public `CompilationService`; compile flow is represented in lifecycle simulation and broader platform contracts.
- **Metrics endpoint**: implemented via HTTP `/metrics`.

### TODO (Internal clients)

- [ ] Complete universal forwarding path to internal `KernelGateway` RPCs per RFC 0004 Appendix A.
- [ ] Reconcile/document the exact split of responsibilities between `system-api`, `kernel`, and `eigen-compiler` once forwarding is primary path.

### Configuration File (`config/server.yaml`)

- **Status**: Not the active canonical configuration mechanism for current implementation.
- Runtime configuration is currently environment-variable based (`SYSTEM_API_*`).

### TODO (Configuration)

- [ ] Introduce and adopt `config/server.yaml` (or update architecture docs to a finalized env-only contract) to avoid configuration drift.

## Inputs / Outputs

| **Input** | **Source** | **Current status** |
|---|---|---|
| Client gRPC Request | External client | Implemented. |
| API Key / Token | gRPC metadata (`authorization`) | Implemented in `static_token` mode; `allow_all` remains supported for local/dev. |
| JobSpec payload | Client request fields (`jobspec_yaml`, program fields) | Implemented validation + mapping checks. |
| Security Context | gRPC metadata (`x-eigen-*`, `traceparent`) | Parsed at ingress; partial downstream propagation enforcement in current direct service behavior. |

---
| **Output** | **Destination** | **Current status** |
|---|---|---|
| gRPC Response | Client | Implemented. |
| Internal gRPC Request | Kernel/Compiler | Partially implemented relative to RFC target; not universal path in current runtime. |
| Security Metadata | Internal headers | RFC/ADR-required, but currently only partially represented in active `system-api` execution model. |
| Metrics & Logs | Prometheus / log sink | Implemented (`/metrics`, structured logs). |

## Storage / State

Current implementation is **not fully stateless**:

- In-memory job registry and lifecycle updates are maintained in service process.
- In-memory idempotency map is maintained.
- No durable persistence in `system-api` for these records.

This differs from the long-term target where Kernel/QFS own authoritative state.

### TODO (Storage/State)

- [ ] Remove authoritative runtime state ownership from `system-api`; move to strict stateless API gateway behavior backed by Kernel/QFS.
- [ ] If temporary caches remain (token/device/rate-limit), document explicit TTLs and consistency guarantees.

## Failure Modes

Implemented and aligned behaviors:

| **Failure** | **Detection** | **Current handling** |
|---|---|---|
| Invalid/Malformed Request | Field validation | `INVALID_ARGUMENT` with structured details. |
| Authentication Failure | Auth check | `UNAUTHENTICATED`. |
| Authorization Failure | RBAC/permission check | `PERMISSION_DENIED`. |
| Payload/size issues | Validation limits | Rejected as `INVALID_ARGUMENT`. |
| Missing job/device | Lookup | `NOT_FOUND`. |
| Results requested too early | Lifecycle state check | `FAILED_PRECONDITION`. |

### TODO (Failure Modes)

- [ ] Reintroduce/confirm `UNAVAILABLE` and retry behavior against real downstream Kernel/Compiler outages when forwarding path is primary.
- [ ] Add explicit rate limiter implementation and `RESOURCE_EXHAUSTED` behavior (currently documented target, not fully enforced runtime contract).

## Observability

### Metrics (implemented)

- `/metrics` endpoint is implemented.
- Request/latency/in-flight/authz-denied style instrumentation is present in service observability module.

### Logs (implemented)

- Structured logs include `service=system-api`, method, request context, and trace correlation fields.

### Traces (implemented at ingress, partial end-to-end by architecture intent)

- `traceparent` and trace identifiers are parsed/extracted at boundary and logged.

### TODO (Observability)

- [ ] Publish and freeze exact metric names/label schema used in code as normative contract in `docs/reference/*`.
- [ ] Add explicit conformance tests that assert end-to-end trace/security-header propagation through real system-api → kernel → downstream calls.

## RFC / ADR cross-check

Checked against:

- RFC 0002 (architecture boundaries)
- RFC 0004 (public gRPC API)
- RFC 0008 (observability MVP)
- RFC 0009 (security/isolation MVP)
- ADR 0002 (MVP1 contract baseline)
- ADR 0012 (explainability API contract)
- ADR 0018 (API/contract versioning policy)

Alignment summary:

- Public gRPC surface and error-model direction are implemented and extended safely.
- Explainability endpoint exists (post-RFC0004 additive evolution).
- Observability boundary exists (`/metrics`, structured logs, trace context parsing).
- Main gap to RFC architecture target: System API still contains in-process lifecycle/state behavior instead of being a thin, always-forwarding gateway.

### TODO (RFC/ADR closure)

- [ ] Add explicit matrix table (`RFC/ADR requirement` → `implemented in code` → `gap/todo`) and keep it versioned per release phase.
- [ ] For each non-implemented RFC/ADR item, track corresponding issue IDs directly in this document.

## Implementation Notes for MVP (actual as-is)

1. gRPC server is the primary and implemented interface.
2. Auth modes are intentionally lightweight (`allow_all`, `static_token`) for MVP/dev ergonomics.
3. Validation and gRPC status mapping are implemented.
4. Device APIs are functional but still minimal/stub-like in returned inventory semantics.
5. Job lifecycle APIs are functionally implemented with in-memory modeled execution progression.

### TODO (Implementation notes)

- [ ] Deliver production-grade device inventory/reservation integration with real Resource Manager/Kernel state.
- [ ] Eliminate skeleton/stub wording and implementation debt once internal forwarding architecture is fully enforced.
