# ADR 0025: Phase-8B QFS-L2/L3 Data Fabric Hardening Contract v1

- **Status**: Accepted
- **Date**: 2026-05-17
- **Decision owners**: Data/Storage, Runtime/Core, Architecture/Governance
- **Supersedes / Related**: RFC 0039, ADR 0023, ADR 0018

## Context

Phase-8B hardens QFS persistence beyond the Phase-8A checkpoint envelope baseline. RFC 0039 defines strict QFS-L3 artifact layout and metadata invariants, deterministic retention and indexing behavior, and QFS-L2 checkpoint/restore admission controls with budget guardrails.

## Decision

Adopt RFC 0039 as the operational baseline for QFS-L2/L3 data-fabric hardening contract v1:

1. QFS-L3 artifacts must follow strict layout, naming, and metadata invariants.
2. Retention execution must produce deterministic cleanup reason codes and preserve auditability.
3. Metadata indexing must support trace-linked lookup across artifacts, checkpoints, and runtime evidence.
4. QFS-L2 checkpoint/restore must enforce schema, checksum, compatibility, size, and time-budget guardrails before admission.
5. Integrity and replay compatibility suites are required CI evidence for release closure.

## Consequences

- Artifact and checkpoint consumers can rely on stable layout, indexing, and restore semantics.
- Storage cleanup and restore failures become diagnosable through deterministic reason codes.
- Future QFS envelope or restore-semantic breakage requires MAJOR classification and migration notes.

## Verification and evidence

- RFC source: `rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md`
- Phase-8B fixture gate: `docs/development/fixtures/phase8b/ci_gate_bundle_v1.json`
- Gate entrypoint: `scripts/ci/check-phase8b-gates.sh`
- Phase-8B closure docs: gap analysis, readiness checklist, compatibility report, and exit evidence bundle
