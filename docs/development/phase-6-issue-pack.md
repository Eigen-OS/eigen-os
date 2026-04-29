This document is a ready-to-use set of GitHub issues for the **Phase-6** stage of the roadmap.

**Context Sources:**
- `docs/roadmap.md` (Section: "Next Milestone — Phase-6: Plugin Ecosystem")
- `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase-6: Plugin Ecosystem")
- `docs/development/phase-6-plugin-ecosystem.md`
- `docs/development/phase-6-rfc-adr-gap-analysis.md`

---

## Versioning & Security Rules (Mandatory for every Phase-6 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer for stable plugin contracts:**
   - Plugin manifest schema, lifecycle events, and compatibility/trust envelopes use `MAJOR.MINOR.PATCH`.
2. **Breaking changes only via `MAJOR`:**
   - Any incompatible plugin API hook, required manifest field, or trust-policy semantic changes require `MAJOR`.
3. **Backward-compatible additions via `MINOR`:**
   - Optional capability flags, diagnostics metadata, and non-breaking extension points use `MINOR`.
4. **`PATCH` for fixes only:**
   - No plugin load-order, compatibility gate, trust enforcement, or sandbox semantic changes in `PATCH` releases.
5. **Mandatory version and trust markers in plugin artifacts:**
   - Every plugin package must include `plugin_api_version`, `eigen_os_compatibility`, signature payload, and transparency evidence references.
6. **Signing default is fixed:**
   - Sigstore/Cosign is the only default stack; public/community plugins use keyless Fulcio + Rekor.
7. **Sandbox default is fixed:**
   - Only out-of-process OCI plugins under gVisor `runsc`; no in-process Python/Rust plugin imports in GA.
8. **GA plugin types are fixed for Phase-6:**
   - `driver`, `compiler_backend`, `optimizer`.

---

## Milestone

- **Milestone:** `Phase-6 Plugin Ecosystem`
- **Suggested labels:** `phase-6`, `plugins`, `runtime`, `security`, `quality`, `rfc`

---

## Issues

### P6-01 — Plugin SDK and Manifest Contract v1 (GA types only)

**Type:** Feature  
**Labels:** `phase-6`, `plugins`, `runtime`

**Problem** Plugin authors need a stable contract to build compatible extensions.

**Scope**
- Manifest schema (`plugin.toml`) with identity, versioning, capabilities, and compatibility constraints.
- GA plugin type enum is fixed to `driver`, `compiler_backend`, `optimizer`.
- SDK baseline for scaffold/validate/package workflows and schema fixtures.

**Acceptance Criteria**
- Manifest schema is versioned and lintable in CI.
- SDK can scaffold and validate a minimal plugin for each GA type.
- Non-GA type declarations fail with deterministic diagnostics.

**RFC link**
- `rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md`

---

### P6-02 — Plugin Discovery, Registration, and Activation Lifecycle

**Type:** Platform  
**Labels:** `phase-6`, `plugins`, `runtime`

**Problem** Extension loading without a formal lifecycle leads to startup drift and operational failures.

**Scope**
- Plugin lifecycle state machine (`DISCOVERED -> REGISTERED -> VALIDATED -> ACTIVE -> ERROR/UNLOADED`).
- Deterministic load ordering and conflict resolution.
- Rollback/deactivation behavior with structured reasons.

**Acceptance Criteria**
- Plugin activation order is deterministic and fixture-tested.
- Conflicting plugins fail closed with actionable diagnostics.
- Rollback path is documented and integration-tested.

**RFC link**
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`

---

### P6-03 — Mandatory OCI + gVisor Sandbox Boundary

**Type:** Security / Platform  
**Labels:** `phase-6`, `security`, `plugins`

**Problem** Third-party plugins increase attack surface unless strict isolation is enforced by runtime boundary.

**Scope**
- Execute plugins only as out-of-process OCI artifacts under gVisor `runsc`.
- Enforce baseline profile: rootless, read-only fs, no network default, dropped capabilities, resource limits.
- Block in-process plugin loading paths in GA.

