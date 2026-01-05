# Resource Manager Reference

Resource Manager is the core resource allocation and isolation component of Eigen OS, responsible for managing quantum resources (qubits, gates, time slots), balancing load across quantum devices, and ensuring secure isolation between concurrent quantum tasks. It provides a high-performance, adaptive resource management system designed specifically for the unique constraints of quantum computing environments.

## Overview

The Resource Manager (RM) offers:

- Dynamic qubit allocation: Topology-aware and noise-aware allocation of physical qubits to logical tasks

- Load balancing: Intelligent distribution of tasks across multiple quantum processors based on current load and capabilities

- Task isolation: Spatial, temporal, and logical isolation between concurrent quantum computations

- Resource monitoring: Real-time tracking of resource utilization and health

- Adaptive policies: Policy-driven resource management with support for custom allocation strategies

## Key Features

### Core Capabilities

- Topology-Aware Allocation: Allocate qubits with consideration for device connectivity graphs and coupling constraints

- Noise-Adaptive Allocation: Adjust allocation based on real-time noise characteristics of qubits and gates

- Multi-Device Load Balancing: Distribute tasks across a heterogeneous fleet of quantum processors

- Strong Isolation Guarantees: Ensure that concurrent tasks do not interfere with each other

- Resource Reservation: Reserve resources for high-priority or time-critical tasks

- Quantum Multiplexing: Efficiently share quantum hardware between multiple concurrent tasks

### Performance Characteristics

- Low Allocation Latency: Sub-millisecond allocation decisions

- High Resource Utilization: Maximize usage of expensive quantum resources

- Scalability: Manage thousands of qubits across hundreds of devices

- Fault Tolerance: Handle device failures and resource degradation gracefully

- Adaptive Optimization: Continuous optimization based on real-time system metrics

## Architecture

### System Architecture
```text
┌─────────────────────────────────────────────────────┐
│                 Resource Manager                    │
├─────────────────────────────────────────────────────┤
│               Allocation Engine                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Qubit      │  │  Topology   │  │   Noise     │  │
│  │ Allocator   │  │   Aware     │  │   Aware     │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────┤
│              Isolation Manager                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Spatial    │  │  Temporal   │  │  Logical    │  │
│  │  Isolation  │  │  Isolation  │  │  Isolation  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────┤
│              Load Balancer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Device     │  │   Task      │  │   Policy    │  │
│  │  Selector   │  │  Distributor│  │  Engine     │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────┤
│              Monitoring System                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Resource   │  │   Health    │  │   Metrics   │  │
│  │  Tracker    │  │   Checker   │  │  Collector  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Component Relationships
```rust
// src/resource_mgr/architecture.rs
pub struct ResourceManagerArchitecture {
    // Core allocation components
    pub qubit_allocator: Arc<dyn QubitAllocator>,
    pub topology_manager: Arc<TopologyManager>,
    pub noise_aware_allocator: Arc<NoiseAwareAllocator>,
    
    // Isolation components
    pub spatial_isolation: Arc<SpatialIsolation>,
    pub temporal_isolation: Arc<TemporalIsolation>,
    pub logical_isolation: Arc<LogicalIsolation>,
    
    // Load balancing
    pub load_balancer: Arc<LoadBalancer>,
    pub device_selector: Arc<DeviceSelector>,
    
    // Monitoring
    pub resource_monitor: Arc<ResourceMonitor>,
    pub metrics_collector: Arc<MetricsCollector>,
    
    // Policy engine
    pub policy_engine: Arc<PolicyEngine>,
    
    // Integration points
    pub driver_manager: Arc<DriverManager>,
    pub qrtx_scheduler: Arc<QrtxScheduler>,
}
```

## Core Components

### 1. Allocation Engine

The Allocation Engine handles the allocation of physical qubits to logical tasks, considering topology and noise constraints.
```rust
// src/resource_mgr/allocation/engine.rs
pub struct AllocationEngine {
    allocators: HashMap<String, Box<dyn QubitAllocator>>,
    cache: AllocationCache,
    constraint_solver: ConstraintSolver,
}

