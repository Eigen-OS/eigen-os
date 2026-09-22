# RFC-0047: Phase-9B Intelligence Closure Contract v1

- Status: Proposed
- Created: 2026-05-20
- Target milestone: Phase-9B Intelligence Closure
- Depends on: RFC-0032, RFC-0034, RFC-0035, RFC-0036

## Summary

This RFC defines normative contracts for Stage-B of the Phase-9 open-core plan: Knowledge Base hardening, deterministic Pattern Miner recommendations, DPDA/GNN quality feedback closure, and Continuous Learning reproducibility with safe canary rollback.

## Motivation

TZ v1.3.0 requires a data-centric self-learning loop. Existing contracts provide partial coverage but do not fully specify deterministic fallback and reproducibility safeguards required for production-grade learning in open core.

## Normative requirements

1. **KB immutability:** Circuit/Pattern/Task records are append-only. Correction happens via superseding records, never in-place mutation.
2. **Anonymization:** user identity in KB-facing records MUST be anonymized before persistence; plaintext identifiers are forbidden in persistent KB payloads.
3. **Pattern Miner determinism:** For the same dataset snapshot and configuration digest, Pattern Miner output MUST be byte-for-byte reproducible.
4. **Recommendation contract:** Compiler-facing recommendation payloads MUST include version, provenance, confidence, and expiry metadata.
5. **Deterministic compiler fallback:** Missing, stale, malformed, or below-threshold recommendations MUST trigger deterministic baseline compile behavior.
6. **Quality metrics schema:** GNN/DPDA quality outputs MUST include at least swap_count, predicted_error, observed_error (when available), and runtime_ms.
7. **Promotion gates:** Model promotion MUST fail closed when non-regression thresholds are violated.
8. **Retrain reproducibility:** Every model version MUST be reproducible from a snapshot manifest, config digest, code revision, and artifact hash set.
9. **Canary rollback:** Canary rollout MUST auto-rollback to previous stable version when regression gates fail and MUST emit stable reason codes.

## Versioning and compatibility

- Contract changes follow RFC-0032 SemVer policy.
- Breaking payload or behavior changes require MAJOR bump and migration notes.
- Compatibility fixtures for recommendation and quality schemas are mandatory.

## Conformance evidence

Phase-9B exit requires:

- reproducible training replay evidence;
- canary rollback drill evidence;
- benchmark uplift or non-regression report;
- fixture-based contract conformance results.

## Security and privacy

- KB persistence path MUST enforce anonymization before durable write.
- Audit events for retrain/promotion/rollback MUST include actor identity (service principal), reason code, and artifact digests.

## Open questions

- Threshold defaults for confidence and non-regression may start as conservative defaults and be tuned by MINOR revisions.
