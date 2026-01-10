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
