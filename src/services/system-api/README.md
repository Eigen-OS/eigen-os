# System API Server

## 🚀 MVP skeleton quickstart (Issue #24)

This repository currently implements a **minimal** gRPC server skeleton exposing:

- `eigen.api.v1.JobService`
- `eigen.api.v1.DeviceService`

Run locally (from repo root):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e src/services/system-api
SYSTEM_API_GRPC_BIND=0.0.0.0:50051 system-api
```

The server performs basic required-field validation and returns structured validation
errors using `google.rpc.BadRequest` field violations.


***System API Server** is the primary interface layer for Eigen OS, providing unified access to quantum computing resources through a high-performance gRPC interface and a compatible REST adapter.

## 🌟 Overview

The System API Server serves as the gateway to Eigen OS, exposing all system capabilities through a modern, scalable API layer. It handles authentication, request routing, protocol translation, and provides comprehensive monitoring.

### Key Features

- **Dual Protocol Support**: Native gRPC for high-performance communication and REST API for web compatibility

- **Unified Authentication**: Multi-provider authentication system (JWT, OAuth2, API keys, mTLS)

- **Role-Based Access Control**: Fine-grained permissions for quantum resources

- **Real-time Updates**: WebSocket and gRPC streaming for job status updates

- **Comprehensive Monitoring**: Built-in metrics, logging, and distributed tracing

- **Scalable Architecture**: Horizontal scaling with load balancing support

## 🏗️ Architecture

### Component Architecture
```test
system-api-server/
├── proto/                    # Protocol Buffers definitions
│   └── eigen_api/v1/
│       ├── service.proto     # Main service definitions
│       ├── jobs.proto        # Job management
│       ├── devices.proto     # Device management
│       ├── compilation.proto # Circuit compilation
│       ├── monitoring.proto  # Monitoring endpoints
│       └── auth.proto        # Authentication and authorization
│
├── src/
│   ├── grpc_server/          # gRPC server implementation
│   │   ├── server.py         # Main gRPC server
│   │   ├── interceptors/     # gRPC interceptors
│   │   │   ├── auth_interceptor.py
│   │   │   ├── logging_interceptor.py
│   │   │   ├── metrics_interceptor.py
│   │   │   └── rate_limit_interceptor.py
│   │   ├── services/         # gRPC service implementations
│   │   │   ├── job_service.py
│   │   │   ├── device_service.py
│   │   │   ├── compilation_service.py
│   │   │   └── monitoring_service.py
│   │   └── utils/
│   │       └── grpc_helpers.py
│   │
│   ├── rest_adapter/         # REST API layer
│   │   ├── app.py            # FastAPI application
│   │   ├── routers/          # REST endpoints
│   │   │   ├── jobs.py
│   │   │   ├── devices.py
│   │   │   ├── compilation.py
│   │   │   └── admin.py
│   │   ├── middleware/       # REST middleware
│   │   │   ├── auth_middleware.py
│   │   │   ├── cors_middleware.py
│   │   │   ├── rate_limit_middleware.py
│   │   │   └── error_handler.py
│   │   └── converters/       # gRPC ↔ REST converters
│   │       ├── job_converter.py
│   │       ├── device_converter.py
│   │       └── result_converter.py
│   │
│   ├── auth/                 # Authentication system
│   │   ├── providers/        # Auth providers
│   │   │   ├── jwt_provider.py
│   │   │   ├── oauth2_provider.py
│   │   │   ├── api_key_provider.py
│   │   │   └── mtls_provider.py
│   │   ├── models/           # Security models
│   │   │   ├── user.py
│   │   │   ├── role.py
│   │   │   └── permission.py
│   │   ├── managers/         # Auth managers
│   │   │   ├── auth_manager.py
│   │   │   ├── token_manager.py
│   │   │   └── session_manager.py
│   │   └── policies/         # Authorization policies
│   │       ├── rbac_policy.py
│   │       ├── quota_policy.py
│   │       └── isolation_policy.py
│   │
│   ├── cache/                # Caching layer
│   │   ├── redis_cache.py
│   │   ├── memory_cache.py
│   │   └── cache_manager.py
│   │
│   ├── monitoring/           # Monitoring and observability
│   │   ├── metrics.py
│   │   ├── tracing.py
│   │   ├── logging.py
│   │   └── health.py
│   │
│   └── config/               # Configuration management
│       ├── config_manager.py
│       └── validators.py
│
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   └── performance/
│
├── config/                   # Configuration files
│   ├── server.yaml
│   ├── development.yaml
│   └── production.yaml
│
├── scripts/                  # Utility scripts
│   ├── generate_proto.py
│   ├── health_check.py
│   └── load_test.py
│
└── docker/                   # Docker files
    ├── Dockerfile
    └── docker-compose.yml
