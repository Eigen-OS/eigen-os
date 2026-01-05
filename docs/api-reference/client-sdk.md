# Client SDK Reference

The Client SDK provides multi-language libraries and tools for interacting with Eigen OS through a unified, consistent interface. These libraries offer high-level abstractions for quantum computing, hiding protocol complexities and serialization details.

## Overview

The Eigen OS Client SDK offers:

    Multi-language support: Python, Rust, and JavaScript/TypeScript implementations

    Unified API: Consistent interfaces across all languages

    High performance: Optimized transports and caching

    Production-ready: Built-in retry mechanisms, circuit breakers, and monitoring

    Framework integration: Seamless integration with popular quantum and ML frameworks

## Installation

### Python SDK
```bash
# Basic installation
pip install eigen-sdk

# With quantum framework integrations
pip install eigen-sdk[quantum]

# With ML framework integrations
pip install eigen-sdk[ml]

# With web framework integrations
pip install eigen-sdk[web]

# Development installation
pip install eigen-sdk[dev]
```

### Rust SDK
```toml
# Cargo.toml
[dependencies]
eigen-sdk = { version = "0.1", features = ["async", "tls"] }

# Optional features
features = ["async", "tls", "metrics", "caching", "serde"]
```

### JavaScript/TypeScript SDK
```bash
# Node.js
npm install @eigenos/sdk-node

# Browser
npm install @eigenos/sdk-web

# React integration
npm install @eigenos/sdk-react
```

## Quick Start

### Python Example
```python
from eigen_sdk import EigenClient

async def main():
    # Initialize client with automatic configuration discovery
    async with EigenClient.from_config() as client:
        # Submit quantum job
        job = await client.jobs.submit(
            name="vqe-hydrogen",
            program=QUANTUM_PROGRAM,
            target="ionq.simulator"
        )
        
        # Stream updates in real-time
        async for update in client.jobs.stream_updates(job.id):
            print(f"Progress: {update.progress}%")
            
            if update.status == "COMPLETED":
                break
        
        # Get results
        results = await client.jobs.get_results(job.id)
        print(f"Energy: {results.energy}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Rust Example
```rust
use eigen_sdk::EigenClient;
use eigen_sdk::models::JobRequest;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = EigenClient::new("localhost:50051").await?;
    
    let request = JobRequest {
        name: "bell-state".to_string(),
        program: QUANTUM_PROGRAM.to_string(),
        target: "simulator".to_string(),
        ..Default::default()
    };
    
    let job = client.jobs.submit(request).await?;
    println!("Job ID: {}", job.id);
    
    Ok(())
}
```

### JavaScript Example
```javascript
import { EigenClient } from '@eigenos/sdk-node';

async function main() {
    const client = new EigenClient({
        endpoint: 'localhost:50051',
        auth: { type: 'jwt', token: process.env.EIGEN_TOKEN }
    });
    
    const job = await client.jobs.submit({
        name: 'quantum-simulation',
        program: QUANTUM_PROGRAM,
        target: 'simulator'
    });
    
    console.log(`Job submitted: ${job.id}`);
}

main().catch(console.error);
```

## Core Components

## EigenClient (Primary Class)

The main client class provides access to all services and features.

### Python Implementation
```python
class EigenClient:
    def __init__(self, endpoint=None, config=None, **kwargs):
        """
        Initialize Eigen OS client.
        
        Args:
            endpoint: Server endpoint (e.g., "localhost:50051")
            config: Configuration dictionary or path to config file
            **kwargs: Additional configuration options
        
        Examples:
            >>> # Automatic configuration discovery
            >>> client = EigenClient.from_config()
            
            >>> # Explicit configuration
            >>> client = EigenClient(
            ...     endpoint="api.example.com:50051",
            ...     auth={"method": "jwt", "token": "..."}
            ... )
        """
```

### Common Methods
```python
# Configuration
client = EigenClient.from_config()           # Auto-configuration
client = EigenClient.from_env()              # Environment variables
client.load_config("config.yaml")            # Load from file

