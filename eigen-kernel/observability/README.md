## Observability Core

**Observability Core** is the centralized monitoring and observability system for Eigen OS, providing comprehensive visibility into the state of hybrid quantum-classical computations. Built in Rust, it offers real-time metrics collection, distributed tracing, and event-driven architecture specifically designed for quantum computing environments.

## 🎯 Overview

Observability Core enables deep observability across the entire Eigen OS stack, from quantum hardware metrics to classical system performance. It addresses the unique challenges of monitoring hybrid quantum-classical workflows where traditional observability tools fall short.

### Key Observability Requirements

- **Quantum hardware metrics**: Real-time monitoring of qubit coherence times (T1, T2), fidelity, gate error rates

- **Hybrid workflow tracing**: End-to-end tracing across quantum and classical execution stages

- **Event-driven monitoring**: Real-time system event processing for proactive management

- **Multi-tenant metric**s: Isolation and aggregation of metrics across different users and projects

- **Performance optimization**: Low-overhead monitoring with minimal impact on quantum computations

## 🏗️ Architecture

### Component Architecture
```text
observability/
├── Cargo.toml
├── README.md
├── src/
│   ├── lib.rs
│   ├── core/              # Core configuration and error handling
│   ├── metrics/           # Metrics collection and export
│   │   ├── collector.rs
│   │   ├── registry.rs
│   │   ├── exporters/     # Prometheus, stdout, custom sinks
│   │   └── types/         # Quantum, system, and business metrics
│   ├── tracing/           # Distributed tracing
│   │   ├── tracer.rs
│   │   ├── span.rs
│   │   ├── exporters/     # OpenTelemetry, Jaeger, file
│   │   └── instrumentation/ # gRPC, HTTP, quantum operations
│   ├── events/            # Event-driven architecture
│   │   ├── bus.rs
│   │   ├── publisher.rs
│   │   ├── subscriber.rs
│   │   ├── types/         # Hardware, job, system, security events
│   │   └── backends/      # Kafka, Redis, in-memory, NATS
│   └── api/               # gRPC, REST, WebSocket APIs
├── proto/                 # Protobuf definitions
├── config/               # Configuration files
├── examples/             # Usage examples
└── tests/               # Unit, integration, benchmark tests
```

### Integration with Eigen OS Ecosystem
```text
┌─────────────────────────────────────────────────────┐
│               System API Server                     │
│               (gRPC/REST Interface)                 │
└─────────────────┬───────────────────────────────────┘
                  │ Observability Data
                  ▼
┌─────────────────────────────────────────────────────┐
│              Observability Core                     │
│    • Metrics Collection & Export                    │
│    • Distributed Tracing                            │
│    • Event Processing                               │
│    • Real-time Monitoring                           │
└───────────────┬────────────┬────────────────────────┘
                │            │
    ┌───────────▼──┐  ┌──────▼───────────┐
    │   QRTX       │  │   Resource       │
    │   Kernel     │  │   Manager        │
    │ (Scheduler)  │  │                  │
    └──────────────┘  └──────────────────┘
                │            │
                └──────┬─────┘
                       │
                ┌──────▼───────────┐
                │  Quantum         │
                │  Hardware        │
                │  & Drivers       │
                └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Rust 1.92+** (stable)

- **Prometheus** (optional, for metrics storage)

- **Jaeger** (optional, for distributed tracing)

- **Apache Kafka** (optional, for event streaming)

- **Docker & Docker Compose** (for containerized deployment)

### Installation
```bash
# Clone the Eigen OS repository
git clone https://github.com/eigen-os/eigen-os.git
cd eigen-os/src/observability-core

# Build Observability Core
cargo build --release --features "prometheus,opentelemetry,kafka"

# Run tests
cargo test --all-features

# Build with Docker (includes all features)
docker build -t eigen-observability-core .

