# Runtime/Data Observability Runbook (Phase-8B)

Use this runbook to triage runtime/storage regressions that require unified diagnostics across queue, scheduler, compiler, driver, and checkpoint persistence stages.

## Contract and version markers

Phase-8B runtime/data observability contract is additive and SemVer-governed.

- `runtime_data_observability_contract_version: 1.0.0`
- Required correlation keys:
  - `trace_id`
  - `job_id`
  - `dispatch_id`
  - `assignment_id`
  - `checkpoint_id`
  - `hardware_session_id`

### Lifecycle span model (required)

All runtime/data telemetry must preserve a single lifecycle chain in this strict order:

1. `queue`
2. `schedule`
3. `dispatch`
4. `execute`
5. `persist`
6. `checkpoint`

Each stage must emit `stage`, `started_at`, `finished_at`, and carry all required correlation keys.

## Alert pack (deterministic thresholds)

Prometheus alerts:

- `monitoring/metrics/prometheus/runtime-data-alerts.yaml`

### Queue pressure

- Trigger: `eigen_orch_queue_depth > 300` and `eigen_orch_queue_oldest_age_seconds > 180` for 10m.
- Why it matters: sustained depth + age indicates user-visible starvation risk.
- First response:
  1. Verify dispatch throughput and admission ratios per tenant.
  2. Confirm no stalled control-plane workers.
  3. Apply safe capacity policy rollback if threshold was introduced in the latest rollout.

### Compiler regressions

- Trigger warning: compile stage p95 > 1.2s for 15m.
- Trigger critical: compile stage p99 > 2.4s for 15m.
- First response:
  1. Compare compile-latency distribution to last known-good release.
  2. Validate compile cache hit rate and backend selection drift.
  3. Roll back compiler policy bundle if regression correlates with a policy/version bump.

### Driver degradation

- Trigger: execute-stage error rate > 3% for 10m.
- First response:
  1. Group failures by `hardware_session_id` and backend/driver version.
  2. Confirm whether degradation is localized to a single hardware pool.
  3. Isolate failing pool and re-route new assignments until driver rollback completes.

#### IBM Quantum-specific checks

When failures are concentrated on the `ibm:qiskit-runtime` target:

1. Confirm credential source and channel in `/healthz` (`auth_source`, `channel`, `instance`).
2. Distinguish taxonomy quickly:
   - `auth` → token/secret drift.
   - `quota` → provider credits or tenant rate limits.
   - `network`/`deadline_exceeded` → transient backend instability.
3. If quota-limited, reduce shot count and allow configured retry budget to absorb bursts before escalating.
4. If deadline failures persist beyond retry budget, fail over workload class to simulator profile and open provider incident with correlation IDs.

### Correlation breakage

- Trigger: any increase in `eigen_cluster_trace_breakage_total` over 10m.
- First response:
  1. Block promotion and mark the build as unsafe for release.
  2. Validate propagation of `trace_id`, `dispatch_id`, `assignment_id`, and `checkpoint_id` through queue envelopes and persistence records.
  3. Roll back the most recent telemetry propagation changes.

## CI/ops diagnostics requirements

Critical regressions must produce deterministic diagnostics payloads with:

- `reason_code` (stable enum-like marker)
- `severity`
- `correlation_keys_present` (boolean)
- `mitigation_hint`

Recommended reason codes:

- `QUEUE_PRESSURE_CRITICAL`
- `COMPILE_P95_REGRESSION`
- `COMPILE_P99_REGRESSION`
- `DRIVER_DEGRADATION_ERROR_RATE`
- `CORRELATION_LINEAGE_BREAKAGE`
