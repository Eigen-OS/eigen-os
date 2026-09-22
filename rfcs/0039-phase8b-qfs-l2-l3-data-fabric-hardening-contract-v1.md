# RFC 0039: Phase-8B QFS-L2/L3 Data Fabric Hardening Contract v1

- **Status:** Accepted
- **Date:** 2026-05-17
- **Authors:** Data/Storage + Runtime/Core
- **Phase:** 8B

## Summary
Defines Phase-8B v1 hardening contract for QFS-L3 artifact layout/retention/indexing and QFS-L2 checkpoint/restore runtime guardrails.

## Motivation
Reliable persistence, replay safety, and bounded operational cost need explicit contracts and deterministic failure semantics.

## Proposal
1. Lock strict artifact layout and metadata invariants for QFS-L3.
2. Define retention-policy execution model with stable cleanup reason codes.
3. Define metadata indexing guarantees for trace-linked retrieval.
4. Define QFS-L2 checkpoint/restore admission controls and budget guardrails.
5. Require integrity suite coverage for decode/replay compatibility.

## Backward compatibility
- New optional metadata keys use `MINOR` with deterministic defaults.
- Envelope or restore semantic breakage requires `MAJOR` + migration notes.

## Acceptance
- Integrity and retention fixtures are versioned and CI-enforced.
- Unsupported/invalid operations return stable reason codes with hints.
