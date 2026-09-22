# Resource Manager - Quantum Resource Management System

**Resource Manager** is the central quantum resource orchestration component of Eigen OS, providing intelligent allocation, isolation, and monitoring of quantum resources in real-time environments.

## 🎯 Overview

The Resource Manager functions as the **"Quantum Resource Broker"** for Eigen OS, transforming heterogeneous, unstable quantum hardware into predictable, manageable computational resources. It implements advanced allocation strategies that consider:

- **Topology-aware allocation** - mapping logical to physical qubits considering connectivity

- **Noise-adaptive placement** - allocating qubits based on real-time noise characteristics

- **Fair-share scheduling** - equitable resource distribution among users and projects

- **Cross-device optimization** - intelligent workload distribution across multiple QPUs

## 🏗️ Architecture

### Core Components
```text
resource-manager/
├── src/
│   ├── allocator/          # Qubit allocation algorithms
│   │   ├── topology_aware_allocator.rs
│   │   ├── noise_aware_allocator.rs
│   │   └── first_fit_allocator.rs
│   ├── scheduler/         # Resource scheduling
│   │   ├── temporal_scheduler.rs
│   │   ├── spatial_scheduler.rs
│   │   └── hybrid_scheduler.rs
│   ├── isolation/         # Resource isolation mechanisms
│   │   ├── spatial_isolation.rs
│   │   ├── temporal_isolation.rs
│   │   └── logical_isolation.rs
│   ├── monitor/          # Real-time monitoring
│   │   ├── resource_monitor.rs
│   │   ├── health_checker.rs
│   │   └── metrics_collector.rs
│   ├── policies/         # Resource management policies
│   │   ├── allocation_policy.rs
│   │   ├── balancing_policy.rs
│   │   └── isolation_policy.rs
│   └── api/             # Management API
│       ├── grpc_server.rs
│       ├── models.rs
│       └── errors.rs
```

### Architectural Diagram
```text
┌─────────────────────────────────────────────────────┐
│               System API Server                     │
│               (gRPC/REST Interface)                 │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│               QRTX Kernel                           │
│           (DAG Scheduler & Orchestrator)            │
└─────────────────┬───────────────────────────────────┘
                  │ Resource Requests
                  ▼
┌─────────────────────────────────────────────────────┐
│               RESOURCE MANAGER                      │
│  ┌────────────────────────────────────────────────┐ │
│  │           Device Registry & Discovery          │ │
│  │  • Real-time device availability               │ │
│  │  • Topology mapping                            │ │
│  │  • Noise characteristics                       │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │        Intelligent Allocation Engine           │ │
│  │  • Topology-aware placement                    │ │
│  │  • Noise-adaptive allocation                   │ │
│  │  • Load balancing across devices               │ │
│  │  • Fragmentation minimization                  │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │         Quantum Isolation Layer                │ │
│  │  • Spatial separation                          │ │
│  │  • Temporal multiplexing                       │ │
│  │  • Hardware-enforced isolation                 │ │
│  │  • Cross-talk mitigation                       │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │       Real-time Monitoring & Analytics         │ │
│  │  • Resource utilization tracking               │ │
│  │  • Predictive load forecasting                 │ │
│  │  • Hotspot detection                           │ │
│  │  • Automated rebalancing                       │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────┘
                  │ Allocated Resources
                  ▼
┌─────────────────────────────────────────────────────┐
│               Quantum Hardware                      │
│               (Simulators & Physical QPUs)          │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Rust 1.92+** (stable)

- **Protobuf compiler** (protoc)

- **Docker** (optional, for containerized deployment)

- **PostgreSQL 18+** (for persistent state storage)

### Installation
```bash
# Clone the Eigen OS repository
git clone https://github.com/eigen-os/eigen-os.git
cd eigen-os/src/kernel/resource-manager

# Build Resource Manager
cargo build --release

# Run tests
cargo test --all-features