```

### System Integration
```text
┌─────────────────────────────────────────────────────┐
│           External Clients                          │
│    • CLI Tools                                      │
│    • Web Applications                               │
│    • SDK Libraries                                  │
│    • Third-party Integrations                       │
└─────────────┬───────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────┐
│           System API Server                         │
│    • gRPC Interface (50051)                         │
│    • REST Interface (8080)                          │
│    • Authentication & Authorization                 │
│    • Request Routing & Load Balancing               │
└─────────────┬─────────────────────────┬─────────────┘
              │                         │
    ┌─────────▼──────────┐    ┌─────────▼──────────┐
    │   Eigen Kernel     │    │   Eigen Compiler   │
    │   (QRTX, Resource  │    │   (Circuit         │
    │    Manager, QFS)   │    │   Compilation)     │
    └────────────────────┘    └────────────────────┘
              │
    ┌─────────▼──────────┐
    │  Quantum Hardware  │
    │  (Simulators &     │
    │   Physical QPUs)   │
    └────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**

- **Redis 8+** (for caching and rate limiting)

- **Docker & Docker Compose** (for containerized deployment)

- **Protocol Buffers Compiler** (protoc)

- **gRPC Python Tools**

### Installation
```bash
# Clone the repository
git clone https://github.com/eigen-os/eigen-os.git
cd eigen-os/system-api-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate gRPC code from protobuf definitions
python scripts/generate_proto.py

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running the Server

**Development Mode**
```bash
# Start in development mode with hot reload
python -m src.main --config config/development.yaml

# Or use the script
./scripts/start_dev.sh

# Start with Docker Compose (includes all dependencies)
docker-compose up -d
```

**Production Mode**
```bash
# Build and run with Docker
docker build -t eigen-system-api -f docker/Dockerfile .
docker run -p 50051:50051 -p 8080:8080 -p 9090:9090 \
  -v ./config:/config \
  -e JWT_SECRET_KEY=your_secret_key \
  eigen-system-api

# Or use the production script
./scripts/start_production.sh --config config/production.yaml
```

### Basic Configuration

Create c`onfig/server.yaml`:
```yaml
server:
  grpc:
    host: "0.0.0.0"
    port: 50051
    max_workers: 10
    max_message_size: 104857600  # 100MB
    keepalive_time: 7200  # 2 hours
    keepalive_timeout: 20
  
  rest:
    enabled: true
    host: "0.0.0.0"
    port: 8080
    workers: 4
    reload: false  # Set to false for production
  
  auth:
    enabled: true
    providers:
      - "jwt"
      - "api_key"
    
    jwt:
      secret_key: "${JWT_SECRET_KEY}"
      algorithm: "HS256"
      access_token_expire_minutes: 30
      refresh_token_expire_days: 7
    
    api_key:
      header: "X-API-Key"
      rotation_days: 90
  
  security:
    cors:
      allow_origins: ["*"]
      allow_credentials: true
      allow_methods: ["*"]
      allow_headers: ["*"]
    
    rate_limiting:
      enabled: true
      requests_per_minute: 100
      requests_per_hour: 1000
      burst_limit: 50
  
  monitoring:
    metrics:
      enabled: true
      port: 9090
      path: "/metrics"
    
    tracing:
      enabled: true
      provider: "jaeger"
      endpoint: "http://jaeger:14268/api/traces"
    
    logging:
      level: "INFO"
      format: "json"
      file: "/var/log/eigen-api/server.log"
  
  backend_connections:
    kernel:
      grpc_endpoint: "eigen-kernel:50052"
      timeout_seconds: 30
    
    compiler:
      grpc_endpoint: "eigen-compiler:50053"
      timeout_seconds: 60
    
    storage:
      endpoint: "eigen-qfs:9000"
      access_key: "${MINIO_ACCESS_KEY}"
      secret_key: "${MINIO_SECRET_KEY}"
```

## 🔧 API Usage

### gRPC API
```python
import grpc
import eigen_api.v1.jobs_pb2 as jobs_pb
import eigen_api.v1.jobs_pb2_grpc as jobs_pb_grpc
import eigen_api.v1.devices_pb2 as devices_pb
import eigen_api.v1.devices_pb2_grpc as devices_pb_grpc

# Create a channel
channel = grpc.insecure_channel('localhost:50051')

