# Security & Isolation

- **Document status:** Normative security baseline + target architecture specification
- **Phase:** MVP → MVP-3 hardening baseline (with Phase-1+ targets explicitly separated)
- **Contract version:** `1.0.0`
- **Snapshot date:** 2026-05-25
- **Applies to:** `system-api`, `eigen-kernel (QRTX)`, `eigen-compiler`, `driver-manager`, QFS, observability pipeline, future HWE / GNN Optimizer / Knowledge Base / Neuro-Symbolic Core

---

## 0. Purpose

The Security & Isolation subsystem defines the authentication, authorization, isolation, validation, secrets handling, and auditability baseline for Eigen OS runtime and orchestration components.

This document is **normative** for:

- security boundaries and invariants,
- error semantics for authn/authz/security policy decisions,
- security telemetry requirements,
- compatibility constraints required by the technical specification.

It explicitly separates:

- **Implemented now (MVP truth)**
- **Required target behavior (TЗ baseline / Phase-1+)**

---

## 1. Contract Versioning

### 1.1 Contract marker metric (recommended)

Conformant deployments SHOULD export:

```text
eigen_security_contract_info{version="1.0.0"} 1
```

---

### 1.2 SemVer policy

#### MAJOR

- breaking changes to authn/authz semantics,
- breaking changes to security context propagation,
- breaking changes to isolation enforcement model,
- breaking changes to audit schema requirements.

#### MINOR

- additive claims / fields (bounded),
- additive policy controls,
- additive audit events,
- additive security telemetry metrics.

#### PATCH

- documentation fixes,
- alert/dashboard tuning,
- implementation fixes with no semantic change.

---

## 2. Security Model Overview

Eigen OS security is a multi-layer model:

2. **Ingress security (System API):** authentication, authorization, request validation, payload limits, metadata sanitization.
2. **Compiler safety:** AST-only processing, forbidden constructs, resource limits.
3. **Kernel enforcement (target):** policy gating before scheduling/execution, deterministic security decisions, replay evidence.
4. **Execution boundary (Driver Manager):** isolation from vendor SDKs, credential confinement, normalized error handling.
5. **Data plane security (QFS):** artifact integrity, retention, access control, provenance.
6. **Observability security:** no secrets in telemetry, bounded labels, audit-grade event logging.

The security subsystem MUST NOT depend on non-deterministic or opaque decisions in the request path without a deterministic fallback.

---

## 3. Responsibility Scope

### 3.1 Implemented now (MVP truth)

#### Authentication boundary (System API)

System API enforces auth modes:

- `SYSTEM_API_AUTH_MODE=allow_all`
- `SYSTEM_API_AUTH_MODE=static_token`

Static token mode uses:

`SYSTEM_API_AUTH_TOKEN=<token>`

Authn enforcement exists at ingress.

#### Authorization (System API)

Coarse-grained authorization exists with permission categories:

- `jobs:submit`
- `jobs:read`
- `devices:list`
- `devices:reserve`

Authorization logic currently uses static in-process role mappings.

#### Input validation and sanitization

Request validation is implemented for:

- program source payload size,
- embedded JobSpec YAML size,
- malformed request payloads,
- invalid compiler/frontend constructs.

Payload limits:

- `SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES`
- `SYSTEM_API_MAX_JOBSPEC_YAML_BYTES`

Compiler/frontend validation enforces:

- AST limits,
- resource limits,
- forbidden construct rejection.
- Runtime isolation hooks (partial)

A Rust `security-module` crate exists as a placeholder integration point, but **kernel-side enforcement is not wired** into the execution decision path.

#### Security observability (partial)

Implemented:

- structured security-related logging,
- denied authorization counters,
- request correlation metadata,
- runtime trace propagation.

---

### 3.2 Required target responsibility (TЗ / Phase-1+ baseline)

#### Authentication and identity

- OIDC/JWT federation (issuer validation, audience checks, expiry validation)
- centralized identity provider integration
- token rotation and refresh support
- service identity (mTLS / workload identity)
- end-to-end identity propagation

#### Authorization and policy

- centralized RBAC/ABAC policy engine
- dynamic policy evaluation with versioned policy snapshots
- multi-tenant access controls
- fine-grained runtime permissions (per job/device/artifact)
- device-level authorization and policy gating
- fail-closed behavior on policy backend outage
- immutable audit sink for security decisions
- replay markers on authorization decisions
- sandbox profile enforcement hooks
- normalized security context propagation to downstream services