# Build with Docker
docker build -t eigen-resource-manager .
```
### Configuration

Create `config/resource_manager.yaml`:
```yaml
resource_manager:
  # Allocation policies
  allocation:
    strategy: "topology_aware"
    fallback_strategy: "first_fit"
    enable_caching: true
    cache_size: 1000
    fragmentation_threshold: 0.3
  
  # Load balancing
  load_balancing:
    enabled: true
    interval: "30s"
    strategy: "least_loaded"
    threshold: 0.8
  
  # Isolation settings
  isolation:
    default_level: "medium"
    hardware_isolation: true
    enable_cross_task_protection: true
    spatial_separation: 1  # buffer qubits between tasks
  
  # Monitoring
  monitoring:
    collect_interval: "5s"
    retention_period: "7d"
    alert_thresholds:
      qubit_utilization: 0.9
      allocation_failure_rate: 0.05
      isolation_violations: 1
  
  # Optimization
  optimization:
    enable_preallocation: false
    preallocation_window: "5m"
    enable_ml_prediction: true
  
  # Database
  database:
    url: "postgresql://localhost:5432/resource_manager"
    pool_size: 10
    migrations_path: "./migrations"
```

### Running Resource Manager
```bash
# Start with default configuration
./target/release/resource-manager --config config/resource_manager.yaml

# Start with Docker
docker run -p 50052:50052 \
  -v ./config:/config \
  -v ./data:/data \
  -e DATABASE_URL=postgresql://host.docker.internal:5432/resource_manager \
  eigen-resource-manager

# Start with systemd
sudo systemctl start eigen-resource-manager
```

### Basic API Usage
```rust
use resource_manager::api::client::ResourceManagerClient;
use resource_manager::proto::resource_manager::{ResourceRequest, AllocationConstraints};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Connect to Resource Manager
    let mut client = ResourceManagerClient::connect("http://localhost:50052").await?;
    
    // Create resource request for a quantum task
    let request = ResourceRequest {
        job_id: "quantum_job_001".to_string(),
        min_qubits: 5,
        max_qubits: 5,
        topology: TopologyConstraint::Grid(2, 3),
        fidelity_requirement: 0.99,
        coherence_time_required: Duration::from_micros(100),
        estimated_duration: Duration::from_secs(60),
        priority: Priority::Normal,
        isolation_required: true,
        ..Default::default()
    };
    
    // Request resource allocation
    let allocation = client.allocate_resources(request).await?;
    println!("Allocated resources: {:?}", allocation);
    
    // Monitor resource usage
    let metrics = client.get_resource_metrics().await?;
    println!("Resource utilization: {:.2}%", metrics.qubit_utilization * 100.0);
    
    // Release resources when done
    client.release_resources(&allocation.job_id).await?;
    println!("Resources released");
    
    Ok(())
}
```

## 🔧 Key Features

### 1. Topology-Aware Allocation
```rust
// Request allocation with topology constraints
let allocation = resource_manager.allocate_resources(
    ResourceRequest {
        topology: TopologyConstraint::Linear,  // or Grid, Complete, Custom
        required_connectivity: connectivity_matrix(),
        min_qubits: 4,
        max_qubits: 4,
        ..Default::default()
    },
    AllocationConstraints {
        device_preference: Some("ibm_guadalupe".to_string()),
        max_swap_operations: 5,
        noise_budget: 0.05,
        ..Default::default()
    },
).await?;

// The allocator will find physical qubits matching the logical topology
match allocation.topology_mapping {
    Some(mapping) => {
        println!("Logical → Physical mapping: {:?}", mapping);
        // e.g., {0: 12, 1: 13, 2: 14, 3: 15} for a linear chain
    }
    None => println!("No topology mapping required"),
}
```

### 2. Noise-Adaptive Placement
```rust
// Configure noise-aware allocation
let allocator = NoiseAwareAllocator::new()
    .with_noise_threshold(0.01)  // Max error rate per gate
    .with_fidelity_requirement(0.98)
    .with_coherence_time(Duration::from_micros(50))
    .build();

// Allocate with noise constraints
let noise_constrained_allocation = allocator.allocate_qubits(
    device,
    required_qubits,
    topology,
    NoiseProfile {
        t1: Duration::from_micros(100),
        t2: Duration::from_micros(80),
        single_qubit_error: 0.001,
        two_qubit_error: 0.01,
        readout_error: 0.02,
        // ... other noise parameters
    },
).await?;
```

### 3. Multi-Level Isolation
```rust
// Configure isolation levels
let isolation_manager = IsolationManager::new()
    .with_level(IsolationLevel::Strong)  // Strong, Medium, Weak
    .with_hardware_enforcement(true)
    .with_crosstalk_mitigation(true)
    .build();

