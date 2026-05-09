# Kernel (QRTX) – Implementation Status Snapshot

- **Original phase intent**: MVP (Phase 0), per RFC 0007.
- **Current implementation snapshot date**: 2026-05-09.
- **Status**: Implemented as a minimal internal orchestration kernel in `src/rust/crates/eigen-kernel` with an in-memory store and a reduced state machine; part of the RFC intent remains deferred.

## Responsibility

Implemented now:

- QRTX accepts internal job submissions and orchestrates a linear async pipeline: compile → execute → persist results/artifacts.
- QRTX coordinates with:
  - `CompilationService` (compile + validate call paths are present),
  - `DriverManagerService` (device status + execute circuit),
  - QFS via `CircuitFsLocal` (layout + artifacts/results/error payload persistence).
- QRTX exposes job lifecycle and terminal result/error payload via internal gRPC.

TODO (not fully реализовано относительно RFC/архитектурного намерения):

- TODO: Expand lifecycle orchestration from current reduced machine (`Pending → Compiling → Running → Done/Error/Cancelled/Timeout`) to the full RFC chain (`Pending → Validating → Compiling → Queued → Allocating → Executing → Completing → Completed` + documented sub-states).
- TODO: Add explicit scheduler semantics for queueing/allocation as first-class runtime stages (currently represented only implicitly, without dedicated persisted states).
- TODO: Add durable state storage/recovery semantics expected for production-grade orchestration (currently only in-memory store).

## Interfaces

Implemented now:

- **Internal gRPC API**: `KernelGatewayService` with:
  - `EnqueueJob`, `GetJobStatus`, `CancelJob`, `GetJobResults`.
- **Outbound gRPC clients**:
  - `CompilationService`
  - `DriverManagerService`
- **QFS client**:
  - `CircuitFsLocal` used for `jobs/<job_id>/...` artifacts/results/error files.

TODO:

- TODO: `ListDevices` in `KernelGateway` is referenced in older architecture docs/RFC notes but is **not** present in current `kernel_gateway.proto`; align component docs + RFC appendix references to current contract and single source of truth.
- TODO: Finalize and document whether device listing is owned by Kernel gateway or remains exclusively proxied from System API to Driver Manager in current architecture.

## Inputs / Outputs

Implemented now:

- **Inputs**:
  - `EnqueueJobRequest` (name/program/target/options/metadata).
  - `GetJobStatusRequest`, `CancelJobRequest`, `GetJobResultsRequest`.
  - Compiler and driver responses via outbound gRPC.
- **Outputs**:
  - gRPC status/result responses including terminal error payload fields (`error_code`, `error_summary`, `error_details_ref`).
  - QFS artifacts and metadata (compiled IR, counts, execution metadata, persisted error details).

TODO:

- TODO: Add explicit, documented inbound device-status update stream contract (current integration polls/calls services; no dedicated async status ingestion API on Kernel gateway).
- TODO: Reconcile artifact path conventions in this component doc with current runtime/QFS docs to avoid stale `circuit_fs/<job_id>/` wording where runtime now uses canonical `jobs/<job_id>/...` layout helpers.

## Storage / State

Implemented now:

- **State persistence**:
  - In-memory `JobStore` with per-job record, timestamps, state, counts, result metadata, error payload.
- **QFS usage**:
  - Job layout initialization and persistence of artifacts/results/errors in local QFS root.
- **Terminalization semantics**:
  - Terminal states reject further transitions except idempotent re-terminalization for matching terminal event.

TODO:

- TODO: Add durable state backend (DB/event-log) and startup recovery.
- TODO: Add checkpointing/resume semantics (explicitly absent).
- TODO: Add formal reservation/queue-depth aggregation state in Kernel if Resource Manager responsibilities are to be hosted here long-term.

## Failure Modes

Implemented now:

- **Compiler failure / connect failure** → job transitions to `Error`, structured error payload is set.
- **Driver execution/connect failure** → job transitions to `Error`, structured error payload is set.
- **QFS persistence/layout failure** → pipeline returns error, job transitions to `Error`.
- **Cancellation** supported for non-terminal jobs.
- **Timeout state** exists in state machine and proto enum.

TODO:

- TODO: Introduce explicit runtime timeout enforcement mechanism (state exists, but dedicated scheduler timeout policy/worker currently not documented as implemented in kernel runtime path).
- TODO: Add robust retry/backoff policy specification and implementation guarantees for QFS/network partitions (currently failures mostly surface as immediate pipeline errors).

## Observability

Implemented now:

- Structured tracing/logging is wired in kernel pipeline (`tracing`, request metadata propagation including `traceparent`/`trace_id`).
- Stage-oriented spans are emitted around async pipeline execution.

TODO:

- TODO: Implement and document the metrics set previously declared here (`eigen_kernel_job_state_transitions_total`, `eigen_kernel_stage_duration_seconds`, `eigen_kernel_queue_depth`, `eigen_kernel_active_jobs`) if these are required by accepted observability RFC/ADR gates; current kernel implementation snapshot focuses on logs/traces and does not expose this full metric surface in the component runtime code.
- TODO: Synchronize this section with accepted observability contracts and release-gate docs so required telemetry is explicitly testable.

---

## RFC / ADR Consistency Notes

Checked against repository RFC/ADR artifacts relevant to QRTX:

- RFC 0007 defines fuller lifecycle granularity than currently implemented state machine.
- RFC 0004 internal API appendix historically references optional `KernelGateway.ListDevices`; current proto omits this RPC.
- ADR package for MVP release/readiness and later phases should continue to treat reduced-kernel behavior as current baseline until expansion work lands.

TODO:

- TODO: When lifecycle expansion or contract changes land, update this component document + `docs/reference/api/grpc-internal.md` + contract map in one atomic doc change to prevent drift.