**Acceptance Criteria**
- In-process plugin activation attempts are rejected by policy.
- `runsc` runtime boundary is required in activation path.
- Isolation profile violations are observable in logs/metrics and covered by security tests.

**RFC link**
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`

---

### P6-04 — Plugin Compatibility Matrix and Load-Time Gate

**Type:** API / Quality  
**Labels:** `phase-6`, `quality`, `plugins`

**Problem** Plugin/core version drift can break runtime behavior and diagnostics.

**Scope**
- Compatibility matrix for `core_version x plugin_api_version x eigen_lang_version`.
- Load-time compatibility evaluator and deterministic failure modes.
- Contract fixture suite for supported/unsupported combinations.

**Acceptance Criteria**
- Unsupported version combinations are blocked with explicit remediation hints.
- Compatibility evaluation is deterministic and snapshot-tested.
- Version policy is documented in contributor/operator docs.

**RFC link**
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`

---

### P6-05 — Sigstore/Cosign Trust Gate (Fulcio + Rekor)

**Type:** Security / Governance  
**Labels:** `phase-6`, `security`, `rfc`

**Problem** Operators need verifiable trust controls for plugin supply-chain safety.

**Scope**
- Sigstore/Cosign verification as mandatory default.
- Keyless signing requirements for public/community plugins (Fulcio + Rekor evidence).
- Private/air-gapped support via self-hosted Sigstore or KMS/BYO PKI with same verification contract.

**Acceptance Criteria**
- Unsigned plugins are rejected in default policy.
- Fulcio/Rekor evidence is validated and auditable.
- Air-gapped/private policy profile keeps compatible artifact and verification format.

**RFC link**
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`

---

### P6-06 — GA Plugin Type Implementation Pack

**Type:** Platform / Compiler  
**Labels:** `phase-6`, `plugins`, `compiler`, `runtime`

**Problem** Phase-6 needs a strict minimal plugin surface aligned with roadmap extension areas.

**Scope**
- `driver` plugin contract (simulators + hardware adapters).
- `compiler_backend` plugin contract (transpilation / IR backends).
- `optimizer` plugin contract (circuit/backend optimization passes).
- Keep scheduler policy extension in core-configurable path (no GA plugin type in Phase-6).

**Acceptance Criteria**
- All three GA plugin types have fixture-backed contract tests.
- Scheduler plugin type declarations are rejected for Phase-6.
- Docs and CLI diagnostics explicitly mention the fixed GA type set.

**RFC link**
- `rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md`

---

### P6-07 — SRE Pack for Plugin Health, Trust, and Sandbox Violations

**Type:** Observability  
**Labels:** `phase-6`, `observability`, `plugins`

**Problem** Plugin failures and trust/sandbox rejects must be visible to operators.

**Scope**
- Metrics for discovery/activation failures, compatibility rejects, signature rejects, sandbox rejects.
- Dashboards for plugin inventory, health, activation latency, and rejection reasons.
- Alerts + runbook for startup degradation due to plugin failures.

**Acceptance Criteria**
- Dashboards expose plugin critical path and top failure reasons.
- Alerts trigger on plugin failure-rate and startup-SLO threshold breaches.
- Runbook includes deterministic triage and rollback steps.

**RFC link**
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`

---

### P6-08 — RFC Package for Phase-6 Plugin Contracts

**Type:** Architecture / Governance  
**Labels:** `phase-6`, `rfc`, `architecture`

**Problem** Phase-6 implementation cannot be stabilized without formal plugin contract RFCs.

**Scope**
- Create/accept RFCs for:
  1. plugin SDK + manifest contract,
  2. plugin lifecycle + runtime isolation contract,
  3. plugin compatibility + trust policy contract.
- Link RFCs from roadmap/development docs.

**Acceptance Criteria**
- Required Phase-6 RFC set is merged and indexed.
- Each RFC includes compatibility and test-plan sections.
- RFC statuses are explicit (`Draft`/`Accepted`/`Implemented`).

**RFC link**
- `rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md`
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`
