# Neuro-Symbolic Advisory Boundary

This addendum records the compiler-facing boundary for the neuro-symbolic layer.

The normative source of truth for the full symbolic-core / KB / ML-advisor boundary is:

- `docs/architecture/components/neuro-symbolic-core.md`

## Compiler rule

The compiler must treat neuro-symbolic output as advisory only. Deterministic validation, normalization, lowering, AQO contract checks, and workload-profile resolution remain authoritative.

Neuro-symbolic suggestions must not be able to produce invalid IR, bypass semantic validation, infer compiler legality, or relax lowering constraints.

## Allowed advisor behavior

The advisor may:

- propose rewrites,
- rank candidates,
- emit heuristic hints,
- explain why a deterministic compiler action was suggested.

The advisor may not:

- override rule-engine approval,
- mutate compiler semantics on its own,
- force acceptance of an invalid candidate,
- introduce nondeterministic compile output.

## Safe interface contract

When a suggestion is observed by the compiler boundary, the outcome must be recorded as one of:

- `accepted`
- `rejected`
- `transformed`

`transformed` is used when a suggestion is converted into a deterministic compiler action after rule-engine approval.

Telemetry for these outcomes is exported from the neuro-symbolic service as:

- `eigen_neuro_suggestion_outcomes_total{outcome="accepted"}`
- `eigen_neuro_suggestion_outcomes_total{outcome="rejected"}`
- `eigen_neuro_suggestion_outcomes_total{outcome="transformed"}`

Structured logs should include the same `suggestion_outcome` field when available.

## Compatibility

This boundary is advisory-only and does not change the deterministic compiler contract or AQO schema.