# Create stubs
jobs_stub = jobs_pb_grpc.JobServiceStub(channel)
devices_stub = devices_pb_grpc.DeviceServiceStub(channel)

# Submit a job
job_request = jobs_pb.SubmitJobRequest(
    name="quantum_fourier_transform",
    program="""
    from eigen import *
    
    @quantum
    def qft(n_qubits: int):
        q = QuantumRegister(n_qubits)
        for j in range(n_qubits):
            H(q[j])
            for k in range(j+1, n_qubits):
                CPHASE(pi/(2**(k-j)), q[k], q[j])
        return q
    
    result = qft(4)
    """,
    target="simulator",
    priority=50
)

# Add authentication metadata
metadata = [('authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...')]

# Submit the job
job_response = jobs_stub.SubmitJob(job_request, metadata=metadata)
print(f"Job submitted with ID: {job_response.job_id}")

# Stream job updates
updates_request = jobs_pb.JobUpdatesRequest(job_id=job_response.job_id)
for update in jobs_stub.StreamJobUpdates(updates_request, metadata=metadata):
    print(f"Job update: {update.status}, Progress: {update.progress}%")
    if update.status == jobs_pb.JobStatus.COMPLETED:
        break

# Get job results
results_request = jobs_pb.JobResultsRequest(job_id=job_response.job_id)
results = jobs_stub.GetJobResults(results_request, metadata=metadata)
print(f"Job results: {results}")
```

### REST API
```python
import requests
import json

# Base URL for REST API
BASE_URL = "http://localhost:8080/api/v1"

# Authentication headers
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "Content-Type": "application/json"
}

# Submit a job
job_data = {
    "name": "vqe_hydrogen",
    "program": """
    from eigen import *
    from eigen.chemistry import MolecularHamiltonian
    
    @quantum
    def vqe_circuit(theta: float):
        q = QuantumRegister(2)
        H(q[0])
        CNOT(q[0], q[1])
        RY(theta, q[0])
        return measure_all(q)
    
    hamiltonian = MolecularHamiltonian("H2")
    result = vqe(hamiltonian, vqe_circuit)
    """,
    "target": "ibm_guadalupe",
    "priority": 75,
    "metadata": {
        "experiment": "chemistry",
        "molecule": "H2"
    }
}

response = requests.post(
    f"{BASE_URL}/jobs",
    headers=headers,
    json=job_data
)

job_id = response.json()["job_id"]
print(f"Job submitted with ID: {job_id}")

# Get job status
status_response = requests.get(
    f"{BASE_URL}/jobs/{job_id}/status",
    headers=headers
)

print(f"Job status: {status_response.json()}")

# List available devices
devices_response = requests.get(
    f"{BASE_URL}/devices",
    headers=headers
)

devices = devices_response.json()["devices"]
print(f"Available devices: {devices}")

# WebSocket for real-time updates (Python example using websockets)
import asyncio
import websockets
import json

async def stream_job_updates(job_id: str):
    async with websockets.connect(
        f"ws://localhost:8080/api/v1/jobs/{job_id}/stream",
        extra_headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
    ) as websocket:
        while True:
            update = await websocket.recv()
            data = json.loads(update)
            print(f"Update: {data}")
            if data["status"] == "COMPLETED":
                break

# Run the WebSocket client
asyncio.run(stream_job_updates(job_id))
```

### Authentication Examples
```python
# JWT Authentication
import jwt
import datetime

# Generate a JWT token
payload = {
    "user_id": "alice_123",
    "roles": ["researcher", "quantum_user"],
    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
    "iat": datetime.datetime.utcnow()
}

secret_key = "your-secret-key"
jwt_token = jwt.encode(payload, secret_key, algorithm="HS256")

# API Key Authentication
api_key = "eigen_sk_live_1234567890abcdef"
headers = {"X-API-Key": api_key}

# OAuth2 Authentication (for external services)
import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

client_id = "your-client-id"
client_secret = "your-client-secret"

client = BackendApplicationClient(client_id=client_id)
oauth = OAuth2Session(client=client)
token = oauth.fetch_token(
    token_url="https://auth.eigenos.org/oauth/token",
    client_id=client_id,
    client_secret=client_secret
)

