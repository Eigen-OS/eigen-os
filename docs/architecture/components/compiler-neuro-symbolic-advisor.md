# Compiler Neuro-Symbolic Advisor Contract

- **Document status:** Normative compiler-facing boundary note
- **Subsystem:** Compiler Service advisory boundary
- **Contract version:** `1.0.0`
- **Applies to:** `src/services/eigen-compiler/`, `src/services/neuro-symbolic-service/`
- **Last updated:** 2026-06-22

The authoritative architecture spec for the symbolic core, knowledge base, and ML advisor boundary is:

- `docs/architecture/components/neuro-symbolic-core.md`

This document keeps the compiler-specific rules small and explicit. It does not redefine the broader NSC contract.

---

## 1. Compiler boundary rule

The compiler must treat neuro-symbolic output as advisory only.

Deterministic validation, normalization, lowering, AQO contract checks, and workload-profile resolution remain authoritative in the compiler rule engine and deterministic pipeline.

Neuro-symbolic suggestions must not be able to produce invalid IR, bypass semantic validation, or relax lowering constraints.

The compiler may invoke the symbolic rewrite pipeline one stage at a time, but stage order and stage advancement remain deterministic and under compiler control.

---

## 2. Allowed advisor behavior

The advisor may:

- propose rewrites,
- rank candidates,
- emit heuristic hints,
- explain why a deterministic compiler action was suggested,
- contribute bounded replay evidence that can be validated by the compiler.

The advisor may not:

- override rule-engine approval,
- mutate compiler semantics on its own,
- force acceptance of an invalid candidate,
- introduce nondeterministic compile output,
- infer compiler legality, policy approval, or replay identity.

---

## 3. Safe interface contract

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

For the symbolic rewrite pipeline, each stage invocation MUST be logged independently with the stage name, stage index, and stage outcome attached to the same bounded replay evidence.

---

## 4. Compatibility

This boundary is advisory-only and does not change the deterministic compiler contract or AQO schema.

Any compiler change that lets advisory output bypass deterministic checks is a breaking change and must be documented against the source-of-truth spec above.
