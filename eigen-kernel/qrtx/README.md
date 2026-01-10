# QRTX - Quantum Real-Time Executive

**QRTX** is a high-performance scheduler kernel and task dispatcher for Eigen OS, responsible for orchestrating hybrid quantum-classical workflows.

## 🎯 Overview

QRTX transforms declarative descriptions of hybrid quantum-classical computations into efficient execution plans, considering the unique constraints of quantum systems:

- **DAG-oriented approach** — all tasks are represented as directed acyclic graphs

- **Noise-adaptive scheduling** — dynamic replanning based on real-time device state

- **Hybrid-first design** — unified representation of quantum and classical computation stages

- **Prioritization and fair distribution** — multi-level priority system with fair-share scheduling

## 🏗️ Architecture

### Core Components
```text
qrtx-core/
├── src/
│   ├── dag/              # DAG representation and manipulation
│   ├── scheduler/        # Scheduling algorithms
│   ├── state_machine/    # Task state management
│   ├── queue/            # Queue system
│   ├── resource/         # Resource management
│   ├── execution/        # Task execution
│   ├── api/             # Internal API
│   └── monitoring/       # Monitoring and telemetry
```

### Architectural Diagram
```text
┌─────────────────────────────────────────┐
│          System API Server              │
│        (gRPC/REST Interface)            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│             QRTX Kernel                 │
│  ┌───────────────────────────────────┐  │
│  │           DAG Engine              │  │
│  │  • Graph task model               │  │
│  │  • Dependency validation          │  │
│  │  • Dynamic reconfiguration        │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │      State Machine Manager        │  │
│  │  • 12+ task states                │  │
│  │  • Deterministic transitions      │  │
│  │  • Checkpointing and recovery     │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │        Quantum Scheduler          │  │
│  │  • Noise-aware scheduling         │  │
│  │  • Topology-aware distribution    │  │
│  │  • Predictive scheduling (ML)     │  │
│  └───────────────────────────────────┘  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Quantum Data Fabric (QFS)         │
│    • CircuitFS — circuits & artifacts   │
│    • StateStore — quantum states        │
│    • LiveQubitManager — live qubits     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Driver Manager                  │
│    (QDriver API Implementation)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Quantum Hardware                  │
│    (Simulators & Physical QPUs)         │
└─────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Rust 1.92+ (stable)

- Protobuf compiler (protoc)

- Docker (optional, for containerized deployment)

### Installation
```bash
# Clone the Eigen OS repository
git clone https://github.com/eigen-os/eigen-os.git
cd eigen-os/src/kernel/qrtx

# Build QRTX
cargo build --release

# Run tests
cargo test --all-features

# Build with Docker
docker build -t eigen-qrtx .
```

### Basic Configuration

Create `config/qrtx.yaml`:
```yaml
qrtx:
  scheduler:
    algorithm: "noise_aware"  # noise_aware, topology_aware, predictive
    time_slice: "10ms"
    max_queue_size: 10000
  
  queues:
    priority_levels: 10
    aging_enabled: true
    fair_share_enabled: true
  
  execution:
    max_concurrent_tasks: 100
    checkpoint_interval: "5m"
    retry_policy:
      max_retries: 3
      backoff_strategy: "exponential"
  
  monitoring:
    metrics_collection_interval: "5s"
    dashboard_refresh_rate: "1s"
    alert_thresholds:
      queue_length: 1000
      scheduling_latency: "100ms"
      error_rate: 0.01
```

### Running QRTX
```bash
# Start QRTX with default configuration
./target/release/qrtx --config config/qrtx.yaml

# Start with Docker
docker run -p 50051:50051 -v ./config:/config eigen-qrtx
```

### Submitting Your First Task
```rust
use qrtx::api::client::QRTXClient;
use qrtx::proto::qrtx::{TaskRequest, QuantumTaskSpec};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Connect to QRTX
    let mut client = QRTXClient::connect("http://localhost:50051").await?;
    
    // Create a simple quantum task
    let task = TaskRequest {
        job_id: "test_job_001".to_string(),
        spec: Some(QuantumTaskSpec {
            qubits: 2,
            circuit: vec!["H 0".to_string(), "CNOT 0 1".to_string()],
            shots: 1024,
            device_constraints: None,
            priority: 1,
            ..Default::default()
        }),
        ..Default::default()
    };
    
    // Submit the task
    let response = client.submit_task(task).await?;
    println!("Task submitted: {:?}", response.task_id);
    
    // Check status
    let status = client.get_task_status(&response.task_id).await?;
    println!("Task status: {:?}", status.state);
    
    Ok(())
}
```

## 🔧 Key Features

### 1. DAG-based Task Representation
```rust
// Example of creating a hybrid workflow DAG
let mut dag = QuantumDAG::new();

