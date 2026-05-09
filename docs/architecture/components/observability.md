# Observability

- Phase: MVP
- Status snapshot date: 2026-05-09

## Responsibility

Observability in the current codebase is **distributed across services** (System API, Kernel, Driver Manager, Compiler, benchmark/runtime packs) rather than a single fully implemented "Observability Core" service.

### Implemented now

- Structured JSON logging with correlation fields in System API (`trace_id`, `job_id`, `traceparent`, `request_id`, etc.).
- Basic Prometheus-compatible `/metrics` endpoint in System API.
- W3C TraceContext (`traceparent`) propagation is part of MVP observability contracts and tested in runtime/integration flow.
- Runtime observability and release gates are formalized via RFC/ADR package (RFC 0018 + ADR 0007).

### TODO (not fully implemented as a standalone component)

- [ ] Centralized Observability Core service with unified ownership of metrics/traces/events.
- [ ] Unified cross-component observability control plane for all Eigen OS components.
- [ ] Full quantum-specific metric model (T1/T2/fidelity) exposed consistently by runtime services.

## Interfaces

### 1. gRPC API

### Implemented now

- No dedicated `ObservabilityService` gRPC API is implemented as an independent service in this repository state.

### TODO

- [ ] Define and implement `proto/observability/service.proto`.
- [ ] Implement `ObservabilityService` methods:
  - [ ] `PushMetrics()`
  - [ ] `QueryMetrics()`
  - [ ] `ExportSpans()`
  - [ ] `SubscribeToEvents()`
  - [ ] `PublishEvent()`
  - [ ] `HealthCheck()`

### 2. REST API endpoints

### Implemented now

- `GET /metrics` exists in System API observability helper server.

### TODO

- [ ] Standardize and document a single service-level `GET /health` for observability subsystem.
- [ ] `GET /metrics/quantum/{device}` endpoint.
- [ ] `GET /traces/{trace_id}` endpoint.
- [ ] `WS /events/stream` endpoint for live event monitoring.

### 3. Event bus interface

### Implemented now

- Event-bus architecture exists at contract/architecture intent level only for this component.

### TODO

- [ ] Implement publisher/subscriber event bus abstraction for observability events.
- [ ] Implement/select production backends (Kafka, Redis, in-memory, NATS) for this component.
- [ ] Formalize event schemas for `HardwareEvents`, `JobEvents`, `SystemEvents`, `SecurityEvents`.

### 4. Integration points

### Implemented now
- System API instrumentation exists (logs + basic metrics).
- Runtime observability requirements across `system-api -> kernel -> driver-manager` are codified in RFC 0018 and ADR 0007.

### TODO
- [ ] Automatic job lifecycle instrumentation in a dedicated kernel-observability integration layer.
- [ ] Dedicated driver-level quantum hardware metric ingestion pipeline for central observability component.
- [ ] Unified SDK/helpers for standardized metrics+trace emission by all services.

## Inputs / Outputs

### Inputs

### Implemented now

- Request lifecycle timing/counts from System API.
- Authorization denial counters from System API.
- Trace context headers (`traceparent`) and derived `trace_id` in request context.

### TODO

- [ ] Full ingestion of quantum hardware metrics (T1, T2, gate/readout fidelity).
- [ ] Unified ingestion of distributed span payloads for storage/query.
- [ ] Unified ingestion of hardware/job/system/security events.
- [ ] Centralized YAML-driven configuration for collection intervals/exporters/event bus settings.

### Outputs

### Implemented now

- Prometheus text payload from System API `/metrics`.
- Structured JSON logs for request lifecycle and authz denials.

### TODO

- [ ] Time-series backend integration managed by a dedicated observability service.
- [ ] Jaeger/OTLP trace storage and retrieval API as productized component feature.
- [ ] Kafka/WebSocket alert/event fan-out from observability subsystem.
- [ ] Dedicated observability API query responses for historical metrics/traces.

