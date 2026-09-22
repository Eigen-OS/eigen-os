# Authorization Policy Contract

**Document status:** Wave 0 baseline
**Subsystem:** System API, Security & Isolation, service-to-service authorization
**Contract version:** `1.0.0`
**Applies to:** Product 1.0 alignment stream

---

## 1. Scope

This document defines the Product 1.0 authorization baseline referenced by architecture and API contracts. It intentionally freezes the minimum policy surface needed before Wave 1 public API implementation begins.

Detailed security architecture remains in `docs/architecture/components/security-isolation.md`; this reference page is the canonical location for method-level authorization requirements.

---

## 2. Principals

Product 1.0 authorization decisions are evaluated for these principal classes:

| Principal | Description |
|---|---|
| External user/client | CLI, SDK, automation, or dashboard caller authenticated through the public System API. |
| Service workload | Internal Eigen OS service using service-to-service credentials. |
| Operator | Human or automation principal with deployment/operations privileges. |

---

## 3. Public method scopes

| Surface | Minimum required scope | Notes |
|---|---|---|
| `SubmitJob` | `jobs:submit` | Also requires tenant/project quota checks when multi-tenancy is enabled. |
| `GetJobStatus` | `jobs:read` | Caller must be authorized for the job tenant/project. |
| `StreamJobUpdates` | `jobs:read` | Same authorization as `GetJobStatus`; streaming sessions must preserve the initial decision context. |
| `CancelJob` | `jobs:cancel` | Caller must own the job or hold an operator/admin role. |
| `GetJobResults` | `jobs:read` | Result artifact access must also satisfy QFS artifact policy. |
| `GetDispatchRationale` | `jobs:read` | Sensitive policy details may be redacted by deployment policy. |
| `ListDevices` / device read methods | `devices:read` | Deployment may filter devices by tenant/project eligibility. |
| `ReserveDevice` | `devices:reserve` | Requires quota and lease-policy checks. |
| Benchmark REST | `benchmarks:run` | Applies to `POST /benchmarks/run`. |
| Explain REST | `runtime:explain` | Applies to `POST /explain/backend-selection`. |

---

## 4. Runtime security contract additions for Wave 4

- Public ingress MUST validate JWT/OAuth2 or configured static bearer tokens.
- Service-to-service calls MUST carry normalized service identity.
- Security policy MUST be loaded from a versioned snapshot or fail closed.
- Security decisions MUST be written to an immutable audit sink.
- Sandbox profile selection MUST be denied when not listed in the active policy snapshot.

## 4.1 Wave 9 policy decision requirements

- Every authorization decision MUST include the active policy snapshot version.
- Internal calls MUST carry a normalized service identity.
- Replay-sensitive security decisions MUST preserve deterministic replay markers.
- Policy backend unavailability MUST result in deny behavior.
- Missing policy snapshots MUST NOT fall back to allow behavior.
- Knowledge Base retrieval and runtime decision logging MUST fail closed when security context, policy evidence, or redaction cannot be completed.

---

## 5. Internal service scopes

Internal service-to-service calls MUST authenticate workload identity and authorize by role. Product 1.0 implementation work MUST preserve least privilege for:

- System API to Kernel/QRTX lifecycle calls,
- Kernel/QRTX to Compiler calls,
- Kernel/QRTX to Driver Manager calls,
- Kernel/QRTX to NeuroSymbolicService calls,
- Compiler to NeuroSymbolicService advisory calls,
- Kernel/QRTX to QFS persistence calls,
- Kernel/QRTX / eigen-compiler to NeuroSymbolicService advisory calls,
- runtime and benchmark services emitting observability or knowledge-base records.
- runtime and benchmark services emitting observability or knowledge-base records,
- CLI-only offline dataset ingestion into the KB-backed training corpus.

NeuroSymbolicService MUST fail closed when the service identity, tenant/project binding, or policy snapshot version is missing. Public ingress principals are not authorized to reach this service directly. CLI dataset ingestion MUST also reject missing ownership, provenance, redaction, or manifest digest evidence.

---

## 6. Denial semantics

Authorization failures MUST use canonical error semantics:

- unauthenticated or invalid credentials map to `UNAUTHENTICATED`,
- authenticated principals lacking required scope map to `PERMISSION_DENIED`,
- tenant/project/resource policy denials must include a stable reason code when exposed through structured error details.

NeuroSymbolicService MUST fail closed when the service identity, tenant/project binding, or policy snapshot version is missing. Public ingress principals are not authorized to reach this service directly. CLI dataset ingestion MUST also reject missing ownership, provenance, redaction, approval, replay identifiers, or manifest digest evidence.

All denial behavior must follow `docs/reference/error-model.md` and `docs/reference/error-mapping.md`.

---

## 7. Wave 9 normalized security context

Wave 9 public ingress handlers MUST normalize and propagate a deterministic security context to downstream calls. The canonical context includes:

- `subject`
- `roles`
- `tenant`
- `auth_mode`
- `policy_version`
- `service_identity`
- `service_role`
- `sandbox_profile`
- request and trace correlation metadata where available

The public ingress boundary MUST reject requests by default unless the configured identity and policy checks succeed. Allow-all behavior remains a local/dev compatibility mode only when explicitly configured.

All workload-family variants (`QuantumJob`, `HybridWorkflow`, `DistributedJob`, `BenchmarkJob`, `PipelineJob`, `ReplayJob`) MUST use this same normalized ingress path. No workload kind may introduce a separate authn/authz, trace, or audit branch.

---

### 7.1 Security audit trail and replay evidence

Security decisions MUST be written to the canonical append-only audit sink with bounded, secret-free metadata. Each audit event MUST include the decision outcome, decision reason, policy version, service identity, sandbox profile, replay marker, and request trace correlation where available.

This audit schema applies uniformly to every workload-family kind. Workload-specific semantics MAY influence the decision reason, but they MUST NOT change the audit envelope shape or introduce family-specific security fields.

Security telemetry for the audit path MUST remain bounded. Audit sink health is surfaced as counters rather than free-form labels, and audit records MUST NOT embed raw payloads, bearer tokens, or provider secrets.

### 7.2 Knowledge Base retrieval enforcement

Knowledge Base retrieval paths MUST be gated before data is returned. The retrieval decision flow MUST perform, in order:

1. authorization for the caller,
2. capability validation for the requested scope, and
3. validation against the active policy snapshot.

Retrieval allow/deny outcomes MUST be written to the audit sink with the active policy version and correlation metadata when available.

---

## 8. Security conformance suite

CI MUST run the security conformance suite that exercises the mandatory regression gates for:

- token leakage
- cross-tenant access
- policy bypass
- retrieval bypass
- missing context
- malicious prompt injection

---

## 9. Production readiness gate alignment

The security conformance suite is a release blocker, not a best-effort check. A release candidate MUST remain blocked until the following are evidenced:

- redaction validated
- tenant isolation validated
- policy enforcement validated
- explainability validated
- audit validated
- fail-closed validated

The evidence set MUST include the security architecture baseline, the System API security baseline, and the CI conformance suite that exercises cross-tenant access, policy bypass, retrieval bypass, missing context, token leakage, and prompt injection regressions.
