# Observability

- **Document status:** Normative architecture + contracts index (MVP → Phase-1 baseline)
- **Scope:** Cross-cutting telemetry for Eigen OS runtime, orchestration, compilation, execution, and adaptive decisioning
- **Snapshot date:** 2026-05-25
- **Contract version:** `1.0.0`

This document defines the **system-wide observability model** for Eigen OS and the **minimum stable conventions** that all services MUST follow. Component-specific metric catalogs are defined in dedicated contracts (referenced below). This document is the normative glue across:

- metrics (Prometheus/OpenMetrics),
- traces (OpenTelemetry + W3C TraceContext),
- structured logs,
- runtime/audit events,
- health/readiness endpoints,
- CI conformance requirements,
- determinism + replay traceability requirements.

---

## 1. Contract Versioning

### 1.1 Contract marker metric

All services that export Eigen OS telemetry MUST expose:

```text
eigen_observability_contract_info{version="1.0.0"} 1
```

---

### 1.2 SemVer policy

#### MAJOR

- rename/remove metric families that are declared stable in a contract,
- incompatible label meaning changes,
- incompatible trace/log schema changes,
- breaking changes to event taxonomy.

#### MINOR

- add new metrics or optional labels (bounded),
- add new event types (additive),
- add new trace spans/attributes (additive),
- add new dashboards/alerts.

#### PATCH

- documentation corrections,
- implementation fixes without semantic changes,
- alert/dashboard tuning without changing meaning.

---

## 2. Normative References (Source of Truth)

This document delegates detailed metric catalogs to contract docs:

- `docs/architecture/orchestration-observability-contract.md` (scheduler/control plane metrics)
- `docs/architecture/intelligent-runtime-observability-contract.md` (runtime decisioning + explainability metrics)
- `docs/reference/error-model.md and docs/reference/error-mapping.md` (failure semantics and reason codes)
- `docs/architecture/contract-map.md and docs/architecture/data-flow.md` (end-to-end flow + correlation boundaries)

If a detail conflicts: **the specialized contract for that subsystem wins**, unless this document explicitly states a global rule (e.g., label cardinality prohibitions).

---

## 3. Responsibility

The Observability subsystem provides the unified telemetry, tracing, metrics, logging, and operational visibility layer for Eigen OS components.

### 3.1 Implemented in current repository (truthful baseline)

- Structured JSON logging in core runtime services.
- W3C TraceContext propagation (`traceparent`) implemented across core request flows.
- Prometheus-compatible `/metrics` endpoints exist in:
  - `system-api`
  - `driver-manager`
  - runtime helper services (where present)
- `/healthz` endpoints exist for runtime services.
- MVP observability release gates are enforced via RFC 0018 and ADR 0007 (CI/integration checks).

---

### 3.2 Target responsibility (architecture baseline)

The final Observability subsystem SHALL provide end-to-end visibility across:

- System API, Kernel/QRTX, Compiler, Driver Manager,
- distributed runtime split/merge,
- HWE, GNN Optimizer, Neuro-Symbolic Core, Knowledge Base (when enabled),
- hardware telemetry normalization and SLO signals,
- deterministic replay evidence and auditability.

---

## 4. Global Observability Principles (MUST)

### 4.1 Deterministic correlation

Every user-facing job lifecycle and execution MUST be traceable via stable correlation identifiers:

- `trace_id` (distributed tracing)
- `job_id` (runtime identity)
- `device_id` / `backend_id` (where applicable)

---

### 4.2 gRPC status-first error visibility

Errors MUST follow canonical gRPC status semantics and structured details (see error model/mapping). Logs/traces MUST record:

- gRPC status code,
- stable reason code (`EIGEN_*` family),
- correlation IDs,
- optional artifact references (never raw sensitive payloads).

---

### 4.3 Bounded label cardinality

Metric labels MUST remain bounded and deterministic.
Metric labels MUST NOT include:

- `job_id`, `trace_id`, `request_id`, `tenant_id`, `user_id`,
- freeform error messages,
- arbitrary backend payload values,
- unbounded strings (policy expressions, stack traces, etc.).

Correlation belongs in traces/logs and QFS artifacts, not metric labels.

---

### 4.4 No sensitive leakage

Telemetry MUST NOT expose:

- credentials,
- tokens,
- secrets,
- raw provider responses containing sensitive identifiers,
- user payload data.

---

### 4.5 “No silent degradation”

If telemetry drops, sampling increases, or explainability is disabled, the system MUST emit explicit indicators (metrics + logs).

---

## 5. Telemetry Surfaces

Eigen OS uses four telemetry classes:

1. **Metrics** (Prometheus/OpenMetrics)
2. **Traces** (OpenTelemetry; W3C TraceContext propagation)
3. **Logs** (structured JSON; correlation fields)
4. **Events** (job/runtime/audit events; optionally durable)

---

## 6. Metrics Contract (Global Rules)

### 6.1 Required HTTP endpoints

Runtime services MUST expose:

- `GET /metrics` (Prometheus text format)
- `GET /healthz` (liveness baseline)

Target environments SHOULD additionally expose:

- `GET /ready` (readiness)
- `GET /live` (liveness with dependency checks as appropriate)

---

### 6.2 Metric namespace rules

- Service-level metrics SHOULD use `eigen_<service>_*` (e.g., `eigen_api_*`, `eigen_driver_*`).
- Subsystem contract metrics MUST use their declared prefixes:
  - orchestration: `eigen_orch_*`
  - intelligent runtime: `eigen_runtime_*`
  - cluster/distributed runtime (split/merge): `eigen_cluster_*` (where defined by contract)
- Global contract markers:
  - `eigen_observability_contract_info{version=...} 1`

---

### 6.3 Histograms

Latency and size measurements MUST be exported as Prometheus histograms with full families:

- `_bucket`
- `_sum`
- `_count`

Histogram bucket choices MUST be stable within a MAJOR version of the relevant contract.

---

### 6.4 Minimum “always-on” service metrics (baseline)

All production services MUST export a minimal baseline:

- request counter
- request duration histogram
- error counter (by stable reason/status family, bounded)
- exporter snapshot freshness (timestamp + age)

If a service-specific contract exists, it governs naming; otherwise, the following patterns are acceptable:

```text
eigen_service_requests_total{rpc,code}
eigen_service_request_latency_ms_bucket{rpc}
eigen_service_internal_errors_total{component}
eigen_service_snapshot_timestamp_seconds
eigen_service_snapshot_age_seconds
```

`rpc` MUST be bounded (enumerated RPC names). `code` MUST be bounded (gRPC code set).

---

### 6.5 Contract-specific metrics (authoritative)

Use the dedicated contracts for required catalogs:

- Orchestration control plane metrics: `docs/architecture/orchestration-observability-contract.md`
- Intelligent runtime decisioning metrics: `docs/architecture/intelligent-runtime-observability-contract.md`

---

## 7. Tracing Contract (Global Rules)

### 7.1 Propagation

Eigen OS uses **W3C TraceContext**. Required header: `traceparent`

Propagation path (minimum MVP baseline):

```text
Client/CLI/SDK
→ System API
→ Kernel/QRTX
→ Compiler
→ Driver Manager
→ Backend (where supported)
```

---

### 7.2 Required span attributes (bounded)

Spans SHOULD include bounded attributes:

- `eigen.job_id` (OK in traces; not in metrics)
- `eigen.device_id` / `eigen.backend_id` (where applicable)
- `rpc.method`
- `rpc.service`
- `grpc.status_code`
- `eigen.error_reason` (stable `EIGEN_*` code when failure)

---

### 7.3 Required span coverage (target)

When components exist/enabled, tracing MUST include spans for:

- scheduling decisions,
- compilation phases (parse/validate/lower/serialize),
- driver dispatch and backend execution,
- split/merge planner, worker execution, merge coordinator,
- explainability endpoints (when enabled),
- optimizer/neuro-symbolic advisory calls (when enabled).

---

## 8. Structured Logging Contract (Global Rules)

### 8.1 Required log fields (baseline)

All services MUST emit structured JSON logs with (at minimum):

| **Field** | **Required** | **Notes** |
|---|---|---|
| `timestamp` | yes | RFC3339 or epoch ms (must be consistent per service) |
| `level` | yes | info/warn/error |
| `service` | yes | stable service name |
| `message` | yes | human-readable |
| `trace_id` | yes | derived from tracing context |
| `span_id` | yes | where applicable |
| `job_id` | no | include when known |
| `device_id` | no | include when relevant |
| `rpc_method` | no | for RPC logs |
| `grpc_status` | no | for RPC logs |
| `error_reason` | no | stable `EIGEN_*` reason code |
| `artifact_ref` | no | QFS reference for large diagnostics |

---

### 8.2 Redaction rules (MUST)

Logs MUST NOT include:

- secrets/tokens,
- raw provider payloads (unless explicitly redacted and policy-permitted),
- user source code content (unless explicitly allowed and stored via artifact refs).

---

## 9. Event Model (Runtime/Audit)

### 9.1 Current implementation state

- No standalone, production event-bus runtime is required for MVP.
- Event streaming is an architecture target; some “events” exist as logs + QFS timeline artifacts depending on deployment.

---

### 9.2 Target behavior

Observability SHALL support event streaming backends:

- Kafka
- NATS
- Redis Streams
- in-memory mode (dev)

Event durability modes:

- transient
- buffered
- durable/auditable

---

### 9.3 Required event classes (bounded taxonomy)

- `JobEvents`
- `HardwareEvents`
- `CompilerEvents`
- `OrchestrationEvents`
- `RuntimeDecisionEvents`
- `OptimizerEvents`
- `SecurityEvents`
- `SystemEvents`

Each event MUST include:

- event type (bounded),
- timestamp,
- correlation ids (trace_id/job_id where applicable),
- stable reason codes where applicable,
- optional `artifact_ref` for large payloads.

---

## 10. Storage, Replay, and Auditability

### 10.1 MVP baseline

- Centralized observability persistence is not mandatory for MVP execution.
- QFS persistence is authoritative for job-scoped artifacts (results, errors, timelines).

---

### 10.2 Target requirements

To support deterministic replay and audits, the system SHOULD persist:

- timeline artifacts,
- error artifacts,
- decision/explainability artifacts (where enabled),
- optimizer/neuro-symbolic decision traces (where enabled).

Recommended job-scoped layout (illustrative; exact paths may vary by deployment profile):

```text
qfs://jobs/<job_id>/
  results/results.json
  results/error.json
  timeline/timeline.json
  logs/run.log
  orchestration/...
  runtime/...
  explain/...
```

---

## 11. Health and Readiness

### 11.1 MVP endpoints (implemented)

- `GET /healthz`

---

### 11.2 Target health model

Services SHOULD expose:

- /live – process liveness
- /ready – dependency readiness (DB/QFS/exporter connections)
- component health signals for:
  - metrics exporter health,
  - trace exporter health,
  - event bus health (if enabled),
  - storage health.

---

## 12. Failure Modes and Degradation (Normative Requirements)

### 12.1 Required failure taxonomy (observability pipeline)

- metrics backend unavailable
- trace export failure
- event bus outage
- ingestion overload
- exporter misconfiguration
- schema incompatibility
- missing credentials
- correlation loss / partial partitions
- clock skew effects

---

### 12.2 Required recovery mechanisms (target)

Observability SHOULD support:

- bounded buffering,
- adaptive sampling (explicitly signaled),
- dead-letter queues (for events/spans where applicable),
- circuit breakers for exporters,
- replay-safe recovery (no silent drops),
- safe default telemetry mode.

---

## 13. Observability of Observability