## Storage / State

### Internal state

### Implemented now

- In-memory counters in System API metrics state:
  - request total
  - request duration sum
  - authz denied total

### TODO

- [ ] Central metrics registry with labels and richer metric types.
- [ ] Trace buffering with batch export policies.
- [ ] Event buffering and backpressure controls.
- [ ] Subscription/session state for realtime stream consumers.

### External storage

### Implemented now

- No mandatory centralized external observability storage implemented by this component itself.

### TODO

- [ ] Prometheus/compatible TSDB as managed storage target.
- [ ] Jaeger/OTLP-compatible trace backend integration.
- [ ] Event-log retention backend (e.g., Kafka topics).
- [ ] Central configuration storage contract (file/env/control-plane).

### Caching

### Implemented now

- No dedicated caching layer documented/implemented for observability component.

### TODO

- [ ] Metric aggregation cache for frequent queries.
- [ ] Trace sampling configuration and cache.
- [ ] Event deduplication/batching cache.

## Failure Modes

### Implemented now

- RFC 0018 defines required runtime observability checks as release gates.
- System API metrics server behavior is test-covered for payload correctness.

### TODO

- [ ] Backend unavailability strategy for metrics/traces/events (buffering, drop policies, circuit breakers).
- [ ] Resource exhaustion strategies (adaptive sampling, throttling, degradation modes).
- [ ] Data-loss controls (overflow policies, dead-letter flow, auditability).
- [ ] Clock-skew handling across distributed telemetry producers.
- [ ] Configuration error recovery strategy (fail-fast + safe defaults + audit trail).

## Observability (of observability)

### Metrics

### Implemented now

- Service-local counters exist (System API):
  - `eigen_api_requests_total`
  - `eigen_api_request_duration_seconds`
  - `eigen_api_authz_denied_total`

### TODO

- [ ] Observability-subsystem self-metrics family (`observability_*`) as originally planned.
- [ ] Explicit backend error/drop/latency metrics for observability pipelines.
- [ ] Capacity and saturation metrics for observability internals.

### Logs

### Implemented now

- Structured JSON logs with request correlation fields in System API.

### TODO

- [ ] Cross-service unified JSON log schema enforcement (including full RFC 0008 field set).
- [ ] Audit logging for observability config changes/exports.
- [ ] Slow-path/bottleneck standardized log events across components.

### Traces

### Implemented now

- Trace context propagation is required and contract-tested in MVP runtime flow.

### TODO

- [ ] Full self-instrumentation of observability pipelines.
- [ ] Persistent trace export pipeline with backend management.
- [ ] First-class trace query UX/API.

### Health checks

### Implemented now

- No dedicated health hierarchy for a standalone observability core service.

### TODO

- [ ] Component-level health endpoints for observability subsystems.
- [ ] Dependency health checks (Prometheus/Kafka/Jaeger connectivity).
- [ ] Resource-based alarms and autoscaling hooks.

### Dashboards & alerts

### Implemented now

- Prometheus alert packs/runbooks/dashboards exist for multiple domains (orchestrator, benchmark, intelligent runtime, cluster runtime, plugin runtime) at repository level.

### TODO

- [ ] Preconfigured dedicated "Observability Core" dashboard.
- [ ] Alert rules specifically for centralized observability-pipeline failures.
- [ ] Capacity forecasting for observability infrastructure as a unified subsystem.

## RFC / ADR alignment check

### Reviewed

- RFC 0008 (Observability MVP)
- RFC 0018 (MVP-3 Runtime Observability and Release Gates)
- ADR 0007 (MVP-3 release readiness and observability gates)

### Alignment summary

- Current implementation is aligned with **minimum MVP-3 runtime observability gates** (trace propagation + required checks in CI/process).
- The original broad "Observability Core" scope from earlier architecture description remains **partially implemented** and is now explicitly captured as TODOs above to avoid scope loss.
