# Security Isolation (MVP)

- Phase: MVP
- - Last verified against implementation: 2026-05-09
- Verified sources: `rfcs/0009-security-isolation-mvp.md`, `docs/adr/0007-mvp3-release-readiness-runtime-contracts-and-security-closure.md`, `rfcs/0018-mvp3-runtime-observability-and-release-gates.md`, System API + Rust security module code.

## MVP Threat Model (Current Baseline)

Implemented in MVP:

- Public API authn boundary is enforced in System API via explicit auth mode:
  - `SYSTEM_API_AUTH_MODE=allow_all` (dev default)
  - `SYSTEM_API_AUTH_MODE=static_token` + `SYSTEM_API_AUTH_TOKEN=<token>`
- Coarse authz checks are enforced at gRPC method level (e.g., `jobs:submit`, `jobs:read`, `devices:list`, `devices:reserve`).
- Request payload bounds are enforced:
  - `SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES` (default `262144`)
  - `SYSTEM_API_MAX_JOBSPEC_YAML_BYTES` (default `65536`)
- Compiler/frontend path rejects forbidden Eigen-Lang constructs and enforces AST/resource limits (per RFC 0009 + existing validation pipeline).

Not implemented in MVP (tracked for later phases):

- **TODO:** Full multi-tenant runtime sandboxing/isolation guarantees at kernel/driver/hardware layer.
- **TODO:** OIDC/JWT federation and centralized per-user RBAC/ABAC policy engine.
- **TODO:** Hardware-rooted trust, confidential compute, attestation chain.
- **TODO:** Comprehensive secret scanning/DLP on submitted artifacts.

## Responsibility

Current MVP component responsibilities:

1. **Authentication boundary (implemented)**
   - Enforce explicit auth mode in System API (`allow_all` / `static_token`).

2. **Authorization checks (implemented)**
   - Enforce coarse role/permission model in System API with static in-process role mappings.

3. **Input validation & sanitization (implemented)**
   - Reject malformed/oversized source and embedded JobSpec YAML metadata.

4. **Isolation hook at kernel boundary (partial)**
   - Rust `security-module` crate exists as MVP placeholder.
   - **TODO:** Implement `SecurityModule.check(task, device)`-style runtime isolation decision path (currently no real enforcement logic in crate).

5. **Audit/security observability (partial)**
   - Authz denied events are counted and logged in System API.
   - **TODO:** Complete structured audit trail for all security-sensitive actions (submit/reserve/cancel/etc.) with durable sink and schema freeze.

## Interfaces

### System API (Python)

Implemented:

- Authn gate (`enforce_authn`) for incoming gRPC requests.
- Authz gate (`enforce_authz`) on protected methods.
- `auth_context(...)` extraction of `subject`, `roles`, `tenant` (used for request context).

Partially implemented / TODO:

- **TODO:** Canonical interceptor/middleware-based auth chain for both gRPC + REST surface (current baseline is gRPC service-method enforcement; REST parity must be explicitly confirmed/extended).
- **TODO:** Externalized policy source (current role-permission map is static in code).

### Kernel (Rust) – Security Module Hook

Implemented:

- `src/rust/crates/security-module` crate exists and is wired as placeholder component.

Not yet implemented:

- **TODO:** Real kernel-side isolation/security trait + decision API integration (`check(task, device) -> Result<(), SecurityError>`), including deny paths and audit fields.

### Internal security context metadata

RFC 0009 contract fields:

- `x-eigen-sub`
- `x-eigen-roles`
- `x-eigen-tenant`
- `traceparent`

Current state:

- `traceparent` is parsed/propagated in System API observability context.
- `x-eigen-*` fields are consumed by auth context/authz logic.
- **TODO:** Verify and enforce end-to-end forwarding contract across all internal gRPC hops (`system-api -> kernel -> driver-manager`) and include these fields in kernel audit records per RFC 0009.

## Inputs / Outputs

| **Input** | **Source** | **Current state** |
|-------------------|-------------------|-------------------|
| Authorization token | gRPC metadata (`authorization`) | Implemented for `static_token` mode. |
| Program source bytes | SubmitJob payload | Implemented size validation. |
| Embedded `jobspec_yaml` | SubmitJob metadata | Implemented size validation and parse path checks. |
| Security context (`x-eigen-*`) | Request metadata | Partially implemented in System API only; **TODO:** full internal propagation guarantees. |
| Device info for isolation decision | Driver Manager / Kernel path | **TODO:** not implemented as enforceable security isolation decision in MVP code. |

