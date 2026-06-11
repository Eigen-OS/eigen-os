# Product 1.0 Wave 7 RFC / ADR Gap Analysis

**Wave:** Product 1.0 Wave 7 — Neuro-Symbolic Compiler and GNN Optimizer
**Status:** Planning baseline

---

## 1. Purpose

This document identifies the RFC and ADR updates required to close Wave 7.

---

## 2. Gaps

### 2.1 Compiler contract gap

Current architecture docs describe the compiler boundary, but Wave 7 requires a frozen Product 1.0 compiler contract with:

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

The boundary between compiler output and optimizer input must be versioned explicitly.

### 2.4 Observability gap

The optimizer path needs explicit explainability and bounded metrics so release evidence can be generated deterministically.

### 2.5 Persistence / evidence gap

Compiler and optimizer outputs need a release-evidence shape aligned with QFS artifact persistence and provenance.

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