impl AllocationEngine {
    /// Allocate qubits for a given task
    pub async fn allocate_qubits(
        &self,
        task: &QuantumTask,
        device: &QuantumDevice,
    ) -> Result<QubitAllocation> {
        // 1. Check cache for similar allocations
        if let Some(cached) = self.cache.get(task, device).await {
            if self.validate_allocation(&cached, device).await {
                return Ok(cached);
            }
        }
        
        // 2. Select appropriate allocator based on task requirements
        let allocator = self.select_allocator(task, device).await?;
        
        // 3. Perform allocation
        let allocation = allocator.allocate(task, device).await?;
        
        // 4. Validate allocation meets constraints
        self.constraint_solver.validate(&allocation, task).await?;
        
        // 5. Cache the allocation
        self.cache.put(task, device, allocation.clone()).await?;
        
        Ok(allocation)
    }
    
    /// Release allocated qubits
    pub async fn release_qubits(&self, allocation: &QubitAllocation) -> Result<()> {
        let device = self.get_device(&allocation.device_id).await?;
        let allocator = self.select_allocator_for_device(&device).await?;
        
        allocator.release(allocation).await?;
        self.cache.invalidate(allocation).await?;
        
        Ok(())
    }
}
```

### 2. Isolation Manager

The Isolation Manager ensures that concurrent quantum tasks do not interfere with each other, providing spatial, temporal, and logical isolation.
```rust
// src/resource_mgr/isolation/manager.rs
pub struct IsolationManager {
    spatial: SpatialIsolation,
    temporal: TemporalIsolation,
    logical: LogicalIsolation,
    policy_enforcer: IsolationPolicyEnforcer,
}

impl IsolationManager {
    /// Apply isolation to a set of resources for a task
    pub async fn isolate_resources(
        &self,
        task: &QuantumTask,
        resources: &ResourceSet,
    ) -> Result<IsolationContext> {
        // 1. Determine isolation requirements based on task
        let requirements = self.determine_isolation_requirements(task).await?;
        
        // 2. Apply spatial isolation (physical separation of qubits)
        let spatial_ctx = self.spatial.isolate(resources.qubits(), &requirements).await?;
        
        // 3. Apply temporal isolation (time-slicing of device access)
        let temporal_ctx = self.temporal.isolate(resources.time_slots(), &requirements).await?;
        
        // 4. Apply logical isolation (logical separation via error-correcting codes)
        let logical_ctx = self.logical.isolate(resources, &requirements).await?;
        
        // 5. Create combined isolation context
        let context = IsolationContext::new(spatial_ctx, temporal_ctx, logical_ctx);
        
        // 6. Enforce isolation policies
        self.policy_enforcer.enforce(&context, task).await?;
        
        Ok(context)
    }
    
    /// Release isolation context
    pub async fn release_isolation(&self, context: &IsolationContext) -> Result<()> {
        self.spatial.release(&context.spatial).await?;
        self.temporal.release(&context.temporal).await?;
        self.logical.release(&context.logical).await?;
        
        Ok(())
    }
}
```

### 3. Load Balancer

The Load Balancer distributes tasks across multiple quantum devices to optimize resource utilization and minimize queue times.
```rust
// src/resource_mgr/load_balancing/balancer.rs
pub struct LoadBalancer {
    device_registry: DeviceRegistry,
    load_tracker: LoadTracker,
    distribution_algorithm: Box<dyn DistributionAlgorithm>,
    policy_engine: PolicyEngine,
}

impl LoadBalancer {
    /// Select the best device for a given task
    pub async fn select_device(
        &self,
        task: &QuantumTask,
        constraints: &ResourceConstraints,
    ) -> Result<DeviceSelection> {
        // 1. Get available devices that meet basic constraints
        let available_devices = self.device_registry.get_available_devices().await?
            .into_iter()
            .filter(|device| self.device_meets_constraints(device, constraints).await)
            .collect::<Vec<_>>();
        
        if available_devices.is_empty() {
            return Err(LoadBalancerError::NoSuitableDevice);
        }
        
        // 2. Get current load information for each device
        let device_loads = self.load_tracker.get_current_loads().await?;
        
        // 3. Apply distribution algorithm to select the best device
        let selection = self.distribution_algorithm.select_device(
            task,
            &available_devices,
            &device_loads,
        ).await?;
        
        // 4. Apply any policies that might override the selection
        let final_selection = self.policy_engine.apply_selection_policies(
            selection,
            task,
            &available_devices,
        ).await?;
        
        Ok(final_selection)
    }
    