# Connection management
await client.connect()                       # Establish connection
await client.ping()                          # Check connectivity
await client.close()                         # Close connection

# Service access
client.jobs                                  # Job management
client.devices                               # Device management
client.compilation                           # Circuit compilation
client.monitoring                            # System monitoring
```

## Service Interfaces

### Job Service

Manages quantum computation jobs.

```python
# Python
jobs = client.jobs

# Submit job
job = await jobs.submit(
    name="quantum-experiment",
    program=QUANTUM_CODE,
    target="simulator",
    priority=75,
    metadata={"experiment": "vqe-h2"}
)

# Get status
status = await jobs.get_status(job.id)

# Stream updates
async for update in jobs.stream_updates(job.id):
    print(f"Status: {update.status}, Progress: {update.progress}%")

# Get results
results = await jobs.get_results(job.id)

# Cancel job
await jobs.cancel(job.id)
```

```rust
// Rust
let jobs = client.jobs();

let request = JobRequest {
    name: "quantum-experiment".to_string(),
    program: QUANTUM_CODE.to_string(),
    target: "simulator".to_string(),
    priority: 75,
    metadata: Some(HashMap::from([
        ("experiment".to_string(), "vqe-h2".to_string())
    ])),
    ..Default::default()
};

let job = jobs.submit(request).await?;
let status = jobs.get_status(&job.id).await?;
```

### Device Service

Manages quantum devices and hardware.

```python
# List available devices
devices = await client.devices.list()

# Filter devices
filtered = await client.devices.list(
    provider="ibmq",
    status="online",
    min_qubits=5
)

# Get device details
device = await client.devices.get("ibmq_santiago")

# Reserve device
reservation = await client.devices.reserve(
    device_id="ibmq_santiago",
    duration_minutes=60,
    purpose="experiment-123"
)

# Get real-time status
status = await client.devices.get_status("ibmq_santiago")
```

### Compilation Service

Handles quantum circuit compilation and optimization.

```python
# Compile quantum circuit
compiled = await client.compilation.compile(
    circuit=QUANTUM_CIRCUIT,
    target="ibmq_santiago",
    optimization_level=3
)

# Optimize for specific device
optimized = await client.compilation.optimize(
    circuit=QUANTUM_CIRCUIT,
    target="rigetti.aspen-m-3",
    noise_model="rigetti_noise_v1"
)

# Validate circuit syntax
validation = await client.compilation.validate(
    circuit=QUANTUM_CIRCUIT,
    check_syntax=True,
    check_semantics=True
)
```

## Authentication

### Supported Authentication Methods
```python
# JWT Token Authentication
client = EigenClient(
    endpoint="api.example.com:50051",
    auth={
        "method": "jwt",
        "token": "eyJhbGciOiJIUzI1NiIs..."
    }
)

# API Key Authentication
client = EigenClient(
    endpoint="api.example.com:50051",
    auth={
        "method": "api_key",
        "api_key": "your-api-key-here"
    }
)

# OAuth2 Authentication
client = EigenClient(
    endpoint="api.example.com:50051",
    auth={
        "method": "oauth2",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "token_url": "https://auth.example.com/oauth/token"
    }
)

# mTLS Authentication
client = EigenClient(
    endpoint="api.example.com:50051",
    auth={
        "method": "mtls",
        "cert_file": "client.crt",
        "key_file": "client.key",
        "ca_cert": "ca.crt"
    }
)
```

### Token Management
```python
from eigen_sdk.auth import TokenManager

# Automatic token management
token_manager = TokenManager(
    storage="file",          # Store tokens in ~/.eigen/tokens
    auto_refresh=True,       # Automatically refresh expired tokens
    refresh_before_expiry=300  # Refresh 5 minutes before expiry
)

# Manual token management
token = await client.auth.get_token()
await client.auth.refresh_token()
await client.auth.revoke_token()
```

## Advanced Features

### Caching
```python
from eigen_sdk.cache import CacheConfig

