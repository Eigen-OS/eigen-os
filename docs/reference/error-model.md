# Error model (MVP)

> **Status**: MVP freeze  
> This page describes the **principles** of error handling in Eigen OS.  
> For detailed "who maps what to where", see: [`error-mapping.md`](error-mapping.md).

## Principles

- Errors in RPC are encoded as **gRPC status code** (OK/INVALID_ARGUMENT/…).
- Response bodies **do not** contain `success=false` / `error_message` as an alternative to status codes.
- For structural details (validation, retry hints, machine-readable reason), we use `google.rpc.Status` and `google.rpc.*` details.

## When to return INVALID_ARGUMENT vs FAILED_PRECONDITION

- `INVALID_ARGUMENT` — arguments are bad **regardless of the system's state** (e.g., broken source/JobSpec).
- `FAILED_PRECONDITION` — arguments are correct, but the system is **in an unsuitable state** (e.g., **GetJobResults** before job completion).

## Error details recommendations

- Validation: `BadRequest.FieldViolation` (field path + description)
- Retry/backoff: `RetryInfo`
- Resource identity: `ResourceInfo`
- Stable reason: `ErrorInfo.reason` (e.g., `EIGEN_UNSUPPORTED_FORMAT`)

## Implementation requirements

- All services adhere to a unified mapping (see [`error-mapping.md`](error-mapping.md)).
- Kernel stores `error_summary` and `error_details_ref` (QFS) for job in `ERROR` state.
- Client/SDK displays: **code**, **message**, **hint** (if available).

## Normalized backend error envelope (P1-05)

For backend-facing failures, services MUST emit `google.rpc.Status` with a normalized `ErrorInfo` detail carrying:

- `reason`: stable Eigen code (`EIGEN_BACKEND_*`)
- `domain`: `eigen.driver_manager`
- `metadata.taxonomy`: one of `provider | network | auth | quota | internal`
- `metadata.remediation`: actionable operator/client hint
- `metadata.correlation_id`: request correlation id for incident triage
- `metadata.job_timeline`: pointer to timeline artifact (`qfs://jobs/<job_id>/timeline.json`) when available
- `metadata.trace`: trace pointer (`trace://<trace_id>`) when available

This envelope is additive and does not change existing gRPC status semantics.