#### Runtime isolation enforcement

- kernel-level execution gating (pre-schedule and pre-dispatch)
- hardware-aware isolation policies (device class, trust tier, provider boundary)
- sandboxing of runtime execution contexts (where applicable)
- tenant isolation guarantees
- deterministic “fail-closed” isolation on ambiguous cases (configurable, but default secure)

#### Hardware trust and attestation (Phase-1+)

- device trust verification hooks
- signed execution artifacts and manifests
- attestation evidence support (provider-dependent)
- confidential compute support (where available)

#### Data protection

- secret redaction
- secure telemetry policies (no sensitive identifiers in labels)
- secret lifecycle audit entries MUST carry redacted references or digests only
- encrypted artifact handling (at rest and in transit)
- retention enforcement
- export provenance tracking

#### Auditability and compliance

- immutable audit logs for security decisions
- deterministic replay evidence for policy gating
- policy evaluation traceability (policy version + decision rationale)
- security event provenance chains

---

## 4. Architecture Position and Trust Boundaries

Security & Isolation is cross-cutting and integrates with:

- `system-api` (public boundary)
- `eigen-kernel` (authoritative orchestration; target enforcement point)
- `eigen-compiler` (AST-only, safe compilation)
- `driver-manager` (vendor boundary + credential confinement)
- `qfs` (artifact persistence and provenance)
- future: `knowledge-base`, `neuro-symbolic-core`, `hwe`, `gnn-optimizer`

#### Mandatory boundary rules

1. **System API** is the only public ingress.
2. Vendor SDKs/providers are accessible **only** via Driver Manager (no direct kernel/provider coupling).
3. Security decisions must be auditable and replayable when deterministic mode is enabled.
4. Telemetry must never leak secrets or unbounded identifiers.

---

## 5. Interfaces

### 5.1 System API Interfaces (implemented)

Authn/authz enforced in request handling via middleware-like functions:

- `enforce_authn`
- `enforce_authz`
- `auth_context(...)`

Request metadata currently supports:

- `authorization`
- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

#### Required target behavior

System API SHALL provide:

- unified auth middleware with **gRPC + REST parity**
- externalized policy loading (versioned snapshots)
- centralized identity federation (OIDC/JWT)
- structured security context propagation to downstream services
- deterministic logging and sanitization rules

---

### 5.2 Kernel Security Interfaces (target; not wired today)

A placeholder crate exists:

- `src/rust/crates/security-module`

#### Required kernel-side policy gate (normative target API)

```rust
check_execution(task, device, context) -> Result<SecurityDecision, SecurityError>
```

#### Required inputs

- tenant identity (subject, tenant, roles/claims)
- job metadata (labels, requested capabilities, security profile)
- device capabilities and trust tier
- scheduling context (queue, priority, region)
- execution constraints (network/filesystem/sandbox requested)
- policy snapshot version / hash
- determinism mode

#### Required outputs

- allow/deny
- policy rationale (bounded)
- audit metadata reference
- deterministic replay marker (hash/digest)

---

### 5.3 Driver Manager Security Interfaces (current + target)

#### Current baseline

- Driver Manager is internal-only
- Credentials are not exposed to clients
- Vendor/provider boundary is encapsulated
- Provider credentials are resolved only through the security/secrets path and never through raw provider env/config secrets in production profiles
- Provider configuration is explicit, versioned, and validated before provider activation

#### Required target

- per-provider credential vault integration (no raw secrets in env in production profiles)
- provider config versioning with deterministic validation and fail-closed rejection of missing or revoked secrets
- plugin signing verification for drivers (if/when dynamic plugins are enabled)
- execution isolation boundaries between plugins/drivers and the manager runtime
- provider egress controls (network policy by deployment profile)

---

### 5.4 QFS Security Interfaces (target alignment)

QFS SHALL support:

- access control checks on artifact read/write
- artifact integrity (checksums, optional signatures)
- provenance metadata (producer component, version, timestamp)
- retention/expiry policies and deletion auditing

---

## 6. Security Context Propagation

### 6.1 Implemented now

- `traceparent` propagation exists
- partial propagation of `x-eigen-sub`, `x-eigen-roles`, `x-eigen-tenant` exists in **System API only**