// Add quantum task
dag.add_node(DAGNode::QuantumTask {
    id: NodeId::new(),
    circuit_spec: bell_circuit(),
    shots: 4096,
    device_constraints: DeviceConstraints::default(),
    noise_tolerance: 0.95,
    estimated_duration: Duration::from_secs(5),
    checkpointable: true,
});

// Add classical processing task
dag.add_node(DAGNode::ClassicalTask {
    id: NodeId::new(),
    program_spec: python_script("process_results.py"),
    runtime: RuntimeType::Python,
    dependencies: vec![DataDependency::from_task("bell_task")],
    estimated_duration: Duration::from_secs(2),
});

// Add control flow
dag.add_edge(DAGEdge {
    source: "bell_task".into(),
    target: "process_task".into(),
    edge_type: EdgeType::Data,
    data_spec: Some(DataSpec::Results),
    latency_constraint: Some(Duration::from_secs(10)),
});
```

### 2. Noise-Aware Scheduling
```rust
// Configure noise-adaptive scheduler
let scheduler = NoiseAwareScheduler::new()
    .with_noise_model(ibm_guadalupe_noise_model())
    .with_prediction_horizon(Duration::from_minutes(30))
    .with_ml_predictor(degradation_predictor_model())
    .build();

// Schedule task with noise constraints
let schedule = scheduler.compute_noise_aware_schedule(
    &task,
    &available_devices,
    NoiseConstraints {
        max_error_rate: 0.01,
        min_fidelity: 0.95,
        coherence_time_required: Duration::from_micros(100),
    },
).await?;
```

### 3. Multi-level Queue System
```rust
// Configure priority queues
let queue = QuantumPriorityQueue::new()
    .with_priority_levels(10)
    .with_aging(true)
    .with_fair_share(true)
    .with_deadline_awareness(true)
    .build();

// Enqueue tasks with dynamic priority
let token = queue.enqueue(QueuedTask {
    id: task_id,
    priority: Priority::calculate_dynamic(
        base_priority,
        urgency,
        waiting_time,
        dependencies,
    ),
    deadline: Some(deadline),
    estimated_duration,
}).await;
```

### 4. Checkpointing and Recovery
```rust
// Configure checkpoint manager
let checkpoint_manager = CheckpointManager::new()
    .with_policy(CheckpointPolicy::Adaptive {
        interval: Duration::from_minutes(5),
        min_fidelity_drop: 0.05,
        max_checkpoint_size: 1024 * 1024 * 100, // 100MB
    })
    .with_storage(qfs_state_store())
    .build();

// Create checkpoint
let checkpoint = checkpoint_manager
    .checkpoint_task(&task, CheckpointStrategy::Incremental)
    .await?;

// Restore from checkpoint
let restored_task = checkpoint_manager
    .restore_task(&checkpoint.id)
    .await?;
```

## 📊 Monitoring and Metrics

### Real-time Dashboard
```bash
# Start QRTX dashboard
qrtx-dashboard --port 8080

# Access at http://localhost:8080
```

### Key Metrics
```rust
struct QRTXMetrics {
    // Scheduling metrics
    scheduling_latency: Histogram<f64>,     // p95 < 100ms
    scheduling_decisions: Counter,           // decisions/sec
    queue_length: Gauge<u64>,                // tasks in queue
    
    // Execution metrics
    task_duration: Histogram<f64>,           // task execution time
    quantum_execution_time: Histogram<f64>,  // quantum stage time
    classical_execution_time: Histogram<f64>, // classical stage time
    
    // Resource metrics
    qubit_utilization: Gauge<f64>,           // % qubit usage
    device_utilization: HashMap<DeviceId, Gauge<f64>>,
    allocation_efficiency: Gauge<f64>,       // % efficient allocation
    
    // Quality metrics
    task_success_rate: Gauge<f64>,           // % successful tasks
    quantum_fidelity: Histogram<f64>,        // fidelity distribution
    error_rates: HashMap<ErrorType, Counter>,
}
```

### Prometheus Integration
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'qrtx'
    static_configs:
      - targets: ['localhost:9091']
    metrics_path: '/metrics'
```

## 🔗 Integration

### With Eigen Compiler
```rust
// QRTX receives compiled circuits from Eigen Compiler
let compiled_circuit = eigen_compiler
    .compile(eigen_lang_program, CompilationTarget::SpecificDevice(device_id))
    .await?;

// Schedule and execute
let result = qrtx.execute_compiled_circuit(compiled_circuit).await?;
```

### With Quantum Data Fabric (QFS)
```rust
// Checkpoint quantum state through QFS
let checkpoint = qfs.state_store()
    .capture_state(
        device_id,
        qubits,
        TomographyConfig::adaptive(target_fidelity: 0.99),
    )
    .await?;

// Store circuit metadata
qfs.circuit_fs()
    .store_circuit(circuit, metadata, StorageClass::Hot)
    .await?;
```

### With Resource Manager
```rust
// Request quantum resources
let allocation = resource_manager
    .allocate_qubits(
        task.qubit_requirements(),
        topology_constraints,
        noise_constraints,
    )
    .await?;

// Execute on allocated qubits
let result = qrtx.execute_on_allocation(task, allocation).await?;
```

