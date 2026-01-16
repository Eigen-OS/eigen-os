# Error mapping matrix (MVP) — Eigen OS

> **Recommended repo path:** `docs/reference/error-mapping.md`  
> **Purpose:** a *reference contract* that makes error behavior consistent across **System API → Kernel → Driver Manager → Backend**.
>
> It’s a **shared implementation contract**:
> - backend implementers map vendor errors → DriverManager gRPC status + details
> - Kernel maps internal failures → JobStatus + public API responses
> - clients/SDK implement correct retry / UX behavior

---

## 1) Principles (MVP)

### 1.1 Two kinds of errors
1) **Synchronous RPC errors**: the RPC itself fails (gRPC status != OK).
2) **Asynchronous job failures**: SubmitJob succeeds, but later execution fails.  
   These show up as:
   - `GetJobStatus.state = ERROR`
   - `GetJobResults` behavior defined below

### 1.2 Contract rule
- **Never** return `success=false` in response bodies.  
- Errors are represented by **gRPC status code**, and structured details via `google.rpc.Status` + `google.rpc.*` details where useful.

### 1.3 MVP recommendation for results access
- `GetJobResults(job_id)`:
  - If job is `DONE` → OK + results
  - If job is `ERROR` → OK + `JobResults` containing `error_summary` + `error_details_ref` (QFS, e.g. `results/error.json`)  
  - If job is not terminal → `FAILED_PRECONDITION` (optionally with RetryInfo hint)

---

## 2) Canonical mapping (table)

Legend:
- **Origin**: where the error starts
- **DM**: Driver Manager gRPC status (internal)
- **K**: Kernel action/state
- **API**: System API outward behavior

| Scenario | Origin | DM → K (internal) | Kernel behavior | System API behavior | Client guidance |
|---|---|---|---|---|---|
| Invalid JobSpec / missing required field | API validation | — | reject before enqueue | `INVALID_ARGUMENT` + BadRequest violations | Fix request; no retry |
| Invalid Eigen‑Lang source (AST rule violation) | Compiler | `INVALID_ARGUMENT` + BadRequest | job → ERROR (stage=COMPILING) | SubmitJob: either `INVALID_ARGUMENT` (pre-compile) or job enters ERROR quickly | Fix source; no retry |
| Unsupported target / format | Compiler or DM | `UNIMPLEMENTED` (preferred) | job → ERROR | status ERROR; results returns error payload | Change target/format |
| Job not found | API/Kernel | — | — | `NOT_FOUND` | Verify job_id |
| Device not found | API/Kernel/DM | `NOT_FOUND` | job → ERROR if already running | `NOT_FOUND` from device RPC | Fix device_id |
| Permission denied | API/K | `PERMISSION_DENIED` | reject / ERROR | `PERMISSION_DENIED` | No retry |
| Unauthenticated | API | — | — | `UNAUTHENTICATED` | Re-auth |
| Rate limit / quota | API/K or DM | `RESOURCE_EXHAUSTED` | QUEUED or ERROR (policy) | `RESOURCE_EXHAUSTED` | Retry with backoff |
| Scheduler cannot allocate | Kernel | — | remain QUEUED / deadline → ERROR | status shows QUEUED | Wait |
| Backend unavailable | Vendor/DM | `UNAVAILABLE` | ERROR (or reschedule if enabled) | status ERROR; results contains error | Retry later |
| Backend busy / queue full | Vendor/DM | `RESOURCE_EXHAUSTED` (MVP) | QUEUED or ERROR | QUEUED/ERROR | Retry later |
| Deadline exceeded | any RPC | `DEADLINE_EXCEEDED` | if internal, ERROR | `DEADLINE_EXCEEDED` for sync calls | Retry / increase deadline |
| User cancelled | API/K | `CANCELLED` | CANCELLED | Cancel OK; status CANCELLED | No retry |
| Unexpected bug | any service | `INTERNAL` | ERROR | `INTERNAL` for sync; results error payload for job | Report issue |

---

## 3) Structured error details (optional but recommended)

If you use `google.rpc.Status` details:
- **BadRequest.FieldViolation**: validation problems (field path + description)
- **ErrorInfo**: stable machine-readable reason (e.g., `EIGEN_UNSUPPORTED_FORMAT`)
- **ResourceInfo**: identify resource types/ids (`device`, `job`)
- **RetryInfo**: hints for backoff

---

## 4) JobStatus alignment (public)

Public states (MVP):
- `PENDING`, `COMPILING`, `QUEUED`, `RUNNING`, `DONE`, `ERROR`, `CANCELLED`

For `ERROR`, expose:
- `error_code` (stable reason)
- `error_message` (human)
- `error_details_ref` (QFS object for full trace/logs)

---

## 5) Hard invariants
- Same scenario → same canonical gRPC status.
- Respect `INVALID_ARGUMENT` vs `FAILED_PRECONDITION` distinction.
- No boolean success flags in response bodies.
- Vendor errors are normalized before they reach Kernel.

