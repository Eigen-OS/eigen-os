# RFC 0035: Phase-8A GNN Optimizer Service Contract v1

- **Status**: Accepted
- **Authors**: Eigen OS maintainers
- **Created**: 2026-05-16
- **Target Milestone**: Phase 8A
- **Tracking Issue**: P8A-02

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

`OptimizeCircuitRequest` includes:
- `envelope.contract_version` (SemVer lock);
- stable `request_id`;
- input AQO payload (`input_aqo`);
- topology/noise/profile context (`topology`);
- objective preset + weighted objective map (`objective`);
- deterministic seed (`deterministic_seed`);
- bounded budget/timeout fields (`candidate_budget`, `timeout_ms`);
- trace metadata (`trace_context`).

### Response

`OptimizeCircuitResponse` includes:
- stable `request_id`;
- mapped AQO candidates (`OptimizedCandidate[]`) with `ScoreBreakdown`;
- selected candidate id (`selected_candidate_id`);
- explainability summary per candidate;
- `model_version`, `fallback_used`, and `fallback_reason`;
- latency/trace fields (`optimizer_latency_ms`, `scoring_latency_ms`, `mapping_latency_ms`, `trace_id`);
- explicit error envelope (`OptimizerError`) with reason code + retry semantics.

### Determinism and fallback

- Same `(input_aqo, topology, objective, deterministic_seed)` tuple must be replay-stable in contract tests.
- If `candidate_budget` is absent, deterministic default is `1`; if `timeout_ms` is absent, deterministic default is `100` ms.
- If model is unavailable or confidence falls below policy threshold, return heuristic baseline with `fallback_used=true`, non-empty `fallback_reason`, and the original `deterministic_seed` echoed in response.

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

- Golden fixture `src/services/system-api/tests/fixtures/contracts/optimizer_v1/service_contract_v1_0_0.json` freezes v1 request/response/error + fallback semantics.
- Seeded determinism replay tests must assert stable `selected_candidate_id` and score breakdown for repeated identical inputs.
- Fallback path conformance tests must assert `fallback_used=true` and required `fallback_reason`.
- Contract drift gate includes `proto/eigen/internal/v1/optimizer_service.proto` and fixture hashes in `scripts/ci/contract-version-manifest.json`.

## Compatibility and versioning

- **Version impact:** optimizer API contract `1.0.0`.
- **Compatibility:** new optional score fields are `MINOR`; response semantic changes are `MAJOR`.

## Open questions

- Minimum explainability payload for external clients.
- Normalization policy for score comparability across backends.
