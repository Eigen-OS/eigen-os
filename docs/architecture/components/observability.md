# Observability

- Phase: MVP

## Responsibility

Observability Core provides centralized monitoring, tracing, and event processing for Eigen OS. It enables visibility into system health, performance, and quantum workflow execution across all components. Key responsibilities include:

- **Metrics Collection & Export**: Gather system, quantum hardware, and business metrics, exporting them to Prometheus.

- **Distributed Tracing**: Implement end-to-end trace propagation across hybrid quantum-classical workflows.

- **Event-Driven Architecture**: Publish and subscribe to system events (hardware changes, job lifecycle, security alerts).

- **Health Monitoring**: Provide health check endpoints for system components.

- **Real-time Monitoring**: Support WebSocket streams for live event monitoring.

## Interfaces

### 1. gRPC API:

- Defined in `proto/observability/service.proto`

- `ObservabilityService` with methods:

    - `PushMetrics()`: Stream metrics to central collector

    - `QueryMetrics()`: Query historical metrics

    - `ExportSpans()`: Send trace spans for storage

    - `SubscribeToEvents()`: Stream real-time events

    - `PublishEvent()`: Publish new events

    - `HealthCheck()`: System health status

### 2. REST API Endpoints:

- `GET /health`: Service health status

- `GET /metrics`: Prometheus-formatted metrics

- `GET /metrics/quantum/{device}`: Quantum-specific metrics

- `GET /traces/{trace_id}`: Retrieve specific trace

- `WS /events/stream`: WebSocket for real-time events

### 3. Event Bus Interface:

- Publisher/Subscriber pattern for system events

- Multiple backend support: Kafka, Redis, in-memory, NATS

- Event types: HardwareEvents, JobEvents, SystemEvents, SecurityEvents

### 4. Integration Points:

- **Kernel (QRTX) Integration**: Automatic instrumentation of job lifecycle

- **Driver Integration**: Quantum hardware metrics collection

- **System Components**: Standardized metrics and trace collection

## Inputs / Outputs

### Inputs:

1. **Metrics Data:**

    - Quantum hardware metrics (T1, T2, gate fidelity, readout fidelity)

    - System metrics (queue size, active jobs, compilation/execution time)

    - Resource metrics (CPU, memory, network usage)

2. **Trace Data:**

    - Span data from distributed workflow execution

    - Quantum operation instrumentation

    - gRPC/HTTP request tracing

3. **Events:**

    - Hardware calibration events

    - Job lifecycle events (submitted, started, completed, failed)

    - System alerts and security events

4. **Configuration:**

    - YAML configuration files for metrics collection intervals, exporters, event bus setting

### Outputs:

1. **Exported Metrics:**

    - Prometheus metrics endpoint (`/metrics`)

    - Time-series database integration

    - Real-time dashboard data

2. **Trace Storage:**

    - Jaeger/OpenTelemetry compatible trace data

    - Queryable trace database

3. **Event Streams:**

    - Kafka topics for event processing

    - WebSocket streams for real-time monitoring

    - Alert notifications

4. **API Responses:**

    - Health status

    - Metric queries

    - Trace retrieval

## Storage / State

### Internal State:

1. **Metrics Registry**: In-memory storage of active metrics with labels and values

2. **Trace Buffer**: Temporary storage of trace spans before batch export

3. **Event Buffer**: In-memory queue for event batching and backpressure management

4. **Subscription State**: Active WebSocket connections and event subscriptions

### External Storage:

1. **Time-Series Database**: Prometheus (or compatible) for metric storage

2. **Trace Storage**: Jaeger backend or OTLP-compatible storage

3. **Event Logging**: Kafka topics with retention policies

4. **Configuration Storage**: File-based YAML configurations

### Caching:

- Metric aggregation caching for frequent queries

- Trace sampling configuration to reduce storage volume

- Event deduplication and batching

## Failure Modes

**1. Backend Service Unavailability:**

- **Prometheus Down**: Metrics buffered in memory with configurable retention, logged warnings

- **Jaeger/Trace Collector Down**: Trace spans buffered locally, configurable drop policies after buffer limits

- **Kafka/Event Bus Down**: Events queued in memory, with circuit breaker pattern to prevent memory exhaustion

**2. Resource Exhaustion:**

- **Memory Pressure**: Adaptive sampling reduces trace/event volume, prioritized metric retention

- **CPU Saturation**: Throttles metric collection frequency, degrades to essential metrics only

- **Network Issues**: Implements retry with exponential backoff for external exports

**3. Data Loss Scenarios:**

- **Buffer Overflow**: Configurable policies (drop oldest, sample, or block)

- **Export Failures**: Dead letter queues for failed exports with manual recovery options

- **Clock Skew**: Handles timestamp inconsistencies across distributed components

4. **Configuration Errors:**

    **Invalid Config**: Fail-fast with clear error messages, fallback to safe defaults

    **Permission Issues**: Graceful degradation of affected features with audit logging

**Recovery Strategies:**

- Automatic reconnection to backend services

- Configurable retry policies with jitter

- Health checks and automatic failover for critical paths

- Audit trails for all data loss events

## Observability (of Observability Core)

### Metrics:

- Internal performance metrics: `observability_events_processed_total`, `observability_metrics_collection_duration_seconds`

- Error rates: `observability_backend_errors_total`, ``observability_events_dropped_total``

- Resource usage: `observability_memory_usage_bytes`, `observability_cpu_usage_percent`

- Throughput: `observability_event_bus_latency_seconds`, `observability_tracing_spans_created_total`

### Logs:

- Structured JSON logging with correlation IDs

- Audit logs for all configuration changes and data export operations

- Error logs with full context for debugging failures

- Performance logs for slow operations and bottlenecks

### Traces:

- Self-instrumentation of Observability Core operations

- Trace propagation through event processing pipelines

- Performance analysis of metric collection and export paths

### Health Checks:

- Component-level health endpoints (`/health` for each subsystem)

- Dependency health monitoring (Prometheus, Kafka, Jaeger connectivity)

- Resource utilization alarms and automatic scaling triggers

### Dashboard & Alerts:

- Pre-configured Grafana dashboards for Observability Core

- Alert rules for critical failures and performance degradation

- Capacity planning metrics and predictive scaling