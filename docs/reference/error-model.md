# Error model (MVP snapshot)

- **Phase**: MVP
- **Snapshot date**: 2026-05-10
- **Purpose**: fix current unified error contract in Eigen OS and explicitly list missing pieces required for contract freeze.

For detailed scenario matrix, see [`error-mapping.md`](error-mapping.md).

## 1) Core principles (normative)

1. RPC failures are represented by **gRPC status** (`OK`, `INVALID_ARGUMENT`, `FAILED_PRECONDITION`, ...).
2. Response bodies MUST NOT encode transport-level failures via ad-hoc wrappers (`success=false`, `error_message`).
3. Structured error semantics SHOULD be encoded via `google.rpc.Status` details (`BadRequest`, `ErrorInfo`, `ResourceInfo`, `RetryInfo`).
4. For async job execution, terminal failure is reflected both:
   - in lifecycle state (`ERROR`), and
   - in durable/inspectable fields (`error_code`, `error_summary`, `error_details_ref`).

## 2) Canonical status split

### `INVALID_ARGUMENT`
Use when request/program input is invalid **independently of runtime state**:
- malformed or unsupported input syntax,
- missing required fields,
- invalid format/version/value range.

### `FAILED_PRECONDITION`
Use when arguments are valid but operation cannot proceed due to **current state**:
- reading results before terminal completion,
- operation not legal in current lifecycle state,
- required prerequisite artifact/state not yet available.

This split is mandatory and must remain deterministic across services.

## 3) Required structured details

### Validation failures
- `google.rpc.BadRequest` with one or more `FieldViolation` entries:
  - `field`: stable field path,
  - `description`: actionable explanation.

### Retry/deadline hints
- `google.rpc.RetryInfo` for retryable transient failures.

### Resource identity / ownership context
- `google.rpc.ResourceInfo` when resource type/name aids remediation.

### Stable machine reason
- `google.rpc.ErrorInfo` with:
  - `reason`: stable Eigen code (`EIGEN_*` family),
  - `domain`: owning subsystem,
  - metadata for remediation/correlation where applicable.

## 4) Normalized backend error envelope (P1-05)

Backend-facing failures MUST include `ErrorInfo` in `google.rpc.Status` with the following keys:

- `reason`: stable Eigen backend code (`EIGEN_BACKEND_*`)
- `domain`: `eigen.driver_manager`
- `metadata.taxonomy`: `provider | network | auth | quota | internal`
- `metadata.remediation`: operator/client action hint
- `metadata.correlation_id`: correlation id for incident triage
- `metadata.job_timeline`: optional pointer to timeline artifact (`qfs://jobs/<job_id>/timeline.json`)
- `metadata.trace`: optional distributed trace pointer (`trace://<trace_id>`)

This envelope is additive and does not alter canonical gRPC semantics.

## 5) Minimum client/SDK handling contract

Clients/SDKs should consistently surface:

1. gRPC code,
2. human-readable message,
3. structured hint/details (when present),
4. correlation id / trace pointer (when present).

For async terminal failures, SDKs should read either inline summary (`error_code`/`error_summary`) or dereference `error_details_ref`.

## 6) Current system snapshot (implemented vs not yet frozen)

### Already aligned in docs/runtime direction

- gRPC-status-first policy is documented on public/internal API pages.
- Async error envelope fields are part of job status/results contracts.
- QFS layout includes durable error artifact path (`results/error.json`).
- Backend normalization taxonomy/reason model is defined at reference level.

### Missing for strict contract freeze

1. **No single normative RPC-by-RPC error table**
   - Need one frozen reference mapping each method and failure class to exact status + required detail types.
2. **Per-endpoint detail schema pinning is incomplete**
   - Public/internal/explain endpoints still need explicit required/optional `google.rpc.*` detail sets.
3. **Retryability/deadline policy is not globally fixed**
   - Canonical retry budgets and timeout classes per status are not yet frozen.
4. **Cross-service conformance coverage is incomplete**
   - Need CI/golden tests for deterministic status+reason mapping across repeated same-class failures.
5. **Reason-code catalog governance is not formally versioned**
   - Need ownership, compatibility, and deprecation policy for `EIGEN_*` codes.

## 7) Hardening criteria before post-MVP widening

Contract may be treated as frozen only after all items are completed:

1. Publish normative RPC error matrix document and link from public/internal API references.
2. Add conformance tests for:
   - `INVALID_ARGUMENT` with field violations,
   - `FAILED_PRECONDITION` state gating,
   - transient backend normalization (`UNAVAILABLE`, `RESOURCE_EXHAUSTED`),
   - auth/authz split (`UNAUTHENTICATED`, `PERMISSION_DENIED`).
3. Freeze retry/deadline policy consumed by SDK/CLI.
4. Freeze reason-code catalog and versioning policy.
5. Enforce invariant that async `ERROR` jobs always expose actionable summary and/or durable error reference.

## 8) Invariants (must remain true)

- Same failure class maps to same canonical gRPC status.
- `INVALID_ARGUMENT` and `FAILED_PRECONDITION` are never conflated.
- No ad-hoc success/error wrappers in RPC bodies.
- Backend/provider-native failures are normalized before public exposure.
