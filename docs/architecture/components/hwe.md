# HWE (Hardware Workflow Engine)

- **Phase:** Post-MVP / roadmap (target component, no standalone service yet)
- **Implementation state (verified on 2026-05-08):** Dedicated `hwe` service/crate/proto is **not** present in runtime tree; current responsibilities are split between `eigen-kernel`, `driver-manager`, and partially planned `qfs` Level-1 semantics.
- **Source alignment:** RFC 0006, RFC 0016, RFC 0019, RFC 0009, ADR 0007, ADR 0006, architecture overview.

## Responsibility

HWE is treated as a **future orchestration layer for hardware-aware execution lifecycle** that should eventually centralize:

1. hardware capability and health ingestion,
2. execution-time adaptation decisions,
3. feed-forward/live-qubit lifecycle controls,
4. cross-backend execution-policy hooks.

### What is already implemented (today)

- Hardware execution entrypoint exists through `eigen-kernel -> driver-manager` internal gRPC contract (`DriverManagerService`).
- Driver-side capability handshake and healthcheck are implemented in the `driver-manager` plugin contract.
- Minimal backend diversity exists: simulator path + Qiskit Runtime skeleton.
- Security/isolation for runtime exists at MVP baseline level only (logical controls, no hardware-rooted isolation guarantees).

### TODO (not yet implemented, must be preserved)

- TODO: Introduce explicit `HWE` bounded context (service or crate) with clear ownership boundaries vs `driver-manager`, `resource-manager`, and `kernel`.
- TODO: Move hardware-aware policy logic from implicit/fragmented placement into a documented HWE API.
- TODO: Define and implement lifecycle ownership for live-qubit/feed-forward operations currently tracked only as architecture intent.
- TODO: Define production semantics for adaptive runtime decisions based on hardware telemetry (noise, queue, calibration freshness, outage).

## Interfaces

## 1) Current implemented interfaces

- `eigen-kernel` uses internal gRPC `DriverManagerService` for:
  - `ListDevices`,
  - `GetDeviceStatus`,
  - `ExecuteCircuit`,
  - `CalibrateDevice`.
- Driver plugins implement base software contract (`BaseDriver` / `QDriver`) with:
  - `initialize`,
  - `capability_handshake`,
  - `healthcheck`,
  - `get_devices`,
  - `get_device_status`,
  - `execute_circuit`,
  - optional calibration path.

## 2) TODO interface surface for HWE

- TODO: Define dedicated `HWEControlService` protobuf contract (or equivalent Rust API) instead of overloading driver-manager interface.
- TODO: Add API for hardware snapshot ingestion (`noise`, `topology`, `availability`, `queue pressure`, `policy constraints`).
- TODO: Add API for execution adaptation decisions (reroute/retry/defer/abort with reason taxonomy).
- TODO: Add API for feed-forward primitives and live resource handles (if/when QFS Level-1 is activated).
- TODO: Add explicit idempotency and determinism policy for adaptive actions.

## Inputs / Outputs

## Implemented now

### Inputs

- Compiled circuit payload (`AQO`-backed payload through kernel execution path).
- Target `device_id` and runtime options.
- Driver capability metadata and device-status snapshots from drivers.

### Outputs

- Execution counts + metadata from selected backend/driver.
- Device status responses and calibration references.
- Structured error surface propagated back through kernel/public API pipeline.

## TODO for HWE

- TODO: Define canonical `HardwareExecutionContext` object (policy, constraints, telemetry snapshot, provenance).
- TODO: Define normalized `ExecutionDecision` and `ExecutionOutcome` schemas (including adaptation trail).
- TODO: Define contract for partial results under adaptive retries/failover.
- TODO: Define stable mapping between hardware telemetry confidence and scheduling/execution decisions.

## Storage / State

## Implemented now

- No dedicated persistent HWE store exists.
- Driver registry and device ownership map are in-memory in `driver-manager`.
- Durable artifacts remain outside this concern in current architecture (results and artifacts handled by existing runtime/QFS paths).

## TODO for HWE

- TODO: Define authoritative state model for hardware snapshots and calibration validity windows.
- TODO: Decide persistence boundary (in-memory cache vs durable store) for adaptation decisions and audit trail.
- TODO: Define retention and compaction policy for telemetry/history used by future adaptive algorithms.
- TODO: Define consistency model across clustered runtime (single-writer, eventual, or strongly consistent path).

## Failure modes

## Implemented now

- Missing driver/device mapping produces structured `NOT_FOUND` style execution errors.
- Backend execution failures are surfaced as structured driver-manager execution errors with metadata.
- Driver readiness/auth misconfiguration (e.g., runtime token path) is reflected in health status and invocation failure.
- No HWE-specific failure taxonomy exists yet.

## TODO for HWE

- TODO: Define HWE-specific failure taxonomy (`telemetry_stale`, `adaptation_conflict`, `policy_denied`, `fallback_exhausted`, `feed_forward_timeout`).
- TODO: Define retry/failover matrix by failure class and determinism mode.
- TODO: Define circuit-safety invariants for adaptation (what cannot change without invalidating job semantics).
- TODO: Define blast-radius limits and circuit breaker behavior for provider-wide incidents.

## Observability

## Implemented now

- Existing runtime observability is exposed through current kernel/driver-manager metrics, logs, and health endpoints.
- Driver-manager publishes baseline request counters and exposes health/status information suitable for operator runbooks.
- Trace-context propagation/logging exists; full HWE-level tracing model is not defined.

## TODO for HWE

- TODO: Define HWE metrics namespace (decision latency, adaptation count, fallback success rate, telemetry freshness age).
- TODO: Define HWE tracing spans/events linking compile intent, decision, backend invocation, and final outcome.
- TODO: Define structured explainability payload for “why this hardware decision was taken”.
- TODO: Add SLO/SLI set for hardware-adaptive execution quality (success rate under degraded hardware, p95 decision latency, deterministic replay compliance).

## RFC / ADR consistency check (2026-05-08)

- RFC 0006 and RFC 0016 establish the current executable boundary around `kernel <-> driver-manager`, which is implemented and currently absorbs responsibilities that a future HWE could formalize.
- RFC 0019 (phase-1 production runtime) expands robustness expectations for real-provider execution, but still does not instantiate a standalone HWE component.
- RFC 0009 and ADR 0007/0006 maintain MVP security/runtime boundaries (no advanced hardware isolation baseline), consistent with current absence of HWE-specific trust/isolation lifecycle.
- Architecture overview and component docs still carry explicit TODOs for live-qubit/feed-forward and deeper hardware-aware adaptation, which this document preserves as forward work.

## Scope guardrails for next stage

To avoid scope drift in next iteration:

1. Keep `driver-manager` focused on provider adapter contract + transport concerns.
2. Introduce HWE only with explicit contract/versioning and conformance tests.
3. Land HWE in phases:
   - Phase A: decision model + passive observability,
   - Phase B: active adaptation (retry/reroute),
   - Phase C: feed-forward/live-qubit lifecycle.
4. Gate each phase with RFC+ADR update, docs contract-map update, and release-readiness checklist deltas.
