# RFC 0009: Security & Isolation MVP: authz, validation, isolation hooks

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0004,0007

## Summary

Defines MVP access control model and isolation checks before scheduling on real devices.

## Motivation

Even in MVP, we need clear permission boundaries and input validation to avoid unsafe execution and resource misuse.

## Goals

- Define role/permission model (`resource:action`).
- Validate inputs at system-api boundary.
- Provide kernel hooks for isolation constraints.

## Non-Goals

- Full OIDC integration.
- Hardware-level isolation guarantees (vendor-specific).

## Guide-level explanation

### Auth context propagation (internal)

System API is the only public ingress. After authenticating the caller, it forwards a minimal auth context to internal services via gRPC metadata:

- `x-eigen-sub` (subject / user id)
- `x-eigen-roles` (comma-separated roles)
- `x-eigen-tenant` (optional tenant/org)
- `traceparent` (for correlation)

Kernel MUST include these fields in audit logs for job submission and device reservation.


system-api authenticates the caller and maps to roles.
Authorization checks use permissions like `jobs:submit`, `jobs:read`, `devices:list`, `devices:reserve`.
Kernel calls Security Module before allocating live qubits.

## Reference-level design

### Interfaces / APIs

system-api interceptors enforce authn/authz.
Kernel isolation hook: `SecurityModule.check(task, device) -> decision`.

### Data model

Roles:
- admin: `*`
- user: `jobs:*`, `devices:list`, `devices:status`
- readonly: `jobs:read`, `devices:list`
Audit log includes `subject`, `action`, `resource`, `job_id`.

### Error model

Permission denied returns gRPC PERMISSION_DENIED. Invalid input returns INVALID_ARGUMENT.

### Security & privacy

Reject oversized payloads.
Program source must be scanned for prohibited imports (MVP optional, Phase 1 stronger sandboxing).
All internal services are network-restricted.

### Observability

Security events are logged with audit fields. Metrics include denied counts per endpoint.

### Performance notes

Authz checks must be constant-time lookups (cached roles).

## Testing plan

Unit tests for permission matrices; integration tests for denied actions.

## Rollout / Migration

Start with API key / static token auth for MVP; upgrade to OIDC later.

## Alternatives considered

- No auth in MVP (rejected: public OSS still needs safe defaults).

## Open questions

- How to handle multi-tenant device reservation?