# Start with Docker Compose (full observability stack)
docker-compose up -d
```

### Basic Configuration

Create `config/default.yaml`:
```yaml
observability:
  metrics:
    enabled: true
    port: 9090
    path: "/metrics"
    scrape_interval: "15s"
    retention_period: "7d"
    
    quantum_metrics:
      collection_interval: "5s"
      enabled_metrics:
        - "t1_time"
        - "t2_time"
        - "gate_fidelity"
        - "readout_fidelity"
    
    system_metrics:
      collection_interval: "10s"
      enabled_metrics:
        - "queue_length"
        - "job_completion_rate"
        - "compilation_latency"
        - "execution_latency"
  
  tracing:
    enabled: true
    exporter: "jaeger"  # or "otlp", "stdout"
    jaeger:
      endpoint: "http://localhost:14268/api/traces"
      service_name: "eigen-os"
      batch_size: 100
      sampling_rate: 0.1  # 10% of traces
  
  events:
    enabled: true
    bus_type: "kafka"  # or "redis", "in_memory", "nats"
    kafka:
      bootstrap_servers: "localhost:9092"
      topic_prefix: "eigen_events_"
      partitions: 3
      replication_factor: 1
      compression: "snappy"
  
  api:
    grpc:
      enabled: true
      port: 50051
      max_concurrent_streams: 100
    rest:
      enabled: true
      port: 8080
      health_check_path: "/health"
      metrics_path: "/internal/metrics"
    websocket:
      enabled: false
      port: 8081
      max_connections: 1000
```

### Running Observability Core
```bash
# Start with default configuration
./target/release/observability-core --config config/default.yaml

# Start with specific features
./target/release/observability-core \
  --features "prometheus,jaeger,kafka" \
  --config config/production.yaml

# Start with Docker
docker run -p 9090:9090 -p 50051:50051 -p 8080:8080 \
  -v ./config:/config \
  -e KAFKA_BROKERS=kafka:9092 \
  eigen-observability-core

# Start with systemd
sudo systemctl start eigen-observability-core
```

### Basic API Usage
```rust
use observability_core::{ObservabilityBuilder, MetricCollector, Tracer};
use std::time::{Duration, Instant};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize observability
    let observability = ObservabilityBuilder::new()
        .with_prometheus_endpoint("0.0.0.0:9090")
        .with_jaeger_endpoint("http://jaeger:14268/api/traces")
        .with_kafka_brokers(vec!["kafka:9092"])
        .build()
        .await?;

    // Register custom metrics
    let jobs_counter = observability.metrics
        .register_counter("jobs_processed_total", "Total number of processed jobs");
    
    let execution_time = observability.metrics
        .register_histogram("job_execution_seconds", "Job execution time");

    // Start tracing span
    let span = observability.tracer.start_span("quantum_workflow");
    
    // Execute quantum computation
    let start = Instant::now();
    // ... quantum circuit execution ...
    let duration = start.elapsed();

    // Record metrics
    jobs_counter.increment(1);
    execution_time.record(duration.as_secs_f64());

    // Publish event
    observability.events.publish(
        "job_completed",
        JobEvent::Completed {
            job_id: "job_123".to_string(),
            duration: duration.as_secs_f64(),
            success: true,
        }
    ).await?;

    Ok(())
}
```

## 🔧 Key Features

### 1. Quantum Hardware Metrics
```rust
use observability_core::metrics::{MetricCollector, QuantumMetrics};

// Define quantum metrics structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuantumMetrics {
    pub qubit_id: String,
    pub t1_time: f64,               // Relaxation time (ns)
    pub t2_time: f64,               // Dephasing time (ns)
    pub readout_fidelity: f64,      // Readout accuracy
    pub gate_error_rates: HashMap<String, f64>,  // Gate-specific error rates
    pub thermal_population: f64,    // Thermal population
}

// Record quantum metrics
let quantum_metrics = QuantumMetrics {
    qubit_id: "qubit_0".to_string(),
    t1_time: 75.3,
    t2_time: 50.2,
    readout_fidelity: 0.992,
    gate_error_rates: [
        ("h".to_string(), 0.0012),
        ("cx".to_string(), 0.015),
    ].iter().cloned().collect(),
    thermal_population: 0.02,
};

