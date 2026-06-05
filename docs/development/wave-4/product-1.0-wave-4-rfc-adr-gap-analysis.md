# Product 1.0 Wave 4 RFC / ADR Gap Analysis

**Wave:** Product 1.0 Wave 4  
**Status:** Governance planning baseline  
**Created:** 2026-06-06

---

## 1. Purpose

Wave 4 introduces architectural decisions that materially affect runtime persistence, replay semantics, security enforcement, and public mirror compatibility. These changes require explicit governance records before implementation closes.

This document tracks the RFCs and ADRs required for Wave 4 closure.

---

## 2. Mandatory Wave 4 governance records

| ID | Type | Title | Status | Reason |
|---|---|---|---|---|
| RFC-0051 | RFC | Product 1.0 QFS storage authority and retention semantics | Required | QFS L1/L2/L3 ownership and retention rules affect runtime determinism and replay behavior |
| ADR-0037 | ADR | QFS live-resource ownership boundary | Required | Product 1.0 must define whether live-resource semantics belong to QFS, Resource Manager, or a split boundary |
| ADR-0038 | ADR | Product 1.0 checkpoint envelope and restore compatibility policy | Required | Checkpoint compatibility affects replay and mixed-version restore behavior |
| RFC-0052 | RFC | Product 1.0 security identity and fail-closed policy | Required | Security posture changes are MAJOR behavioral changes for internal/runtime enforcement |
| ADR-0039 | ADR | Public REST schema parity policy | Required | Product 1.0 must freeze whether REST uses OpenAPI, JSON Schema, or a hybrid publication model |
| ADR-0040 | ADR | Knowledge Base decision-log lineage contract | Required | Runtime lineage and replay semantics require one canonical decision-log structure |

---

## 3. Cross-wave governance dependencies

| Dependency | Producing wave | Consuming wave | Reason |
|---|---|---|---|
| Kernel/QRTX lifecycle authority | Wave 2 | Wave 4 | QFS and audit lineage depend on canonical lifecycle ownership |
| Compiler artifact persistence handoff | Wave 3 | Wave 4 | QFS maturity must not reopen compiler ownership semantics |
| QFS live-resource ownership | Wave 4 | Wave 5 | Scheduling authority cannot stabilize until reservation ownership is frozen |
| Security identity propagation | Wave 4 | Wave 6+ | Driver Manager and optimizer contracts require normalized service identity |
| KB decision-log lineage | Wave 4 | Wave 7 and Wave 8 | Intelligent-runtime replay and optimization provenance depend on stable lineage semantics |

---

## 4. Required architectural clarifications

### 4.1 QFS L1 ownership ambiguity

Current documentation allows multiple interpretations:

- QFS-owned live-resource semantics,
- Resource Manager-owned semantics,
- or a split authority.

Wave 4 MUST freeze one authoritative model.

### 4.2 Checkpoint compatibility policy

The current architecture references checkpoints and replay but does not freeze:

- checkpoint compatibility windows,
- restore guarantees across versions,
- required metadata fields,
- deterministic replay constraints.

Wave 4 MUST define the compatibility envelope.

### 4.3 REST publication model

The Product 1.0 baseline requires schema artifacts but does not freeze:

- OpenAPI-only publication,
- JSON Schema-only publication,
- hybrid publication,
- or generation strategy.

Wave 4 MUST freeze the policy.

### 4.4 Decision-log replay structure

Knowledge Base lineage references exist, but the canonical replay-safe decision-log structure is not frozen.

Wave 4 MUST define:

- minimum replay payload,
- provenance references,
- retention policy,
- anonymization boundary,
- deterministic replay identifiers.

---

## 5. Closure requirement

Wave 4 cannot be marked complete until:

- all mandatory RFCs and ADRs are merged,
- unresolved `TBD` governance notes are removed,
- manifest and inventory references are synchronized,
- and the Wave 4 evidence bundle references the approved governance records.