---

### 6.2 Required target behavior

Security metadata SHALL propagate deterministically across:

- system-api → kernel → compiler → driver-manager → qfs
- and into observability pipelines (sanitized)

#### Propagation guarantees

- deterministic forwarding (no mutation except validated normalization)
- trace correlation preserved
- sensitive claims never logged verbatim
- explicit allowlist of forwarded headers/metadata keys

---

## 7. Isolation Policy Surface (Alignment with JobSpec)

JobSpec defines security controls (see `docs/reference/jobspec.md`):

- `security.sandbox`: `disabled | standard | strict`
- `security.filesystem.readonly`: boolean
- `security.network.mode`: `disabled | restricted | enabled`

#### Normative interpretation

- These controls MUST be treated as **requested constraints**.
- Enforcement is:
    - **partial today** (validation mostly),
    - **mandatory target** (kernel + runtime enforcement).

If a deployment cannot enforce a requested constraint, it MUST:

- reject with `FAILED_PRECONDITION` or `UNIMPLEMENTED` (preferred for unsupported features),
- include structured error details describing unsupported enforcement.

---

## 8. Error Semantics (Normative)

Eigen OS uses **gRPC status-first semantics** (no `success=false` wrappers).

### 8.1 Implemented outputs

- `UNAUTHENTICATED`
- `PERMISSION_DENIED`
- `INVALID_ARGUMENT`
- structured logs
- denied authorization metrics

---

### 8.2 Required structured details (target)

Security-related responses SHOULD attach:

- **google.rpc.ErrorInfo** (reason/domain)
- **google.rpc.RetryInfo** (for transient identity/policy backend failures)
- **google.rpc.ResourceInfo** (for resource scoped denials, e.g., device/artifact)
- **google.rpc.BadRequest** (validation violations)

---

### 8.3 Failure handling stance
Authorization MUST be **fail-closed** by default when policy cannot be evaluated.
Auth provider outages may be configured as fail-open only in explicit dev profiles (non-production).

---

## 9. Storage / State

### 9.1 Implemented now

- env-driven auth configuration
- in-memory metrics counters
- static role-permission mappings
- no centralized policy store
- no immutable audit sink

---

### 9.2 Required target storage

#### Policy storage

- versioned RBAC/ABAC registry
- signed policy manifests (recommended)
- tenant isolation rules

#### Audit storage

- immutable audit logs
- replay-safe event store for security decisions
- provenance and export tracking

#### Security runtime state

- token/session cache (bounded)
- trust evaluation cache (bounded TTL)
- policy evaluation cache (bounded TTL, version pinned)

---

## 10. Failure Modes

### 10.1 Implemented now

- authn failures → `UNAUTHENTICATED`
- authz failures → `PERMISSION_DENIED`
- validation failures → `INVALID_ARGUMENT`
- no kernel-side enforcement failures because kernel security gate is not wired

---

### 10.2 Required target failure taxonomy

#### Authentication

- invalid token
- expired token
- issuer/audience mismatch
- identity provider unavailable
- malformed claims

#### Authorization

- insufficient permissions
- tenant boundary violation
- policy evaluation failure
- stale policy snapshot

#### Runtime isolation

- unsafe device assignment
- sandbox violation
- hardware trust failure / attestation mismatch
- constraint enforcement unavailable

#### Audit

- audit sink unavailable
- immutable storage failure
- telemetry loss affecting audit guarantees
- replay inconsistency

---

### 10.3 Recovery and fallback (required)

- fail-closed authorization
- bounded degraded modes (explicitly configured)
- audit-safe fallback behavior
- policy rollback
- circuit breaker for policy backends
- replay-safe recovery when deterministic mode is enabled

---

## 11. Observability (Security Telemetry)

Security telemetry must align with global observability rules:

- bounded label cardinality,
- no secrets,
- no user payload data,
- no trace-level identifiers in metric labels.

---

### 11.1 Implemented metrics (examples)

- `eigen_api_authz_denied_total`
- `eigen_api_requests_total`
- `eigen_api_request_duration_seconds`

---

### 11.2 Required target metrics

#### Authn/Authz

```text
security_auth_attempts_total{mode,result}
security_auth_failures_total{reason}
security_policy_denials_total{action,resource_type,reason}
security_policy_eval_duration_seconds_bucket
security_audit_write_failures_total{sink}
```

