# System API

- **Phase:** MVP → MVP-3 gateway hardening baseline
- **Document status:** Normative public-ingress contract + implementation snapshot
- **Contract type:** Stable public gateway contract (public surface), with explicit target-architecture requirements
- **Contract version:** `1.0.0`
- **Status snapshot date:** 2026-05-25
- **Source alignment:** RFC 0002, RFC 0004, RFC 0008, RFC 0009, ADR 0002, ADR 0012, ADR 0018, runtime API contracts, System API implementation state
**Applies to:** system-api service, SDK/CLI clients, public gRPC consumers, future REST adapter

---

## 0. Purpose

The System API is the **sole public ingress boundary** for Eigen OS (MVP and MVP-3 evolution). It provides a stable external contract for:

- public API exposure,
- authentication and authorization,
- request validation and normalization,
- lifecycle ingress handling,
- observability boundary enforcement,
- security-context propagation,
- compatibility governance and error semantics.

**Important:** Current implementation includes **some lifecycle/state** handling for MVP convenience. The **target architecture** requires the System API to be a **strictly stateless gateway** that forwards authoritative lifecycle ownership to Kernel/QRTX.

This document is normative for:

- public contract semantics,
- security/validation behavior at ingress,
- error/status rules,
- propagation and observability rules,
- compatibility constraints.

---

## 1. Contract Versioning

### 1.1 Contract marker metric (recommended)

Conformant deployments SHOULD export:

```text
eigen_system_api_contract_info{version="1.0.0"} 1
```

---

### 1.2 SemVer policy

#### MAJOR

- breaking changes to public RPC semantics
- removal/rename of RPCs, messages, fields
- incompatible error mapping changes
- incompatible authentication/authorization semantics
- incompatible metadata propagation requirements

#### MINOR

- additive fields (optional only)
- additive RPCs
- additive bounded-cardinality labels
- additive auth modes (without changing semantics of existing modes)

#### PATCH

- docs fixes
- performance fixes without semantic change
- bug fixes that restore intended deterministic behavior

---

## 2. Responsibilities

### 2.0 Product 1.0 public envelope responsibilities

For Wave 1 public-boundary closure, the System API owns canonical envelope normalization for every public gRPC request. It MUST:

- normalize `ApiRequestEnvelope` from request payload, authenticated context, gRPC metadata, and transport deadline,
- validate `contract_version` before dispatching to Kernel/QRTX or any other internal service,
- reject malformed versions with `INVALID_ARGUMENT` plus `PUBLIC_CONTRACT_VERSION_MALFORMED` details and unsupported/incompatible versions with `FAILED_PRECONDITION` plus `PUBLIC_CONTRACT_VERSION_UNSUPPORTED` details,
- derive deterministic defaults for missing MVP-client envelope fields (`contract_version=1.0.0`, stable `req_<sha256-prefix>` request IDs, `tenant-default`, and `project-default`) before audit, idempotency, or internal forwarding,
- compute the `SubmitJob` idempotency digest from the normalized request and persist it with tenant/project scope, assigned `job_id`, and configurable TTL,
- purge expired idempotency records before comparison so same-key submissions after TTL create new jobs,
- enforce public payload limits before forwarding requests to internal services,
- emit public API contract marker metrics with bounded labels and request/trace correlation, including `SubmitJob` outcomes `accepted`, `replayed`, `conflict`, and `limit`,
- never leak raw internal exceptions, credentials, or provider details through public errors.

The public wire contract for these requirements is defined in `docs/reference/api/grpc-public.md`; this component document describes ownership only.

For W1-04, System API also owns JobSpec 1.0 normalization at ingress. It accepts native `eigen.os/v1` payloads and documented `eigen.os/v0.1` migration inputs, computes the canonical JobSpec digest, attaches package metadata (`jobspec_digest`, `jobspec_version`, `source_sha256`), and maps scheduling/security/observability sections into bounded internal metadata without adding internal-only fields to the public protobuf surface. The source-of-truth contract is `docs/reference/jobspec.md` and the schema is `docs/reference/schemas/jobspec-1.0.schema.json`.

---

### 2.1 Implemented now (MVP truth)

System API currently provides:

