# Error mapping matrix (MVP snapshot) — Eigen OS

- **Phase**: MVP
- **Snapshot date**: 2026-05-10
- **Purpose**: freeze the currently implemented error behavior across **Public API → KernelGateway → Compiler/Driver Manager**, and document what is still missing before a stricter contract freeze.

Related references:
- `docs/reference/error-model.md`
- `docs/reference/api/grpc-public.md`
- `docs/reference/api/grpc-internal.md`

---

## 1) Contract baseline (what is fixed now)

1. Errors are represented by gRPC status (non-`OK`), not `success=false` payload wrappers.
2. Validation must use `INVALID_ARGUMENT`; state-dependent access should use `FAILED_PRECONDITION`.
3. For asynchronous jobs, terminal failure is represented in job lifecycle (`ERROR`) plus structured fields (`error_code`, `error_summary`, `error_details_ref`).
4. Driver/provider-native failures are normalized before surfacing to public contract.

---

## 2) Current end-to-end mapping (MVP)

- **Origin**: where the failure starts
- **Internal**: expected Kernel/DM/Compiler mapping
- **Public/API**: client-visible behavior

| Scenario | Origin | Internal mapping | Public/API behavior | Client guidance |
|---|---|---|---|---|
| Missing required request field (`name`, `job_id`, etc.) | API/Kernel validation | `INVALID_ARGUMENT` | RPC fails with `INVALID_ARGUMENT` | Fix request; no retry |
| Unknown `job_id` | Kernel store lookup | `NOT_FOUND` | RPC fails with `NOT_FOUND` | Verify id / eventual consistency window |
| Cancel on terminal job | Kernel state machine | `CancelJob` returns `accepted=false` (not transport error) | `OK` + `accepted=false` | Treat as terminal no-op |
| `GetJobResults` before terminal state | API policy (target contract) | `FAILED_PRECONDITION` (recommended) | Public should return `FAILED_PRECONDITION` | Poll/stream until terminal |
| Compiler input/source invalid | Compiler validation | `INVALID_ARGUMENT` | Submit may fail fast or job moves to `ERROR` quickly | Fix program/jobspec |
| Unsupported language/feature in compiler path | Compiler | `UNIMPLEMENTED` | Error surfaced directly or as async job `ERROR` | Change format/feature |
| Backend temporarily unavailable | Driver/provider | `UNAVAILABLE` | Async job transitions to `ERROR` with normalized reason | Retry with backoff |
| Backend throttling/quota | Driver/provider | `RESOURCE_EXHAUSTED` | Async job `ERROR` (or queued by policy) | Retry later / reduce load |
| Deadline exceeded on downstream call | Any internal hop | `DEADLINE_EXCEEDED` | Sync call fails or async job `ERROR` | Retry and tune deadlines |
| Permission/auth failure from backend | Driver/provider | `PERMISSION_DENIED` / `UNAUTHENTICATED` | Error propagated/normalized | Re-auth / fix entitlement |
| Unexpected runtime fault | Any service | `INTERNAL` | Sync failure or async `ERROR` with error payload | Escalate with correlation id |

---

## 3) Normalized backend envelope (current target)

For backend-facing failures, services should emit `google.rpc.Status` with `ErrorInfo` containing:

- `reason`: stable Eigen code (`EIGEN_BACKEND_*`)
- `domain`: `eigen.driver_manager`
- `metadata.taxonomy`: `provider | network | auth | quota | internal`
- `metadata.remediation`: actionable hint
- `metadata.correlation_id`
- optional `metadata.job_timeline`, `metadata.trace`

Canonical examples currently used in docs:

| Backend condition | gRPC status | `ErrorInfo.reason` |
|---|---|---|
| Invalid/expired token | `UNAUTHENTICATED` | `EIGEN_BACKEND_AUTH` |
| Access denied | `PERMISSION_DENIED` | `EIGEN_BACKEND_AUTHZ` |
| Provider outage/transient | `UNAVAILABLE` | `EIGEN_BACKEND_UNAVAILABLE` |
| Quota/rate exceeded | `RESOURCE_EXHAUSTED` | `EIGEN_BACKEND_QUOTA` |
| Unsupported provider operation | `UNIMPLEMENTED` | `EIGEN_BACKEND_PROVIDER` |
| Malformed provider payload | `INVALID_ARGUMENT` | `EIGEN_BACKEND_INVALID_ARGUMENT` |
| Unknown provider/runtime failure | `INTERNAL` | `EIGEN_BACKEND_INTERNAL` |

---

## 4) System state snapshot vs gaps

### What is already aligned

1. Public and internal docs explicitly use gRPC-status-first model.
2. Public `JobStatus`/`GetJobResults` include async error envelope fields (`error_code`, `error_summary`, `error_details_ref`).
3. Kernel runtime maps downstream `tonic::Status` codes into pipeline error categories and persists async error artifacts in QFS (`results/error.json` path is part of QFS contract).
   
### What is still missing (must be fixed)

1. **No single normative RPC-by-RPC matrix in code/docs**
   - We still need one frozen table per method/failure class → exact status + required details type.
2. **`GetJobResults` pre-terminal behavior needs strict conformance lock**
   - Reference contract says `FAILED_PRECONDITION`; this must be tested end-to-end for all public SDKs.
3. **Error detail schemas are not fully pinned per endpoint**
   - `BadRequest`, `ErrorInfo`, `ResourceInfo`, `RetryInfo` usage must be explicit for each RPC.
4. **Retry budgets and deadline policy are not globally frozen**
   - Status mapping exists, but operational retry/deadline semantics are still implementation-defined.
5. **Cross-service conformance tests are incomplete**
   - Need CI gates proving canonical status mapping and stable reason-code determinism for same failure class.
6. **Explain/auxiliary endpoints still need explicit mapping appendix**
   - E.g., `GetDispatchRationale` unavailable/corrupt/missing states should map deterministically (`NOT_FOUND` vs `FAILED_PRECONDITION` etc.).

---

## 5) Required hardening backlog (contract freeze criteria)

1. Add `docs/reference/error-cases-by-rpc.md` (normative): every public+internal RPC with mandatory status/detail mapping.
2. Add golden integration tests:
   - validation failures (`INVALID_ARGUMENT` + field violations),
   - precondition failures (`FAILED_PRECONDITION`),
   - normalized backend transient failures (`UNAVAILABLE`/`RESOURCE_EXHAUSTED`),
   - auth/authz failures (`UNAUTHENTICATED`/`PERMISSION_DENIED`).
3. Add deterministic reason-code catalog (`EIGEN_*`) with ownership/versioning policy.
4. Freeze retryability table consumed by SDK/CLI (which status codes are retryable and under what policy).
5. Add contract tests ensuring async `ERROR` jobs always expose one of:
   - inline summary (`error_code` + `error_summary`), and/or
   - durable artifact reference (`error_details_ref`).

---

## 6) Invariants (must remain true)

- Same failure class must map to the same canonical gRPC status.
- `INVALID_ARGUMENT` and `FAILED_PRECONDITION` must not be conflated.
- No ad-hoc boolean success/error wrappers in RPC bodies.
- Vendor/provider errors must be normalized before reaching public contract.
