# System API Server Reference

System API Server is the primary interface layer of Eigen OS, providing unified access to quantum computing resources through high-performance gRPC and REST APIs.

## Quick Start
```python
import grpc
from eigen_api.v1 import job_service_pb2, job_service_pb2_grpc

# Connect to gRPC server
channel = grpc.insecure_channel('localhost:50051')
stub = job_service_pb2_grpc.JobServiceStub(channel)

# Submit a quantum job
request = job_service_pb2.SubmitJobRequest(
    name="vqe-hydrogen",
    program=QUANTUM_PROGRAM,
    target="ionq.simulator"
)
response = stub.SubmitJob(request, metadata=[('authorization', 'Bearer YOUR_TOKEN')])
print(f"Job ID: {response.job_id}")
```

## Core Services

### JobService

Manages quantum computation jobs.

### gRPC Methods:
```protobuf
service JobService {
    rpc SubmitJob(SubmitJobRequest) returns (JobResponse);
    rpc GetJobStatus(JobStatusRequest) returns (JobStatusResponse);
    rpc CancelJob(CancelJobRequest) returns (CancelJobResponse);
    rpc StreamJobUpdates(JobUpdatesRequest) returns (stream JobUpdate);
    rpc GetJobResults(JobResultsRequest) returns (JobResultsResponse);
}
```

### REST Endpoints:

    *POST /api/v1/jobs* - Submit new job

    *GET /api/v1/jobs/{job_id}* - Get job status

    *DELETE /api/v1/jobs/{job_id}* - Cancel job

    *GET /api/v1/jobs/{job_id}/results* - Get job results

    *GET /api/v1/jobs/{job_id}/stream* - Stream job updates (SSE)

## DeviceService

Manages quantum devices and hardware.

### gRPC Methods:
```protobuf
service DeviceService {
    rpc ListDevices(ListDevicesRequest) returns (ListDevicesResponse);
    rpc GetDeviceDetails(DeviceDetailsRequest) returns (DeviceDetailsResponse);
    rpc GetDeviceStatus(DeviceStatusRequest) returns (DeviceStatusResponse);
    rpc ReserveDevice(ReserveDeviceRequest) returns (ReserveDeviceResponse);
}
```

### REST Endpoints:

    *GET /api/v1/devices* - List available devices

    *GET /api/v1/devices/{device_id}* - Get device details

    *POST /api/v1/devices/{device_id}/reserve* - Reserve device

    *GET /api/v1/devices/{device_id}/status* - Get real-time status

## CompilationService

Handles quantum circuit compilation and optimization.

### gRPC Methods:
```protobuf
service CompilationService {
    rpc CompileCircuit(CompileCircuitRequest) returns (CompileCircuitResponse);
    rpc OptimizeCircuit(OptimizeCircuitRequest) returns (OptimizeCircuitResponse);
    rpc ValidateCircuit(ValidateCircuitRequest) returns (ValidateCircuitResponse);
}
```

### REST Endpoints:

    *POST /api/v1/compile* - Compile quantum circuit

    *POST /api/v1/compile/optimize* - Optimize circuit for target

    *POST /api/v1/compile/validate* - Validate circuit syntax

## MonitoringService

Provides system monitoring and metrics.

### gRPC Methods:
```protobuf
service MonitoringService {
    rpc GetSystemMetrics(SystemMetricsRequest) returns (SystemMetricsResponse);
    rpc GetJobMetrics(JobMetricsRequest) returns (JobMetricsResponse);
    rpc StreamMetrics(StreamMetricsRequest) returns (stream MetricUpdate);
}
```

### REST Endpoints:

    *GET /api/v1/metrics/system* - System-wide metrics

    *GET /api/v1/metrics/jobs/{job_id}* - Job-specific metrics

    *GET /api/v1/metrics/stream* - Real-time metrics stream

## Authentication & Authorization

### Authentication Methods
```python
# JWT Authentication (gRPC)
metadata = [('authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')]

# API Key Authentication (REST)
headers = {'X-API-Key': 'your-api-key-here'}

# mTLS Authentication
context = grpc.ssl_channel_credentials(
    root_certificates=root_cert,
    private_key=private_key,
    certificate_chain=cert_chain
)
```

### Authorization Roles
```python
# Role-based permissions
ROLES = {
    "guest": ["jobs:read", "devices:list"],
    "user": ["jobs:create", "jobs:read", "jobs:cancel", "devices:list"],
    "researcher": ["jobs:*", "devices:*", "compilation:*"],
    "admin": ["*"]
}
```

## Message Types

### Job Management
```protobuf
message SubmitJobRequest {
    string name = 1;
    string program = 2;
    map<string, string> compiler_options = 3;
    string target = 4;
    int32 priority = 5;
    map<string, string> metadata = 6;
    repeated string dependencies = 7;
}

message JobResponse {
    string job_id = 1;
    JobStatus status = 2;
    google.protobuf.Timestamp created_at = 3;
    string message = 4;
}

enum JobStatus {
    UNKNOWN = 0;
    PENDING = 1;
    COMPILING = 2;
    QUEUED = 3;
    RUNNING = 4;
    COMPLETED = 5;
    FAILED = 6;
    CANCELLED = 7;
}
```

