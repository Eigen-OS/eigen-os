# P9A-02 Implementation Spec — Live Qubit Manager Atomic Allocation + Offline Failover

## Scope

This specification defines Stage-9A implementation closure for LQM (QFS L1):

1. Atomic qubit allocation/deallocation with anti-double-booking guarantees.
2. Deterministic offline-node detection and state transitions.
3. Reconnect/backoff policy with safe degradation.
4. Stable error propagation across LQM ↔ QDriver boundaries.

Normative references:
- `docs/development/phase-9-open-core-tz-1.3.0-gap-and-plan.md`
- `docs/development/phase-9a/phase-9a-execution-plan.md`
- `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`
- `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

## Deterministic State Model

### Device state machine

`ONLINE -> DEGRADED -> OFFLINE -> RECONNECTING -> ONLINE`

Rules:
- `ONLINE -> DEGRADED` when driver health is partial or transient allocation errors exceed threshold.
- `DEGRADED -> OFFLINE` when healthcheck fails for `N` consecutive probes.
- `OFFLINE -> RECONNECTING` on scheduled reconnect attempt.
- `RECONNECTING -> ONLINE` only after successful healthcheck + allocation dry-run.
- `RECONNECTING -> OFFLINE` on reconnect failure with backoff increment.

All transitions must emit structured event records with:
- `device_id`
- `from_state`
- `to_state`
- `reason_code`
- `attempt`
- `trace_id`
- `timestamp_utc`

### Allocation state machine

`PENDING -> RESERVED -> ACTIVE -> RELEASED`

Failure path:
`PENDING -> FAILED`

Rules:
- Transition to `RESERVED` only via atomic compare-and-set over qubit ownership map.
- `ACTIVE` requires successful driver reservation acknowledgment.
- On driver failure after reservation, rollback to free pool is mandatory before returning error.
- `RELEASED` idempotent: duplicate release requests must not mutate state after first success.

## Atomicity Contract

For every `(device_id, qubit_id)` pair at any instant:
- Ownership cardinality is `0..1`.
- No overlapping `ACTIVE` allocations may include same pair.

Implementation constraints:
- Single logical transaction boundary for selection + reservation write.
- Deallocation is idempotent and monotonic.
- Read path must be linearizable for active ownership queries.

## Offline Failover Policy

### Probe policy

- Health probe interval: fixed configurable duration.
- Consecutive failure threshold: deterministic integer (`offline_after_failures`).
- Consecutive success threshold before ONLINE restore (`online_after_successes`).

### Reconnect policy

Exponential backoff with cap:
- `delay = min(max_backoff_ms, base_backoff_ms * 2^(attempt-1))`
- Optional deterministic jitter (seeded by `device_id`) is allowed only if explicitly fixed and reproducible.

### Safe degradation

When device in `OFFLINE` or `RECONNECTING`:
- New allocations targeting that device fail fast with stable error class.
- Existing ACTIVE allocations are marked `at_risk` and surfaced in telemetry.
- Scheduler/higher runtime receives availability update event for re-placement.

## Error Taxonomy Mapping (LQM ↔ QDriver)

All driver-originated errors must map to stable runtime classes:

- `INVALID_ARGUMENT` -> `LQM_ALLOCATION_INVALID_REQUEST`
- `FAILED_PRECONDITION` (device offline/unavailable) -> `LQM_DEVICE_OFFLINE`
- `RESOURCE_EXHAUSTED` -> `LQM_CAPACITY_EXHAUSTED`
- `UNAVAILABLE` -> `LQM_DRIVER_UNAVAILABLE_RETRYABLE`
- `DEADLINE_EXCEEDED` -> `LQM_DRIVER_TIMEOUT_RETRYABLE`
- `INTERNAL` / unknown -> `LQM_DRIVER_INTERNAL`

Retry semantics:
- Retryable classes: `UNAVAILABLE`, `DEADLINE_EXCEEDED`.
- Non-retryable classes: `INVALID_ARGUMENT`, `FAILED_PRECONDITION`, `RESOURCE_EXHAUSTED`.
- Retry policy must be deterministic and bounded by configured `max_attempts`.

## Test & Fixture Evidence (Required)

1. **Atomic race prevention**
   - Concurrent allocation attempts for same qubit set.
   - Assert exactly one success and deterministic loser error.
2. **Double-release idempotence**
   - Releasing same allocation twice returns deterministic result and no state corruption.
3. **Offline transition determinism**
   - Simulate probe failures/successes and assert exact state transition sequence.
4. **Reconnect backoff determinism**
   - Validate computed delay series against fixture for attempts 1..N.
5. **Error mapping conformance**
   - Inject each driver status and validate exact LQM error code.
6. **Telemetry observability**
   - Assert transition/allocation events include required fields.

## CI Gate Expectations

The Stage-9A CI must fail closed if any of the following regresses:
- allocation race prevention suite;
- offline/reconnect deterministic transition fixture;
- error taxonomy mapping fixture;
- contract drift without SemVer/migration notes compliance.

## Implementation Evidence (Current Repository)

- Reference implementation (deterministic in-process LQM model): `src/services/system-api/src/system_api/lqm.py`
- Conformance and deterministic fixtures/tests:
  - `src/services/system-api/tests/test_lqm_atomic_offline_failover.py`

## Versioning & Compatibility Classification

- Contract shape additions (new optional telemetry fields / reason codes): `MINOR`.
- Behavior-only bug fixes preserving contract semantics: `PATCH`.
- Any breaking state-model or error-code rewrite: `MAJOR` + migration notes required.