// Apply isolation for a task
let isolation_context = isolation_manager.isolate_resources(
    &allocation.device_id,
    &allocation.qubit_indices,
    IsolationRequirements {
        level: IsolationLevel::Strong,
        max_crosstalk: 0.001,
        require_hardware_reset: true,
        temporal_separation: Duration::from_micros(10),
    },
).await?;

// The isolation context ensures:
// 1. Spatial separation from other tasks
// 2. Temporal multiplexing with guard intervals
// 3. Hardware-level isolation where supported
// 4. Cross-talk suppression through frequency detuning
```

### 4. Intelligent Load Balancing
```rust
// Monitor and balance load across devices
let load_balancer = LoadBalancer::new()
    .with_strategy(BalancingStrategy::LeastLoaded)
    .with_threshold(0.8)  // Trigger rebalancing at 80% load
    .with_interval(Duration::from_secs(30))
    .build();

// Get current load distribution
let device_loads = load_balancer.get_device_loads().await?;
for (device_id, load) in device_loads {
    println!("{}: {:.1}% loaded", device_id, load * 100.0);
}

// Trigger rebalancing if needed
if let Some(rebalance_plan) = load_balancer.should_rebalance(&device_loads).await? {
    println!("Rebalancing needed. Plan: {:?}", rebalance_plan);
    
    // Execute rebalancing (migrate tasks between devices)
    let result = load_balancer.execute_rebalance(rebalance_plan).await?;
    println!("Rebalanced {} tasks", result.migrations_count);
}
```

### 5. Real-time Monitoring
```rust
// Set up comprehensive monitoring
let monitor = ResourceMonitor::new()
    .with_realtime_streaming(true)
    .with_prometheus_integration("localhost:9090")
    .with_alert_rules(vec![
        AlertRule::new("high_qubit_utilization")
            .condition(Condition::GreaterThan(0.9))
            .duration(Duration::from_secs(60))
            .severity(Severity::Warning),
        AlertRule::new("allocation_failure_rate_high")
            .condition(Condition::GreaterThan(0.05))
            .duration(Duration::from_secs(300))
            .severity(Severity::Critical),
    ])
    .build();

// Stream real-time metrics
let mut metrics_stream = monitor.stream_metrics().await?;
while let Some(metrics) = metrics_stream.next().await {
    println!("Qubit utilization: {:.2}%", metrics.qubit_utilization * 100.0);
    println!("Allocation success rate: {:.2}%", metrics.allocation_success_rate * 100.0);
    println!("Active allocations: {}", metrics.active_allocations);
    
    // Check for alerts
    if let Some(alerts) = monitor.check_alerts(&metrics).await {
        for alert in alerts {
            println!("ALERT: {}", alert.message);
            // Trigger automated response or notification
        }
    }
}
```

## 📊 Performance Metrics

### Key Performance Indicators
```rust
pub struct PerformanceMetrics {
    // Allocation efficiency
    pub allocation_success_rate: f64,        // Target: > 99%
    pub average_allocation_time_ms: f64,     // Target: < 50ms
    pub fragmentation_level: f64,            // Target: < 0.3
    
    // Resource utilization
    pub qubit_utilization: f64,              // Target: 70-80%
    pub device_utilization: HashMap<String, f64>,
    pub load_imbalance_score: f64,           // Target: < 0.1
    
    // Quality of service
    pub job_wait_time_p95: Duration,         // Target: < 500ms
    pub isolation_violations: usize,         // Target: 0
    pub reallocation_count: usize,           // Target: minimal
}
```

### Prometheus Metrics
```yaml
# Example Prometheus queries for monitoring

# Qubit utilization by device
sum(rate(resource_manager_qubit_allocated_seconds_total[5m])) 
/ sum(resource_manager_qubits_available) * 100

# Allocation success rate
rate(resource_manager_allocations_success_total[5m]) 
/ rate(resource_manager_allocations_total[5m])

# Allocation latency histogram
histogram_quantile(0.95, 
  sum(rate(resource_manager_allocation_duration_seconds_bucket[5m])) by (le))

# Isolation violations
rate(resource_manager_isolation_violations_total[5m])

