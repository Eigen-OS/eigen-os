# RFC 0013: MVP-2 JobSpec Parser and Submit Contract

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-24
- **Target Milestone**: Phase 0 (MVP-2)
- **Tracking Issue**: #113
- **Replaces / Related**: RFC 0003, RFC 0004, ADR 0003

## Summary

Define the MVP-2 contract for transforming `job.yaml` (JobSpec v0.1) into a canonical `SubmitJobRequest` payload, with deterministic validation, field-level diagnostics, and reproducible packaging behavior for CLI and services.

## Motivation

MVP-2 depends on a stable and testable boundary between user-facing JobSpec files and System API requests. Without a formal RFC, parser behavior can drift across CLI, tests, and service implementations.

## Goals

- Standardize JobSpec parsing and validation behavior for MVP-2.
- Make request construction deterministic for fixture-based testing.
- Guarantee consistent `INVALID_ARGUMENT` diagnostics for invalid input.
- Freeze required field mapping from JobSpec to `SubmitJobRequest` for v0.1.

## Non-Goals

- Introducing a new JobSpec version beyond `eigen.os/v0.1`.
- Expanding MVP-2 to advanced scheduling or multi-file package manifests.
- Defining post-MVP policy engines for admission control.

## Guide-level Explanation

A user runs `eigen submit -f job.yaml`. The tooling:

1. Loads `job.yaml`.
2. Verifies schema and semantic constraints.
3. Resolves program descriptor + source path references.
4. Builds `SubmitJobRequest` with canonical field mapping.
5. Emits precise field violations on invalid data.

This behavior must be identical in CLI tests and backend integration tests.

## Reference-level Design

## Interfaces / APIs

- Input: JobSpec file (`apiVersion: eigen.os/v0.1`).
- Output: protobuf `SubmitJobRequest` compatible with `JobService.SubmitJob`.
- Error surface: gRPC status `INVALID_ARGUMENT` + `google.rpc.BadRequest.FieldViolation` details.

Canonical mapping requirements:

- `apiVersion` must equal `eigen.os/v0.1`.
- Program source and entrypoint descriptors are mandatory.
- Quantum constraints (`qubits`, `shots`, target device) must pass range and presence checks.
- Client-request idempotency key handling must remain deterministic.

## Data Models

- JobSpec remains versioned as v0.1 for MVP-2.
- Mapping rules are additive-only for MVP freeze window.
- Any breaking mapping change requires a follow-up RFC.

## Security and Privacy

- Reject path traversal and unsafe file reference patterns during packaging.
- Cap input size to avoid parser memory abuse.
- Never execute user-provided source while validating metadata.

## Observability

- Emit structured validation error logs with request correlation IDs.
- Track parser outcomes (`success`, `invalid_schema`, `invalid_semantics`).
- Preserve trace context into submission path.

## Performance

- Parser should remain linear with respect to input size.
- Fixture tests should assert stable behavior without nondeterministic timestamps.
- Validation overhead target: negligible relative to compile + execute path.

## Testing Plan

- Positive fixture set (`job.yaml` → expected `SubmitJobRequest`).
- Negative fixture set with field-level diagnostics.
- CLI integration tests verifying outgoing request shape.
- CI gate requiring deterministic fixture output.

## Implementation / Migration

1. Finalize mapping table in reference docs.
2. Implement/lock parser behavior in shared library.
3. Add deterministic fixture tests.
4. Enforce checks in CI.
5. Promote RFC status after MVP-2 validation.

## Considered Alternatives

- **Loose YAML pass-through**: rejected (too ambiguous for compatibility).
- **Service-only parsing without CLI parity**: rejected (drift risk).

## Open Questions

- Should MVP-2 require explicit program path override when multiple candidates exist?
- What is the final policy for optional metadata fields at freeze time?