    /// Rebalance tasks across devices
    pub async fn rebalance(&self) -> Result<RebalancePlan> {
        // 1. Get current load distribution
        let current_load = self.load_tracker.get_current_loads().await?;
        
        // 2. Identify imbalances
        let imbalances = self.identify_imbalances(&current_load).await?;
        
        // 3. Generate rebalance plan
        let plan = self.generate_rebalance_plan(&imbalances).await?;
        
        // 4. Execute plan (migrate tasks if supported)
        if self.policy_engine.rebalancing_enabled().await {
            self.execute_rebalance_plan(&plan).await?;
        }
        
        Ok(plan)
    }
}
```

## Resource Allocation Strategies

### 1. Topology-Aware Allocation
```rust
// src/resource_mgr/allocation/topology_aware.rs
pub struct TopologyAwareAllocator {
    graph_analyzer: GraphAnalyzer,
    placement_algorithms: HashMap<String, Box<dyn PlacementAlgorithm>>,
    cache: TopologyCache,
}

impl TopologyAwareAllocator {
    pub async fn allocate_with_topology(
        &self,
        task: &QuantumTask,
        device: &QuantumDevice,
    ) -> Result<QubitAllocation> {
        // 1. Analyze task's connectivity requirements
        let required_connectivity = self.analyze_connectivity_requirements(task).await?;
        
        // 2. Get device topology graph
        let topology = device.get_topology().await?;
        
        // 3. Select placement algorithm based on topology type
        let algorithm = self.select_placement_algorithm(&topology).await?;
        
        // 4. Find optimal placement
        let placement = algorithm.find_placement(&topology, &required_connectivity).await?;
        
        // 5. Convert placement to allocation
        let allocation = self.placement_to_allocation(placement, device).await?;
        
        Ok(allocation)
    }
}
```

### 2. Noise-Aware Allocation
```rust
// src/resource_mgr/allocation/noise_aware.rs
pub struct NoiseAwareAllocator {
    noise_monitor: NoiseMonitor,
    fidelity_predictor: FidelityPredictor,
    calibration_manager: CalibrationManager,
}

impl NoiseAwareAllocator {
    pub async fn allocate_with_noise_consideration(
        &self,
        task: &QuantumTask,
        device: &QuantumDevice,
    ) -> Result<QubitAllocation> {
        // 1. Get current noise characteristics of device
        let noise_profile = self.noise_monitor.get_noise_profile(device.id()).await?;
        
        // 2. Predict fidelity for different possible allocations
        let candidate_allocations = self.generate_candidate_allocations(task, device).await?;
        
        let scored_allocations: Vec<_> = candidate_allocations
            .into_iter()
            .map(|allocation| {
                let predicted_fidelity = self.fidelity_predictor.predict(
                    task,
                    &allocation,
                    &noise_profile,
                ).await;
                
                (allocation, predicted_fidelity)
            })
            .collect();
        
        // 3. Select allocation with highest predicted fidelity
        let best_allocation = scored_allocations
            .iter()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(Ordering::Equal))
            .map(|(allocation, _)| allocation.clone())
            .ok_or(NoiseAwareAllocatorError::NoValidAllocation)?;
        
        // 4. If fidelity is below threshold, trigger calibration
        let best_fidelity = self.fidelity_predictor.predict(
            task,
            &best_allocation,
            &noise_profile,
        ).await;
        
        if best_fidelity < task.fidelity_requirement() {
            self.calibration_manager.schedule_calibration(device.id()).await?;
        }
        
        Ok(best_allocation)
    }
}
```

## Configuration

### Configuration Files
```yaml
# configs/default/resource_manager.yaml
resource_manager:
  # Allocation settings
  allocation:
    default_strategy: "topology_aware"
    fallback_strategy: "first_fit"
    enable_caching: true
    cache_ttl: "1h"
    
  # Load balancing settings
  load_balancing:
    enabled: true
    algorithm: "weighted_round_robin"
    weights:
      ibm_quantum: 0.3
      rigetti: 0.25
      ionq: 0.25
      simulator: 0.2
    rebalance_interval: "5m"
    imbalance_threshold: 0.2
    
  # Isolation settings
  isolation:
    spatial:
      enabled: true
      minimum_distance: 2  # Minimum qubits between tasks
    temporal:
      enabled: true
      time_slice_duration: "10ms"
    logical:
      enabled: false  # Requires error-correcting codes
      
  # Monitoring settings
  monitoring:
    collect_interval: "10s"
    metrics_retention: "7d"
    alerting:
      enabled: true
      high_utilization_threshold: 0.85
      allocation_failure_threshold: 0.05
      
  # Policy settings
  policies:
    allocation_policies:
      - "fair_share"
      - "priority_based"
    isolation_policies:
      - "strict_isolation_for_high_priority"
    balancing_policies:
      - "avoid_overloaded_devices"