- **Public gRPC ingress** for `eigen.api.v1`.
- **Authn/authz enforcement** using env-configured modes and coarse RBAC.
- **Request validation** including payload limits and schema checks.
- **Partial lifecycle handling:**
    - in-memory job registry,
    - local lifecycle progression,
    - local update streaming for `StreamJobUpdates`.
- **Observability boundary:**
    - structured JSON logs,
    - trace context extraction,
    - Prometheus `/metrics`,
    - request instrumentation.
- **Security metadata parsing:**
    - `authorization`,
    - `x-eigen-sub`,
    - `x-eigen-roles`,
    - `x-eigen-tenant`,
    - `traceparent`.

---

### 2.2 Required target responsibilities (architecture baseline)

The System API SHALL evolve into a **strict gateway** providing:

#### Stateless gateway behavior

- strict forwarding to Kernel/QRTX for lifecycle ownership,
- no authoritative job state persistence,
- no execution orchestration logic,
- deterministic request routing.

#### Public contract enforcement

- canonical request validation and normalization,
- API version negotiation / compatibility enforcement,
- backward-compatible evolution discipline,
- consistent error semantics and structured details.

#### Security boundary enforcement

- production-grade identity (OIDC/JWT) in addition to dev modes,
- policy-driven authorization,
- tenant isolation enforcement at ingress,
- audit-safe security context propagation.

#### Observability ingress

- distributed trace propagation end-to-end,
- audit-safe request logging,
- ingress telemetry and propagation integrity indicators.

---

## 3. Architecture Position

System API is the mandatory **public ingress** layer and the only externally reachable runtime component.

It integrates with:

- `eigen-kernel` (QRTX) via `KernelGatewayService` (target),
- `eigen-compiler`, `driver-manager` (indirectly via kernel in target model),
- QFS artifact layer (via kernel/QFS facade),
- observability subsystem,
- security-isolation subsystem,
- future: neuro-symbolic-core, knowledge-base, HWE, optimizer services.

#### Boundary invariants

- System API is the only public ingress.
- System API MUST NOT talk to vendor backends.
- System API MUST NOT execute user code.
- System API MUST enforce payload limits and validation before forwarding.
- System API MUST propagate trace context deterministically.

---

## 4. Public Interfaces

### 4.1 Public gRPC APIs (implemented)

Defined in: `proto/eigen/api/v1/*.proto`

#### JobService (public)

- `SubmitJob`
- `GetJobStatus`
- `CancelJob`
- `StreamJobUpdates`
- `GetJobResults`
- `GetDispatchRationale`

#### DeviceService (public)

- `ListDevices`
- `GetDeviceDetails`
- `GetDeviceStatus`
- `ReserveDevice`

**Notes**

- `GetDispatchRationale` is an additive extension relative to original MVP surface.
- `StreamJobUpdates` is currently implemented as poll/stream behavior backed by local state; target behavior forwards to kernel-owned event stream.

---

### 4.2 REST APIs (not implemented; target)

No production REST adapter is active today.

Target endpoints:

#### Jobs

- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/cancel`
- `GET /api/v1/jobs/{job_id}/results`
- `GET /api/v1/jobs/{job_id}/rationale` (optional)

#### Devices

- `GET /api/v1/devices`
- `GET /api/v1/devices/{device_id}`
- `GET /api/v1/devices/{device_id}/status`
- `POST /api/v1/devices/{device_id}/reserve`

#### Health / telemetry

- `GET /metrics`
- `GET /health`
- `GET /ready`
- `GET /live`

REST semantics MUST remain consistent with gRPC semantics (status codes, error model, idempotency behavior).

---

## 5. Core Ingress Semantics

### 5.1 Request validation (normative)

System API MUST validate before accepting/forwarding:

- required fields present,
- enum correctness,
- regex/range constraints,
- payload size limits,
- JobSpec mapping validity (when JobSpec is used),
- program source constraints (format rules, path rules, etc.),
- forbidden ambiguity (e.g., multiple program sources set at once).

Validation failures MUST return:

```text
INVALID_ARGUMENT
```

with structured violations where possible (`google.rpc.BadRequest` recommended).

---

### 5.2 Payload size limits (implemented baseline + target)

Implemented env limits:

- `SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES`
- `SYSTEM_API_MAX_JOBSPEC_YAML_BYTES`

Target additions (recommended):

- `SYSTEM_API_MAX_METADATA_BYTES`
- `SYSTEM_API_MAX_LABELS`
- `SYSTEM_API_MAX_ANNOTATIONS`
- `SYSTEM_API_MAX_PARAMETERS_BYTES`

Oversized payloads SHOULD return:

```text
RESOURCE_EXHAUSTED
```

or `INVALID_ARGUMENT` if treated as validation (choose one and keep consistent; target preference: `RESOURCE_EXHAUSTED` for size exhaustion).

---

### 5.3 Idempotency (target requirement)

System API SHOULD support idempotent submission using a client-supplied idempotency key.

Recommended metadata key:

- `x-eigen-idempotency-key`

Rules:

- same key + different request MUST return `FAILED_PRECONDITION`.
- records MUST be persisted with tenant/project scope, assigned `job_id`, and configurable TTL.

This is implemented in the MVP System API server for `SubmitJob`.

---

### 5.4 Deadline propagation

- Clients set gRPC deadlines.
- System API MUST propagate deadlines downstream.
- Long-running execution MUST NOT be represented as blocking RPC; it is asynchronous and observable via status/results APIs.

---

## 6. Authentication and Authorization

### 6.1 Implemented now

Auth modes:

- `SYSTEM_API_AUTH_MODE=allow_all`
- `SYSTEM_API_AUTH_MODE=static_token`
- `SYSTEM_API_AUTH_TOKEN=<token>`

`allow_all` is only acceptable for local/dev ingress bootstrap. Internal KB audit and retrieval helpers do not accept permissive fallback; missing security context or policy evidence MUST deny.

Coarse RBAC permissions:

- `jobs:submit`
- `jobs:read`
- `devices:list`
- `devices:reserve`

Failures:

- authn failure → `UNAUTHENTICATED`
- authz failure → `PERMISSION_DENIED`

---

### 6.2 Required target

System API SHALL support:

- OIDC/JWT validation (issuer/audience/expiry),
- tenant isolation at ingress,
- policy-driven RBAC/ABAC (versioned policy snapshots),
- sanitized security context propagation to kernel and observability.

Security metadata supported at ingress (current + target):

- `authorization`
- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

**Propagation guarantee (target):** forwarded security context MUST be deterministic and normalized (no uncontrolled user-provided headers forwarded beyond allowlist).

---

## 7. Runtime Lifecycle Handling

### 7.1 Implemented now (architecture divergence)

System API currently maintains:

- an in-memory job registry,
- lifecycle progression,
- local streaming updates.

This is acceptable for MVP but is **not** the target architecture.

---

### 7.2 Target behavior (normative)

System API SHALL forward lifecycle ownership to Kernel/QRTX:

- `SubmitJob` → `KernelGatewayService.EnqueueJob`
- `GetJobStatus` → `KernelGatewayService.GetJobStatus`
- `CancelJob` → `KernelGatewayService.CancelJob`
- `GetJobResults` → `KernelGatewayService.GetJobResults`
- `StreamJobUpdates` → kernel-owned stream / subscription API (or poll-stream wrapper).

System API MUST NOT invent or reinterpret lifecycle states.

Canonical client-visible states (from architecture contracts):

```text
PENDING → COMPILING → QUEUED → RUNNING → DONE | ERROR | CANCELLED
```

---

## 8. Dispatch Rationale / Explainability

### 8.1 Implemented now

`GetDispatchRationale` exists as an additive endpoint.

---

### 8.2 Target requirements

Rationale retrieval MUST:

- be replay-safe,
- include stable references (e.g., QFS refs) for large artifacts,
- avoid embedding oversized payloads,
- include policy and decision metadata without leaking secrets.

Recommended outputs:

- decision summary,
- candidate set (bounded),
- selected backend/device (if applicable),
- constraints applied,
- deterministic digest / lineage ref.

---

## 9. Observability Boundary

### 9.1 Implemented now

- structured JSON logs
- request correlation metadata
- trace context extraction (`traceparent`) from public metadata and `ApiRequestEnvelope`
- Prometheus `/metrics`, including the bounded public API contract marker counters

---

### 9.2 Target requirements

System API SHALL:

- propagate W3C TraceContext across downstream calls,
- preserve public ingress `traceparent` and derived `trace_id` in request logs and job correlation metadata,
- emit ingress spans and downstream forwarding spans,
- export ingress metrics including propagation failures and downstream error rates,
- ensure telemetry is safe (no secrets, bounded labels).

Recommended additional metrics (target):

- `eigen_api_requests_inflight`
- `eigen_api_forwarding_latency_seconds`
- `eigen_api_downstream_errors_total{service,code}`
- `eigen_api_propagation_failures_total{type}`

---

## 10. Error Model (Normative)

System API uses **gRPC status-first semantics**.

### 10.1 Canonical status rules

- `INVALID_ARGUMENT` — invalid request independent of runtime state
- `FAILED_PRECONDITION` — valid request blocked by runtime/system state
- `RESOURCE_EXHAUSTED` — quota/capacity/payload-size exhaustion (consistent usage required)
- `UNAVAILABLE` — transient downstream failure
- `DEADLINE_EXCEEDED` — timeout
- `NOT_FOUND` — missing resource
- `UNAUTHENTICATED` / `PERMISSION_DENIED` — authn/authz failure

---

### 10.2 Structured details (recommended)

- `google.rpc.BadRequest`
- `google.rpc.ErrorInfo`
- `google.rpc.ResourceInfo`
- `google.rpc.RetryInfo`

---

## 11. Storage / State

### 11.1 Implemented now

System API maintains:

- in-memory job registry,
- lifecycle state,
- idempotency-like tracking (limited),
- request correlation state.

No durable persistence exists in System API.

---

### 11.2 Required target state behavior

System API SHALL be:

- stateless,
- horizontally scalable,
- replay-safe.

Allowed transient state (bounded with TTL):

- token caches,
- rate-limit counters,
- bounded idempotency cache.

Any retained state MUST define:

- TTL,
- consistency guarantees,
- failure behavior,
- replay implications.

---

## 12. Configuration

### 12.1 Implemented now

Env-driven configuration namespace: `SYSTEM_API_*`

Key settings (observed/expected):

- `SYSTEM_API_GRPC_BIND` (default `0.0.0.0:50051`)
- `SYSTEM_API_AUTH_MODE`
- `SYSTEM_API_AUTH_TOKEN` (static_token mode)
- `SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES`
- `SYSTEM_API_MAX_JOBSPEC_YAML_BYTES`

---

### 12.2 Target configuration model

System API SHOULD support:

- structured config files (e.g., `config/server.yaml`)
- env overrides
- versioned config schema
- safe defaults
- policy attachment config (auth provider, policy engine endpoints, etc.)

---

## 13. Failure Modes and Recovery

### 13.1 Implemented now

- validation failures → `INVALID_ARGUMENT`
- authn failures → `UNAUTHENTICATED`
- authz failures → `PERMISSION_DENIED`
- missing resources → `NOT_FOUND`
- invalid lifecycle access → `FAILED_PRECONDITION`

---

### 13.2 Target failure taxonomy

#### Downstream

- kernel unavailable
- compiler unavailable (if directly invoked in some paths)
- QFS unavailable (via kernel)
- timeout propagation failure

#### Capacity

- rate-limit exceeded
- ingress overload
- payload-size exhaustion

#### Propagation

- trace metadata loss
- auth-context propagation failure
- replay correlation inconsistency

---

### 13.3 Required recovery behavior (target)

System API SHALL support:

- retry-safe forwarding (bounded retries),
- circuit breakers for downstream services,
- deterministic error mapping,
- graceful degradation (explicitly defined),
- overload protection (rate limiting / backpressure).

---

## 14. CI and Conformance Requirements (Target)

CI SHOULD validate:

- required public RPC presence and proto compatibility (`buf lint`, `buf breaking`)
- validation behavior (golden tests for `INVALID_ARGUMENT`)
- authn/authz behavior (golden tests for `UNAUTHENTICATED` / `PERMISSION_DENIED`)
- metric presence and type stability
- trace propagation integrity (integration tests)
- idempotency behavior (when implemented)
- forwarding correctness to kernel (when gateway becomes strict)

---

## 15. Alignment Summary

#### Implemented and aligned

- public gRPC ingress
- validation and canonical error mapping
- authentication modes + coarse RBAC
- observability boundary (logs/metrics/trace extraction)
- device APIs and rationale endpoint support

#### Remaining gaps (required future work)

- strict stateless gateway behavior
- universal forwarding to Kernel/QRTX
- end-to-end propagation guarantees (security + replay markers)
- REST parity adapter
- production-grade rate limiting and overload protection
- idempotent submission contract
- forwarding-path conformance tests as kernel becomes authoritative

These gaps are intentionally preserved to prevent architecture scope loss while keeping the MVP implementation description truthful.

---

## Appendix A. Diagrams (normative)

### A.1 C4 Context — System API as the sole public ingress

![C4 Context](https://i.imgur.com/c8u41kL.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Ext["External"]
    SDK[SDK/CLI]
    Web[Public gRPC clients]
    IdP["OIDC IdP\n(Phase-1+)"]
  end

  subgraph Public["Public boundary"]
    API["System API\nAuthn/Authz/Validation\nObservability ingress"]
  end

  subgraph Core["Runtime core (internal)"]
    K["Kernel/QRTX\nKernelGatewayService"]
    QFS[(QFS)]
  end

  SDK --> API
  Web --> API
  IdP <--> API
  API --> K
  K --> QFS

  classDef boundary stroke-width:2px,stroke-dasharray: 5 5;
  class API boundary
```

