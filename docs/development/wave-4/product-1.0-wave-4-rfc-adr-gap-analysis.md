# Product 1.0 Wave 4 RFC / ADR Gap Analysis

**Wave:** Product 1.0 Wave 4  
**Status:** Governance closure record  
**Created:** 2026-06-06  
**Updated:** 2026-06-11

---

## 1. Purpose

Wave 4 required explicit governance records for runtime persistence, replay semantics, security enforcement, REST mirror publication, and Knowledge Base lineage. This document now records the final closure set and the evidence that those decisions are synchronized with the implementation snapshot.

---

## 2. Mandatory Wave 4 governance records

| ID | Type | Title | Status | Reason |
|---|---|---|---|---|
| RFC-0051 | RFC | Product 1.0 QFS storage authority and retention semantics | Proposed | Defines the authoritative QFS L1/L2/L3 retention and ownership boundary needed for Wave 4 closure |
| ADR-0037 | ADR | QFS live qubit / reservation split authority | Accepted | Live-resource semantics are now explicitly split between Kernel/QRTX and the future Resource Manager boundary |
| ADR-0038 | ADR | Product 1.0 checkpoint envelope and restore compatibility policy | Accepted | Checkpoint replay and restore compatibility are now frozen |
| RFC-0052 | RFC | Product 1.0 security identity and fail-closed policy | Proposed | Defines the public/internal security posture required for Product 1.0 closure |
| ADR-0039 | ADR | Product 1.0 public REST schema parity policy | Accepted | The OpenAPI-first REST mirror publication model is now frozen |
| ADR-0040 | ADR | Product 1.0 Knowledge Base decision-log lineage contract | Accepted | The canonical replay-safe KB decision-log shape is now frozen |

---

## 3. Closure evidence

The following evidence closes the Wave 4 governance gaps:

- `docs/development/wave-4/product-1.0-wave-4-compatibility-report.md`
- `docs/development/wave-4/product-1.0-wave-4-release-readiness-checklist.md`
- `docs/development/wave-4/product-1.0-wave-4-exit-evidence-bundle.md`
- `docs/development/wave-4/product-1.0-wave-4-public-parity-matrix.md`
- `docs/development/wave-4/product-1.0-wave-4-w4-06-privacy-policy-compatibility-report.md`
- `docs/development/wave-4/product-1.0-wave-4-w4-06-exit-evidence-bundle.md`

---

## 4. Resolution notes

### 4.1 QFS L1 ownership

Resolved by ADR 0037. Kernel/QRTX owns live execution reservation tokens and lease TTLs; Resource Manager remains the future scheduling authority.

### 4.2 Checkpoint compatibility policy

Resolved by ADR 0038. Checkpoint envelopes now have explicit restore compatibility semantics and deterministic replay expectations.

### 4.3 REST publication model

Resolved by ADR 0039. The Product 1.0 public REST mirror uses a schema-first OpenAPI publication model under `contracts/product-1.0/`.

### 4.4 Decision-log replay structure

Resolved by ADR 0040. The Knowledge Base decision-log shape now captures replay-safe lineage, provenance, anonymization, and retention boundaries.

### 4.5 Security identity and fail-closed policy

Resolved by RFC 0052 and the existing System API security tests. Public ingress must fail closed, carry normalized service identity, and persist immutable audit evidence.

---

## 5. Closure requirement

Wave 4 can be marked complete because:

- all mandatory RFCs and ADRs now exist and are cross-linked from the closure evidence,
- unresolved `TBD` governance notes have been removed from the Wave 4 closure package,
- manifest and inventory references are synchronized with the published closure artifacts,
- and the Wave 4 evidence bundle references the approved governance records.

## 6. Migration notes for MAJOR deltas

The only MAJOR wave delta is the QFS live-resource ownership boundary captured in ADR 0037 and the associated RFC 0051. No public API breaking change is required for the REST, KB, or observability closure slices.