# Device load imbalance
stddev(resource_manager_device_utilization) 
/ avg(resource_manager_device_utilization)
```

## 🔗 Integration

### With QRTX (Scheduler)
```rust
// QRTX requests resources for a task
let allocation = resource_manager.allocate_resources(
    job.spec.resource_requirements(),
    job.constraints(),
).await?;

// QRTX executes on allocated resources
let result = qrtx.execute_on_allocation(job, &allocation).await?;

// QRTX releases resources when complete
resource_manager.release_resources(job.id()).await?;
```

### With Driver Manager
```rust
// Get real-time device state
let device_state = driver_manager.get_device_state(device_id).await?;

// Apply hardware-level isolation
driver_manager.apply_isolation(
    device_id,
    &qubit_indices,
    isolation_level,
).await?;

// Monitor device health
let health_status = driver_manager.check_device_health(device_id).await?;
if !health_status.healthy {
    resource_manager.mark_device_unavailable(device_id, health_status.reason).await?;
}
```

### With Quantum Data Fabric
```rust
// Store allocation metadata
qfs.circuit_fs().store_allocation_metadata(
    &allocation,
    StorageClass::Hot,
).await?;

// Checkpoint quantum state
let checkpoint = qfs.state_store().capture_state(
    allocation.device_id,
    &allocation.qubit_indices,
    tomography_config,
).await?;
```

### With Security Module
```rust
// Apply security policies to allocation
let security_context = security_module.verify_allocation(
    &allocation,
    user_context,
).await?;

// Enforce isolation policies
security_module.enforce_isolation(
    &allocation,
    IsolationPolicy::QuantumSafe,
).await?;

// Audit resource usage
security_module.audit_resource_access(
    &allocation,
    &user_context,
).await?;
```

## ⚙️ Configuration Examples

### Advanced Allocation Policies
```yaml
resource_manager:
  allocation_policies:
    - name: "research_priority"
      priority: 100
      conditions:
        user_group: "quantum_researchers"
        time_window: "09:00-18:00"
      actions:
        preallocation: true
        qubit_guarantee: 0.8
        isolation_level: "strong"
    
    - name: "student_access"
      priority: 50
      conditions:
        user_group: "students"
        project_type: "educational"
      actions:
        max_qubits: 10
        time_limit: "1h"
        noise_tolerance: 0.05
    
    - name: "production_workload"
      priority: 200
      conditions:
        sla_required: true
        job_criticality: "high"
      actions:
        device_preference: ["ibm_guadalupe", "rigetti_aspen"]
        redundancy: 2
        checkpoint_interval: "30s"
```

### Device-Specific Configuration
```yaml
devices:
  - id: "ibm_guadalupe"
    type: "superconducting"
    qubits: 16
    topology: "heavy_hex"
    noise_profile:
      t1_avg: "120µs"
      t2_avg: "80µs"
      single_qubit_error: 0.001
      two_qubit_error: 0.01
    allocation_constraints:
      max_concurrent_tasks: 3
      min_qubit_separation: 1
      calibration_interval: "4h"
    
  - id: "ionq_harmony"
    type: "trapped_ion"
    qubits: 11
    topology: "all_to_all"
    noise_profile:
      t1_avg: "10s"
      t2_avg: "1s"
      single_qubit_error: 0.0005
      two_qubit_error: 0.005
    allocation_constraints:
      max_concurrent_tasks: 1  # Full device exclusive
      reconfiguration_time: "100ms"
```

## 🧪 Testing

### Unit Tests
```bash
# Run all unit tests
cargo test --lib

# Run specific module tests
cargo test --test allocator_tests
cargo test --test isolation_tests
cargo test --test scheduler_tests
```

### Integration Tests
```bash
# Run integration tests with simulated devices
cargo test --test integration --features "integration_testing"

# Test with different database backends
cargo test --test db_tests --features "postgres"
cargo test --test db_tests --features "sqlite"
```

### Performance Benchmarks
```rust
#[tokio::test]
async fn benchmark_allocation_performance() {
    let mut manager = ResourceManager::new_for_testing();
    
    // Benchmark allocation time
    let start = Instant::now();
    for i in 0..1000 {
        let request = create_test_request(i);
        let _allocation = manager.allocate_resources(request).await.unwrap();
    }
    let duration = start.elapsed();
    
    println!("Allocated 1000 tasks in {:?}", duration);
    println!("Average allocation time: {:?}", duration / 1000);
    assert!(duration < Duration::from_secs(10));  // < 10ms per allocation
}

