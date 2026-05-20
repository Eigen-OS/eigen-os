# P9B-01 — KB Immutability + Anonymization + Index Profile Hardening

## Scope

This Stage-9B specification closes the KB hardening gap by defining immutable ingest semantics, deterministic user-id anonymization requirements, and indexed-query latency SLO evidence gates.

Normative references:
- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`
- `rfcs/0034-phase8a-knowledge-base-api-contract-v1.md`
- `rfcs/0047-phase9b-intelligence-closure-contract-v1.md`

## 1) Immutable Knowledge Records

### Record classes in scope
- `Circuit`
- `Pattern`
- `Task`

### Contract rules
- Ingest is append-only: a persisted `(record_type, record_id, ingest_seq)` tuple is immutable after write success.
- Post-ingest mutation operations are rejected with stable reason code `KB_IMMUTABILITY_VIOLATION`.
- Supersession uses additive versioning only (`record_version = previous + 1`), never in-place overwrite.
- Every rejected mutation must emit an audit event containing:
  - `record_type`
  - `record_id`
  - `actor_anonymous_id`
  - `trace_id`
  - `reason_code`
  - `timestamp_utc`

## 2) User-ID Anonymization Hardening

### Runtime constraints
- Runtime query/write path MUST never expose raw user identifiers in record payloads, indexes, or audit attributes.
- Runtime mapping from raw user identifier to anonymized identifier is one-way only.
- Reversible mapping in runtime path is prohibited.

### Salt policy
- Anonymization digest:
  - `algorithm`: `HMAC-SHA256`
  - `id_format`: `anon:<salt_epoch>:<hex_digest_32>`
- Salt epochs are versioned and rotatable.
- Rotation policy metadata is required in contract artifacts:
  - `rotation_period_days`
  - `overlap_acceptance_days`
  - `max_runtime_salt_epochs`
- During overlap window, prior epoch digests remain queryable for backward compatibility; new writes use current epoch.

## 3) Index Profile + Latency SLO Gate

### Required index profile artifact
Publish a versioned artifact for structural/vector retrieval profile containing:
- `profile_version`
- `structural_indexes`
- `vector_indexes`
- `query_dimensions`
- `max_result_window`

### Required SLO envelope
- Structural indexed search `p95 <= 100ms`
- Vector search `p95 <= 180ms`
- Composite hybrid search `p95 <= 220ms`

### Required CI evidence
A deterministic fixture-backed CI gate must fail closed when:
- latency SLO envelope is violated;
- index profile drift occurs without SemVer metadata update;
- immutable write conformance regressions are detected.

## 4) Versioning and Compatibility

- Additive capability introduction (immutability error code, anonymization policy metadata, index profile artifact): `MINOR`.
- Any behavioral rewrite that permits post-ingest mutation or removes anonymization guarantees: `MAJOR`.
- CI and fixture updates are versioned artifacts and must be drift-tested.