```

### Environment Variables
```bash
# Required
export RM_ENDPOINT="0.0.0.0:50052"
export RM_STORAGE_PATH="/var/lib/eigen/resource_manager"

# Optional
export RM_LOG_LEVEL="INFO"
export RM_ALLOCATION_STRATEGY="topology_aware"
export RM_LOAD_BALANCING_ENABLED="true"
export RM_ISOLATION_LEVEL="spatial_temporal"
```

## Monitoring and Metrics

### Built-in Metrics
```rust
// src/resource_mgr/metrics/mod.rs
#[derive(Clone)]
pub struct ResourceManagerMetrics {
    // Allocation metrics
    pub allocation_requests: Counter,
    pub allocation_successes: Counter,
    pub allocation_failures: Counter,
    pub allocation_latency: Histogram,
    
    // Resource utilization
    pub qubit_utilization: GaugeVec,
    pub device_utilization: GaugeVec,
    pub gate_utilization: GaugeVec,
    
    // Load balancing metrics
    pub load_imbalance_score: Gauge,
    pub rebalance_operations: Counter,
    rebalance_latency: Histogram,
    
    // Isolation metrics
    pub isolation_violations: Counter,
    pub isolation_overhead: Histogram,
    
    // Performance metrics
    pub decision_making_time: Histogram,
    pub cache_hit_rate: Gauge,
}

impl ResourceManagerMetrics {
    pub fn new() -> Self {
        let registry = Registry::new();
        
        Self {
            allocation_requests: Counter::new(
                "rm_allocation_requests_total",
                "Total number of allocation requests"
            ).unwrap(),
            
            allocation_latency: Histogram::with_opts(
                HistogramOpts::new("rm_allocation_latency_seconds", "Allocation decision latency")
                    .buckets(vec![0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0])
            ).unwrap(),
            
            qubit_utilization: GaugeVec::new(
                Opts::new("rm_qubit_utilization", "Qubit utilization per device"),
                &["device_id", "device_type"]
            ).unwrap(),
            
            // Initialize all metrics...
        }
    }
}
```

## Integration with Other Components

### QRTX Integration
```rust
// src/resource_mgr/integration/qrtx.rs
pub struct QrtxIntegration {
    qrtx_client: QrtxClient,
    resource_manager: Arc<ResourceManager>,
}

impl QrtxIntegration {
    pub async fn handle_qrtx_request(
        &self,
        request: ResourceRequest,
    ) -> Result<ResourceAllocation> {
        // 1. Extract task requirements from QRTX request
        let task = self.translate_request_to_task(request).await?;
        
        // 2. Use Resource Manager to allocate resources
        let allocation = self.resource_manager.allocate_resources(task).await?;
        
        // 3. Convert allocation to QRTX format
        let qrtx_allocation = self.convert_allocation(allocation).await?;
        
        Ok(qrtx_allocation)
    }
    
    pub async fn notify_qrtx_of_changes(&self, changes: ResourceChanges) -> Result<()> {
        // Notify QRTX of resource changes (e.g., device failure, calibration)
        self.qrtx_client.notify_resource_changes(changes).await?;
        
        Ok(())
    }
}
```

### Driver Manager Integration
```rust
// src/resource_mgr/integration/driver.rs
pub struct DriverIntegration {
    driver_manager: Arc<DriverManager>,
    device_state_tracker: DeviceStateTracker,
}

impl DriverIntegration {
    pub async fn get_device_resources(&self, device_id: DeviceId) -> Result<DeviceResources> {
        // Get detailed resource information from driver
        let driver = self.driver_manager.get_driver(device_id).await?;
        let resources = driver.get_resources().await?;
        
        // Track state changes
        self.device_state_tracker.update(device_id, &resources).await?;
        
        Ok(resources)
    }
    
