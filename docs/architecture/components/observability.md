# Observability

- **Phase:** MVP → Phase-1 evolution baseline
- **Status snapshot date:** 2026-05-25
- **Source alignment:** RFC 0008, RFC 0018, ADR 0007, architecture overview, runtime observability contracts

---

# Responsibility

The Observability subsystem provides the unified telemetry, tracing, metrics, logging, and operational visibility layer for Eigen OS runtime and orchestration components.

Current implementation is distributed across runtime services (`system-api`, `eigen-kernel`, `driver-manager`, `eigen-compiler`) and satisfies MVP runtime observability gates.

The long-term architecture target is a centralized observability platform with unified telemetry ingestion, trace correlation, quantum-hardware monitoring, adaptive-runtime explainability, and operational analytics.

---

# Responsibility Scope

## Implemented now

### Runtime telemetry

- Structured JSON logging is implemented in runtime services.
- Correlation fields are propagated and logged:
  - `trace_id`
  - `traceparent`
  - `request_id`
  - `job_id`
  - `device_id` (where available)
- W3C TraceContext (`traceparent`) propagation is implemented and validated in integration/runtime flows.

### Metrics

- Prometheus-compatible `/metrics` endpoints exist in:
  - `system-api`
  - `driver-manager`
  - runtime helper services
- MVP runtime metrics and release gates are enforced through RFC 0018 and ADR 0007.

### Runtime release-readiness observability

- Runtime observability checks are integrated into MVP release-readiness contracts.
- Trace propagation and metrics correctness are validated in CI/runtime integration flows.

### Health visibility

- Basic `/healthz` endpoints exist for runtime services.
- Driver Manager exposes health and metrics endpoints for operational diagnostics.

---

## Required target responsibility (architecture baseline)

The final Observability subsystem SHALL provide:

- Unified telemetry collection across all Eigen OS components.
- Distributed tracing across:
  - System API
  - Compiler
  - Kernel
  - Driver Manager
  - HWE
  - Neuro-Symbolic Core
  - GNN Optimizer
  - Knowledge Base
- Quantum hardware observability:
  - T1/T2 metrics
  - gate fidelity
  - readout fidelity
  - queue depth
  - calibration freshness
  - topology degradation indicators
- Runtime event streaming and auditability.
- Deterministic traceability and replay support.
- Operational SLO/SLI visibility.
- Explainability telemetry for adaptive and neuro-symbolic decisions.
- Security telemetry and compliance audit trails.

---

# Architecture Position

Observability is a cross-cutting platform capability.

It integrates with:

- `system-api`
- `eigen-kernel`
- `eigen-compiler`
- `driver-manager`
- future `hwe`
- future `gnn-optimizer`
- future `knowledge-base`
- future `neuro-symbolic-core`

Observability is mandatory infrastructure for:

- deterministic replay,
- adaptive-runtime auditability,
- rollback verification,
- distributed runtime diagnostics,
- release-readiness validation,
- production SLO enforcement.

---

# Interfaces

# 1. gRPC Interfaces

## Implemented now

- No standalone `ObservabilityService` gRPC service is implemented in the current repository state.
- Telemetry is emitted independently by runtime services.

---

## Target gRPC API

The future centralized observability subsystem SHALL expose:

### `ObservabilityService`

### Required methods

- `PushMetrics`
- `PushEvents`
- `ExportSpans`
- `QueryMetrics`
- `QueryTraces`
- `SubscribeToEvents`
- `PublishEvent`
- `HealthCheck`

---

## Required contracts

### Metrics ingestion

#### Input

- metric name
- labels
- timestamp
- value
- source service
- tenant/environment metadata

### Trace export

#### Input

- trace spans
- correlation IDs
- runtime context
- hardware context
- optimizer/neuro-symbolic decision metadata

### Event streaming

#### Supported event classes

- `JobEvents`
- `HardwareEvents`
- `CompilerEvents`
- `OptimizerEvents`
- `SecurityEvents`
- `SystemEvents`

---

# 2. REST Interfaces

## Implemented now

### Available endpoints

- `GET /metrics`
- `GET /healthz`

Implemented in runtime services and helper servers.

---

## Required target endpoints

### Health

- `GET /health`
- `GET /ready`
- `GET /live`