# Use the token
headers = {"Authorization": f"Bearer {token['access_token']}"}
```

## 📡 API Endpoints

### gRPC Services

| **Service** | **Method** | **Description** |
|-------------------|-------------------|-------------------|
| **JobService** | `SubmitJob`, `GetJobStatus`, `CancelJob`, `StreamJobUpdates`, `GetJobResults` | Quantum job management and monitoring |
| **DeviceService** | `ListDevices`, `GetDeviceDetails`, `GetDeviceStatus`, `ReserveDevice` | Quantum device information and reservation |
| **CompilationServic** | `CompileCircuit`, `OptimizeCircuit`, `ValidateCircuit` | Quantum circuit compilation and optimization |
| **MonitoringServic** | `GetMetrics`, `GetLogs`, `GetTraces`, `GetHealth` | System monitoring and observability |
| **AdminService** | `GetSystemStatus`, `UpdateConfig`, `ExportMetrics`, `ImportBackup` | Administrative operations |

### REST Endpoints

| **Endpoint** | **Method** | **Description** | **Authentication** |
|-------------------|-------------------|-------------------|-------------------|
| `/api/v1/jobs` | POST | Submit a new quantum job | Required |
| `/api/v1/jobs/{id}` | GET | Get job details | Required |
| `/api/v1/jobs/{id}/status` | GET | Get job status | Required |
| `/api/v1/jobs/{id}/cancel` | POST | Cancel a running job | Required |
| `/api/v1/jobs/{id}/results` | GET | Get job results | Required |
| `/api/v1/jobs/{id}/stream` | GET | Stream job updates (WebSocket) | Required |
| `/api/v1/devices` | GET | List available quantum devices | Required |
| `/api/v1/devices/{id}` | GET | Get device details | Required |
| `/api/v1/devices/{id}/reserve` | POST | Reserve a device | Required |
| `/api/v1/compile` | POST | Compile a quantum circuit | Required |
| `/api/v1/health` | GET | Health check | Optional |
| `/api/v1/metrics` | GET | System metrics (Prometheus format) | Optional |
| `/api/v1/auth/token` | POST | Get authentication token | Optional |
| `/api/v1/admin/status` | GET | System status (admin only) | Required (Admin) |
| `/api/v1/admin/config` | GET/PUT | System configuration (admin only) | Required (Admin) |

## 🔐 Authentication & Authorization

### Supported Authentication Methods

1. **JWT (JSON Web Tokens)**

    - Bearer token format

    - Configurable expiration

    - Refresh token support

2. **OAuth 2.0**

    - Authorization Code flow

    - Client Credentials flow

    - Integration with external identity providers

3. **API Keys**

    - Static keys for service-to-service communication

    - Key rotation policies

    - Per-key rate limiting

4. **mTLS (Mutual TLS)**

    - Certificate-based authentication

    - Hardware security module (HSM) integration

    - High-security environments

### Role-Based Access Control
```python
# Example RBAC configuration
ROLES = {
    "guest": [
        "jobs:read",
        "devices:list"
    ],
    "user": [
        "jobs:create", "jobs:read", "jobs:cancel",
        "devices:list", "devices:read",
        "compilation:request"
    ],
    "researcher": [
        "jobs:*",
        "devices:*",
        "compilation:*",
        "results:export"
    ],
    "admin": ["*"]
}

# Permission checking example
def check_permission(user: User, resource: str, action: str) -> bool:
    for role in user.roles:
        permissions = ROLES.get(role, [])
        required_permission = f"{resource}:{action}"
        if (required_permission in permissions or
            f"{resource}:*" in permissions or
            "*" in permissions):
            return True
    return False
```

### Rate Limiting
```python
# Rate limiting configuration
RATE_LIMITS = {
    "default": {
        "requests_per_minute": 100,
        "requests_per_hour": 1000,
        "burst_limit": 50
    },
    "researcher": {
        "requests_per_minute": 500,
        "requests_per_hour": 5000,
        "burst_limit": 100
    },
    "admin": {
        "requests_per_minute": 1000,
        "requests_per_hour": 10000,
        "burst_limit": 200
    }
}

# Apply rate limiting based on user role
def apply_rate_limit(user: User, endpoint: str):
    limits = RATE_LIMITS.get(user.primary_role, RATE_LIMITS["default"])
    # Implementation using Redis or in-memory store
    return check_rate_limit(user.id, endpoint, limits)
```

## ⚙️ Configuration

### Environment Variables

| **Variable** | **Description** | **Default** | **Required** |
|-------------------|-------------------|-------------------|-------------------|
| `JWT_SECRET_KEY` | Secret key for JWT signing | - | Yes |
| `GRPC_HOST` | gRPC server host | `0.0.0.0` | No |
| `GRPC_PORT` | gRPC server port | `50051` | No |
| `REST_HOST` | REST server host | `0.0.0.0` | No |
| `REST_PORT` | REST server port | `8080` | No |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ENVIRONMENT` | Environment (dev/staging/prod) | `development` | No |
| `KERNEL_ENDPOINT` | Eigen Kernel gRPC endpoint | `eigen-kernel:50052` | No |
| `COMPILER_ENDPOINT` | Eigen Compiler gRPC endpoint | `eigen-compiler:50053` | No |