### 13.1 Implemented baseline examples (non-exhaustive)

- `eigen_api_requests_total`
- `eigen_api_request_duration_seconds`
- `eigen_api_authz_denied_total`

---

### 13.2 Required target platform metrics

- `observability_requests_total`
- `observability_pipeline_errors_total`
- `observability_export_latency_seconds`
- `observability_trace_drop_total`
- `observability_event_backpressure`

---

### 13.3 Quantum hardware telemetry (target)

Standardized metric families (names may be finalized in a dedicated hardware observability contract; until then these are normative targets):

- `eigen_quantum_t1_seconds`
- `eigen_quantum_t2_seconds`
- `eigen_quantum_gate_fidelity`
- `eigen_quantum_readout_fidelity`
- `eigen_quantum_queue_depth`
- `eigen_quantum_calibration_age_seconds`
- `eigen_quantum_topology_degradation_total`

---

## 14. Dashboards, Alerts, and Runbooks

### 14.1 Current state

Repository-level dashboards/runbooks exist for multiple subsystems (orchestration, intelligent runtime, benchmark/runtime helpers) depending on deployment profile.

---

### 14.2 Target dashboards

Operational dashboards SHOULD include:

- runtime overview (submit→compile→execute→results),
- orchestration (queue depth/age, fairness, quota),
- compilation (latency, failure rates, limit hits),
- driver/backend execution (latency, errors, availability),
- hardware state (calibration freshness, fidelity, queue),
- intelligent runtime (decisioning, fallback, explain endpoints),
- distributed runtime split/merge (if enabled),
- replay/audit health.

---

### 14.3 Alert categories (target)

- telemetry ingestion/export failures,
- trace continuity loss,
- hardware degradation,
- optimizer instability (when enabled),
- neuro-symbolic drift (when enabled),
- replay inconsistency,
- SLO violations.

---

## 15. Security and Compliance (Normative)

Observability pipelines MUST:

- use encrypted transport for telemetry export where applicable,
- enforce RBAC for any query/export endpoints,
- support retention controls,
- maintain an immutable audit trail for security-relevant events,
- avoid multi-tenant leakage (no unsafe labels; redaction in logs).

---

## 16. CI / Conformance Requirements

CI MUST validate (MVP baseline):

1. `/metrics` endpoint exists and is scrapeable for required services,
2. `/healthz` exists for required services,
3. trace propagation works across core path,
4. metric type stability for declared stable metrics,
5. bounded label rules (no prohibited labels),
6. dashboards/alerts reference valid metrics (where shipped).

CI SHOULD validate (as subsystems land):

- orchestration contract metrics (`eigen_orch_*`) presence and types,
- intelligent runtime contract metrics (`eigen_runtime_*`) presence and types,
- split/merge observability metrics presence (where enabled),
- explainability level encoding rules (where applicable).

---

## 17. Closure Criteria

The Observability subsystem is considered MVP-complete when:

1. core services export `/metrics` and `/healthz`,
2. trace propagation is enforced end-to-end across the MVP flow,
3. structured logs include correlation IDs,
4. error semantics are observable and normalized,
5. CI enforces observability release gates (RFC 0018 / ADR 0007).

The subsystem is considered Phase-1 complete when:

1. orchestration + intelligent runtime observability contracts are fully satisfied in production,
2. distributed runtime (split/merge) telemetry is integrated (where enabled),
3. hardware telemetry normalization is standardized,
4. explainability telemetry is complete for adaptive decisioning paths,
5. replay/audit artifacts are consistently persisted and retrievable.

---

## 18. Invariants (MUST remain true)

- Trace propagation uses W3C TraceContext.
- Metrics labels remain bounded and do not contain correlation identifiers.
- Logs/traces carry correlation identifiers for debugging and auditability.
- No silent telemetry degradation; drops/sampling must be visible.
- Observability changes that affect stable contracts require SemVer governance.
- Observability never weakens security or determinism guarantees.