---

| **Output** | **Destination** | **Current state** |
|-------------------|-------------------|-------------------|
| Authn/Authz decision | System API → Client | Implemented (`UNAUTHENTICATED`, `PERMISSION_DENIED`). |
| Validation decision | System API → Client | Implemented (`INVALID_ARGUMENT` + field violations). |
| Security metrics | `/metrics` endpoint | Partially implemented (`eigen_api_authz_denied_total` plus generic request metrics). |
| Security audit log | Structured logs | Partially implemented; **TODO:** durable audit sink + full event coverage. |

## Storage / State

Implemented:

- Security config comes from env vars at process startup/runtime reads.
- In-memory metrics counters for denied authz and request totals.

Not implemented / TODO:

- **TODO:** Config-backed role-permission mapping file (RFC text examples mention YAML, but current implementation is in-code static map).
- **TODO:** Dedicated audit log file path contract (`/var/log/eigen/audit.log`) and rotation/retention policy.
- **TODO:** Token/context cache with TTL (not present in current code).

## Failure Modes

| **Failure** | **Detection** | **Current mitigation state** |
|-------------------|-------------------|-------------------|
| Missing/invalid token in `static_token` mode | `enforce_authn` | Implemented: return `UNAUTHENTICATED`. |
| Insufficient permission | `enforce_authz` | Implemented: return `PERMISSION_DENIED`; increment denied metric/log event. |
| Oversized source / YAML | validation/jobspec parser | Implemented: return `INVALID_ARGUMENT` with field violations. |
| Security module unavailable / non-functional | kernel path | **TODO:** no explicit runtime health-gated behavior documented in code; placeholder crate only. |
| Audit sink write failure | audit subsystem | **TODO:** no dedicated audit sink/fallback path implemented. |

## Observability

### Metrics

Implemented:

- `eigen_api_authz_denied_total`
- `eigen_api_requests_total`
- `eigen_api_request_duration_seconds`

Not implemented / TODO:

- **TODO:** RFC-aligned security metric family with labels for auth attempts, permission checks, and validation error types (the previous proposed `security_*` set is not currently exposed).

### Logs

Implemented:

- JSON logs with common request fields (`trace_id`, `traceparent`, `method`, `request_id`, optional `job_id`).
- Authz denied structured warning log entries.

Not implemented / TODO:

- **TODO:** Full security audit schema (subject/action/resource/outcome across all sensitive operations) and immutable/durable audit retention policy.

### Traces

Implemented:

- `traceparent` ingestion and `trace_id` extraction in System API request context.

Not implemented / TODO:

- **TODO:** End-to-end security span contract with required tags (`user`, `roles`, `resource`, `action`, `outcome`) across all services.

## RFC / ADR Conformance Check (2026-05-09)

### RFC 0009 (Security & Isolation MVP)

- **Implemented:** explicit authn mode, coarse authz, payload size limits, baseline role-permission model.
- **Partially implemented:** auth context metadata handling + security observability.
- **TODO gaps:** real kernel isolation checks, end-to-end metadata propagation guarantees, complete audit event model.

### ADR 0007 (MVP-3 security closure)

- ADR requires security audit completion for kernel-driver boundary controls as release evidence.
- **TODO:** this component doc still needs explicit link/evidence artifact for completed kernel-driver security audit and resulting controls.

### RFC 0018 (runtime observability + release gates)

- Security/privacy clause requires no secret leakage and actionable sanitized diagnostics.
- **Partially implemented:** bounded logs and basic structured fields.
- **TODO:** explicit security-focused log redaction policy + CI assertions tied to security telemetry fields.

## Implementation Notes for MVP (frozen current state)

1. Auth is environment-driven (`allow_all` / `static_token`).
2. Authz is coarse-grained and static-map based in System API.
3. Request-size validation for source and `jobspec_yaml` is implemented and tested.
4. Rust `security-module` currently acts as placeholder library, not as a complete enforcement component.
5. Security observability is partial (denied counter + structured logs) and not yet a full audit subsystem.
6. Network isolation assumptions are documented at architecture level, but **TODO:** enforceable/measured control evidence should be linked here when available.
