# How to Run Observability

## When to Use

Use this scenario when you need to locally verify MVP observability:
- Export of `/metrics` endpoints for services;
- JSON logs with `trace_id` and `job_id`;
- Propagation of `traceparent` through the chain System API → Kernel → Compiler → DriverManager.

## Prerequisites

- Python 3.12+ for `system-api`, `eigen-compiler`, `driver-manager` services.
- Rust toolchain (for `eigen-kernel` smoke test).
- Available ports:
  - System API metrics: `9090`
  - Driver Manager metrics: `9092`
  - Compiler metrics: `9093`

## Instructions

1. Start the services with observability ports:

```bash
SYSTEM_API_METRICS_PORT=9090 system-api
DRIVER_MANAGER_METRICS_PORT=9092 driver-manager
EIGEN_COMPILER_METRICS_PORT=9093 python -m eigen_compiler.main
```

2. Check the metrics:

```bash
curl -s http://127.0.0.1:9090/metrics
curl -s http://127.0.0.1:9092/metrics
curl -s http://127.0.0.1:9093/metrics
```

3. For trace propagation, run the kernel integration test:

```bash
cd src/rust
cargo test -p eigen-kernel integration_propagates_traceparent_to_compiler_and_driver
```

## Verification

- Each `/metrics` response contains at least one `*_requests_total`.
- Service logs are written in JSON and contain `trace_id`; for job RPC also `job_id`.
- The test `integration_propagates_traceparent_to_compiler_and_driver` passes.
