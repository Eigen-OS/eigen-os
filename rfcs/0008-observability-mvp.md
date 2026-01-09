# RFC 0008: Observability MVP: metrics, logs, traces, events

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0002,0004,0007,0006

## Summary

Defines the minimum observability surface to debug end-to-end job execution and performance.

## Motivation

MVP without observability is not debuggable, especially with multi-service execution and backends.

## Goals

- Standardize log fields (`trace_id`, `job_id`, `service`, `device_id`).
- Provide Prometheus metrics for API + kernel + driver-manager.
- Propagate trace context end-to-end.

## Non-Goals

- Full SLOs and alerting policies.
- Long-term retention and multi-tenant dashboards.

## Guide-level explanation

MVP uses OpenTelemetry-compatible trace context propagation. The canonical header is W3C TraceContext `traceparent`,
propagated via gRPC metadata between System API → Kernel → Compiler/Driver Manager.


For MVP we run Prometheus + Grafana.
system-api exports `/metrics`.
kernel exports stage metrics.
driver-manager exports per-driver metrics.
Tracing uses OpenTelemetry headers; exporter optional.

## Reference-level design

### Interfaces / APIs

Metrics endpoints:
- system-api: `:9090/metrics`
- kernel: `:9091/metrics` (example)
- driver-manager: `:9092/metrics` (example)
Trace propagation via gRPC metadata headers (`traceparent`).

### Data model

Log fields (JSON):
- timestamp
- level
- service
- trace_id
- span_id
- job_id
- device_id (optional)
- stage (optional)
- message
- error (optional)

### Error model

Errors must be logged once at source, with `error_kind` and `root_cause` where possible.

### Security & privacy

Never log secrets (tokens, credentials). Redact metadata keys by allowlist.

### Observability

Required metrics (MVP):
- `eigen_api_requests_total{method,endpoint,status}`
- `eigen_api_request_duration_seconds{method,endpoint}`
- `eigen_kernel_job_state_transitions_total{from,to}`
- `eigen_kernel_stage_duration_seconds{stage}`
- `eigen_driver_requests_total{driver,op,success}`
- `eigen_driver_request_duration_seconds{driver,op}`

### Performance notes

Metrics collection must be non-blocking; avoid high-cardinality labels (no job_id as label).

## Testing plan

Smoke test starts stack and checks metrics endpoints; golden log schema tests (optional).

## Rollout / Migration

Enable metrics/logging by default. Tracing can be off by default but must be easy to turn on.

## Alternatives considered

- Logs only (rejected: metrics are required for performance debugging).

## Open questions

- Which tracing backend by default (Jaeger/Tempo)?
- Do we need an event bus for job updates in MVP?
