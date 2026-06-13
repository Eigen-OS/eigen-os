# Product 1.0 Wave 9 Execution Plan

**Wave:** Product 1.0 Wave 9 — Security, identity, policy, and isolation  
**Status:** Planned for execution planning  
**Date:** 2026-06-13  
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`  
**Inventory:** `docs/development/product-1.0-contract-inventory.md`  
**Version policy:** `docs/development/product-1.0-version-policy.md`  
**Sources of truth:** `docs/architecture/**`, `docs/reference/**`

---

## 1. Goal

Wave 9 turns the existing security baseline from a set of MVP helpers into a fail-closed platform boundary. The wave hardens authentication, authorization, service identity, policy snapshots, sandbox isolation, secrets handling, and auditability without relaxing the deterministic replay and bounded-telemetry guarantees that Product 1.0 already depends on.

The intended outcome is a security posture where every public ingress decision is explicit, every internal request is attributable to a service identity, every policy decision is versioned, and every sensitive operation is either sanitized, quarantined, or rejected before it can reach the runtime boundary.

---

## 2. Normative source map

| Wave 9 area | Canonical source | Implementation surface | Primary evidence |
|---|---|---|---|
| Ingress authentication and authorization | `docs/architecture/components/security-isolation.md`; `docs/reference/security/authz.md` | System API ingress middleware; canonical authn/authz decisions; security context propagation | Security baseline and public-boundary conformance tests |
| Service identity and policy snapshots | `docs/architecture/components/security-isolation.md`; `docs/reference/error-model.md` | Internal service identity; versioned policy evaluation; normalized decision traces | Policy snapshot and traceability fixtures |
| Sandbox isolation and secrets lifecycle | `docs/architecture/components/security-isolation.md`; `docs/architecture/components/driver-manager.md` | Compiler, driver-manager, and runtime sandbox profiles; secrets confinement | Isolation and secrets-handling fixtures |
| Auditability and security telemetry | `docs/architecture/components/security-isolation.md`; `docs/architecture/components/observability.md` | Immutable audit sink; bounded security metrics; traceable security events | Audit and telemetry evidence |
| Release evidence and conformance gating | `docs/development/product-1.0-version-policy.md`; `docs/development/product-1.0-contract-inventory.md` | Compatibility report; readiness checklist; exit evidence bundle | Reviewable release package |

---

## 3. Wave 9 scope

### In scope

1. Enforce authentication and authorization as a fail-closed ingress boundary.
2. Propagate normalized security context to downstream services.
3. Introduce service identity and versioned policy-snapshot semantics for internal calls.
4. Enforce sandbox profiles, secrets confinement, and provider-boundary isolation.
5. Add immutable audit evidence for security decisions and telemetry that stays bounded and secret-free.
6. Add Wave 9 conformance fixtures, compatibility documentation, and release-evidence artifacts.

### Out of scope

- Changing the Product `1.0.0` release number.
- Redefining existing public or internal wire shapes without an RFC/ADR-backed contract change.
- Emitting secrets, tokens, or raw payloads into logs, metrics, or labels.
- Broadening observability scope beyond the existing Product 1.0 bounded-label contract families.
- Replacing the existing security baseline with an opaque policy backend that is not documented in architecture or reference docs.

---

## 4. Delivery sequence

| Step | Issue | Dependency | Outcome |
|---:|---|---|---|
| 1 | W9-01 Authentication, authorization, and normalized security context | Security baseline and public ingress helpers | Fail-closed ingress decisions with canonical errors and propagated context |
| 2 | W9-02 Service identity, policy snapshots, and deterministic policy decisions | W9-01 | Attributable internal calls and versioned policy evaluation |
| 3 | W9-03 Sandbox isolation, secrets lifecycle, and provider boundary hardening | W9-01 and W9-02 | Constrained execution surfaces and secret confinement |
| 4 | W9-04 Audit store, security telemetry, and replayable security evidence | W9-01 through W9-03 | Immutable security evidence with bounded telemetry |
| 5 | W9-05 Security conformance, fail-closed gating, and release evidence bundle | W9-01 through W9-04 | Closure evidence, readiness proof, and compatibility documentation |

---

## 5. Contract decisions required before implementation

1. **Identity model:** decide whether internal service identity is modelled as mTLS/workload identity, a documented local equivalent, or a staged combination.
2. **Policy backend:** decide which policy snapshot format and storage path is canonical for Product 1.0 security decisions.
3. **Sandbox taxonomy:** define the canonical sandbox-profile vocabulary for compiler, driver-manager, and runtime plugin paths.
4. **Audit sink:** decide the canonical audit storage and retention profile for security decisions.
5. **Fail-closed behavior:** decide which security failures are blocking versus recoverable under replay-safe fallback rules.
6. **Release gating:** decide which security, isolation, and secrets regressions block release and which are informational only.

---

## 6. Definition of done

Wave 9 is 100% complete when:

- authentication and authorization are fail-closed at ingress;
- internal service calls are attributable and policy decisions are versioned;
- sandbox and secrets boundaries are enforced and documented;
- audit events are immutable and traceable;
- bounded security telemetry is available without leaking sensitive payloads;
- the compatibility report, release-readiness checklist, and exit evidence bundle are complete;
- the inventory and README navigation are synchronized with the Wave 9 package.

---

## 7. Handoff to Wave 10

Wave 10 can start when the security baseline is fail-closed, attributable, and policy-versioned so observability hardening can assume stable boundary semantics. At that point, release evidence becomes the final operational proof layer rather than a substitute for unresolved security decisions.