#[tokio::test]
async fn test_concurrent_allocations() {
    // Test concurrent allocation from multiple threads
    let manager = Arc::new(ResourceManager::new_for_testing());
    let mut handles = vec![];
    
    for i in 0..100 {
        let manager_clone = manager.clone();
        let handle = tokio::spawn(async move {
            let request = create_test_request(i);
            manager_clone.allocate_resources(request).await
        });
        handles.push(handle);
    }
    
    // Verify all allocations succeeded
    for handle in handles {
        let result = handle.await.unwrap();
        assert!(result.is_ok());
    }
}
```

### Load Testing
```bash
# Run load tests with varying concurrent requests
./scripts/load_test.sh --concurrent 100 --duration 5m

# Test with different allocation patterns
./scripts/load_test.sh --pattern "burst" --burst-size 50
./scripts/load_test.sh --pattern "steady" --rate 10
```

## 📈 Performance Targets

### Acceptance Criteria

| **Metric** | **Target** | **Status** |
|-------------------|-------------------|-------------------|
| Allocation success rate | > 99% | ✅ |
| Average allocation time | < 50ms | ✅ |
| Qubit utilization | 70-80% | 🟡 |
| Load imbalance score | < 0.1 | 🟡 |
| Isolation violations | 0 | ✅ |
| Rebalancing overhead | < 1% | 🔴 |

### Scaling Characteristics

- **Allocation time**: O(log n) with caching, O(n) worst-case

- **Memory usage**: Linear with number of active allocations

- **Concurrent allocations**: Scales with CPU cores

- **Device count**: Scales to 1000+ devices with clustering

## 🔮 Roadmap

### Phase 1: Basic Allocation (Current)

- ✅ First-fit allocation

- ✅ Simple isolation (logical)

- ✅ Basic monitoring

- ✅ Synchronous API

## Phase 2: Advanced Features

- 🚧 Topology-aware allocation

- 🚧 Hardware-level isolation

- 🚧 Asynchronous API

- 🚧 Load balancing

### Phase 3: Intelligent Management

- 🔜 ML-based load prediction

- 🔜 Automated rebalancing

- 🔜 Adaptive policies

- 🔜 GNN optimizer integration

### Phase 4: Production Optimization

- 🔜 Quantum resource defragmentation

- 🔜 Predictive pre-allocation

- 🔜 Cross-device optimization

- 🔜 Industry certification

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

### Development Setup
```bash
# Clone and setup
git clone https://github.com/eigen-os/eigen-os/src/kernel/resource-manager.git
cd resource-manager
rustup override set stable

# Install development dependencies
cargo install cargo-make
cargo install sqlx-cli

# Setup database
sqlx database create
sqlx migrate run

# Run development environment
cargo make dev
```

### Code Quality Standards
```bash
# Run linter
cargo clippy --all-features -- -D warnings

# Format code
cargo fmt --all

# Security audit
cargo audit

# Run all tests
cargo make test-all
```

## 📚 Documentation

- [API Documentation](https://docs.eigen-os.org/resource-manager/api)

- [Architecture Guide](https://docs.eigen-os.org/resource-manager/architecture)

- [Performance Tuning](https://docs.eigen-os.org/resource-manager/performance)

- [Troubleshooting Guide](https://docs.eigen-os.org/resource-manager/troubleshooting)

## 🐛 Issue Reporting

Found a bug? Please [open an issue](https://github.com/Eigen-OS/eigen-os/issues) with:

1. Resource Manager version

2. Steps to reproduce

3. Expected vs actual behavior

4. Logs and error messages

5. Configuration file (redacted)

## 📄 License

Resource Manager is part of Eigen OS and is licensed under the [Apache License 2.0](LICENSE).

## 🙏 Acknowledgments

- Quantum hardware providers: IBM, Google, Rigetti, IonQ

- Research partners and academic collaborators

- Early adopters and community contributors

**Resource Manager** — Transforming heterogeneous quantum resources into predictable, manageable computational infrastructure for the quantum computing era.