</details>

---

### A.2 C4 Container — MVP vs Target forwarding model

![C4 Container](https://i.imgur.com/IAklit4.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph MVP["MVP (today)"]
    API1["System API\n- gRPC public surface\n- authn/authz\n- validation\n- partial lifecycle + local streaming"]
    K1["Kernel/QRTX\n(partial forwarding)"]
    API1 --> K1
  end

  subgraph Target["Target (MVP-3 / Phase-1+)"]
    API2["System API\nStrict stateless gateway\nForward-only"]
    K2["Kernel/QRTX\nAuthoritative lifecycle"]
    API2 -->|all lifecycle RPCs| K2
  end
```

</details>

---

### A.3 Ingress decision pipeline (status-first)

![Ingress decision pipeline](https://i.imgur.com/vNkJe2b.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Req[Incoming gRPC request] --> Parse["Parse + normalize metadata\n(allowlist)"]
  Parse --> V{"Validate request\n(schema + limits)"}
  V -- invalid --> IA["INVALID_ARGUMENT\n(+ BadRequest details)"]
  V -- ok --> A{Authn mode}
  A -->|allow_all| Z{Authz}
  A -->|static_token| T{Token valid?}
  A -->|"oidc/jwt (Phase-1+)"| J{"JWT valid?\niss/aud/exp"}
  T -- no --> UA1[UNAUTHENTICATED]
  T -- yes --> Z
  J -- no --> UA2[UNAUTHENTICATED]
  J -- yes --> Z
  Z -- deny --> PD["PERMISSION_DENIED\n(+ ErrorInfo.reason)"]
  Z -- allow --> F{Forward or local-handled?}
  F -->|target: always forward| FW[Forward to KernelGatewayService]
  F -->|MVP: some local lifecycle| L["Local state path\n(temporary)"]
```

</details>

----

### A.4 Sequence — SubmitJob end-to-end (target: strict forwarding)

![SubmitJob end-to-end](https://i.imgur.com/Fn3OdfV.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client SDK/CLI
  participant API as System API
  participant K as KernelGatewayService (QRTX)

  C->>API: SubmitJob (authorization, traceparent,\n x-eigen-tenant, x-client-request-id)
  API->>API: validate + enforce_authn + enforce_authz
  API->>K: EnqueueJob (forward ctx + deadline)
  K-->>API: EnqueueJobResponse(job_id, initial_state)
  API-->>C: SubmitJobResponse(job_id, status)
```

</details>

---

### A.5 Idempotency key semantics (x-eigen-idempotency-key)

![Idempotency key semantics](https://i.imgur.com/gw4QmIX.png)

<details>
<summary>code</summary>

```text
flowchart TB
  K1[Request + idempotency key] --> N["Normalize request\n(canonical form)"]
  N --> H[Compute request_fingerprint]
  H --> Cache{"Idempotency cache\n(key -> fingerprint, job_id)"}
  Cache -- miss --> Create["Forward EnqueueJob\n(store key->fingerprint->job_id)"]
  Cache -- hit same fp --> Reuse[Return same job_id]
  Cache -- hit different fp --> Conflict["FAILED_PRECONDITION\n(idempotency key conflict)"]
```

</details>

---

### A.6 Sequence — Retry-safe SubmitJob with idempotency

![Retry-safe SubmitJob with idempotency](https://i.imgur.com/rvgrcP7.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client
  participant API as System API
  participant K as Kernel/QRTX

  C->>API: SubmitJob (x-eigen-idempotency-key=K)
  API->>API: normalize + payload-limit check
  API->>API: persisted idempotency miss -> forward
  API->>K: EnqueueJob
  API->>API: persist key + digest + job_id + TTL
  API-->>C: job_id=J

  C->>API: SubmitJob retry (same key=K, same normalized body)
  API->>API: persisted hit before TTL -> job_id=J
  API-->>C: job_id=J (no duplicate)

  C->>API: SubmitJob retry (same key=K, different normalized body)
  API-->>C: FAILED_PRECONDITION idempotency conflict
```

</details>

---

### A.7 Header allowlist propagation (deterministic)

![Header allowlist propagation](https://i.imgur.com/h19sF0k.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Client -->|authorization?\ntraceparent\nx-client-request-id\nx-eigen-tenant\nx-eigen-project| API[System API]
  API -->|forward allowlisted only\n+ sanitized security ctx digest| K[Kernel/QRTX]
  API -.->|DROP / DO NOT FORWARD\nunknown/unbounded headers| Drop[Rejected metadata]
```

</details>

---

### A.8 Sequence — Deadline propagation (gRPC)

![Deadline propagation](https://i.imgur.com/V94OAAL.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant C as Client
  participant API as System API
  participant K as Kernel/QRTX

  C->>API: RPC with deadline=T
  API->>API: ensure bounded default if none
  API->>K: Forward RPC with same/derived deadline
  alt downstream exceeds deadline
    K-->>API: DEADLINE_EXCEEDED
    API-->>C: DEADLINE_EXCEEDED (status-first)
  else ok
    K-->>API: success
    API-->>C: success
  end
```

</details>

---

### A.9 StreamJobUpdates (MVP local vs Target kernel-owned stream)

![StreamJobUpdates](https://i.imgur.com/rJ6jvwy.png)

<details>
<summary>code</summary>

```text
flowchart TB
  subgraph MVP["MVP (today)"]
    API1[System API]
    Local[In-memory lifecycle + stream]
    API1 --> Local
    Client1[Client] --> API1
  end

  subgraph Target["Target (Phase-1+)"]
    Client2[Client] --> API2[System API]
    API2 --> K["Kernel stream API\n(StreamJobEvents/Updates)"]
  end
```

</details>

---

### A.10 Observability flow (logs/metrics/traces)

![Observability flow](https://i.imgur.com/M6Pf0ft.png)

<details>
<summary>code</summary>

```text
flowchart LR
  API[System API] --> M["/metrics\nPrometheus scrape/"]
  API --> L["Structured logs\n(trace_id/span_id)"]
  API --> T["OTel traces\n(traceparent propagation)"]
  M --> Obs[(Observability backend)]
  L --> Obs
  T --> Obs
```

</details>

---

### A.11 “No silent degradation” (telemetry health signaling)

![No silent degradation](https://i.imgur.com/guawBt3.png)

<details>
<summary>code</summary>

```text
flowchart TB
  Export[Exporter/Downstream/Policy component] --> Degraded{Degraded?}
  Degraded -- no --> OK[Normal operation]
  Degraded -- yes --> Signal[Emit explicit signals:\n- metric increment\n- structured log\n- optional audit marker]
  Signal --> Continue["Continue in bounded mode\n(no silent drops)"]
```

</details>

---

### A.12 Error mapping overview (gRPC status-first)

![Error mapping overview](https://i.imgur.com/UEmFtEm.png)

<details>
<summary>code</summary>

```text
flowchart TB
  E[Failure source] --> Map["Canonical mapping\n(error-model.md)"]
  Map --> IA["INVALID_ARGUMENT\n(BadRequest)"]
  Map --> UA[UNAUTHENTICATED]
  Map --> PD["PERMISSION_DENIED\n(ErrorInfo.reason)"]
  Map --> NF["NOT_FOUND\n(ResourceInfo)"]
  Map --> FP[FAILED_PRECONDITION]
  Map --> RE["RESOURCE_EXHAUSTED\n(RetryInfo)"]
  Map --> UN["UNAVAILABLE\n(RetryInfo)"]
  Map --> DE[DEADLINE_EXCEEDED]
  Map --> IN[INTERNAL]
```

</details>
