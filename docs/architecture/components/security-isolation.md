# Security Isolation (MVP)

- Phase: MVP

## Responsibility

The Security & Isolation module in MVP provides **basic access control, authentication, and resource isolation** to ensure safe, multi‑tenant quantum‑classical job execution. It focuses on:

1. **Authentication & Authorization**: Enforcing who can submit jobs, access devices, and view results.

2. **Security Context Propagation**: Passing authenticated user identity and roles through the system.

3. **Input Validation & Sanitization**: Preventing malicious or malformed job specifications.

4. **Isolation Hooks**: Providing a minimal interface for future hardware‑level isolation checks (stubbed or simulated in MVP).

## Interfaces

### System API (Python)

- **Authentication Interceptors**: Validate API keys/tokens from incoming gRPC/REST requests.

- **Authorization Engine**: Maps users/roles to permissions (e.g., `jobs:submit`, `devices:list`).

- **Context Propagation**: Injects security context (`x‑eigen‑sub`, `x‑eigen‑roles`, `x‑eigen‑tenant`) into gRPC metadata for internal calls.

### Kernel (Rust) – Security Module Hook

- **Trait**: `SecurityModule`

- **Method**: `check(task: &Task, device: &DeviceInfo) -> Result<(), SecurityError>`

- **Purpose**: Placeholder for future isolation checks; in MVP, logs the request and returns `Ok(())` by default.

### Internal gRPC Metadata Headers

- `x‑eigen‑sub`: User/Service identifier.

- ``x‑eigen‑roles``: Comma‑separated list of roles (e.g., `user,researcher`).

- `x‑eigen‑tenant`: Optional tenant/organization ID.

- `traceparent`: W3C TraceContext for observability.

## Inputs / Outputs

| **Input** | **Source** | **Description** |
|-------------------|-------------------|-------------------|
| API Key / Token | HTTP/gRPC Header | Provided by client via `Authorization` header. |
| JobSpec (YAML) | Client → System API | Validated for safety (no secrets, size limits). |
| Security Context | System API → Kerneln | Propagated via gRPC metadata. |
| Device Info | Driver Manager → Kernel | Used for isolation hook (device capabilities, status). |

---

| **Output** | **Destination** | **Description** |
|-------------------|-------------------|-------------------|
| AuthZ Decision | System API → Client | Allow/Deny with gRPC status (`PERMISSION_DENIED`, `UNAUTHENTICATED`). |
| Audit Log Entry | Local log file / stdout | Structured JSON log of security‑relevant events. |
| Security Metrics | Prometheus endpoint | Counters for auth successes/denials, validation errors. |

## Storage / State

- **Role‑Permission Mapping**: Static configuration file (e.g., `configs/security.yaml`), loaded at startup.

- **Audit Logs**: Written to local disk (JSONL format) under `/var/log/eigen/audit.log`.

- **Security Context Cache**: In‑memory cache in System API for validated tokens (optional, TTL‑based).

## Failure Modes

| **Failure** | **Detection** | **Mitigation** |
|-------------------|-------------------|-------------------|
| Invalid/Missing Token | System API interceptor | Return `UNAUTHENTICATED` (gRPC status `16`). |
| Insufficient Permissions | Authorization engine | Return `PERMISSION_DENIED` (gRPC status `7`). |
| Malformed JobSpec | Input validation | Return `INVALID_ARGUMENT` (gRPC status `3`) with details. |
| Security Module Unavailable | Kernel health check | Log warning; proceed without isolation check (MVP fallback). |
| Audit Log Write Failure | File I/O error | Log to stderr as fallback; increment metric `security_audit_failures`. |

## Observability

### Metrics (Prometheus)

- `security_auth_attempts_total{outcome="success|denied"}`

- `security_permission_checks_total{resource,action,allowed}`

- `security_validation_errors_total{type}`

- `security_audit_events_total`

### Logs (JSON)
```json
{
  "timestamp": "2026-01-10T10:30:00Z",
  "level": "INFO",
  "service": "system-api",
  "trace_id": "abc123",
  "job_id": "job-xyz",
  "user": "user@example.com",
  "roles": ["user"],
  "action": "SubmitJob",
  "resource": "jobs",
  "allowed": true
}
```

### Traces

- Security‑relevant spans (auth, validation) are included in the end‑to‑end trace.

- Span tags: `user`, `roles`, `resource`, `action`, `outcome`.

---

## Implementation Notes for MVP

1. **Authentication**: Simple API‑key validation (symmetric tokens). OIDC integration is post‑MVP.

2. **Authorization**: Static role‑permission mapping defined in YAML. No dynamic policy engine.

3. **Isolation**: The `SecurityModule` in the kernel is a stub that logs and approves all requests. Real hardware‑level isolation is Phase 2+.

4. **Input Validation**: Basic checks for payload size, forbidden patterns (e.g., `exec`, `eval`), and allowed imports (Eigen‑Lang DSL only).

5. **Audit**: All security‑sensitive actions (job submission, device reservation) are logged with user context.

6. **Network Security**: All internal services (Kernel, Compiler, Driver Manager) are on a private Docker network. No public exposure.