observability.metrics.record_quantum_metrics(
    "ibm_guadalupe",
    quantum_metrics
).await?;
```

### 2. Distributed Tracing for Hybrid Workflows
```rust
use observability_core::tracing::{Tracer, HybridTraceContext};

// Context for hybrid quantum-classical traces
#[derive(Debug, Clone)]
pub struct HybridTraceContext {
    pub trace_id: String,
    pub span_id: String,
    pub trace_flags: u8,
    pub quantum_stage: QuantumExecutionStage,
    pub classical_stage: ClassicalExecutionStage,
    pub correlation_id: String,  // For linking quantum and classical stages
}

// Quantum execution stages
pub enum QuantumExecutionStage {
    Compilation,
    Optimization,
    QubitAllocation,
    CircuitExecution,
    Measurement,
    ErrorMitigation,
}

// Instrument gRPC calls
let grpc_instrumentation = GrpcInstrumentation::new(tracer.clone());
let interceptor = grpc_instrumentation.intercept_client();

// Create trace for hybrid workflow
let mut span = tracer.start_span("hybrid_vqe_workflow");
span.set_attribute("algorithm", "VQE");
span.set_attribute("qubits", 4);
span.set_attribute("iterations", 100);

// Add events to span
span.add_event("classical_optimization_started");
// ... classical computation ...
span.add_event("quantum_execution_started");
// ... quantum computation ...
span.add_event("results_processed");

span.end();
```

### 3. Event-Driven Monitoring
```rust
use observability_core::events::{EventBus, HardwareEvent, JobEvent};

// Initialize event bus with Kafka backend
let event_bus = EventBus::new()
    .with_backend(KafkaBackend::new("localhost:9092", "eigen_events"))
    .with_buffer_size(10000)
    .build()
    .await?;

// Define hardware events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HardwareEvent {
    QubitCalibrationStarted { device_id: String, timestamp: DateTime<Utc> },
    QubitFidelityChanged { qubit_id: String, old_fidelity: f64, new_fidelity: f64 },
    DeviceTemperatureAlert { device_id: String, temperature: f64, threshold: f64 },
    GateErrorRateUpdate { gate_type: String, error_rate: f64 },
}

// Define job events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum JobEvent {
    JobSubmitted { job_id: String, user_id: String, priority: u8 },
    JobCompilationStarted { job_id: String, compiler_version: String },
    JobExecutionCompleted { job_id: String, result_hash: String, execution_time: f64 },
    JobFailed { job_id: String, error: String, stage: String },
}

// Publish events
event_bus.publish(
    "hardware_events",
    HardwareEvent::QubitFidelityChanged {
        qubit_id: "qubit_5".to_string(),
        old_fidelity: 0.992,
        new_fidelity: 0.987,
    }
).await?;

// Subscribe to events
let mut event_stream = event_bus.subscribe("job_events").await?;
while let Some(event) = event_stream.next().await {
    match event {
        JobEvent::JobCompleted { job_id, duration, success } => {
            println!("Job {} completed in {}s, success: {}", job_id, duration, success);
            // Update dashboards, trigger alerts, etc.
        }
        JobEvent::JobFailed { job_id, error, stage } => {
            eprintln!("Job {} failed at stage {}: {}", job_id, stage, error);
            // Trigger incident response
        }
        _ => {}
    }
}
```

### 4. Integration with QRTX Scheduler
```rust
// In QRTX kernel integration
use observability_core::{MetricCollector, Tracer, EventBus};

pub struct QRTX {
    scheduler: Scheduler,
    observability: Arc<ObservabilityContext>,
}

impl QRTX {
    pub fn new(config: Config) -> Self {
        let observability = ObservabilityBuilder::new()
            .with_metrics_collector(PrometheusCollector::new())
            .with_tracer(JaegerTracer::new("qrtx"))
            .with_event_bus(KafkaEventBus::new())
            .build();

        Self {
            scheduler: Scheduler::new(),
            observability: Arc::new(observability),
        }
    }

