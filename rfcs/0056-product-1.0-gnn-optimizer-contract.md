# RFC 0056 — Product 1.0 GNN Optimizer Contract

## Status

Accepted

## Summary

Define the frozen optimizer contract for Product 1.0.

## Motivation

The optimizer must provide deterministic scoring, stable metadata, and explainable outputs for the neuro-symbolic pipeline.

## Scope

- graph encoding
- scoring semantics
- ranking / policy selection
- fallback behavior
- confidence metadata
- optimizer observability hooks
- deterministic replay semantics
- optimizer digest semantics

## Normative contract

The frozen Product 1.0 optimizer contract requires:

- a canonical graph encoding with an explicit encoding version and canonical SHA-256 digest,
- deterministic ranking semantics using score, confidence, and stable candidate-id tie-breakers,
- deterministic replay for identical `(input_aqo, topology, objective, deterministic_seed)` tuples,
- fallback when graph features are incomplete, with a stable fallback reason code,
- confidence reporting in the closed interval `[0..1]`,
- bounded explainability references that do not affect execution semantics,
- a reproducibility digest covering canonical request inputs and canonical outputs.

## Fallback semantics

If the model path is unavailable, the confidence threshold is not met, or graph features are incomplete, the optimizer must return a deterministic fallback result instead of introducing nondeterministic output.

The fallback path must preserve the original deterministic seed, populate `fallback_used=true`, provide a non-empty `fallback_reason`, and set a stable `fallback_reason_code` from the `EIGEN_OPT_*` family.

## Non-goals

- changing the compiler contract itself
- introducing hidden state across compile/optimize boundaries
- changing the public API surface
- allowing explainability payloads to influence ranking decisions

## Compatibility

This RFC is backward-compatible because the frozen surface is expressed as additive fields and deterministic semantics on the existing internal optimizer namespace. Any future change that alters ranking order, fallback rules, or confidence semantics is a major contract change.
