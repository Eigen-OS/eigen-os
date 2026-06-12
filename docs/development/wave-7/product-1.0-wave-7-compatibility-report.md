# Product 1.0 Wave 7 Compatibility Report

**Wave:** Product 1.0 Wave 7 — Neuro-Symbolic Compiler and GNN Optimizer
**Status:** Planning baseline

## Summary

Wave 7 is a contract-freeze wave for compiler and optimizer semantics.
The expected compatibility outcome is deterministic replay across the compiler-to-optimizer boundary.

## Contract areas

### Compiler

- Eigen-Lang lowering
- AQO normalization
- compiler error mapping
- artifact lineage

### Optimizer

- graph encoding
- scoring and ranking
- fallback heuristics
- confidence reporting

### Handoff

- compiler output envelope
- optimizer input envelope
- stable identifiers
- versioned boundary metadata

## Compatibility rules

1. identical inputs must produce identical normalized outputs,
2. unsupported inputs must fail deterministically,
3. explainability metadata must not alter execution semantics,
4. persistence metadata must not affect optimizer decisions.

## Closure requirements

- compatibility checked against inventory,
- RFCs accepted,
- ADRs accepted,
- evidence bundle published.