#### Validation

```text
security_validation_failures_total{component,reason}
```

#### Runtime isolation

```text
security_runtime_isolation_denials_total{stage,reason}
security_tenant_isolation_violations_total{reason}
```

#### Audit pipeline

```text
security_audit_write_failures_total{sink}
security_audit_backlog_size
security_replay_verification_failures_total{reason}
```

---

### 11.3 Logging (required shape)

#### Implemented now

- structured JSON logs with `trace_id`, `traceparent`, `method`, `request_id`, optional `job_id`
- append-only security audit records with `decision`, `reason`, `policy_version`, `service_identity`, `sandbox_profile`, and `replay_marker`
- bounded audit pipeline health counters for sink write failures

#### Required target

- unified security audit schema (immutable sink)
- policy evaluation logs (policy version + decision outcome)
- isolation decision logs (stage + constraints + rationale)
- secret-safe redaction rules enforced

---

### 11.4 Tracing (required)

Security tracing spans MUST include attributes (as trace attributes, not metric labels):

- subject/tenant (sanitized or stable IDs per policy)
- action/resource
- outcome
- policy version/hash
- decision rationale reference (bounded)

Tracing MUST span:

- system-api → kernel → compiler → driver-manager → qfs
- and adaptive runtime components when enabled

---

## 12. Dashboards and Alerts (Target)

#### Dashboards

- authentication overview
- authorization denials by action/resource_type
- policy evaluation latency + error rate
- audit pipeline health (backlog, write failures)
- isolation decisions + violations
- attestation/trust health (Phase-1+)

#### Alerts

- auth failure spikes
- policy denial spikes
- policy backend outage / evaluation failures
- audit sink failures / backlog saturation
- replay verification failures (deterministic mode)
- attestation failures (Phase-1+)
- suspected isolation violations

---

## 13. Security and Compliance Controls (Target)

#### Identity and access

- OIDC federation
- RBAC/ABAC
- least privilege
- service identity support

#### Runtime trust

- signed artifacts / manifests
- attestation hooks where supported
- sandbox enforcement
- credential vault integration

#### Compliance

- immutable audit retention
- export provenance tracking
- replay evidence preservation
- retention/versioning policies

---

## 14. Architectural Invariants (Mandatory)
1. **Public ingress invariant:** only system-api is externally reachable.
2. **No user code execution invariant:** compiler and services do not execute user code server-side.
3. **Fail-safe invariant:** authorization is fail-closed by default when policy cannot be evaluated.
4. **Telemetry safety invariant:** no secrets and no unbounded identifiers in telemetry.
5. **Vendor boundary invariant:** only Driver Manager communicates with vendor SDKs/APIs.
6. **Replay integrity invariant:** when deterministic mode is enabled, security decisions must be replay-verifiable.

---

## 15. Alignment Summary

#### Implemented and aligned (MVP baseline)

- explicit authentication modes
- coarse-grained authorization
- payload size validation
- compiler AST safety constraints
- baseline security logs and authz denial metrics
- trace propagation

#### Remaining gaps (required future work)

- centralized identity federation (OIDC/JWT)
- kernel-level policy gating and isolation enforcement
- end-to-end security context propagation guarantees
- immutable audit subsystem
- device-level authorization and trust/attestation hooks
- credential vault integration
- adaptive-runtime security controls (HWE/NSC/GNN/KB)
- deterministic replay evidence for security decisions

These gaps are intentionally preserved to prevent architecture scope loss while keeping MVP semantics truthful and stable.

---

## Appendix A. Diagrams (normative)

### A.1 C4 Context — Security boundaries across Eigen OS