### Production Configuration Example
```yaml
# config/production.yaml
server:
  grpc:
    host: "0.0.0.0"
    port: 50051
    max_workers: 50
    max_message_size: 104857600
    keepalive_time: 7200
    keepalive_timeout: 20
    options:
      - ["grpc.max_concurrent_streams", 1000]
      - ["grpc.http2.max_frame_size", 16777216]
  
  rest:
    enabled: true
    host: "0.0.0.0"
    port: 8080
    workers: 8
    reload: false
  
  auth:
    enabled: true
    providers:
      - "jwt"
      - "mtls"
    
    jwt:
      secret_key: "${JWT_SECRET_KEY}"
      algorithm: "RS256"
      public_key_file: "/etc/ssl/jwt-public.pem"
      private_key_file: "/etc/ssl/jwt-private.pem"
      access_token_expire_minutes: 15
      refresh_token_expire_days: 7
    
    mtls:
      ca_certificate: "/etc/ssl/ca-cert.pem"
      require_client_cert: true
      verify_client: "require"
  
  security:
    cors:
      allow_origins:
        - "https://app.eigenos.org"
        - "https://dashboard.eigenos.org"
      allow_credentials: true
      allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allow_headers: ["*"]
    
    rate_limiting:
      enabled: true
      redis_url: "${REDIS_URL}"
      default_limit: 100
      default_period: 60
      burst_limit: 50
  
  monitoring:
    metrics:
      enabled: true
      port: 9090
      path: "/metrics"
    
    tracing:
      enabled: true
      provider: "jaeger"
      endpoint: "jaeger-collector:14268"
      sampling_rate: 0.1
    
    logging:
      level: "INFO"
      format: "json"
      outputs:
        - type: "file"
          path: "/var/log/eigen-api/server.log"
          max_size: "100MB"
          backup_count: 10
        - type: "stdout"
  
  cache:
    redis:
      url: "${REDIS_URL}"
      max_connections: 50
      default_ttl: 300
    
    memory:
      enabled: true
      max_size: 1000
      default_ttl: 60
  
  backend_connections:
    kernel:
      grpc_endpoint: "${KERNEL_ENDPOINT}"
      timeout_seconds: 30
      retry_attempts: 3
      circuit_breaker:
        failure_threshold: 5
        reset_timeout: 60
    
    compiler:
      grpc_endpoint: "${COMPILER_ENDPOINT}"
      timeout_seconds: 60
      retry_attempts: 2
    
    storage:
      endpoint: "${STORAGE_ENDPOINT}"
      access_key: "${STORAGE_ACCESS_KEY}"
      secret_key: "${STORAGE_SECRET_KEY}"
      secure: true
```

## 🐳 Deployment

### Docker Deployment
```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY proto/ ./proto/
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Generate gRPC code
RUN python scripts/generate_proto.py

# Create non-root user
RUN groupadd -r eigen && useradd -r -g eigen eigen
USER eigen

# Expose ports
EXPOSE 50051  # gRPC
EXPOSE 8080   # REST
EXPOSE 9090   # Metrics

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python scripts/health_check.py

# Run the application
CMD ["python", "-m", "src.main", "--config", "/config/server.yaml"]
```

### Kubernetes Deployment
```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: system-api
  namespace: eigen-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: system-api
  template:
    metadata:
      labels:
        app: system-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: api-server
        image: eigenos/system-api:latest
        ports:
        - containerPort: 50051
          name: grpc
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: jwt-secret-key
        - name: REDIS_URL
          value: "redis://eigen-redis:6379"
        - name: KERNEL_ENDPOINT
          value: "eigen-kernel.eigen-system.svc.cluster.local:50052"
        - name: ENVIRONMENT
          value: "production"
        volumeMounts:
        - name: config
          mountPath: /config
          readOnly: true
        - name: tls-certs
          mountPath: /etc/ssl
          readOnly: true
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: api-config
      - name: tls-certs
        secret:
          secretName: tls-certificates
---
apiVersion: v1
kind: Service
metadata:
  name: system-api
  namespace: eigen-system
spec:
  selector:
    app: system-api
  ports:
  - name: grpc
    port: 50051
    targetPort: 50051
  - name: http
    port: 8080
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: LoadBalancer
```