## ⚙️ Configuration

### Environment Variables
```bash
# Core settings
export QRTX_LOG_LEVEL=info
export QRTX_MAX_CONCURRENT_TASKS=100
export QRTX_QUEUE_CAPACITY=10000

# Scheduler settings
export QRTX_SCHEDULER_ALGORITHM=noise_aware
export QRTX_ENABLE_ML_PREDICTION=true
export QRTX_PREDICTION_HORIZON_MINUTES=30

# Monitoring
export QRTX_METRICS_PORT=9091
export QRTX_DASHBOARD_PORT=8080
export QRTX_TRACING_ENABLED=true
```

### Advanced Configuration
```yaml
qrtx:
  optimization:
    cache_size: 1000
    prefetch_enabled: true
    compression_level: 2
    
  security:
    isolation_level: "spatial_partition"
    enable_quantum_crypto: true
    audit_log_enabled: true
    
  scaling:
    horizontal_scaling: true
    max_instances: 3
    auto_scaling_threshold: 0.8
    
  experimental:
    enable_ml_scheduling: true
    quantum_network_routing: false
    distributed_checkpointing: true
```

## 🧪 Testing

### Unit Tests
```bash
# Run all unit tests
cargo test --lib

# Run specific module tests
cargo test --test dag_tests
cargo test --test scheduler_tests
```

### Integration Tests
```bash
# Run integration tests with Docker
./scripts/run-integration-tests.sh

# Test with different backends
cargo test --features "integration,redis_backend"
cargo test --features "integration,postgres_backend"
```

### Benchmarks
```bash
# Run performance benchmarks
cargo bench --bench scheduling_benchmarks

# Run stress tests
cargo test --test stress_tests -- --nocapture
```

## 📈 Performance Targets

### Acceptance Criteria

| **Metric** | **Target** | **Status** |
|-------------------|-------------------|-------------------|
| Scheduling latency (p95) | < 100ms | ✅ |
| Task queue capacity | 10,000+ tasks | ✅ |
| Concurrent task execution* | 100+ tasks | ✅ |
| Quantum state checkpoint time | < 500ms | 🟡 |
| Error recovery success rate | > 99% | 🟡 |
| Cross-device migration time | < 1s | 🔴 |

### Scaling Characteristics
```rust
// QRTX scales with:
- Number of quantum devices: O(n log n)
- Queue size: O(log n) for priority operations
- DAG complexity: O(v + e) for graph operations
- Concurrent tasks: Linear scaling up to hardware limits
```

## 🔮 Roadmap

### Phase 1: Core Scheduler (Current)

- ✅ Basic DAG engine

- ✅ FIFO scheduling

- ✅ Simple task states

- ✅ Integration with simulators

### Phase 2: Advanced Scheduling

- 🚧 Noise-aware algorithms

- 🚧 Topology-aware allocation

- 🚧 Predictive scheduling (ML)

- 🚧 Checkpoint/recovery system

### Phase 3: Intelligent Optimization

- 🔜 ML-based performance prediction

- 🔜 Automated DAG optimization

- 🔜 Integration with real quantum hardware

- 🔜 Quantum network routing

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

1. Fork the repository

2. Create a feature branch

3. Make your changes

4. Add tests

5. Submit a pull request

### Development Setup
```bash
# Clone and setup
git clone https://github.com/eigen-os/eigen-os/src/kernel/qrtx.git
cd qrtx
rustup override set stable
cargo install cargo-make

# Install development tools
cargo install --locked cargo-nextest
cargo install cargo-llvm-cov

# Run development environment
cargo make dev
```

### Code Quality
```bash
# Run linter
cargo clippy --all-features -- -D warnings

# Format code
cargo fmt --all

# Security audit
cargo audit

# Coverage report
cargo llvm-cov --html
```

## 📚 Documentation

- [API Documentation](https://docs.eigen-os.org/qrtx/api)

- [Architecture Guide](https://docs.eigen-os.org/qrtx/architecture)

- [Performance Tuning](https://docs.eigen-os.org/qrtx/performance)

- [Troubleshooting Guide](https://docs.eigen-os.org/qrtx/troubleshooting)

## 🐛 Issue Reporting

Found a bug? Please [open an issue](https://github.com/Eigen-OS/eigen-os/issues) with:

1. QRTX version

2. Steps to reproduce

3. Expected vs actual behavior

4. Logs and error messages

## 📄 License

QRTX is part of Eigen OS and is licensed under the [Apache License 2.0](LICENSE).

## 🙏 Acknowledgments

- Quantum computing frameworks: Qiskit, Cirq, PennyLane

- Rust ecosystem: Tokio, tonic, serde, prometheus

- Research partners and early adopters


**QRTX** — The heart of Eigen OS, transforming quantum potential into computational reality.