![C4 Context](https://i.imgur.com/4yxXuaP.png)

<details>
<summary>code</summary>

```text
flowchart LR
    subgraph Ext["External"]
        Client["SDK/CLI"]
        IdP["OIDC IdP\n(Phase-1+)"]
    end

    subgraph Public["Public Boundary"]
        API["System API\n(authn/authz/validation)"]
    end

    subgraph Core["Runtime Core"]
        K["Kernel / QRTX\n(target policy gate)"]
        C["Compiler\n(AST-only sandbox)"]
        DM["Driver Manager\n(vendor boundary)"]
        QFS["(QFS\n\(artifacts + lineage\))"]
    end

    subgraph Adaptive["Adaptive (future)"]
        HWE[HWE]
        OPT[GNN Optimizer]
        KB["Knowledge Base / OKB"]
        NSC["Neuro-Symbolic Core"]
    end

    Client --> API --> K
    API <--> IdP
    K --> C
    K --> DM
    K --> QFS
    DM --> QFS
    HWE --> K
    OPT --> HWE
    KB --> OPT
    NSC --> K

    classDef boundary stroke-width:2px,stroke-dasharray: 5 5;
    class API,DM boundary
```

</details>

---

### A.2 C4 Container — MVP vs Target security enforcement points

![C4 Container](https://i.imgur.com/4yxXuaP.png)

<details>
<summary>code</summary>

```text
flowchart TB
    subgraph MVP["MVP (today)"]
        API1["System API\nstatic_token/allow_all\ncoarse RBAC"]
        K1["Kernel\n(no policy gate wired)"]
        C1["Compiler\nAST allowlist + limits"]
        DM1["Driver Manager\ninternal-only boundary"]
        
        API1 --> K1 --> C1
        K1 --> DM1
    end

    subgraph Target["Target (MVP-3 / Phase-1+)"]
        API2["System API\nOIDC/JWT + policy context"]
        PE["Policy Engine\n(RBAC/ABAC snapshots)"]
        K2["Kernel\ncheck_execution gate"]
        C2["Compiler\nsandbox profile + resource caps"]
        DM2["Driver Manager\nmTLS + vault + plugin verify"]
        QFS2[(QFS\nACL + integrity + retention)]
        
        API2 --> PE
        API2 --> K2
        K2 --> PE
        K2 --> C2
        K2 --> DM2
        K2 --> QFS2
    end
```

</details>

---

### A.3 Metadata propagation path (allowlist forwarding)

![Metadata propagation path](https://i.imgur.com/JtBlGLH.png)

<details>
<summary>code</summary>

```text
flowchart LR
    Client["Client SDK"] -->|authorization, traceparent,<br>x-eigen-tenant, x-eigen-roles,<br>x-client-request-id| API["System API"]
    
    API -->|forward allowlisted metadata<br>+ sanitized security context| K["Kernel/QRTX"]
    
    K -->|traceparent + security ctx digest| C["Compiler"]
    K -->|traceparent + security ctx digest| DM["Driver Manager"]
    
    C -->|"artifact refs only<br>(no raw source in logs)"| QFS[(QFS)]
    DM -->|results + normalized errors| QFS

    classDef store fill:#f0f4c3,stroke:#689f38
    class QFS store
```

</details>

---

### A.4 Sequence — End-to-end auth context propagation (target)

![End-to-end auth context propagation](https://i.imgur.com/0EXyzLP.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant SDK as SDK/CLI
  participant API as System API
  participant K as Kernel/QRTX
  participant C as Compiler
  participant DM as Driver Manager
  participant Q as QFS

  SDK->>API: SubmitJob (authorization, traceparent,\n x-eigen-tenant, x-eigen-roles,\n x-client-request-id)
  API->>API: enforce_authn + enforce_authz\n(sanitize headers)
  API->>K: EnqueueJob (forward ctx)\n+ security_ctx_digest
  K->>C: CompileJob (traceparent + security_ctx_digest)
  C->>Q: write compiled artifacts (no secrets)
  K->>DM: ExecuteCircuit (traceparent + security_ctx_digest)
  DM->>Q: write execution results/error artifact refs
  K-->>API: status/result (gRPC status-first)
  API-->>SDK: response (no secret leakage)
```

</details>

---

### A.5 Authn/Authz decision tree (status-first)

![Authn/Authz decision tree](https://i.imgur.com/1hFZ6MZ.png)

<details>
<summary>code</summary>

```text
flowchart TB
    Req["Incoming request"] --> Mode{AUTH_MODE}
    
    Mode -->|allow_all| Allow["ALLOW (dev only)"]
    Mode -->|static_token| Tok{"token valid?"}
    Mode -->|"oidc_jwt (Phase-1+)"| JWT{"JWT valid?\niss/aud/exp"}
    
    Tok -- no --> UA1[UNAUTHENTICATED]
    Tok -- yes --> RBAC1{"RBAC allowed?"}
    
    JWT -- no --> UA2[UNAUTHENTICATED]
    JWT -- yes --> Policy{"Policy eval ok?"}
    
    Policy -- fail --> FailClosed["PERMISSION_DENIED\n(fail-closed default)"]
    Policy -- ok --> RBAC2{"RBAC/ABAC allow?"}
    
    RBAC1 -- no --> PD1[PERMISSION_DENIED]
    RBAC1 -- yes --> OK1[OK]
    
    RBAC2 -- no --> PD2["PERMISSION_DENIED\n+ ErrorInfo.reason"]
    RBAC2 -- yes --> OK2[OK]
```

</details>

---

### A.6 Sequence — Policy snapshot evaluation (Phase-1+)

![Policy snapshot evaluation](https://i.imgur.com/bERwAuw.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant API as System API
  participant PE as Policy Engine
  participant K as Kernel/QRTX

  API->>PE: Evaluate(action, resource, subject, tenant)\n+ policy_snapshot_hint
  PE-->>API: decision (allow/deny)\n+ policy_version/hash\n+ rationale_ref (bounded)
  API->>K: forward security_ctx_digest\n+ policy_version/hash
```

</details>

---

### A.7 Kernel execution gate — pre-schedule + pre-dispatch checks

![Kernel execution gate](https://i.imgur.com/uG09OFi.png)

<details>
<summary>code</summary>

```text
flowchart TB
    Enq["Job accepted"] --> Gate1{"check_execution\n(pre-schedule)"}
    
    Gate1 -- deny --> Deny1["ERROR\n(PERMISSION_DENIED or FAILED_PRECONDITION)\n+ audit marker"]
    Gate1 -- allow --> Sched["Queue / Allocate"]
    
    Sched --> Gate2{"check_execution\n(pre-dispatch)"}
    
    Gate2 -- deny --> Deny2["ERROR\n+ revoke reservation\n+ audit marker"]
    Gate2 -- allow --> Dispatch["Dispatch to Driver Manager"]
```

</details>

---

### A.8 State machine — Isolation enforcement outcomes (target)

![State machine](https://i.imgur.com/pbT9nge.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> INGRESS_VALIDATED
  INGRESS_VALIDATED --> POLICY_ALLOWED: authn+authz ok
  INGRESS_VALIDATED --> POLICY_DENIED: deny (fail-closed)
  POLICY_ALLOWED --> SANDBOX_READY: compiler/runtime sandbox constraints satisfied
  POLICY_ALLOWED --> SANDBOX_UNAVAILABLE: enforcement missing
  SANDBOX_UNAVAILABLE --> REJECTED: UNIMPLEMENTED/FAILED_PRECONDITION
  SANDBOX_READY --> EXEC_ALLOWED: kernel gate allow
  EXEC_ALLOWED --> EXEC_DENIED: late deny (pre-dispatch)
  POLICY_DENIED --> REJECTED
  EXEC_DENIED --> REJECTED
  REJECTED --> [*]
```

</details>

---

### A.9 Compiler safety boundary (AST-only + sandbox profile)

![Compiler safety boundary](https://i.imgur.com/bo4MmJp.png)

<details>
<summary>code</summary>

```text
flowchart LR
    Src["Source bytes/ref"] --> Parse["Parse AST"]
    Parse --> Allow{"Allowlist OK?"}
    
    Allow -- no --> Reject["INVALID_ARGUMENT\n(forbidden construct)"]
    Allow -- yes --> Lower["Lower to IR/AQO\n(deterministic)"]
    
    Lower --> Emit["Emit to QFS\natomic write"]

    subgraph Sandbox["Compiler Sandbox Profile (required)"]
        NoNet["network: disabled by default"]
        ROFS["fs: read-only outside workspace"]
        Limits["cpu/mem/wall-time limits"]
        Env["allowlisted env only"]
    end

    Parse -.enforced by.-> Sandbox
    Lower -.enforced by.-> Sandbox
```

</details>

---

### A.10 DM security boundary (vault + isolation + no secret leakage)

![DM security boundary](https://i.imgur.com/VBRgGnc.png)

<details>
<summary>code</summary>

```text
flowchart TB
    K["Kernel/QRTX"] -->|"mTLS + traceparent<br>(no provider secrets)"| DM["Driver Manager"]
    DM --> Vault[(Secret Vault<br>Phase-1+)]
    DM --> Driver["Driver Plugin/Remote QDriver"]
    Driver --> Vendor["Vendor API / Simulator"]
    DM --> Logs["Logs/Metrics/Traces"]
    Logs --> Obs[(Observability Pipeline)]

    Note["⚠️ Secrets must NOT appear in:<br>• JobSpec<br>• QFS artifacts<br>• logs/metrics labels<br>• client-visible payloads"]
    Note -.-> DM

    classDef warning fill:#fff3e0,stroke:#f57c00,color:#000
    class Note warning
```

</details>

---

### A.11 QFS access control check (target)

![QFS access control check](https://i.imgur.com/aEqV0Tn.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant S as Service (Kernel/Compiler/DM)
  participant Q as QFS
  participant P as Policy Engine (optional)
  participant A as Audit Sink

  S->>Q: StoreArtifact(ref, bytes, metadata)
  Q->>P: Authorize(artifact_write, ref, subject/tenant)\n(policy snapshot)
  P-->>Q: allow/deny + policy_version/hash
  alt allow
    Q->>Q: write atomically + compute digest
    Q->>A: audit event (artifact_write, ref, digest)
    Q-->>S: ok (ArtifactHandle)
  else deny
    Q-->>S: PERMISSION_DENIED\n+ ErrorInfo.reason
  end
```

</details>

---

### A.12 Integrity chain — signed manifests (Phase-1+)

![Integrity chain](https://i.imgur.com/vAra3o0.png)

<details>
<summary>code</summary>

```text
flowchart LR
    AQO[compiled.aqo.json] --> H1[sha256 digest]
    H1 --> Meta["compiled/metadata.json\nincludes aqo_sha256"]
    Meta --> Manifest["Job manifest (Phase-1+)\noptionally signed"]
    Manifest --> Verify["Verifier / Replay / Audit"]

    classDef important fill:#e3f2fd,stroke:#1976d2
    class Manifest,Verify important
```

</details>

---

### A.13 Audit event flow (immutable sink)

![Audit event flow](https://i.imgur.com/lAcA9ea.png)

<details>
<summary>code</summary>

```text
flowchart LR
  API[System API] -->|authn/authz decisions| Audit[(Immutable Audit Sink)]
  K[Kernel] -->|execution gate decisions| Audit
  DM[Driver Manager] -->|credential access + backend boundary| Audit
  QFS[(QFS)] -->|artifact writes/reads| Audit
  Obs[(Observability)] -->|security alerts| Audit
```

</details>

---

### A.14 Degradation signaling (must be visible)

![Degradation signaling](https://i.imgur.com/P9AjkBC.png)

<details>
<summary>code</summary>

```text
flowchart TB
    Comp["Security component"] --> Fail{"Exporter/Policy/Audit degraded?"}
    
    Fail -- no --> Normal["Normal operation"]
    Fail -- yes --> Signal["Emit explicit indicators:\n- metric increment\n- structured log\n- optional audit event"]
    
    Signal --> Degraded["Degraded mode (bounded)\nnever silent"]

    classDef degraded fill:#fff3e0,stroke:#f57c00,color:#d84315
    class Signal,Degraded degraded
```

</details>

---

### A.15 Data flow & threat surfaces (high-level)

![Data flow & threat surfaces](https://i.imgur.com/9PyZ75i.png)

<details>
<summary>code</summary>

```text
flowchart LR
  Client --> API["System API<br/>(ingress validation)"]
  API --> K["Kernel/QRTX<br/>(orchestration)"]
  K --> C["Compiler<br/>(AST-only)"]
  K --> DM["Driver Manager<br/>(vendor boundary)"]
  C --> QFS[(QFS)]
  DM --> QFS
  DM --> Vendor[Vendor API]

  N_API["⚠ Threats:<br/>- auth bypass<br/>- payload abuse/DoS<br/>- header injection"]
  N_DM["⚠ Threats:<br/>- secret leakage<br/>- supply chain (drivers)<br/>- vendor response leakage"]

  N_API -.-> API
  N_DM -.-> DM

  classDef threat stroke:#d33,stroke-width:2px;
  classDef note fill:#fff3cd,stroke:#ffc107,color:#000,stroke-dasharray: 3 3;
  class API,DM threat;
  class N_API,N_DM note;
```

</details>