### Device Management
```protobuf
message Device {
    string id = 1;
    string name = 2;
    string provider = 3;
    string type = 4;
    int32 qubits = 5;
    DeviceStatus status = 6;
    map<string, string> capabilities = 7;
    repeated string supported_gates = 8;
    double coherence_time = 9;
}

enum DeviceStatus {
    OFFLINE = 0;
    ONLINE = 1;
    CALIBRATING = 2;
    RESERVED = 3;
    MAINTENANCE = 4;
}
```

## Configuration

### Server Configuration (YAML)

```yaml
# config/server.yaml
server:
  grpc:
    host: "0.0.0.0"
    port: 50051
    max_workers: 10
    max_message_size: 104857600  # 100MB
    
  rest:
    enabled: true
    host: "0.0.0.0"
    port: 8080
    workers: 4
    
  auth:
    providers: ["jwt", "api_key", "mtls"]
    jwt:
      secret_key: "${JWT_SECRET_KEY}"
      algorithm: "HS256"
      access_token_expire_minutes: 30
      
  security:
    cors:
      allow_origins: ["*"]
    rate_limiting:
      enabled: true
      requests_per_minute: 100
      
  backend_connections:
    kernel:
      grpc_endpoint: "eigen-kernel:50052"
      timeout_seconds: 30
    compiler:
      grpc_endpoint: "eigen-compiler:50053"
      timeout_seconds: 60
```

### Environment Variables
```bash
# Required
JWT_SECRET_KEY=your-secret-key-here
ENVIRONMENT=production

# Optional
LOG_LEVEL=INFO
GRPC_MAX_WORKERS=10
REDIS_URL=redis://localhost:6379
PROMETHEUS_PORT=9090
```

## Client Libraries

### Python Client
```python
from eigen_api_client import EigenClient

client = EigenClient(
    grpc_endpoint="localhost:50051",
    api_key="your-api-key"
)

# Submit job
job = client.jobs.submit(
    name="quantum-simulation",
    program=circuit_code,
    target="ibmq.simulator"
)

# Stream updates
for update in client.jobs.stream_updates(job.id):
    print(f"Progress: {update.progress}%")
    if update.status == "COMPLETED":
        break

# Get results
results = client.jobs.get_results(job.id)
```

### REST Client (cURL)
```bash
# Submit job
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bell-state",
    "program": "prepare bell_state() { ... }",
    "target": "simulator"
  }'

# Get job status
curl http://localhost:8080/api/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"

# Stream job updates
curl http://localhost:8080/api/v1/jobs/$JOB_ID/stream \
  -H "Accept: text/event-stream"
```

## Monitoring & Metrics

### Prometheus Metrics
```text
# Available metrics endpoints
GET /metrics - Prometheus metrics
GET /health - Health check
GET /ready - Readiness probe
GET /live - Liveness probe

# Example metrics
eigen_api_requests_total{method="POST", endpoint="/api/v1/jobs", status_code="200"}
eigen_api_request_duration_seconds{method="GET", endpoint="/api/v1/devices"}
eigen_api_active_requests
eigen_jobs_processing{status="running"}
eigen_devices_available{provider="ibmq"}
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

# Log format
{
    "event": "job_submitted",
    "job_id": "job-123",
    "user_id": "user-456",
    "target": "ionq.simulator",
    "timestamp": "2024-01-15T10:30:00Z",
    "duration_ms": 45.2,
    "level": "info"
}
```

## Error Handling

### gRPC Status Codes
```python
import grpc

# Common error scenarios
try:
    response = stub.SubmitJob(request, metadata=metadata)
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.UNAUTHENTICATED:
        print("Authentication failed - check your token")
    elif e.code() == grpc.StatusCode.PERMISSION_DENIED:
        print("Insufficient permissions")
    elif e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
        print("Rate limit exceeded")
    elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
        print("Request timeout")
    elif e.code() == grpc.StatusCode.UNAVAILABLE:
        print("Service unavailable")
```

### REST Error Responses
```json
{
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "Job with ID 'job-123' not found",
        "details": {
            "resource_type": "job",
            "resource_id": "job-123"
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "req-789"
    }
}
```

## Performance Optimization

### gRPC Tuning Parameters
```python
# Optimal settings for high-throughput
GRPC_OPTIMIZATIONS = {
    'grpc.max_send_message_length': 100 * 1024 * 1024,  # 100MB
    'grpc.max_receive_message_length': 100 * 1024 * 1024,
    'grpc.max_concurrent_streams': 1000,
    'grpc.keepalive_time_ms': 7200000,  # 2 hours
    'grpc.http2.write_buffer_size': 64 * 1024,  # 64KB
}
```

