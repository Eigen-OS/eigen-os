# RFC 0035: Phase-8A GNN Optimizer Service Contract v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-05-16
- **Target Milestone**: Phase 8A
- **Tracking Issue**: M8A-02

## Summary

Defines the v1 contract for the GNN optimizer service that transforms input AQO/topology context into mapped AQO candidates with quality scores and explainability metadata.

## Goals

- Lock optimizer request/response schema for compiler-runtime integration.
- Provide deterministic fallback semantics when model path is unavailable.
- Define scoring and artifact lineage requirements.

## Non-goals

- Training data pipeline design (covered by learning control-plane RFC).
- Provider-specific calibration strategy.

## Reference-level design

### Request

`OptimizeRequest` includes:
- input `aqo`;
- topology graph/profile;
- noise snapshot reference;
- optimization objective preset;
- deterministic seed.

### Response

`OptimizeResponse` includes:
- mapped `aqo` candidate list;
- `score` and score breakdown;
- selected candidate ID;
- explainability summary;
- `model_version` and `fallback_used` flag.

### Determinism and fallback

- Same input + seed must be replay-stable in contract tests.
- If model unavailable or confidence below threshold, return heuristic baseline with `fallback_used=true`.

### Error model

- `OPT_INVALID_AQO`
- `OPT_TOPOLOGY_MISSING`
- `OPT_MODEL_UNAVAILABLE`
- `OPT_TIMEOUT`
- `OPT_INTERNAL`

## Observability

- optimization latency buckets;
- fallback ratio;
- score distribution trend;
- confidence/quality drift indicators.

## Test plan

- Golden fixtures for optimizer I/O compatibility.
- Seeded determinism replay tests.
- Fallback path conformance tests.

## Compatibility and versioning

- **Version impact:** optimizer API contract `1.0.0`.
- **Compatibility:** new optional score fields are `MINOR`; response semantic changes are `MAJOR`.

## Open questions

- Minimum explainability payload for external clients.
- Normalization policy for score comparability across backends.