    pub async fn submit_job(&self, job: JobSpec) -> Result<JobId> {
        // Start tracing
        let span = self.observability.tracer.start_span("job_submission");
        
        // Record metrics
        self.observability.metrics.increment_counter("jobs_submitted_total", 1);
        
        // Publish event
        self.observability.events.publish(
            "job_events",
            JobEvent::JobSubmitted {
                job_id: job.id.clone(),
                user_id: job.user_id,
                priority: job.priority,
            }
        ).await?;

        // Job processing logic...
        Ok(job.id)
    }
}
```

### 5. Integration with Quantum Drivers
```rust
// In quantum driver implementation
impl QDriver for SuperconductingDriver {
    async fn execute(&self, circuit: CompiledCircuit) -> Result<ExecutionResult> {
        let span = self.observability.tracer.start_span("quantum_execution");
        
        // Collect hardware metrics before execution
        let hardware_metrics = self.get_current_metrics();
        self.observability.metrics.record_quantum_metrics(
            self.device_id.clone(),
            hardware_metrics
        );

        // Execute circuit
        let result = self.inner_execute(circuit).await;

        // Publish completion event
        if let Ok(ref res) = result {
            self.observability.events.publish(
                "hardware_events",
                HardwareEvent::CircuitExecutionCompleted {
                    device_id: self.device_id.clone(),
                    circuit_hash: circuit.hash(),
                    execution_time: res.execution_time,
                    success_rate: res.success_rate,
                }
            ).await?;
        }

        result
    }
}
```

## 📊 API Endpoints

### REST API

| **Endpoint** | **Method** | **Description** |
|-------------------|-------------------|-------------------|
| `/health` | GET | Health check endpoint |
| `/metrics` | GET | Prometheus metrics |
| `/metrics/quantum/{device}` | GET | Quantum metrics for specific device |
| `/metrics/system` | GET | System metrics |
| `/traces/{trace_id}` | GET | Get specific trace |
| `/traces/search` | GET | Search traces |
| `/traces/export` | POST | Export traces |
| `/events/stream` | WS | WebSocket event stream |
| `/events/publish` | POST | Publish event |

### gRPC Service
```protobuf
syntax = "proto3";

package eigen.observability.v1;

service ObservabilityService {
  // Metrics
  rpc PushMetrics(stream MetricBatch) returns (PushResponse);
  rpc QueryMetrics(QueryRequest) returns (stream MetricData);
  
  // Tracing
  rpc ExportSpans(ExportSpansRequest) returns (ExportSpansResponse);
  rpc QueryTraces(QueryTracesRequest) returns (stream Trace);
  
  // Events
  rpc SubscribeToEvents(SubscriptionRequest) returns (stream Event);
  rpc PublishEvent(Event) returns (PublishResponse);
  
  // Health
  rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
}

message MetricBatch {
  repeated Metric metrics = 1;
  int64 timestamp = 2;
  map<string, string> labels = 3;
}

message QuantumMetric {
  string qubit_id = 1;
  double t1_time = 2;
  double t2_time = 3;
  double readout_fidelity = 4;
  map<string, double> gate_errors = 5;
}
```

## ⚙️ Performance and Optimization

### Performance Benchmarks
```rust
// tests/benchmarks/metrics_benchmark.rs
#[bench]
fn metrics_collection_benchmark(b: &mut Bencher) {
    let collector = PrometheusCollector::new();
    b.iter(|| {
        // Collect 1000 metrics
        for i in 0..1000 {
            collector.record_gauge(
                format!("test_metric_{}", i),
                42.0
            );
        }
        collector.collect();
    });
}

