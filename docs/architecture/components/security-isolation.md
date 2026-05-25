# Security Isolation

- **Phase:** MVP → MVP-3 hardening baseline
- **Status snapshot date:** 2026-05-25

## Responsibility

The Security Isolation subsystem defines the authentication, authorization, runtime isolation, validation, and auditability baseline for Eigen OS runtime and orchestration components.

Current MVP implementation provides:

- explicit authentication boundaries,
- coarse-grained authorization,
- request validation and payload limits,
- partial security observability,
- placeholder runtime isolation hooks.

The long-term architecture target is a fully enforceable multi-layer security model with deterministic runtime isolation, policy-driven authorization, audit-grade telemetry, and hardware-aware trust boundaries.

---

# Responsibility Scope

## Implemented now

### Authentication boundary

System API enforces explicit authentication modes:

- `SYSTEM_API_AUTH_MODE=allow_all`
- `SYSTEM_API_AUTH_MODE=static_token`

Static token mode uses:

- `SYSTEM_API_AUTH_TOKEN=<token>`

Authentication enforcement exists in the request ingress layer.

### Authorization

Coarse-grained authorization is implemented in System API.

Implemented permission categories include:

- `jobs:submit`
- `jobs:read`
- `devices:list`
- `devices:reserve`

Authorization logic currently uses static in-process role mappings.

### Input validation and sanitization

Request validation is implemented for:

- program source payload size,
- embedded JobSpec YAML size,
- malformed request payloads,
- invalid compiler/frontend constructs.

Implemented payload limits:

- `SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES`
- `SYSTEM_API_MAX_JOBSPEC_YAML_BYTES`

Compiler/frontend validation enforces:

- AST limits,
- resource limits,
- forbidden construct rejection.

### Runtime isolation hooks (partial)

Rust `security-module` crate exists as a placeholder integration point.

Current implementation does not yet enforce:

- runtime isolation decisions,
- device-level policy enforcement,
- kernel-side execution gating.

### Security observability (partial)

Implemented:

- structured security-related logging,
- denied authorization counters,
- request correlation metadata,
- runtime trace propagation.

---

## Required target responsibility (architecture baseline)

The final Security Isolation subsystem SHALL provide:

### Authentication and identity

- OIDC/JWT federation
- centralized identity provider integration
- token validation and rotation
- service identity support
- workload identity propagation

### Authorization and policy

- centralized RBAC/ABAC policy engine
- dynamic policy evaluation
- multi-tenant access controls
- fine-grained runtime permissions
- device-level authorization

### Runtime isolation

- kernel-level execution isolation
- hardware-aware isolation policies
- runtime sandboxing
- tenant isolation guarantees
- workload confinement

### Hardware trust and attestation

- hardware-rooted trust chains
- confidential compute support
- runtime attestation
- signed execution artifacts
- device trust verification

### Data protection

- secret redaction
- secure telemetry policies
- DLP scanning
- encrypted artifact handling
- retention enforcement

### Auditability and compliance

- immutable audit logs
- deterministic replay evidence
- policy evaluation traceability
- security event provenance
- compliance retention controls

---

# Architecture Position

Security Isolation is a cross-cutting platform capability.

It integrates with:

- system-api
- eigen-kernel
- eigen-compiler
- driver-manager
- QFS
- future knowledge-base
- future neuro-symbolic-core
- future HWE
- future GNN optimizer

Security Isolation is mandatory infrastructure for:

- multi-tenant execution,
- deterministic replay integrity,
- adaptive-runtime safety,
- runtime policy enforcement,
- audit-grade telemetry,
- production deployment readiness,
- release-readiness validation.

---

# Interfaces

## 1. System API Interfaces

### Implemented now

Authentication and authorization are enforced in System API request handling.

Implemented interfaces include:

- `enforce_authn`
- `enforce_authz`
- `auth_context(...)`

Request metadata currently supports:

- `authorization`
- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

### Required target behavior

System API SHALL provide:

- unified auth middleware,
- gRPC + REST parity,
- externalized policy loading,
- centralized identity federation,
- structured security context propagation.

---

## 2. Kernel Security Interfaces

### Implemented now

Placeholder crate exists:

- `src/rust/crates/security-module`

No enforceable runtime isolation API is currently wired into kernel execution flow.

### Required target interfaces

Kernel security SHALL expose:

### Runtime isolation checks

```rust
check(task, device) -> Result<(), SecurityError>
```

### Required policy evaluation inputs

- tenant identity
- workload metadata
- device capabilities
- scheduling context
- execution constraints

### Required outputs

- allow/deny decision
- policy rationale
- audit metadata
- deterministic replay marker

---

## 3. Internal Security Context Propagation

### Implemented now

Trace context propagation exists.

Partial propagation of:

- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`

exists in System API only.

### Required target behavior

Security metadata SHALL propagate across:

- system-api
- kernel
- compiler
- driver-manager
- observability pipelines

Required propagation guarantees:

- deterministic forwarding,
- immutable trace correlation,
- audit-safe metadata handling,
- sanitized logging.

---

# Inputs / Outputs

## Inputs

### Implemented now

#### Authentication inputs

- authorization token
- auth mode environment configuration

#### Validation inputs

- program source bytes
- embedded JobSpec YAML
- request metadata

#### Security metadata

- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

---

### Required target inputs

#### Identity and policy inputs

- JWT/OIDC claims
- tenant policy definitions
- RBAC/ABAC rules
- workload security labels

#### Runtime isolation inputs

- hardware capability metadata
- device trust state
- runtime topology state
- workload execution profile

#### Security telemetry inputs

- audit events
- security alerts
- policy evaluation traces
- anomaly signals

---

## Outputs

### Implemented now

Current outputs include:

- UNAUTHENTICATED
- PERMISSION_DENIED
- INVALID_ARGUMENT
- structured logs
- denied authorization metrics

---

### Required target outputs

#### Security decisions

- policy evaluation result
- runtime isolation decision
- audit metadata
- deterministic replay evidence

#### Security telemetry

- audit streams
- security metrics
- policy traces
- security alerts

#### Compliance outputs

- immutable audit records
- retention metadata
- provenance markers
- replay verification artifacts

---

## Storage / State

### Implemented now

Current runtime state includes:

- env-driven security configuration,
- in-memory metrics counters,
- static role-permission mappings.

No centralized policy store or audit persistence layer exists.

---

### Required target storage

#### Policy storage

- centralized RBAC/ABAC policy registry
- versioned policy snapshots
- tenant isolation rules
- signed policy manifests

#### Audit storage

- immutable audit logs
- replay-safe event storage
- provenance chains
- export tracking

#### Security state

- token/session cache
- isolation state
- trust evaluation cache
- policy evaluation history

---

## Failure Modes

### Implemented now

#### Authentication failures

Handled by:

- `enforce_authn`

Outputs:

- `UNAUTHENTICATED`

#### Authorization failures

Handled by:

- `enforce_authz`

Outputs:

- `PERMISSION_DENIED`

#### Validation failures

Handled by:

- validation pipeline

Outputs:

- `INVALID_ARGUMENT`

#### Security module runtime behavior

No enforceable runtime security module behavior currently exists.

---

### Required target failure taxonomy

#### Authentication failures

- invalid token
- expired token
- identity provider unavailable
- malformed claims

#### Authorization failures

- insufficient permissions
- policy evaluation failure
- tenant boundary violation
- stale policy cache

#### Runtime isolation failures

- unsafe device assignment
- sandbox violation
- hardware trust failure
- attestation mismatch

#### Audit failures

- audit sink unavailable
- immutable storage failure
- telemetry loss
- replay inconsistency

---

### Recovery and fallback requirements

The Security Isolation subsystem SHALL support:

- fail-closed authorization,
- bounded degraded modes,
- audit-safe fallback behavior,
- replay-safe recovery,
- policy rollback,
- circuit-breaker enforcement.

---

## Observability

### Metrics

#### Implemented now

Existing metrics include:

- `eigen_api_authz_denied_total`
- `eigen_api_requests_total`
- `eigen_api_request_duration_seconds`

---

#### Required target metrics

**Security metrics**

- `security_auth_attempts_total`
- `security_auth_failures_total`
- `security_policy_denials_total`
- `security_validation_failures_total`
- `security_runtime_isolation_denials_total`

**Audit metrics**

- `security_audit_write_failures_total`
- `security_audit_backlog_size`
- `security_replay_verification_failures_total`

**Runtime security metrics**

- `security_device_attestation_failures_total`
- `security_policy_eval_duration_seconds`
- `security_tenant_isolation_violations_total`

---

### Logs

#### Implemented now

Structured JSON logs exist with:

- `trace_id`
- `traceparent`
- `method`
- `request_id`
- optional `job_id`

Authorization denial logs are implemented.

---

#### Required target logging

- unified security audit schema
- immutable audit logging
- policy evaluation logging
- runtime isolation logging
- hardware trust logging
- secret-safe telemetry logging

---

### Traces

#### Implemented now

Trace propagation exists via:

- `traceparent`
- `trace_id`

---

#### Required target tracing

Security tracing SHALL include:

- subject
- tenant
- roles
- action
- resource
- outcome
- policy version
- runtime isolation rationale

Distributed tracing SHALL span:

- API
- compiler
- kernel
- driver-manager
- QFS
- adaptive runtime components

---

### Health Checks

#### Implemented now

Basic runtime health endpoints exist.

No dedicated security health hierarchy is implemented.

---

#### Required target health model

**Security subsystem health**

- auth provider health
- policy engine health
- audit sink health
- isolation runtime health

**Runtime security health**

- attestation freshness
- isolation integrity
- audit consistency
- telemetry integrity

---

### Dashboards and Alerts

#### Implemented now

Security-relevant telemetry is partially visible through existing runtime metrics and structured logs.

---

#### Required target dashboards

**Security dashboards**

- authentication overview
- authorization failures
- runtime isolation decisions
- audit pipeline health
- policy evaluation latency
- tenant activity visibility

**Alert categories**

- authentication failures
- policy denial spikes
- audit sink failures
- replay inconsistencies
- attestation failures
- isolation violations
- suspicious runtime activity

---

## Security and Compliance

### Required target controls

#### Identity and access

- OIDC federation
- RBAC/ABAC enforcement
- service identity validation
- least-privilege policies

#### Runtime trust

- signed artifacts
- attestation verification
- sandbox enforcement
- hardware trust validation

#### Compliance controls

- immutable audit retention
- export provenance tracking
- replay evidence preservation
- retention/versioning policies

---

## Alignment Summary

### Implemented and aligned

The following MVP security capabilities are implemented:

- explicit authentication modes,
- coarse-grained authorization,
- request-size validation,
- baseline structured security telemetry,
- trace propagation,
- runtime validation enforcement.

### Remaining architecture gaps

The following architecture targets remain not fully implemented:

- centralized identity federation,
- kernel-level runtime isolation enforcement,
- end-to-end security metadata propagation guarantees,
- immutable audit subsystem,
- policy-driven runtime authorization,
- attestation and confidential compute integration,
- adaptive-runtime security controls,
- replay-grade auditability.

These gaps remain explicitly preserved as required future work to prevent architecture scope loss.