### Helm Chart
```bash
# Add Eigen OS Helm repository
helm repo add eigen-os https://helm.eigen-os.org
helm repo update

# Install System API Server
helm install system-api eigen-os/system-api \
  --namespace eigen-system \
  --set replicaCount=3 \
  --set jwtSecretKey=$(openssl rand -hex 32) \
  --set service.type=LoadBalancer
```

## 📊 Monitoring & Observability

### Metrics

The server exposes Prometheus metrics at `/metrics`:
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter(
    'eigen_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'eigen_api_request_duration_seconds',
    'API request latency',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'eigen_api_active_connections',
    'Number of active connections'
)

JOB_SUBMISSIONS = Counter(
    'eigen_api_job_submissions_total',
    'Total job submissions',
    ['user_id', 'target_device']
)

# Example usage in middleware
async def metrics_middleware(request, call_next):
    start_time = time.time()
    ACTIVE_CONNECTIONS.inc()
    
    try:
        response = await call_next(request)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(time.time() - start_time)
        
        return response
    finally:
        ACTIVE_CONNECTIONS.dec()
```

### Distributed Tracing
```python
import opentelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Setup tracing
trace.set_tracer_provider(TracerProvider())

# Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument gRPC server
GrpcInstrumentorServer().instrument()

# Instrument FastAPI app
FastAPIInstrumentor.instrument_app(app)
```

### Logging Configuration
```python
import structlog
import logging
import sys

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Create logger
logger = structlog.get_logger()

# Log example
logger.info(
    "job_submitted",
    job_id=job_id,
    user_id=user_id,
    target_device=target_device,
    program_size=len(program),
    timestamp=datetime.utcnow().isoformat()
)
```

## 🔒 Security

### Security Headers
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from secure import Secure

# Security middleware configuration
secure_headers = Secure()

# Add security headers to responses
@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.framework.fastapi(response)
    return response

# Security headers include:
# - Content-Security-Policy
# - X-Frame-Options: DENY
# - X-Content-Type-Options: nosniff
# - Referrer-Policy: strict-origin-when-cross-origin
# - Permissions-Policy: various restrictions
```

### Input Validation
```python
from pydantic import BaseModel, validator, Field
import re

class SubmitJobRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    program: str = Field(..., min_length=1, max_length=10_000_000)  # 10MB max
    target: str = Field(..., regex=r'^[a-zA-Z0-9_-]+$')
    priority: int = Field(..., ge=1, le=100)
    
    @validator('program')
    def validate_program_size(cls, v):
        if len(v.encode('utf-8')) > 10_000_000:  # 10MB
            raise ValueError('Program too large')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        # Prevent injection attacks
        if re.search(r'[<>"\']', v):
            raise ValueError('Invalid characters in name')
        return v

# Usage in endpoint
@app.post("/api/v1/jobs")
async def submit_job(request: SubmitJobRequest, user: User = Depends(get_current_user)):
    # Request is already validated by Pydantic
    pass
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# Run with coverage
pytest --cov=src --cov-report=html

# Run with specific markers
pytest -m "not slow"
pytest -m "integration"

# Run with Docker
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

### Test Configuration
```yaml
# config/test.yaml
server:
  grpc:
    host: "localhost"
    port: 50051
    max_workers: 1
  
  rest:
    enabled: true
    host: "localhost"
    port: 8081  # Different port for tests
  
  auth:
    enabled: false  # Disable auth for tests
  
  security:
    cors:
      allow_origins: ["*"]
    
    rate_limiting:
      enabled: false
  
  monitoring:
    metrics:
      enabled: false
    
    tracing:
      enabled: false
    
    logging:
      level: "DEBUG"
      format: "console"
  
  cache:
    memory:
      enabled: true
      max_size: 100
      default_ttl: 10
  
  backend_connections:
    kernel:
      grpc_endpoint: "localhost:50052"
      timeout_seconds: 5
    
    compiler:
      grpc_endpoint: "localhost:50053"
      timeout_seconds: 5
```

### Example Tests
```python
import pytest
import grpc
from src.grpc_server.server import EigenGrpcServer
from src.auth.auth_manager import AuthManager
from src.rest_adapter.app import app
from fastapi.testclient import TestClient