// Expected performance targets:
// - Metrics collection: < 1ms per 1000 metrics
// - Prometheus export: < 5ms
// - Event processing: < 100μs
// - Event throughput: > 10k events/second
```

### Optimization Strategies

1. **Metrics batching**: Aggregate metrics before sending

2. **Asynchronous processing**: Non-blocking I/O operations

3. **Binary serialization**: Use Protobuf/MessagePack for efficiency

4. **Data compression**: Snappy/Zstd compression for trace data

5. **Caching**: Cache frequent metric queries

### 🔒 Security

1. **Authentication & Authorization**: JWT/OAuth2 for API access

2. **Encryption**: TLS for gRPC and HTTP traffic

3. **Data isolation**: Separate metrics by tenants

4. **Rate limiting**: API rate limiting

5. **Audit logging**: Log all metric operations

## 📈 Roadmap

### Phase 1: Basic Metrics (MVP)

- Prometheus metrics exporter

- Basic system metrics (CPU, memory, queue)

- In-memory event bus

- REST API for health checks

### Phase 2: Production Readiness

- OpenTelemetry tracing

- Kafka event bus

- Quantum metrics (T1, T2, fidelity)

- WebSocket for real-time events

### Phase 3: Advanced Capabilities

- Predictive metrics (ML-based anomaly detection)

- Distributed tracing between quantum and classical components

- Auto-scaling based on metrics

- Integration with alerting systems (Alertmanager)

## 🧪 Testing and Validation

### Testing Suite
```bash
# Run all tests
cargo test --all-features

# Run integration tests
cargo test --test integration_tests

# Run benchmarks
cargo bench

# Run with specific backends
cargo test --features "prometheus,kafka"
```

### Performance Validation
```rust
#[test]
fn test_metrics_collection_performance() {
    let collector = PrometheusCollector::new();
    let start = Instant::now();
    
    // Collect 10,000 metrics
    for i in 0..10_000 {
        collector.record_gauge(format!("test_{}", i), i as f64);
    }
    
    let duration = start.elapsed();
    assert!(duration < Duration::from_millis(100),
            "Metrics collection too slow: {:?}", duration);
}

#[tokio::test]
async fn test_event_throughput() {
    let event_bus = InMemoryEventBus::new();
    let mut handles = vec![];
    
    // Test concurrent event publishing
    for i in 0..1000 {
        let bus = event_bus.clone();
        handles.push(tokio::spawn(async move {
            bus.publish("test_topic", TestEvent { id: i }).await
        }));
    }
    
    // Wait for all publishes
    for handle in handles {
        handle.await.unwrap().unwrap();
    }
}
```

## 📊 Monitoring Observability Core Itself
```yaml
# Internal metrics for the observability system
observability_core_internal_metrics:
  - "observability_events_processed_total"
  - "observability_events_dropped_total"
  - "observability_metrics_collection_duration_seconds"
  - "observability_tracing_spans_created_total"
  - "observability_event_bus_latency_seconds"
  - "observability_backend_errors_total"
  ```

  ## 🤝 Contributing

We welcome contributions to Observability Core! Please see our [Contributing Guide](CONTRIBUTING.md).

### Development Setup
```bash
# Clone and setup
git clone https://github.com/eigen-os/eigen-os/src/observability.git
cd observability-core
rustup override set stable

# Install development dependencies
cargo install cargo-make
cargo install cargo-watch

# Setup development environment
cargo make setup-dev

# Run development server
cargo make dev --features "prometheus,jaeger"
```

## 📚 Documentation

- [Architecture Guide](https://docs.eigen-os.org/observability/architecture)

- [API Documentation](https://docs.eigen-os.org/observability/api)

- [Metrics Reference](https://docs.eigen-os.org/observability/metrics)

- [Tracing Guide](https://docs.eigen-os.org/observability/tracing)

- [Events Reference](https://docs.eigen-os.org/observability/events)

## 📄 License

Observability Core is part of Eigen OS and is licensed under the [Apache License 2.0](LICENSE).

## 🙏 Acknowledgments

- Prometheus and OpenTelemetry communities

- Apache Kafka and NATS teams

- Rust observability ecosystem contributors

- Quantum hardware providers for telemetry access

**Observability Core** — Providing comprehensive visibility into hybrid quantum-classical systems, from qubit-level metrics to distributed workflow tracing, ensuring reliability and performance in the quantum computing frontier.