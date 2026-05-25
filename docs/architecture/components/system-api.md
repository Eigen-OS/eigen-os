# System API

- **Phase:** MVP → MVP-3 gateway hardening baseline
- **Status snapshot date:** 2026-05-25
- **Source alignment:** RFC 0002, RFC 0004, RFC 0008, RFC 0009, ADR 0002, ADR 0012, ADR 0018, runtime API contracts, System API implementation state

## Responsibility

The System API is the sole public ingress boundary for Eigen OS during MVP and MVP-3 runtime evolution.

It provides:

- public API exposure,
- authentication and authorization,
- request validation,
- lifecycle ingress handling,
- observability boundary enforcement,
- security-context propagation,
- public contract stability.

Current implementation combines:

- public gRPC API handling,
- lightweight runtime lifecycle orchestration,
- in-memory job state tracking,
- partial forwarding behavior,
- structured observability instrumentation.

The long-term architecture target is a strictly stateless public gateway that forwards execution responsibility to Kernel/QRTX and associated runtime services.

---

# Responsibility Scope

## Implemented now

### Public gRPC ingress

System API exposes the public Eigen OS gRPC API surface.

Implemented services:

### JobService

- `SubmitJob`
- `GetJobStatus`
- `CancelJob`
- `StreamJobUpdates`
- `GetJobResults`
- `GetDispatchRationale`

### DeviceService

- `ListDevices`
- `GetDeviceDetails`
- `GetDeviceStatus`
- `ReserveDevice`

System API runs on:

- `SYSTEM_API_GRPC_BIND`

Default:

```text
0.0.0.0:50051
```

---

### Authentication and authorization

Implemented authentication modes:

- `allow_all`
- `static_token`

Authorization enforcement supports coarse-grained RBAC permissions.

Implemented permission categories include:

- `jobs:submit`
- `jobs:read`
- `devices:list`
- `devices:reserve`

---

### Request validation

Implemented validation includes:

- malformed request rejection,
- payload-size enforcement,
- JobSpec validation,
- request field validation,
- canonical gRPC error mapping.

Implemented gRPC error classes include:

- `INVALID_ARGUMENT`
- `UNAUTHENTICATED`
- `PERMISSION_DENIED`
- `NOT_FOUND`
- `FAILED_PRECONDITION`

---

### Runtime lifecycle handling (partial architecture divergence)

Current implementation maintains:

- in-memory job registry,
- lifecycle progression,
- modeled runtime execution flow,
- local lifecycle update streaming.

Current behavior is not yet a strict forwarding-only gateway.

---

### Observability boundary

Implemented observability features include:

- structured JSON logs,
- request correlation metadata,
- trace context extraction,
- Prometheus-compatible `/metrics`,
- runtime request instrumentation.

---

### Security-context handling

Ingress metadata parsing currently supports:

- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

Partial downstream propagation exists.

Strict end-to-end propagation guarantees are not yet fully enforced across all internal runtime hops.

---

### Required target responsibility (architecture baseline)

The final System API SHALL provide:

#### Stateless gateway behavior

- strict forwarding to Kernel/QRTX,
- no authoritative lifecycle ownership,
- no execution-state persistence,
- deterministic request routing.

#### Public contract enforcement

- canonical public API validation,
- API-version negotiation,
- schema compatibility enforcement,
- backward-compatible API evolution.

#### Security boundary enforcement

- authentication,
- authorization,
- policy enforcement,
- tenant boundary isolation,
- audit metadata propagation.

#### Runtime ingress orchestration

- job submission ingress,
- device management ingress,
- dispatch rationale access,
- explainability access,
- runtime policy attachment.

#### Observability ingress

- distributed trace propagation,
- telemetry correlation,
- audit-safe request logging,
- ingress metrics generation.

---

## Architecture Position

System API is the mandatory public ingress layer for Eigen OS.

It integrates with:

- eigen-kernel
- eigen-compiler
- driver-manager
- QFS
- observability subsystem
- security-isolation subsystem
- future neuro-symbolic-core
- future knowledge-base
- future adaptive-runtime services

System API is responsible for:

- public API stability,
- ingress security,
- request normalization,
- runtime correlation propagation,
- deterministic external contract enforcement.

---

## Interfaces

### 1. Public gRPC Interfaces

