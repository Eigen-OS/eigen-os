# RFC 0017: MVP-3 Results Persistence, Retrieval, and CLI Runtime UX

- **Status**: Draft
- **Authors**: Eigen OS maintainers
- **Created**: 2026-04-25
- **Target Milestone**: Phase 0 (MVP-3)
- **Tracking Issue**: docs/development/mvp-3-tracking-issue.md
- **Replaces / Related**: RFC 0010, RFC 0011, docs/development/mvp-3-execution-and-results.md

## Summary

Define canonical MVP-3 behavior for persisting runtime results, serving immutable `GetJobResults` payloads, and delivering consistent CLI `status/watch/results` user experience.

## Motivation

Compilation readiness is complete in MVP-2, but runtime usability depends on deterministic retrieval contracts and clear CLI behavior for active and terminal jobs.

## Goals

- Freeze canonical QFS artifact layout for runtime result outputs.
- Ensure `GetJobResults` semantics are deterministic for both ready and not-ready states.
- Align CLI `status`, `watch`, and `results` commands with API semantics and terminal exits.
- Define failure handling for jobs that end in `ERROR`, `CANCELLED`, or `TIMEOUT`.

## Non-Goals

- Rich visualization UX or dashboard output formatting.
- Historical analytics APIs across many jobs.
- Cross-region artifact replication strategy.

## Guide-level Explanation

For each `job_id`, runtime outputs must be persisted once in canonical QFS paths under `results/` and `meta/`. Once a job reaches `DONE`, `GetJobResults` returns stable payload data across repeated reads. Before terminal completion, API responses must clearly communicate not-ready state without ambiguous partial success.

CLI behavior in MVP-3:

- `eigen status <job_id>` prints current state and latest known metadata.
- `eigen watch <job_id>` follows state progression and exits exactly on terminal state.
- `eigen results <job_id>` prints normalized counts + metadata for `DONE`; for failed jobs, returns non-zero with actionable reason.

## Reference-level Design

## Interfaces / APIs

- Public RPC: `GetJobResults(job_id)`
  - `DONE`: returns result payload + metadata.
  - `PENDING|COMPILING|RUNNING`: returns not-ready semantic (`FAILED_PRECONDITION` or documented equivalent).
  - unknown `job_id`: returns `NOT_FOUND`.

- CLI exit behavior:
  - success terminal -> exit code `0`
  - runtime failure terminal -> non-zero
  - transport/API failure -> non-zero with canonical mapped message

## Data Models

Canonical persisted artifacts for each job:

- `results/result.json`: normalized counts payload.
- `meta/runtime.json`: execution metadata (`target`, `shots`, duration, correlation ids).
- `meta/error.json` (optional for failed jobs): canonical failure details.

Result payload invariants:

- `counts` map key format is stable and documented.
- metadata fields are ordered/serialized deterministically for fixture comparisons.

## Security and Privacy

- Result retrieval enforces auth/authz policy at API boundary.
- Result payloads omit raw sensitive internals and include only canonical diagnostic fields.
- Failed job metadata must avoid leaking backend secrets.

## Observability

- `GetJobResults` and CLI calls emit trace-linked logs with `job_id`.
- Result retrieval metrics include success/error/not-ready counters.
- CLI watch sessions produce terminal summary logs for troubleshooting.

## Performance

- Repeated `GetJobResults` for terminal jobs should avoid recomputation.
- Result retrieval from QFS should be bounded and predictable.
- CLI watch polling cadence must balance responsiveness and API load.

## Testing Plan

- API tests for `DONE`, not-ready, and `NOT_FOUND` responses.
- Byte-stability tests for repeated result reads of a completed job.
- CLI integration tests for terminal exit behavior and readable output.
- Failure-path tests ensuring `results` command reports actionable diagnostics.

## Implementation / Migration

1. Freeze QFS result artifact paths and serialization contract.
2. Implement deterministic retrieval path and not-ready behavior.
3. Align CLI `status/watch/results` with terminal semantics.
4. Add e2e fixtures covering success and failure terminal jobs.

## Considered Alternatives

- **Return partial results in RUNNING**: rejected for MVP consistency.
- **CLI auto-retry in `results` by default**: rejected; explicit `watch` command is clearer.

## Open Questions

- Should `GetJobResults` on failed jobs return structured error payload in-band or rely solely on status + details?
- Do we freeze a human-readable table format in CLI output for MVP-3, or only semantic fields?