### Metrics and telemetry

- `GET /metrics`
- `GET /metrics/quantum/{device_id}`
- `GET /metrics/runtime/{service}`

### Tracing

- `GET /traces/{trace_id}`
- `GET /traces/job/{job_id}`

### Event streaming

- `WS /events/stream`
- `GET /events/history`

---

# 3. Event Bus Interfaces

## Implemented now

- No production event-bus runtime is implemented specifically for observability.
- Architecture intent exists only at RFC and architecture-document level.

---

## Required target behavior

Observability SHALL support event-streaming backends:

- Kafka
- NATS
- Redis Streams
- in-memory runtime mode

### Required event durability modes

- transient
- buffered
- durable/auditable

---

# 4. Integration Interfaces

## Implemented now

Runtime instrumentation exists for:

- System API
- Driver Manager
- Compiler request lifecycle
- Runtime trace propagation
- Release gates

Runtime observability requirements are enforced through:

- RFC 0018
- ADR 0007

---

## Required future integrations

### Compiler integration

Telemetry for:

- AST parsing
- AQO lowering
- optimizer passes
- neuro-symbolic advisory decisions

### Hardware integration

Telemetry for:

- calibration state
- noise snapshots
- queue pressure
- routing degradation

### Adaptive runtime integration

Telemetry for:

- HWE decisions
- GNN optimizer routing decisions
- neuro-symbolic recommendations
- fallback activations
- deterministic replay markers

---

# Inputs / Outputs

# Inputs

## Implemented now

### Runtime telemetry inputs

- HTTP/gRPC request counts
- request timing
- authorization denials
- trace propagation metadata
- runtime lifecycle events

---

## Required target inputs

### Quantum hardware telemetry

- T1/T2
- gate fidelity
- readout fidelity
- topology state
- calibration freshness
- queue depth
- outage/degradation markers

### Distributed tracing

- OTLP/OpenTelemetry spans
- correlation IDs
- execution lineage metadata

### Runtime events

- execution events
- scheduler decisions
- optimizer events
- security events
- policy violations

### Adaptive-runtime telemetry

- GNN optimizer decisions
- neuro-symbolic confidence and explanations
- fallback activations
- hardware adaptation actions

---

# Outputs

## Implemented now

### Current outputs

- Prometheus metrics payloads
- structured JSON logs
- runtime lifecycle logs
- health responses

---

## Required target outputs

### Time-series telemetry

- Prometheus/OpenMetrics
- OTLP metrics
- long-term TSDB persistence

### Trace exports

- Jaeger
- OTLP
- Tempo-compatible export

### Event fan-out

- Kafka/NATS/WebSocket streams
- alert pipelines
- audit streams

### Explainability telemetry

- optimizer decision traces
- neuro-symbolic rationale payloads
- hardware adaptation explanations

---

# Storage / State

# Internal State

## Implemented now

### Existing runtime state

In-memory counters exist for:

- request totals
- request duration
- authorization denials

Basic metrics registries are implemented in runtime services.

---

## Required target internal state

### Metrics state

- centralized metrics registry
- label indexes
- aggregation windows
- sampling policies

### Trace state

- buffered spans
- batching/export queues
- replay correlation indexes

### Event state

- event queues
- deduplication windows
- backpressure controls
- subscriber/session tracking

---

# External Storage

## Implemented now

- No centralized observability persistence layer is mandatory in current MVP runtime.

---

## Required target storage

### Metrics storage

- Prometheus-compatible TSDB

### Trace storage

- Jaeger
- Tempo
- OTLP backends

### Event storage

- Kafka topics
- audit logs
- immutable event archives

### Replay/audit storage

- deterministic replay traces
- optimizer decision history
- neuro-symbolic audit artifacts

---

# Caching

## Implemented now

- No dedicated observability caching subsystem exists.

---

## Required target caches

- metrics aggregation cache
- trace sampling cache
- event deduplication cache
- topology snapshot cache
- adaptive-runtime telemetry cache

---

# Failure Modes

## Implemented now

- RFC 0018 defines runtime observability release gates.
- Metrics payload correctness is test-covered.
- Trace propagation is integration-tested.

---

## Required target failure taxonomy

### Telemetry pipeline failures

- metrics backend unavailable
- trace export failure
- event bus outage
- ingestion overload

