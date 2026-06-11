# RFC-0052: Product 1.0 security identity and fail-closed policy

- Status: Proposed
- Created: 2026-06-11
- Target milestone: Product 1.0 Wave 4 security closure
- Depends on: RFC-0050, RFC-0051, docs/reference/security/authz.md, docs/architecture/components/security-isolation.md, docs/reference/error-model.md

## Summary

This RFC defines the Product 1.0 security identity and fail-closed posture for public ingress and internal service calls. It freezes the normalized identity model, policy snapshot requirements, audit requirements, and the canonical denial semantics used by the Wave 4 security baseline.

## Motivation

Wave 4 closure requires that public ingress behave deterministically when authentication, authorization, or policy loading fails. Security behavior must be fail-closed, must preserve service identity, and must remain compatible with the canonical error model and trace context requirements already used by System API.

## Goals

- Define the minimum security identity model for public and internal calls.
- Freeze fail-closed behavior for policy, authentication, and authorization failures.
- Preserve immutable audit evidence and sanitized security metadata.
- Align the closure package with the Wave 4 security and isolation implementation.

## Non-Goals

- Introducing new public authorization scopes.
- Changing the canonical error mapping.
- Reworking the internal security module architecture beyond the Product 1.0 boundary.

## Reference-level design

- Public ingress must require JWT/OAuth2 or the configured static bearer mode used by local/test deployments.
- Internal service calls must carry normalized service identity and method-level authorization context.
- Security policy must be versioned and must fail closed when missing or invalid.
- Audit sinks must remain append-only and must record trace correlation metadata.
- Sandbox enforcement must reject disallowed profiles rather than defaulting to permissive access.

## Security and privacy

The policy explicitly prohibits leaking secrets, raw tokens, or unsafe backend payloads in public errors. Denials must map to canonical public status codes and include stable reason metadata only.

## Observability

Security denials and audit decisions must be reflected in bounded contract-marker metrics and traceable logs. Trace continuity must survive authentication, authorization, and sandbox checks.

## Implementation and migration

- Keep the current System API security baseline compatible for Product 1.0 callers.
- Use the new RFC/ADR set only to document the accepted fail-closed behavior.
- No migration notes are required unless a later change alters the public denial contract.

## Considered alternatives

- Allowing missing policy snapshots to pass through as warnings.
- Delegating identity enforcement to callers.
- Treating service identity as optional.

All alternatives are rejected because Product 1.0 requires deterministic fail-closed security semantics.

## Acceptance criteria

- Authentication and authorization failures are deterministic.
- Policy load failures fail closed.
- Audit evidence is immutable.
- The Wave 4 closure package can cite this RFC as the governance record for the security MAJOR delta.
