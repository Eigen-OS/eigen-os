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

---

## 5. Internal service scopes

Internal service-to-service calls MUST authenticate workload identity and authorize by role. Product 1.0 implementation work MUST preserve least privilege for:

- System API to Kernel/QRTX lifecycle calls,
- Kernel/QRTX to Compiler calls,
- Kernel/QRTX to Driver Manager calls,
- Kernel/QRTX to QFS persistence calls,
- runtime and benchmark services emitting observability or knowledge-base records.

---

## 6. Denial semantics

Authorization failures MUST use canonical error semantics:

- unauthenticated or invalid credentials map to `UNAUTHENTICATED`,
- authenticated principals lacking required scope map to `PERMISSION_DENIED`,
- tenant/project/resource policy denials must include a stable reason code when exposed through structured error details.

All denial behavior must follow `docs/reference/error-model.md` and `docs/reference/error-mapping.md`.