class TestSystemAPIServer:
    @pytest.fixture
    async def grpc_server(self):
        """Fixture for test gRPC server"""
        server = EigenGrpcServer(test_config)
        await server.start()
        yield server
        await server.stop()
    
    @pytest.fixture
    def rest_client(self):
        """Fixture for test REST client"""
        return TestClient(app)
    
    @pytest.fixture
    async def auth_token(self, auth_manager):
        """Fixture for test token"""
        return await auth_manager.create_test_token(
            user_id="test-user",
            roles=["user", "tester"]
        )
    
    async def test_submit_job_grpc(self, grpc_server, auth_token):
        """Test job submission via gRPC"""
        async with grpc.aio.insecure_channel(
            f"localhost:{grpc_server.port}"
        ) as channel:
            stub = JobServiceStub(channel)
            
            request = SubmitJobRequest(
                name="test-job",
                program="from eigen import *\nH(0)",
                target="simulator"
            )
            
            metadata = [("authorization", f"Bearer {auth_token}")]
            response = await stub.SubmitJob(request, metadata=metadata)
            
            assert response.job_id is not None
            assert response.status == JobStatus.PENDING
            assert response.created_at is not None
    
    def test_submit_job_rest(self, rest_client):
        """Test job submission via REST"""
        response = rest_client.post(
            "/api/v1/jobs",
            json={
                "name": "test-job",
                "program": "from eigen import *\nH(0)",
                "target": "simulator"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "PENDING"
    
    async def test_rate_limiting(self, grpc_server):
        """Test rate limiting"""
        # Make multiple requests to trigger rate limiting
        for i in range(150):  # More than 100/minute limit
            try:
                await self.make_request(grpc_server)
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.RESOURCE_EXHAUSTED:
                    # Expected error when exceeding limit
                    if i >= 100:
                        return
                raise
        
        assert False, "Rate limiting did not work"
    
    async def test_authentication_failure(self, grpc_server):
        """Test authentication failure"""
        async with grpc.aio.insecure_channel(
            f"localhost:{grpc_server.port}"
        ) as channel:
            stub = JobServiceStub(channel)
            
            request = SubmitJobRequest(
                name="test-job",
                program="from eigen import *\nH(0)",
                target="simulator"
            )
            
            # Try without authentication
            with pytest.raises(grpc.RpcError) as exc_info:
                await stub.SubmitJob(request)
            
            assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED
```

## 🚀 Performance Optimization

### gRPC Optimization
```python
# Optimal gRPC server settings for high performance
GRPC_OPTIMIZATIONS = {
    # Message sizes
    'grpc.max_send_message_length': 100 * 1024 * 1024,  # 100MB
    'grpc.max_receive_message_length': 100 * 1024 * 1024,
    
    # Concurrency
    'grpc.max_concurrent_streams': 1000,
    'grpc.max_connection_idle_ms': 10000,
    'grpc.max_connection_age_ms': 30000,
    'grpc.max_connection_age_grace_ms': 5000,
    
    # Keepalive settings
    'grpc.keepalive_time_ms': 7200000,  # 2 hours
    'grpc.keepalive_timeout_ms': 20000,
    'grpc.keepalive_permit_without_calls': 1,
    'grpc.http2.max_pings_without_data': 0,
    'grpc.http2.min_time_between_pings_ms': 60000,
    'grpc.http2.min_ping_interval_without_data_ms': 300000,
    
    # Buffer sizes
    'grpc.http2.write_buffer_size': 64 * 1024,  # 64KB
    'grpc.http2.max_frame_size': 16384,  # 16KB
}

# Apply optimizations to server
server = grpc.aio.server(
    interceptors=[...],
    options=[(k, v) for k, v in GRPC_OPTIMIZATIONS.items()]
)
```

### Caching Strategy
```python
import redis.asyncio as redis
from functools import lru_cache
from cachetools import TTLCache

class CachingLayer:
    """Caching layer for performance improvement"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.local_cache = TTLCache(maxsize=1000, ttl=60)  # Local cache
    
    async def get_device_list(self, force_refresh=False) -> List[Device]:
        """Get device list with caching"""
        cache_key = "devices:list"
        
        # Check local cache
        if not force_refresh and cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        # Check Redis cache
        cached = await self.redis.get(cache_key)
        if cached and not force_refresh:
            devices = json.loads(cached)
            self.local_cache[cache_key] = devices
            return devices
        
        # Query backend
        devices = await self.backend.get_devices()
        
        # Cache in Redis (TTL 5 minutes)
        await self.redis.setex(
            cache_key,
            300,  # 5 minutes
            json.dumps([d.to_dict() for d in devices])
        )
        
        # Cache in local cache
        self.local_cache[cache_key] = devices
        
        return devices
    
    @lru_cache(maxsize=100)
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Cache user permissions"""
        # This uses Python's built-in LRU cache
        return self._fetch_user_permissions_from_db(user_id)
```

### Connection Pooling
```python
import grpc
from grpc.aio import insecure_channel

class ConnectionPool:
    """gRPC connection pool for backend services"""
    
    def __init__(self, endpoint: str, max_size: int = 10):
        self.endpoint = endpoint
        self.max_size = max_size
        self.pool = []
        self.lock = asyncio.Lock()
    
    async def get_channel(self):
        """Get a channel from the pool"""
        async with self.lock:
            if self.pool:
                return self.pool.pop()
            
            if len(self.pool) < self.max_size:
                channel = insecure_channel(self.endpoint)
                await channel.channel_ready()
                return channel
            
            # Wait for a channel to become available
            return await self._wait_for_channel()
    
    async def return_channel(self, channel):
        """Return a channel to the pool"""
        async with self.lock:
            if len(self.pool) < self.max_size:
                self.pool.append(channel)
            else:
                await channel.close()
    
    async def _wait_for_channel(self):
        """Wait for a channel to become available"""
        # Implementation with asyncio condition
        pass
```

## 📈 Monitoring Dashboard

### Example Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Eigen OS System API",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(eigen_api_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}"
        }]
      },
      {
        "title": "Request Latency (p95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(eigen_api_request_duration_seconds_bucket[5m]))",
          "legendFormat": "{{method}} {{endpoint}}"
        }]
      },
      {
        "title": "Active Connections",
        "targets": [{
          "expr": "eigen_api_active_connections"
        }]
      },
      {
        "title": "Job Submissions",
        "targets": [{
          "expr": "rate(eigen_api_job_submissions_total[5m])",
          "legendFormat": "{{target_device}}"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(eigen_api_requests_total{status_code=~\"5..\"}[5m]) / rate(eigen_api_requests_total[5m])"
        }]
      }
    ]
  }
}
```

## 🔮 Roadmap

### Phase 1: Core Functionality

- ✅ gRPC and REST API interfaces

- ✅ Basic authentication and authorization

- ✅ Job submission and monitoring

- ✅ Device management

- ✅ Circuit compilation

### Phase 2: Production Features

- 🚧 High availability and clustering

- 🚧 Advanced rate limiting

- 🚧 Comprehensive monitoring

- 🚧 Security hardening

- 🚧 Performance optimization

### Phase 3: Advanced Capabilities

- 🔜 GraphQL API support

- 🔜 WebSocket streaming improvements

- 🔜 API versioning and backward compatibility

- 🔜 Advanced caching strategies

- 🔜 Global load balancing

### Phase 4: Future Enhancements

- 🔜 Edge computing support

- 🔜 Quantum network API

- 🔜 Real-time collaboration features

- 🔜 Advanced analytics and insights

- 🔜 AI-powered API optimization

## 🤝 Contributing

We welcome contributions to the System API Server! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/eigen-os/eigen-os.git
cd eigen-os/system-api-server

# Setup development environment
make setup-dev

# Generate protobuf code
make generate-proto

# Run development server
make dev

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

## 📚 Documentation

- [API Reference](https://docs.eigen-os.org/api/reference)

- [Authentication Guide](https://docs.eigenos.org/api/authentication)

- [Deployment Guide](https://docs.eigenos.org/api/deployment)

- [Performance Tuning](https://docs.eigenos.org/api/performance)

- [Security Guidelines](https://docs.eigenos.org/api/security)

## 🐛 Issue Reporting

For bug reports and feature requests, please use our [issue tracker](https://github.com/eigen-os/eigen-os/issues).

## Security Vulnerabilities

Important: For security vulnerabilities, please do **NOT** open public issues. Instead, report them through our [Security Advisory Program](SECURITY.md).

## 📄 License

System API Server is part of Eigen OS and is licensed under the [Apache License 2.0](LICENSE).


**System API Server** — The unified gateway to quantum computing, providing secure, scalable, and performant access to Eigen OS capabilities through modern API standards.
---

## MVP skeleton (Issue #24)

This service currently provides a **minimal** public gRPC surface:
- `JobService`
- `DeviceService`

### Run locally

```bash
cd src/services/system-api
python -m venv .venv
source .venv/bin/activate
pip install -e .

# start server
SYSTEM_API_GRPC_ADDR=0.0.0.0:50051 python -m system_api.main
```

### Run unit tests

```bash
cd src/services/system-api
pip install -e '.[test]'
pytest -q
```
