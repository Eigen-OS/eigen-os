This document is a ready-to-use set of GitHub issues for the **Phase-6** stage of the roadmap.

**Context Sources:**
- `docs/roadmap.md` (Section: "Next Milestone — Phase-6: Plugin Ecosystem")
- `docs/development/post-mvp-open-source-roadmap.md` (Section: "Phase-6: Plugin Ecosystem")
- `docs/development/phase-6-plugin-ecosystem.md`
- `docs/development/phase-6-rfc-adr-gap-analysis.md`

---

## Versioning Rules (Mandatory for every Phase-6 issue)

> Include this block in the description of every issue (as "Definition of Done / Constraints").

1. **SemVer for stable plugin contracts:**
   - Plugin manifest schema, lifecycle events, and compatibility/trust envelopes use `MAJOR.MINOR.PATCH`.
2. **Breaking changes only via `MAJOR`:**
   - Any incompatible plugin API hook, required manifest field, or trust-policy semantic changes require `MAJOR`.
3. **Backward-compatible additions via `MINOR`:**
   - Optional capability flags, diagnostics metadata, and non-breaking extension points use `MINOR`.
4. **`PATCH` for fixes only:**
   - No plugin load-order, compatibility gate, or trust enforcement semantic changes in `PATCH` releases.
5. **Mandatory version markers in plugin artifacts:**
   - Every plugin package must include `plugin_api_version` and `eigen_os_compatibility` metadata.
6. **Deprecation policy:**
   - Plugin API/manifest fields cannot be removed before at least one `MINOR` release marks them deprecated.
7. **Changelog discipline:**
   - Every Phase-6 PR includes:
     - `Version impact`
     - `Compatibility`
     - `Migration notes` (if applicable).

---

## Milestone

- **Milestone:** `Phase-6 Plugin Ecosystem`
- **Suggested labels:** `phase-6`, `plugins`, `runtime`, `eigen-lang`, `security`, `quality`, `rfc`

---

## Issues

### P6-01 — Plugin SDK and Manifest Contract v1

**Type:** Feature  
**Labels:** `phase-6`, `plugins`, `runtime`

**Problem** Plugin authors need a stable contract to build compatible extensions.

**Scope**
- Manifest schema (`plugin.toml`) with identity, versioning, capabilities, and compatibility constraints.
- Plugin SDK baseline for scaffold/validate/package workflows.
- Contract fixtures for manifest validation across plugin types.

**Acceptance Criteria**
- Manifest schema is versioned and lintable in CI.
- SDK can scaffold and validate a minimal plugin end-to-end.
- Incompatible manifest versions fail with deterministic diagnostics.

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

### P6-03 — Runtime Isolation and Capability Enforcement for Plugins

**Type:** Security / Platform  
**Labels:** `phase-6`, `security`, `plugins`

**Problem** Third-party plugins increase attack surface unless strict isolation and capability checks are enforced.

**Scope**
- Isolation profile for plugin execution environment.
- Capability declaration/verification at activation time.
- Policy guardrails for forbidden API or filesystem/network access.

**Acceptance Criteria**
- Unauthorized capability requests are blocked before activation.
- Isolation policy violations are observable in logs/metrics.
- Security regression tests cover privilege-escalation attempts.

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

### P6-05 — Plugin Trust Policy and Signature Verification

**Type:** Security / Governance  
**Labels:** `phase-6`, `security`, `rfc`

**Problem** Operators need verifiable trust controls for plugin supply-chain safety.

**Scope**
- Signature verification and trust profile policy (`prod`, `staging`, `dev`).
- Allowlist/denylist policy inputs.
- Audit trail for trust decisions and override actions.

**Acceptance Criteria**
- Production profile blocks unsigned plugins by default.
- Policy overrides are explicit, logged, and observable.
- Signature verification failures include deterministic reason codes.

**RFC link**
- `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`

---

### P6-06 — Eigen-Lang Plugin Extension Hooks v1

**Type:** Compiler / Language  
**Labels:** `phase-6`, `eigen-lang`, `compiler`

**Problem** Language-level extension points are required for ecosystem growth beyond core built-ins.

**Scope**
- Pluggable standard-library module registration.
- Compiler hooks for plugin-based analysis/transformation passes.
- Deterministic diagnostics for unsupported extension patterns.

**Acceptance Criteria**
- Plugin-provided modules can be imported under explicit namespace policy.
- Compiler hook order is deterministic and test-covered.
- Unsupported hooks fail with actionable and reproducible errors.

**RFC link**
- `rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md`
- `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`

---

### P6-07 — SRE Pack for Plugin Health, Failures, and Drift

**Type:** Observability  
**Labels:** `phase-6`, `observability`, `plugins`

**Problem** Plugin failures and compatibility drift must be visible to operators.

**Scope**
- Metrics for discovery/activation failures, compatibility rejects, and trust-policy rejects.
- Dashboards for plugin inventory, health, and activation latency.
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