### Caching Strategies
```python
from functools import lru_cache
import redis

class CachingManager:
    def __init__(self):
        self.redis = redis.Redis()
        self.local_cache = TTLCache(maxsize=1000, ttl=60)
    
    @lru_cache(maxsize=100)
    async def get_device_list_cached(self) -> List[Device]:
        """Two-level caching: Redis + Local"""
        pass
```

## Security Features

### Request Validation
```python
class SecurityValidator:
    async def validate_request(self, request: Request) -> bool:
        # Rate limiting
        if not await self.rate_limiter.check(request):
            raise RateLimitExceeded()
        
        # SQL injection detection
        if self.sql_injection_detector.detect(request):
            raise SecurityViolation("SQL injection detected")
        
        # XSS protection
        if self.xss_detector.detect(request):
            raise SecurityViolation("XSS attack detected")
        
        # Request size limits
        if request.content_length > 10 * 1024 * 1024:  # 10MB
            raise SecurityViolation("Request too large")
        
        return True
```

### mTLS Configuration
```yaml
security:
  mtls:
    enabled: true
    ca_cert: "/path/to/ca.pem"
    server_cert: "/path/to/server.pem"
    server_key: "/path/to/server.key"
    client_verify: true
    allowed_client_cns:
      - "quantum-client-1"
      - "quantum-client-2"
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ ./proto/
COPY src/ ./src/
COPY config/ ./config/

# Generate gRPC code
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src \
    --grpc_python_out=./src \
    ./proto/eigen_api/v1/*.proto

USER eigen
EXPOSE 50051 8080 9090

CMD ["python", "-m", "src.main"]
```

### Kubernetes Deployment
```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eigen-system-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: eigen-system-api
  template:
    metadata:
      labels:
        app: eigen-system-api
    spec:
      containers:
      - name: api-server
        image: eigen/system-api:latest
        ports:
        - containerPort: 50051  # gRPC
        - containerPort: 8080   # REST
        - containerPort: 9090   # Metrics
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: eigen-secrets
              key: jwt-secret
```

## Examples

### Complete Workflow Example
```python
import eigen_api_client as eigen

# Initialize client
client = eigen.EigenClient(
    endpoint="api.quantum.example.com:50051",
    api_key="your-api-key"
)

# 1. Check available devices
devices = client.devices.list()
print(f"Available devices: {[d.name for d in devices]}")

# 2. Submit quantum job
job = client.jobs.submit(
    name="vqe-energy-calculation",
    program=load_quantum_program("vqe.eigen"),
    target="rigetti.aspen-m-3",
    priority=75,
    metadata={
        "experiment": "molecular-hydrogen",
        "researcher": "alice@example.com"
    }
)

# 3. Monitor progress
for update in client.jobs.stream_updates(job.id):
    print(f"Status: {update.status}, Progress: {update.progress}%")
    if update.status in ["COMPLETED", "FAILED", "CANCELLED"]:
        break

# 4. Get results
if update.status == "COMPLETED":
    results = client.jobs.get_results(job.id)
    print(f"Energy: {results.energy}")
    print(f"Circuit depth: {results.metadata['circuit_depth']}")
```

## Integration Tests
```python
import pytest
import grpc

@pytest.mark.asyncio
async def test_job_lifecycle():
    """Complete job lifecycle test"""
    client = TestClient()
    
    # Submit job
    job = await client.submit_job(TEST_PROGRAM)
    assert job.id is not None
    assert job.status == "PENDING"
    
    # Check status
    status = await client.get_job_status(job.id)
    assert status in ["PENDING", "COMPILING", "RUNNING"]
    
    # Stream updates
    updates = []
    async for update in client.stream_job_updates(job.id):
        updates.append(update)
        if update.status == "COMPLETED":
            break
    
    # Verify completion
    assert updates[-1].status == "COMPLETED"
    
    # Get results
    results = await client.get_job_results(job.id)
    assert results.success == True
    assert hasattr(results, 'quantum_result')
```

## Migration & Backward Compatibility

### API Versioning
```protobuf
// Protocol Buffers versioning
package eigen_api.v1;  // Current version
package eigen_api.v2;  // Future version (breaking changes)

// REST API versioning
/api/v1/jobs    # Current
/api/v2/jobs    # Future
```

### Configuration Migration
```python
class ConfigMigrator:
    async def migrate_config(self, old_config: dict, target_version: str) -> dict:
        """Migrate configuration between versions"""
        migrations = {
            "1.0->1.1": self._migrate_1_0_to_1_1,
            "1.1->1.2": self._migrate_1_1_to_1_2,
        }
        
        migration_key = f"{old_config['version']}->{target_version}"
        if migration_key in migrations:
            return await migrations[migration_key](old_config)
        
        raise MigrationError(f"No migration path from {old_config['version']} to {target_version}")
```

## See Also:

    *eigen-kernel/* - Core quantum runtime

    *eigen-compiler/* - Quantum circuit compiler

    *eigen-cli/* - Command-line interface

    *examples/* - Complete usage examples