#### Implemented now

Defined in:

```text
proto/eigen/api/v1/*.proto
```

Implemented services:

#### JobService

- SubmitJob
- GetJobStatus
- CancelJob
- StreamJobUpdates
- GetJobResults
- GetDispatchRationale

#### DeviceService

- ListDevices
- GetDeviceDetails
- GetDeviceStatus
- ReserveDevice

---

#### Current runtime behavior

`StreamJobUpdates` currently streams from local in-memory lifecycle state.

`GetDispatchRationale` exists as an additive extension relative to original MVP RFC 0004 surface.

---

#### Required target gRPC behavior

System API SHALL provide:

- strict gateway forwarding,
- stable API versioning,
- backward-compatible contracts,
- deterministic error semantics,
- explainability contract propagation.

---

### 2. REST Interfaces

#### Implemented now

No production REST API adapter is currently implemented.

No `/api/v1/*` runtime REST surface is active.

---

#### Required target REST interfaces

**Job endpoints**

- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/cancel`
- `GET /api/v1/jobs/{job_id}/results`

**Device endpoints**

- `GET /api/v1/devices`
- `GET /api/v1/devices/{device_id}`
- `POST /api/v1/devices/{device_id}/reserve`

**Runtime observability endpoints**

- `GET /metrics`
- `GET /health`
- `GET /ready`
- `GET /live`

---

### 3. Internal Runtime Interfaces

#### Implemented now

Partial integration exists with:

- kernel lifecycle flows,
- runtime lifecycle simulation,
- observability instrumentation.

Current implementation does not universally forward all requests to Kernel/QRTX.

----

#### Required target integrations

**Kernel Gateway**

System API SHALL forward lifecycle operations to:

- `KernelGatewayService`

Expected operations:

- `EnqueueJob`
- `GetJobStatus`
- `CancelJob`
- `GetJobResults`

**Compiler integration**

System API SHALL integrate with:

- compilation lifecycle flows,
- validation/error propagation,
- dispatch rationale retrieval.

**Runtime propagation**

System API SHALL propagate:

- security metadata,
- trace metadata,
- request lineage identifiers,
- replay correlation identifiers.

---

### 4. Configuration Interfaces

#### Implemented now

Runtime configuration is environment-variable based.

Implemented configuration namespace:

```text
SYSTEM_API_*
```

---

#### Required target configuration model

System API SHALL support:

- structured config files,
- environment overrides,
- versioned config schema,
- deployment-safe defaults,
- runtime policy attachment.

Potential canonical configuration target:

```text
config/server.yaml
```

---

## Inputs / Outputs

### Inputs

#### Implemented now

**Public client inputs**

- gRPC requests
- authorization metadata
- JobSpec payloads
- device-management requests

**Metadata inputs**

- `authorization`
- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

**Validation inputs**

- source payloads
- embedded JobSpec YAML
- runtime options
- dispatch metadata

---

#### Required target inputs

**Runtime ingress metadata**

- tenant metadata
- policy metadata
- replay identifiers
- optimizer hints
- explainability context

**Distributed tracing metadata**

- trace lineage
- correlation IDs
- runtime propagation headers
- deterministic replay markers

---

### Outputs

#### Implemented now

Current outputs include:

- public gRPC responses,
- lifecycle updates,
- structured logs,
- metrics payloads,
- validation errors,
- authorization failures.

---

#### Required target outputs

**Runtime forwarding outputs**

- KernelGateway RPCs
- runtime lifecycle requests
- compiler forwarding requests
- explainability retrieval requests

**Observability outputs**

- distributed trace metadata
- ingress metrics
- structured audit logs
- replay correlation markers

**Security outputs**

- propagated auth context
- authorization decisions
- sanitized telemetry
- policy metadata

---

## Storage / State

### Implemented now

Current implementation maintains:

- in-memory job registry,
- lifecycle state,
- idempotency tracking,
- request correlation state.

No durable persistence layer exists in System API.

This differs from target architecture where authoritative runtime state belongs to:

- Kernel/QRTX
- QFS
- runtime persistence layers

---

### Required target storage behavior

System API SHALL become:

- stateless,
- replay-safe,
- horizontally scalable,
- forwarding-only for runtime ownership.

Allowed transient state MAY include:

- token caches,
- rate-limit state,
- bounded request deduplication caches.

Any retained state SHALL define:

- TTL,
- consistency guarantees,
- replay semantics,
- failure behavior.

---

## Failure Modes

### Implemented now

#### Validation failures

Handled via:
- canonical request validation

Outputs:

- `INVALID_ARGUMENT`

#### Authentication failures

Outputs:

- `UNAUTHENTICATED`

#### Authorization failures

Outputs:

- `PERMISSION_DENIED`

#### Missing resources

Outputs:

- `NOT_FOUND`

#### Invalid lifecycle access

Outputs:

- `FAILED_PRECONDITION`

---

### Required target failure taxonomy

#### Downstream runtime failures

- Kernel unavailable
- compiler unavailable
- driver-manager unavailable
- timeout propagation failure

#### Capacity failures

- rate-limit exceeded
- ingress overload
- resource exhaustion

#### Propagation failures

- trace metadata loss
- auth-context propagation failure
- replay correlation inconsistency

---

### Required recovery behavior

System API SHALL support:

- retry-safe forwarding,
- deterministic error mapping,
- bounded retries,
- circuit breakers,
- replay-safe request handling,
- graceful degradation.

---

## Observability

### Metrics

#### Implemented now

Implemented metrics include request and authorization instrumentation.

Prometheus-compatible `/metrics` endpoint exists.

---

#### Required target metrics

**API metrics**

- `eigen_api_requests_total`
- `eigen_api_request_duration_seconds`
- `eigen_api_requests_inflight`
- `eigen_api_authz_denied_total`

**Gateway metrics**

- forwarding latency
- downstream error rate
- retry count
- propagation failures

**Security metrics**

- auth failures
- permission denials
- validation failures
- policy rejections

---

### Logs

#### Implemented now

Structured JSON logs include:

- service=system-api
- request identifiers
- trace correlation fields
- method names
- lifecycle metadata

---

#### Required target logging

System API SHALL emit:

- ingress audit logs,
- forwarding lifecycle logs,
- propagation diagnostics,
- replay correlation logs,
- policy evaluation logs.

---

### Traces

#### Implemented now

`traceparent` parsing and trace extraction are implemented at ingress.

---

#### Required target tracing

Distributed tracing SHALL span:

- System API
- kernel
- compiler
- driver-manager
- adaptive runtime components

Required trace metadata:

- request lineage
- job lineage
- dispatch rationale IDs
- replay identifiers
- auth context propagation status

---

### Health Checks

#### Implemented now

Basic runtime health behavior exists through service/runtime infrastructure.

---

#### Required target health model

**Gateway health**

- ingress readiness
- forwarding-path health
- downstream connectivity
- auth subsystem health

**Runtime health**

- request backlog
- propagation integrity
- replay consistency
- overload state

---

### Dashboards and Alerts

#### Implemented now

Metrics and structured logs are available through current observability tooling.

---

#### Required target dashboards

**API dashboards**

- ingress throughput
- request latency
- downstream failures
- auth failures
- request distribution

**Alert categories**

- forwarding failures
- downstream unavailability
- propagation loss
- overload conditions
- replay inconsistencies
- security anomalies

---

## Security and Compliance

### Implemented now

Current security baseline includes:

- explicit auth modes,
- coarse-grained RBAC,
- payload validation,
- structured request telemetry.

---

### Required target controls

#### Security controls

- OIDC/JWT federation
- policy-driven authorization
- tenant isolation
- ingress rate limiting
- audit-grade telemetry

#### Compliance controls

- deterministic replay support
- immutable audit references
- versioned API contracts
- traceable ingress lineage

---

## Alignment Summary

### Implemented and aligned

The following capabilities are implemented:

- public gRPC ingress,
- validation/error mapping,
- authentication and coarse authorization,
- structured observability boundary,
- metrics endpoint,
- trace-context parsing,
- explainability endpoint support.

### Remaining architecture gaps

The following architecture targets remain not fully implemented:

- strict stateless gateway behavior,
- universal forwarding to Kernel/QRTX,
- durable downstream propagation guarantees,
- REST parity layer,
- production-grade rate limiting,
- distributed replay-safe forwarding guarantees,
- fully centralized runtime ownership outside System API.

These gaps remain explicitly preserved as required future work to prevent architecture scope loss.