    pub async fn apply_isolation(
        &self,
        device_id: DeviceId,
        isolation: &IsolationContext,
    ) -> Result<()> {
        // Apply hardware-level isolation through driver
        let driver = self.driver_manager.get_driver(device_id).await?;
        
        if let Some(spatial) = &isolation.spatial {
            driver.isolate_qubits(spatial.qubits()).await?;
        }
        
        if let Some(temporal) = &isolation.temporal {
            driver.reserve_time_slots(temporal.slots()).await?;
        }
        
        Ok(())
    }
}
```

## Example Usage

### Basic Resource Allocation
```rust
use resource_manager::ResourceManagerClient;
use resource_manager::models::{ResourceRequest, TaskRequirements};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize Resource Manager client
    let client = ResourceManagerClient::new("localhost:50052").await?;
    
    // Create resource request
    let request = ResourceRequest {
        task_id: "task-123".to_string(),
        requirements: TaskRequirements {
            qubits: 5,
            connectivity: Connectivity::Linear,
            fidelity: 0.95,
            duration: std::time::Duration::from_secs(10),
            priority: Priority::High,
            isolation: IsolationLevel::Spatial,
        },
        constraints: ResourceConstraints {
            max_wait_time: Some(std::time::Duration::from_secs(30)),
            preferred_devices: vec!["ibm_quantum".to_string()],
            excluded_devices: vec![],
        },
    };
    
    // Request resource allocation
    let allocation = client.allocate_resources(request).await?;
    println!("Allocated resources: {:?}", allocation);
    
    // Use resources...
    
    // Release resources when done
    client.release_resources(allocation.allocation_id).await?;
    
    Ok(())
}
```

### Load Balancing Example
```rust
async fn run_load_balanced_tasks(
    client: &ResourceManagerClient,
    tasks: Vec<QuantumTask>,
) -> Result<Vec<TaskResult>> {
    let mut results = Vec::new();
    let mut allocations = Vec::new();
    
    // Allocate resources for each task with load balancing
    for task in tasks {
        let allocation = client.allocate_resources_for_task(task).await?;
        allocations.push(allocation);
    }
    
    // Execute tasks (in parallel)
    let mut handles = Vec::new();
    for allocation in allocations {
        let task_handle = execute_task_with_allocation(allocation);
        handles.push(task_handle);
    }
    
    // Wait for all tasks to complete
    for handle in handles {
        let result = handle.await?;
        results.push(result);
    }
    
    Ok(results)
}
```

## Performance Tuning

### Tuning Parameters
```rust
// src/resource_mgr/tuning/mod.rs
pub struct ResourceManagerTuner {
    metrics_analyzer: MetricsAnalyzer,
    configuration_manager: ConfigurationManager,
}

impl ResourceManagerTuner {
    pub async fn optimize(&self) -> Result<TuningResult> {
        // Collect performance metrics
        let metrics = self.metrics_analyzer.collect_metrics().await?;
        
        // Analyze for bottlenecks
        let bottlenecks = self.identify_bottlenecks(&metrics).await?;
        
        // Generate tuning recommendations
        let recommendations = self.generate_recommendations(&bottlenecks).await?;
        
        // Apply recommendations
        self.apply_recommendations(&recommendations).await?;
        
        Ok(TuningResult {
            bottlenecks,
            recommendations,
            applied: true,
        })
    }
    
    async fn identify_bottlenecks(&self, metrics: &ResourceManagerMetrics) -> Result<Vec<Bottleneck>> {
        let mut bottlenecks = Vec::new();
        
        // Check allocation latency
        if metrics.allocation_latency_average() > Duration::from_millis(50) {
            bottlenecks.push(Bottleneck::AllocationLatency);
        }
        
        // Check cache hit rate
        if metrics.cache_hit_rate() < 0.5 {
            bottlenecks.push(Bottleneck::CacheEfficiency);
        }
        
        // Check load imbalance
        if metrics.load_imbalance_score() > 0.3 {
            bottlenecks.push(Bottleneck::LoadImbalance);
        }
        
        // Check resource utilization
        if metrics.qubit_utilization_average() > 0.9 {
            bottlenecks.push(Bottleneck::ResourceSaturation);
        }
        
        Ok(bottlenecks)
    }
}
```

## See Also

- **QRTX (Quantum Real-Time Executive)** - Core scheduling engine that uses Resource Manager

- **Driver Manager** - Manages quantum device drivers that provide resource information

- **System API Server** - External API interface that may call Resource Manager

- **Monitoring System** - Observability and telemetry for Resource Manager

**Note**: Resource Manager is a critical component of Eigen OS. For production deployments, ensure proper monitoring and scaling configurations are in place. Regular performance tuning is recommended for optimal operation.