### Runtime degradation

- telemetry throttling
- adaptive sampling activation
- event dropping
- degraded trace retention

### Distributed consistency failures

- clock skew
- duplicate span IDs
- correlation loss
- partial telemetry partitions

### Configuration failures

- invalid exporter configuration
- incompatible schema version
- missing credentials
- malformed alert policy

---

## Recovery and fallback requirements

The observability subsystem SHALL support:

- bounded buffering
- adaptive degradation
- dead-letter queues
- circuit breakers
- replay-safe recovery
- safe default telemetry modes

---

# Observability of Observability

# Metrics

## Implemented now

Existing metrics include:

- `eigen_api_requests_total`
- `eigen_api_request_duration_seconds`
- `eigen_api_authz_denied_total`

---

## Required target metrics

### Platform metrics

- `observability_requests_total`
- `observability_pipeline_errors_total`
- `observability_export_latency_seconds`
- `observability_trace_drop_total`
- `observability_event_backpressure`

### Quantum runtime metrics

- `eigen_quantum_t1_seconds`
- `eigen_quantum_t2_seconds`
- `eigen_quantum_gate_fidelity`
- `eigen_quantum_readout_fidelity`
- `eigen_quantum_queue_depth`

### Adaptive-runtime metrics

- `eigen_hwe_decisions_total`
- `eigen_gnn_optimizer_invocations_total`
- `eigen_neuro_symbolic_fallback_total`
- `eigen_optimizer_confidence_distribution`

---

# Logs

## Implemented now

- Structured JSON logs exist in runtime services.

---

## Required target logging

- unified cross-service schema
- audit logging
- security telemetry
- optimizer decision logging
- hardware adaptation logging
- neuro-symbolic explainability logging

---

# Traces

## Implemented now

- TraceContext propagation exists.
- Runtime trace propagation is contract-tested.

---

## Required target tracing

### Full distributed tracing across

- API
- compiler
- kernel
- driver-manager
- HWE
- optimizer
- neuro-symbolic runtime
- knowledge-base

### Required trace metadata

- job lineage
- backend mapping decisions
- optimizer confidence
- hardware telemetry snapshot
- deterministic replay IDs

---

# Health Checks

## Implemented now

- Basic runtime `/healthz` endpoints exist.

---

## Required target health model

### Component health

- metrics pipeline health
- trace exporter health
- event-bus health
- storage backend health

### Runtime quality health

- telemetry freshness
- queue backlog
- dropped telemetry ratio
- replay consistency validation

---

# Dashboards and Alerts

## Implemented now

Repository-level dashboards and runbooks exist for:

- orchestrator
- benchmark runtime
- intelligent runtime
- cluster runtime
- plugin runtime

---

## Required target dashboards

### Operational dashboards

- runtime overview
- distributed tracing
- quantum hardware state
- adaptive-runtime decisions
- optimizer behavior
- neuro-symbolic advisory decisions

### Alert categories

- telemetry ingestion failures
- trace loss
- hardware degradation
- optimizer instability
- neuro-symbolic drift
- replay inconsistency
- SLO violations

---

# Security and Compliance

## Required target controls

### Telemetry security

- signed telemetry exports
- encrypted transport
- RBAC for observability APIs
- audit retention controls

### Compliance requirements

- immutable audit trail
- deterministic replay evidence
- retention/versioning policy
- export provenance tracking

---

# RFC / ADR Alignment

## Reviewed

- RFC 0008 — Observability MVP
- RFC 0018 — MVP-3 Runtime Observability and Release Gates
- ADR 0007 — MVP-3 release-readiness and observability gates

---

## Alignment Summary

### Implemented and aligned

- MVP runtime observability gates are implemented.
- Trace propagation is implemented and validated.
- Metrics and structured logging exist in runtime services.
- Release-readiness observability requirements are integrated into CI/runtime validation flows.

---

## Remaining architecture gaps

The following architecture targets remain not fully implemented:

- centralized observability control plane,
- unified telemetry storage/query layer,
- quantum hardware observability standardization,
- distributed tracing backend,
- adaptive-runtime explainability telemetry,
- neuro-symbolic and GNN optimizer observability integration.

These gaps remain explicitly preserved as required future work to prevent architecture scope loss.