# Enable caching
client = EigenClient(
    endpoint="api.example.com:50051",
    cache_config=CacheConfig(
        enabled=True,
        ttl=300,           # Cache for 5 minutes
        max_size=1000,     # Maximum 1000 items
        strategy="lru"     # Least Recently Used eviction
    )
)

# Manual cache control
await client.cache.clear()
await client.cache.invalidate("devices:list")
cached = await client.cache.get("devices:list", force_refresh=True)
```

### Retry and Circuit Breaker

```python
from eigen_sdk.retry import RetryConfig, CircuitBreakerConfig

client = EigenClient(
    endpoint="api.example.com:50051",
    retry_config=RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        max_delay=10.0,
        backoff_factor=2.0,
        retryable_errors=["UNAVAILABLE", "DEADLINE_EXCEEDED"]
    ),
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        reset_timeout=30,
        half_open_max_requests=2
    )
)
```

### Streaming
```python
# Stream job updates
async for update in client.jobs.stream_updates(job.id):
    print(f"Status: {update.status}")
    if update.progress >= 100:
        break

# Stream metrics
async for metric in client.monitoring.stream_metrics(
    resource_type="jobs",
    resource_id=job.id,
    interval=5  # seconds
):
    print(f"Metric: {metric.name} = {metric.value}")

# Stream logs
async for log_entry in client.monitoring.stream_logs(
    level="INFO",
    follow=True
):
    print(f"[{log_entry.timestamp}] {log_entry.message}")
```

### Batch Operations
```python
# Submit multiple jobs
jobs = await client.jobs.submit_batch([
    {"name": "job1", "program": CODE1, "target": "simulator"},
    {"name": "job2", "program": CODE2, "target": "simulator"},
    {"name": "job3", "program": CODE3, "target": "simulator"},
])

# Process results in batch
results = await client.jobs.get_results_batch([j.id for j in jobs])

# Cancel multiple jobs
await client.jobs.cancel_batch([j.id for j in jobs])
```

## Integration with Quantum Frameworks

### Qiskit Integration
```python
from eigen_sdk.integrations.qiskit import EigenBackend
from qiskit import QuantumCircuit

# Use as Qiskit backend
backend = EigenBackend(
    target="ibmq_santiago",
    optimization_level=3,
    shots=1024
)

# Execute circuit
circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

job = backend.run(circuit)
result = job.result()
```

### Cirq Integration
```python
from eigen_sdk.integrations.cirq import EigenSampler
import cirq

# Create Cirq circuit
qubits = cirq.LineQubit.range(2)
circuit = cirq.Circuit(
    cirq.H(qubits[0]),
    cirq.CNOT(qubits[0], qubits[1]),
    cirq.measure(*qubits, key='result')
)

# Execute using Eigen OS
sampler = EigenSampler(target="simulator")
results = sampler.run(circuit, repetitions=1000)
```

### PennyLane Integration
```python
from eigen_sdk.integrations.pennylane import EigenQNode
import pennylane as qml

# Define quantum function
@qml.qnode(EigenQNode(device="simulator", wires=2))
def circuit(params):
    qml.RY(params[0], wires=0)
    qml.RY(params[1], wires=1)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(0))

# Execute
result = circuit([0.1, 0.2])
```

## Integration with ML Frameworks

### PyTorch Integration
```python
import torch
from eigen_sdk.integrations.pytorch import QuantumLayer

# Define hybrid model
class HybridModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.classical = torch.nn.Linear(10, 4)
        self.quantum = QuantumLayer(
            n_qubits=4,
            ansatz="hea",
            observable="ising",
            parameter_shift=True
        )
        self.output = torch.nn.Linear(1, 2)
    
    def forward(self, x):
        x = self.classical(x)
        x = self.quantum(x)  # Quantum computation
        return self.output(x)

