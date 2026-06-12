# Product 1.0 Wave 7 RFC / ADR Gap Analysis

**Wave:** Product 1.0 Wave 7 — Neuro-Symbolic Compiler and GNN Optimizer
- **Status:** Complete

---

## 1. Purpose

This document identifies the RFC and ADR updates required to close Wave 7.

---

## 2. Gaps

### 2.1 Compiler contract gap

The current architecture and MVP surfaces already describe the compiler boundary, but Wave 7 requires a frozen Product 1.0 compiler contract with:

- deterministic Eigen-Lang lowering,
- normalized AQO emission,
- stable compiler error taxonomy,
- replay-safe artifact references.

### 2.2 GNN optimizer contract gap

The optimizer architecture exists, but Product 1.0 needs a contract that freezes:

- graph input encoding,
- scoring semantics,
- ranking / selection semantics,
- fallback behavior,
- explainability payloads.

### 2.3 Handoff gap

The boundary between compiler output and optimizer input must be versioned explicitly and backed by a deterministic AQO / IR handoff.

### 2.4 Observability gap

The optimizer path needs explicit explainability and bounded metrics so release evidence can be generated deterministically and reviewed against the same Product 1.0 evidence chain as the compiler.

### 2.5 Persistence / evidence gap

Compiler and optimizer outputs need a release-evidence shape aligned with QFS artifact persistence, provenance, and replay validation.

---

## 3. Required RFCs

1. Product 1.0 Neuro-Symbolic Compiler Contract
2. Product 1.0 GNN Optimizer Contract
3. Product 1.0 Compiler ↔ Optimizer Handoff Contract
4. Product 1.0 Optimization Explainability Contract

---

## 4. Required ADRs

1. Neuro-Symbolic compiler boundary decision record
2. GNN optimizer boundary decision record
3. Compiler/optimizer handoff versioning decision record
4. Explainability and evidence bundle decision record

---

## 5. Decision outcomes expected before closure

- compiler contract frozen,
- optimizer contract frozen,
- handoff schema frozen,
- observability frozen,
- evidence bundle frozen,
- inventory synchronized,
- manifest synchronized.
- existing MVP compiler path integrated with the GNN optimizer contract,
- release notes updated for any compatibility-breaking behavior.

## 6. Closure

All required RFCs and ADRs for Wave 7 are accepted, the compiler and optimizer contracts are
frozen, the handoff boundary is versioned, and the inventory/manifest are synchronized.
