# Product 1.0 Wave 9 Documentation Index

**Wave:** Product 1.0 Wave 9 — Security, identity, policy, and isolation  
**Status:** Planning package published  
**Parent execution plan:** `docs/development/product-1.0-contract-alignment-plan.md`

---

## Core planning documents

- `product-1.0-wave-9-execution-plan.md`
- `product-1.0-wave-9-issue-pack.md`
- `product-1.0-wave-9-rfc-adr-gap-analysis.md`

---

## Closure-target documents

These documents are produced as the Wave 9 implementation package is executed and closed:

- `product-1.0-wave-9-compatibility-report.md`
- `product-1.0-wave-9-release-readiness-checklist.md`
- `product-1.0-wave-9-exit-evidence-bundle.md`

---

## Scope

Wave 9 turns security from MVP helpers into a fail-closed platform boundary. It hardens authentication, authorization, service identity, policy snapshots, sandbox isolation, secrets handling, and auditability while preserving deterministic replay and bounded telemetry.

W9-02 completion requirements:

- service identity propagation is explicit for internal calls;
- authorization decisions include policy snapshot metadata;
- replay evidence includes deterministic decision markers;
- policy backend failures fail closed.

---

## Primary source-of-truth references

- `docs/architecture/components/security-isolation.md`
- `docs/architecture/components/knowledge-base.md`
- `docs/architecture/components/observability.md`
- `docs/architecture/components/driver-manager.md`
- `docs/reference/security/authz.md`
- `docs/reference/error-model.md`
- `docs/reference/orchestration-observability-contract.md`
- `docs/reference/intelligent-runtime-observability-contract.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/api/grpc-internal.md`
- `rfcs/0009-security-isolation-mvp.md`
- `docs/adr/0002-mvp1-contract-baseline.md`
- `docs/development/product-1.0-contract-inventory.md`
- `docs/development/product-1.0-version-policy.md`

---

Wave 9 planning stays synchronized with the Product 1.0 alignment plan, contract inventory, and version policy. Any new security boundary that changes the accepted contract package still requires an RFC/ADR before merge.
