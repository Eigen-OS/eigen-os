# ADR 0023: Phase-8A QFS-L2 Checkpoint Envelope Contract v1

- **Status**: Accepted
- **Date**: 2026-05-16
- **Decision owners**: Runtime/Core, Data/Storage, Architecture/Governance
- **Supersedes / Related**: RFC 0037, ADR 0018, ADR 0019

## Context

Phase-8A checkpoint persistence and replay require a stable QFS-L2 envelope format that supports deterministic decoding across versions. RFC 0037 defines v1 envelope structure, trace-link requirements, and forward extension strategy.

## Decision

Adopt RFC 0037 as the operational baseline for QFS-L2 checkpoint envelope contract v1:

1. Envelope schema and metadata are SemVer-governed stable artifacts.
2. Trace-link identifiers across artifacts/datasets/checkpoints are mandatory.
3. Forward-compatible extension strategy requires deterministic defaulting behavior.
4. Contract drift and breaking changes are CI-gated with fail-closed policy.

## Consequences

- Replay and restoration workflows become version-safe and auditable.
- Persistence/query integrations can depend on stable envelope semantics.
- Future extensions can be introduced additively without disrupting existing consumers.

## Verification and evidence

- RFC source: `rfcs/0037-phase8a-qfs-l2-checkpoint-envelope-contract-v1.md`
- Synchronization pointers: `docs/rfcs-pointer.md`, `docs/development/README.md`
- Phase-8A closure docs: gap analysis, readiness checklist, compatibility report
