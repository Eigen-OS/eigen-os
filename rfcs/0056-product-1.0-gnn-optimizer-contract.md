# RFC 0056 — Product 1.0 GNN Optimizer Contract

## Status

Draft

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

## Non-goals

- changing the compiler contract itself
- introducing hidden state across compile/optimize boundaries

## Compatibility

This RFC is intended to be backward-compatible unless a major contract decision is explicitly approved.
