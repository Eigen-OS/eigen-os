# RFC 0055 — Product 1.0 Neuro-Symbolic Compiler Contract

## Status

Draft

## Summary

Define the frozen compiler contract for Product 1.0.

## Motivation

The compiler pipeline must be deterministic, explainable, and compatible with the Product 1.0 contract inventory.

## Scope

- Eigen-Lang lowering
- semantic validation
- AQO normalization
- compiler error taxonomy
- trace and artifact lineage

## Non-goals

- changing public API surfaces outside compiler-related contracts
- introducing nondeterministic optimization behavior

## Compatibility

This RFC is intended to be backward-compatible unless a major contract decision is explicitly approved.
