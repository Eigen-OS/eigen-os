# Eigen OS Client SDKs

- **Document status:** Normative
- **Subsystem:** Client SDKs / CLI
- **Applies to:** SDKs, CLI, integration clients
- **Compatibility target:** Eigen OS `1.x` public API (`eigen.api.v1`)
- **Last updated:** 2026-05-25

This document is the canonical specification of the Eigen OS Client SDK layer. It separates:

- **Normative contract requirements** (what SDKs MUST implement to be conformant),
- **Current implementation status** (what exists in this repository today),
- **Planned / deferred items** (explicitly non-normative until implemented + released).

The SDK layer is **not** the source of truth for server contracts; it MUST track:

- `docs/reference/api/grpc-public.md`
- `docs/reference/jobspec.md`
- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`
- `docs/architecture/contract-map.md`
- `docs/architecture/data-flow.md`

---

## 1. Purpose

Eigen OS Client SDKs provide standardized client interfaces for interacting with the Eigen OS distributed hybrid quantum-classical runtime.

The SDK layer abstracts:

- transport protocols (gRPC first; REST optional),
- authentication and metadata propagation,
- JobSpec packaging and submission,
- job lifecycle and result retrieval,
- device discovery and reservation,
- deterministic error semantics and retry guidance,
- observability integration (tracing/logging/metrics hooks),
- compatibility negotiation and version pinning.

SDKs are intended for:

- research environments,
- production orchestration systems,
- ML/AI pipelines,
- CI/CD and automation,
- notebook/IDE integrations.

---

## 2. Scope and Non-Goals

### 2.1 SDK responsibilities (normative)

SDKs MUST provide:

- job submission (JobSpec-driven),
- job lifecycle management (polling + streaming updates),
- result retrieval (including artifact references),
- device interactions (list/status/details/reserve),
- authentication + authorization metadata injection,
- deterministic error mapping and typed exceptions,
- deadline/timeout propagation,
- trace propagation (W3C TraceContext),
- bounded and safe client-side observability hooks.

### 2.2 Non-goals

SDKs MUST NOT:

- execute user quantum programs locally as an alternative to Eigen OS (except optional local *validation-only* tools),
- bypass Eigen OS validation or isolation,
- directly access quantum hardware providers (all provider access is via Eigen OS runtime services),
- implement server-side scheduling, compilation determinism, or policy decisions,
- embed transport-layer errors inside application payloads (errors are transport status + structured details).

---

## 3. Supported SDKs and Current Status

### 3.1 SDK portfolio (target)

| **SDK** | **Target role** | **Status** |
|---|---|---|
| **CLI** | Reference client + automation | **Partially implemented** (repository) |
| **Python SDK** | Primary reference SDK | Planned |
| **Rust SDK** | High-performance integration | Planned |
| **JavaScript/TypeScript SDK** | Node + browser integrations | Planned |
| Go SDK | Infra/ops ecosystems | Deferred |
| Java SDK | Enterprise integrations | Deferred |

### 3.2 Conformance requirement

All released SDKs MUST expose **equivalent semantics** for the same Eigen OS API version:

- same lifecycle concepts,
- same idempotency expectations,
- same error categories,
- same retryability guidance,
- same metadata propagation requirements.

Language idioms may differ; semantics MUST NOT.

---

## 4. Contract Anchors and Versioning

### 4.1 Public API contract anchor

SDKs MUST implement the public API as defined by the **proto source of truth**:

- Namespace: `eigen.api.v1`
- Contract stability: breaking changes require a new MAJOR API package/version.

SDKs MUST NOT “invent” new public semantics not reflected in `grpc-public.md` and the `.proto` files.

### 4.2 JobSpec contract anchor

SDKs MUST support JobSpec as defined in:

- `docs/reference/jobspec.md`

JobSpec is the canonical input contract for packaging, reproducibility, and auditability.

### 4.3 Error contract anchor

SDKs MUST implement the error model as defined in:

- `docs/reference/error-model.md`
- `docs/reference/error-mapping.md`

---

## 5. Transport Architecture

### 5.1 Mandatory transport hierarchy

| **Priority** | **Transport** | **Requirement** |
|---|---|---|
| Primary | **gRPC** | MUST be supported by all SDKs |
| Secondary | REST | MAY be supported (optional) |
| Streaming alternative | WebSocket/SSE | MAY be supported (optional) |

### 5.2 Current repository state

Implemented now:

- gRPC transport to `eigen.api.v1`,
- server-streaming job updates (`StreamJobUpdates`),
- status/results polling,
- CLI-based submission flows.

Not implemented as a released SDK feature:

- REST transport fallback,
- automatic transport downgrade,
- WebSocket real-time transport.

---

## 6. Authentication, Authorization, and Metadata Propagation

### 6.1 TLS

SDKs MUST use TLS for all public network calls.

### 6.2 Auth model (public)

SDKs MUST support attaching credentials via request metadata:

- **Bearer token** (JWT/OAuth2 access token) in metadata.
- Token refresh helpers MAY exist, but the SDK MUST at least allow the user to provide a token and reconfigure it.

### 6.3 Required metadata keys (normative)

SDKs MUST support (and propagate) these metadata keys:

- `authorization` — bearer token (if applicable),
- `traceparent` — W3C TraceContext parent,
- `x-client-request-id` — client idempotency / correlation key (bounded),
- `x-eigen-tenant` — tenant context (if applicable in deployment),
- `x-eigen-project` — project context (if applicable in deployment).

SDKs MUST NOT emit unbounded identifiers as metadata.

### 6.4 Idempotency rule (normative)

For operations that create resources (e.g., job submission), SDKs MUST support a client-provided idempotency/correlation key using:

- `x-client-request-id` metadata (preferred),
- OR a request field **only if** the public proto adds such a field in a future version.

Retries MUST reuse the same idempotency key for the same logical operation.

---

## 7. Public API Surface (SDK-facing)

> The proto files are the source of truth. This section is a semantic summary.

### 7.1 JobService (public)

SDKs MUST support:

- `SubmitJob(SubmitJobRequest) -> SubmitJobResponse`
- `GetJobStatus(GetJobStatusRequest) -> GetJobStatusResponse`
- `CancelJob(CancelJobRequest) -> CancelJobResponse`
- `StreamJobUpdates(StreamJobUpdatesRequest) -> stream StreamJobUpdatesResponse`
- `GetJobResults(GetJobResultsRequest) -> GetJobResultsResponse`
- `GetDispatchRationale(GetDispatchRationaleRequest) -> GetDispatchRationaleResponse` (if present in proto)

### 7.2 DeviceService (public)

SDKs MUST support:

- `ListDevices(ListDevicesRequest) -> ListDevicesResponse`
- `GetDeviceDetails(GetDeviceDetailsRequest) -> GetDeviceDetailsResponse`
- `GetDeviceStatus(GetDeviceStatusRequest) -> GetDeviceStatusResponse`
- `ReserveDevice(ReserveDeviceRequest) -> ReserveDeviceResponse`

### 7.3 KnowledgeBaseService (public, if enabled in deployment)

If `KnowledgeBaseService` is part of the deployed public surface, SDKs SHOULD support it, but it MAY be shipped as a separate optional module/package.

---

## 8. Job Submission and Packaging

### 8.1 Canonical input: JobSpec (`job.yaml`)

SDKs MUST accept JobSpec as input (file or in-memory object) and perform deterministic packaging according to `docs/reference/jobspec.md`.

SDKs MUST support the JobSpec program source modes:

- `path` (file-backed),
- `inline`,
- `uri` (remote artifact reference),

while enforcing mutual exclusivity.

If a deployment disables a mode (e.g., inline submission), SDKs MUST surface the server rejection as a structured error without attempting to “work around” the policy.

### 8.2 Deterministic packaging (normative)

SDK packaging MUST:

- normalize paths (no `..`, no absolute paths),
- normalize line endings for hashing when specified by JobSpec packaging rules,
- compute and record stable hashes where required by the packaging rules,
- avoid embedding large artifacts inline when a reference mechanism is required.

### 8.3 Submission semantics

`SubmitJob` MUST:

- propagate `traceparent` and auth metadata,
- attach `x-client-request-id` if provided,
- enforce a request deadline (caller-provided or SDK default),
- return the server-assigned `job_id` and initial status.

---

## 9. Lifecycle Management

### 9.1 Polling

SDKs MUST support `GetJobStatus(job_id)` polling.

SDKs SHOULD provide helpers:

- `wait_for_terminal(job_id, timeout)` (implemented client-side),
- `wait_for_state(job_id, desired_state, timeout)`.

### 9.2 Streaming updates

SDKs MUST support `StreamJobUpdates` as the preferred mechanism when available.

SDKs MUST support resume semantics if the proto supports `last_event_seq` (or equivalent).

### 9.3 Cancellation

SDKs MUST support `CancelJob(job_id)` and MUST document that cancellation is best-effort depending on server state.

---

## 10. Result Retrieval and Artifacts

### 10.1 GetJobResults

SDKs MUST support retrieving results via `GetJobResults(job_id)`.

If results contain large payloads, SDKs MUST support resolving artifact references (e.g., QFS refs) via:

- a dedicated artifact download helper (if the server provides an API),
- OR by returning the reference to the caller in a typed way.

SDKs MUST NOT assume that large artifacts are embedded inline.

### 10.2 Error visibility for async failures

If a job ends in `ERROR`, SDKs MUST expose:

- stable machine-readable `error_code` (when present),
- human-readable `error_summary`,
- durable `error_details_ref` (when present),
- and must preserve the underlying gRPC status + structured details for synchronous calls.

---

## 11. Error Handling Contract (SDK-facing)

### 11.1 Canonical transport semantics (normative)

SDKs MUST treat failures as:

- gRPC status code (primary),
- `google.rpc.Status` details (structured semantics),
- stable reason codes (`google.rpc.ErrorInfo.reason`) when provided.

SDKs MUST NOT rely on ad-hoc `success=false` payloads.

### 11.2 Typed SDK error categories

SDKs MUST expose a stable error taxonomy mapped from canonical gRPC statuses:

| **SDK category** | **Canonical source** |
|---|---|
| `ValidationError` | `INVALID_ARGUMENT` (+ `BadRequest`) |
| `AuthenticationError` | `UNAUTHENTICATED` |
| `AuthorizationError` | `PERMISSION_DENIED` |
| `NotFoundError` | `NOT_FOUND` |
| `PreconditionError` | `FAILED_PRECONDITION` |
| `ResourceExhaustedError` | `RESOURCE_EXHAUSTED` (+ `RetryInfo`) |
| `UnavailableError` | `UNAVAILABLE` (+ `RetryInfo`) |
| `TimeoutError` | `DEADLINE_EXCEEDED` |
| `ConflictError` | `ABORTED` / concurrency conflicts |
| `InternalError` | `INTERNAL` |
| `CancelledError` | `CANCELLED` |

SDKs SHOULD also provide access to raw structured details for advanced clients.

### 11.3 Retry guidance (normative)

SDKs MUST implement retry behavior consistent with `error-model.md`:

- Typically retryable: `UNAVAILABLE`, `RESOURCE_EXHAUSTED`, `ABORTED`, `DEADLINE_EXCEEDED` (policy-dependent)
- Conditionally retryable: `FAILED_PRECONDITION`, `NOT_FOUND` (deployment semantics)
- Typically non-retryable: `INVALID_ARGUMENT`, `UNIMPLEMENTED`, `PERMISSION_DENIED`

If SDKs perform retries automatically, they MUST:

- reuse `x-client-request-id`,
- respect caller deadlines,
- apply bounded exponential backoff,
- stop on non-retryable codes,
- expose retry attempts and final outcome to the caller.

---

## 12. Deadlines and Timeouts

SDKs MUST:

- allow per-call deadlines,
- provide sane defaults (bounded),
- propagate deadlines to the server (gRPC deadlines),
- avoid indefinite blocking on streaming calls (require caller cancellation or deadline).

---

## 13. Observability (Client-side)

### 13.1 Tracing (normative)

SDKs MUST support W3C TraceContext propagation:

- inject/propagate `traceparent`,
- generate a new trace if none is provided (optional, but recommended),
- provide span naming conventions for SDK operations (recommended).

### 13.2 Logging hooks (normative)

SDKs MUST allow structured logging integration and MUST include these fields when logging SDK-level events:

- `timestamp`
- `level`
- `trace_id` (if tracing enabled)
- `span_id` (if tracing enabled)
- `operation` (RPC/method name)
- `message`

Optional fields:

- `job_id`
- `device_id`

SDKs MUST avoid logging secrets and raw payloads by default.

### 13.3 SDK metrics (optional)

SDKs MAY expose client-side metrics (recommended), but MUST obey bounded cardinality rules (no job_id labels, no trace_id labels).

Suggested metric names (non-normative until implemented):

- `eigen_sdk_requests_total`
- `eigen_sdk_request_duration_seconds`
- `eigen_sdk_retries_total`

---

## 14. Security Requirements (Client-side)

SDKs MUST:

- store credentials securely (at minimum: avoid accidental logging),
- support TLS verification,
- support disabling insecure transports,
- validate and bound user-provided metadata (prevent unbounded headers/labels),
- apply payload size limits for client-side packaging to prevent accidental oversized submits.

Credential vault/keychain integration is optional and deferred.

---

## 15. Testing and Conformance

SDK implementations MUST include:

| **Test type** | **Requirement** |
|---|---|
| Unit tests | MUST |
| Integration tests against a real server or harness | MUST |
| Contract tests (golden fixtures where applicable) | MUST |
| Security tests (no secret logging, TLS behavior) | SHOULD |
| Performance/regression tests | SHOULD |

Conformance MUST verify:

- correct mapping to canonical gRPC statuses,
- structured detail parsing,
- retryability rules,
- idempotency key reuse,
- trace propagation and metadata injection,
- JobSpec packaging determinism.

---

## 16. Configuration

### 16.1 Configuration precedence (normative)

1. Explicit client configuration (constructor / flags)
2. Environment variables
3. Config file
4. Built-in defaults

### 16.2 Standard environment variables (recommended)

- `EIGEN_ENDPOINT`
- `EIGEN_TOKEN`
- `EIGEN_TIMEOUT`
- `EIGEN_LOG_LEVEL`

---

## 17. Compatibility Policy

SDKs MUST follow semantic versioning.

### 17.1 API compatibility

SDKs MUST be compatible with declared Eigen OS API versions they claim to support.

Breaking changes in the public API require:

- a new API major version (`eigen.api.v2`, etc.),
- SDK major version changes if behavior changes,
- migration notes.

### 17.2 Minimum supported platforms (targets)

These are targets and may be tightened by release notes:

- Eigen OS: `1.x` public API surface
- Python: `3.12+` (target)
- Rust: `1.75+` (target; adjust to actual toolchain policy)

---

## 18. Current Repository Status Summary

### Implemented (repository)

- public gRPC APIs (`eigen.api.v1`) are present,
- JobService + DeviceService are usable via gRPC,
- streaming job updates exist,
- service-side validation exists,
- trace propagation exists,
- CLI exists but is not yet a fully productized SDK.

### Planned

- official Python/Rust/TS SDK packages,
- optional REST transport,
- circuit breaker and retry libraries with shared policy,
- client-side preflight validation helpers,
- SDK-side metrics packages,
- IDE/notebook adapters.

---

## 19. Invariants (normative)

1. SDK semantics are consistent across languages for the same API version.
2. SDKs do not bypass server validation or isolation.
3. Errors are gRPC-status-first with structured details.
4. Idempotency/correlation keys are supported and reused on retries.
5. Tracing metadata (`traceparent`) is propagated end-to-end.
6. Client observability is bounded and safe (no unbounded labels/headers).
7. JobSpec packaging is deterministic and path-safe.

---