# Train model
model = HybridModel()
optimizer = torch.optim.Adam(model.parameters())
loss_fn = torch.nn.CrossEntropyLoss()

for batch in dataloader:
    optimizer.zero_grad()
    output = model(batch.features)
    loss = loss_fn(output, batch.labels)
    loss.backward()
    optimizer.step()
```

### TensorFlow Integration
```python
import tensorflow as tf
from eigen_sdk.integrations.tensorflow import QuantumLayer

# Define quantum layer
quantum_layer = QuantumLayer(
    n_qubits=4,
    ansatz="hea",
    observable="pauli_z",
    shots=1024
)

# Create model
model = tf.keras.Sequential([
    tf.keras.layers.Dense(4, activation='relu'),
    quantum_layer,
    tf.keras.layers.Dense(2, activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy')
model.fit(x_train, y_train, epochs=10)
```

## Web Integration

### React Integration
```jsx
import React from 'react';
import { useEigenClient, useEigenJob, useEigenDevices } from '@eigenos/sdk-react';

function QuantumApp() {
  const client = useEigenClient();
  const { devices, loading: devicesLoading } = useEigenDevices();
  const { submitJob, status, results } = useEigenJob();
  
  const handleSubmit = async () => {
    await submitJob({
      name: 'quantum-experiment',
      program: QUANTUM_PROGRAM,
      target: selectedDevice
    });
  };
  
  return (
    <div>
      <h1>Quantum Computing Interface</h1>
      
      <DeviceSelector 
        devices={devices}
        onSelect={setSelectedDevice}
      />
      
      <JobStatus 
        status={status}
        onCancel={() => client.jobs.cancel(jobId)}
      />
      
      <ResultsVisualizer 
        results={results}
        format="histogram"
      />
      
      <button onClick={handleSubmit} disabled={!selectedDevice}>
        Run Quantum Job
      </button>
    </div>
  );
}
```

### WebSocket Streaming
```javascript
import { EigenClient } from '@eigenos/sdk-web';

const client = new EigenClient({
  endpoint: 'wss://api.example.com/ws',
  auth: { token: userToken }
});

// Real-time job updates
client.jobs.subscribe(jobId, (update) => {
  console.log('Job update:', update);
  
  if (update.status === 'COMPLETED') {
    // Update UI
    displayResults(update.results);
  }
});

// Real-time device status
client.devices.subscribe('ibmq_santiago', (status) => {
  console.log('Device status:', status);
  updateDeviceStatus(status);
});
```

## Configuration

### Configuration Files
```yaml
# ~/.eigen/config.yaml
eigen:
  client:
    endpoint: "https://api.example.com:50051"
    
    auth:
      method: "jwt"
      token_file: "~/.eigen/token"
    
    transport:
      primary: "grpc"
      fallback: "rest"
      timeout: 30
      max_retries: 3
    
    cache:
      enabled: true
      ttl: 300
      max_size: 1000
    
    metrics:
      enabled: true
      port: 9090
    
    logging:
      level: "INFO"
      format: "json"
    
    plugins:
      - name: "eigen-notifications"
        enabled: true
      - name: "eigen-grafana"
        endpoint: "http://localhost:3000"
```

### Environment Variables
```bash
# Required
export EIGEN_ENDPOINT="https://api.example.com:50051"
export EIGEN_TOKEN="your-jwt-token"

# Optional
export EIGEN_LOG_LEVEL="INFO"
export EIGEN_CACHE_ENABLED="true"
export EIGEN_CACHE_TTL="300"
export EIGEN_METRICS_PORT="9090"
export EIGEN_TIMEOUT="30"
```

## Monitoring and Metrics

### Built-in Metrics Collection
```python
from eigen_sdk.metrics import MetricsCollector

# Initialize metrics
metrics = MetricsCollector(
    enabled=True,
    port=9090,
    prefix="eigen_sdk_"
)

# Record custom metrics
metrics.record_request_latency("job.submit", duration_ms=45.2)
metrics.record_cache_hit("devices", cache_level="l1")
metrics.record_error("connection.timeout")

# Export to Prometheus
await metrics.export_to_prometheus()

# Get metrics as dictionary
metrics_data = await metrics.collect()
```

### Structured Logging
```python
from eigen_sdk.logging import configure_logging
import structlog

# Configure structured logging
configure_logging(
    level="INFO",
    format="json",
    file="/var/log/eigen-sdk/app.log"
)

# Use logger
logger = structlog.get_logger()

# Structured log entries
logger.info(
    "job_submitted",
    job_id=job.id,
    user_id=user.id,
    target=job.target,
    duration_ms=duration,
    timestamp=datetime.utcnow().isoformat()
)
```

### Distributed Tracing
```python
from eigen_sdk.tracing import configure_tracing

# Configure OpenTelemetry tracing
configure_tracing(
    enabled=True,
    service_name="eigen-sdk-client",
    exporter="jaeger",
    endpoint="http://localhost:14268/api/traces"
)

# Automatic tracing
@client.trace_operation("quantum_computation")
async def run_quantum_job(client, program):
    return await client.jobs.submit(program=program)

# Manual tracing
with client.tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("user.id", user.id)
    result = await operation()
```

## Error Handling

### Common Error Types
```python
from eigen_sdk.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError
)

try:
    result = await client.jobs.submit(program=CODE)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Handle authentication failure
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Implement exponential backoff
except ServiceUnavailableError as e:
    print(f"Service unavailable: {e}")
    # Switch to fallback endpoint
except TimeoutError as e:
    print(f"Operation timed out: {e}")
    # Retry with longer timeout
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Fix input data
```

### Error Recovery Strategies
```python
from eigen_sdk.recovery import RecoveryStrategy

# Configure recovery strategy
recovery = RecoveryStrategy(
    max_retries=3,
    backoff_factor=2.0,
    circuit_breaker=True,
    fallback_endpoints=["backup1.eigenos.io", "backup2.eigenos.io"]
)

# Execute with recovery
result = await recovery.execute(
    operation=lambda: client.jobs.submit(program=CODE),
    should_retry=lambda e: isinstance(e, (ServiceUnavailableError, TimeoutError))
)
```

## Testing

### Mock Server for Testing
```python
import pytest
from eigen_sdk.testing import MockEigenServer

@pytest.fixture
async def mock_server():
    """Fixture for mock Eigen OS server"""
    server = MockEigenServer()
    await server.start()
    yield server
    await server.stop()

@pytest.fixture
async def client(mock_server):
    """Fixture for test client"""
    async with EigenClient(endpoint=mock_server.endpoint) as client:
        yield client

@pytest.mark.asyncio
async def test_job_submission(client):
    """Test job submission"""
    job = await client.jobs.submit(
        name="test-job",
        program=TEST_PROGRAM,
        target="simulator"
    )
    
    assert job.id is not None
    assert job.status == "PENDING"
```

### Integration Tests
```python
class TestEigenSDKIntegration:
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete quantum workflow"""
        client = EigenClient(endpoint=TEST_ENDPOINT)
        
        # 1. List devices
        devices = await client.devices.list()
        assert len(devices) > 0
        
        # 2. Submit job
        job = await client.jobs.submit(
            program=BELL_STATE_PROGRAM,
            target="simulator"
        )
        
        # 3. Monitor job
        updates = []
        async for update in client.jobs.stream_updates(job.id, timeout=30):
            updates.append(update)
            if update.status == "COMPLETED":
                break
        
        # 4. Verify results
        assert updates[-1].status == "COMPLETED"
        
        results = await client.jobs.get_results(job.id)
        assert results.success == True
        assert "measurements" in results.data
```

## Performance Optimization

### Connection Pooling
```python
from eigen_sdk.pool import ConnectionPool

# Create connection pool
pool = ConnectionPool(
    endpoint="api.eigenos.io:50051",
    min_connections=5,
    max_connections=20,
    max_idle_time=300
)

# Get connection from pool
async with pool.get_connection() as conn:
    result = await conn.execute(operation)

# Pool statistics
stats = pool.get_stats()
print(f"Active connections: {stats.active}")
print(f"Idle connections: {stats.idle}")
print(f"Total requests: {stats.total_requests}")
```

### Request Batching
```python
from eigen_sdk.batch import BatchProcessor

# Create batch processor
batch_processor = BatchProcessor(
    max_batch_size=100,
    max_wait_time=0.1,  # seconds
    concurrency=10
)

# Submit batch of requests
requests = [
    JobRequest(program=CODE1, target="simulator"),
    JobRequest(program=CODE2, target="simulator"),
    # ... 98 more requests
]

results = await batch_processor.process(
    requests=requests,
    operation=lambda req: client.jobs.submit(**req)
)
```

## Security

### Secure Credential Storage
```python
from eigen_sdk.security import SecureCredentialStorage

# Secure storage for credentials
storage = SecureCredentialStorage(
    encryption_key="your-encryption-key",  # Or use keyring
    storage_path="~/.eigen/credentials"
)

# Store credentials
await storage.save_credentials({
    "endpoint": "api.eigenos.io:50051",
    "token": "your-jwt-token",
    "user_id": "user-123"
})

# Load credentials
credentials = await storage.load_credentials()

# Rotate encryption key
await storage.rotate_key(new_key="new-encryption-key")
```

### Request Validation and Sanitization
```python
from eigen_sdk.security import RequestValidator

validator = RequestValidator(
    max_request_size=10 * 1024 * 1024,  # 10MB
    allowed_protocols=["https", "wss"],
    sanitize_input=True
)

# Validate request
try:
    validated = await validator.validate_request(request)
except SecurityError as e:
    print(f"Security validation failed: {e}")
    
# Sanitize user input
sanitized = validator.sanitize_input(user_input)
```

## Migration and Versioning

### API Version Compatibility
```python
from eigen_sdk.compat import VersionManager

# Check compatibility
version_manager = VersionManager()

compatible = version_manager.check_compatibility(
    client_version="1.2.0",
    server_version="1.3.0"
)

if not compatible:
    print("Version mismatch. Some features may not be available.")
    
# Migrate configuration
old_config = load_old_config()
new_config = await version_manager.migrate_config(
    old_config,
    target_version="1.3.0"
)
```

### Deprecation Warnings
```python
import warnings
from eigen_sdk.compat import deprecated

@deprecated(version="2.0.0", replacement="new_method")
async def old_method():
    """Deprecated method"""
    pass

# Usage emits warning
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    await old_method()
    if w:
        print(f"Deprecation warning: {w[0].message}")
```

## Examples Directory

See the **[examples](.../examples)** directory for complete working examples:

## Basic Examples

- **examples/basic/simple_job.py** - Submit and monitor a quantum job

- **examples/basic/device_management.py** - List and reserve quantum devices

- **examples/basic/streaming.py** - Real-time updates and metrics

## Advanced Examples

- **examples/advanced/hybrid_ml.py** - Quantum-classical machine learning

- **examples/advanced/distributed_computing.py** - Distributed quantum workflows

- **examples/advanced/custom_integration.py** - Integration with custom frameworks

## Framework Integrations

- **examples/integrations/qiskit_example.py** - Qiskit backend integration

- **examples/integrations/pytorch_example.py** - PyTorch quantum layers

- **examples/integrations/react_example.jsx** - React web interface

## See Also

- **System API Server** - The backend API that Client SDK communicates with

- **Eigen-Lang** - Quantum DSL for writing quantum programs

- **Eigen Kernel** - Core quantum runtime and scheduler

- **Eigen Compiler** - Neuro-symbolic quantum compiler

- **Eigen QDAL** - Quantum Device Abstraction Layer

**Note**: The Client SDK is actively developed. For the latest features and updates, please check the