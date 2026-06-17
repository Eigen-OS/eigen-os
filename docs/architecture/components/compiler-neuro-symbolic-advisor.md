# Compiler Neuro-Symbolic Advisor Contract

- **Document status:** Normative architecture contract
- **Subsystem:** Compiler Service advisory boundary
- **Contract version:** `1.0.0`
- **Applies to:** `src/services/eigen-compiler/`, `src/services/neuro-symbolic-service/`
- **Last updated:** 2026-06-17

This document defines the only allowed role of the neuro-symbolic layer inside the compiler pipeline. The compiler core remains deterministic and authoritative. The advisor may help with suggestions, ranking, and explanation, but it must never become the source of truth for validity or semantics.

---

## 1. Purpose

The neuro-symbolic advisor exists to provide bounded assistance to deterministic compiler logic.

Allowed uses:
- rewrite suggestions,
- ranking of deterministic alternatives,
- heuristic hints,
- explainability metadata,
- replay-safe advisory telemetry.

Disallowed uses:
- producing IR that bypasses validation,
- overriding the compiler rule engine,
- lowering directly into emitted AQO without deterministic checks,
- mutating compiler semantics,
- introducing nondeterminism into compilation.

---

## 2. Contract rules

The compiler must apply the following rules whenever advisor output is available:

1. Deterministic compiler rules are authoritative.
2. Any advisor suggestion is advisory only.
3. The compiler may accept, reject, or transform a suggestion only through deterministic validation and lowering.
4. No advisor output may be emitted as final IR without rule-engine approval.
5. Advisor availability must not be required for successful compilation.
6. A disabled advisor must leave compiler behavior unchanged except for advisory metadata.

---

## 3. Safe interface

The compiler and advisor communicate through a bounded advisory envelope.

The envelope may carry:
- request identity,
- policy snapshot version,
- model or heuristic version,
- bounded feature digest,
- advisory decision,
- confidence / ranking information,
- explainability reference,
- replay digest.

The envelope must not carry:
- unvalidated IR,
- mutable compiler state,
- hidden control flags,
- any field that can bypass semantic validation or lowering constraints.

The compiler must treat the envelope as read-only input.

---

## 4. Deterministic approval flow

A suggestion becomes effective only after deterministic compiler approval.

Approved outcomes are recorded as one of the following bounded states:
- `accepted` — the suggestion matched deterministic rules and was used as-is,
- `rejected` — the suggestion failed rule-engine approval,
- `transformed` — the suggestion was converted into a deterministic compiler action,
- `disabled` — no advisor participation occurred.

Every outcome must be attributable to a named compiler stage or rule check.

---

## 5. Telemetry and auditability

Compiler telemetry must record:
- whether the advisor was enabled,
- the advisory outcome,
- the deterministic compiler stage that approved or rejected the suggestion,
- the replay-safe digest for the decision path,
- whether the final AQO changed because of a deterministic compiler action.

Telemetry must remain bounded and must not expose secrets, request bodies, or unbounded free-form model output.

---

## 6. Compatibility

This contract is backward-compatible with the existing deterministic compiler pipeline.

- The compiler remains valid when the advisor is unavailable.
- Advisor implementations may be swapped without changing AQO semantics.
- Advisor outputs may evolve only within the bounded advisory envelope.
- Any future change that lets advisory output bypass deterministic checks is a breaking change.

---

## 7. Relationship to other contracts

This document narrows the compiler role described in:
- `docs/architecture/components/compiler.md`
- `docs/architecture/components/neuro-symbolic-core.md`

It does not change AQO semantics, compiler validation rules, or the public ingress model.
