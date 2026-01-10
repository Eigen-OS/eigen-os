# System API

- Phase: MVP

## Responsibility

The **System API** is the **sole public ingress** for Eigen OS in MVP. It provides:

1. **Public gRPC & REST Interfaces**: Exposes the core Job and Device services to clients.

2. **Authentication & Authorization**: Validates API keys/tokens and enforces role-based access control (RBAC).

3. **Request Validation & Sanitization**: Validates incoming JobSpecs and input payloads for safety and correctness.

4. **Protocol Translation & Forwarding**: Converts public requests to internal gRPC calls (to Kernel, Compiler) and streams/polls for results.

5. **Observability Boundary**: Collects metrics, logs, and traces for all client interactions.

6. **Security Context Propagation**: Injects authenticated user identity (`x-eigen-sub`, `x-eigen-roles`) into all downstream internal calls.

## Interfaces

### Public gRPC API (proto/eigen_api/v1/service.proto)

- **JobService**: `SubmitJob`, `GetJobStatus`, `CancelJob`, `StreamJobUpdates`, `GetJobResults`

- **DeviceService**: `ListDevices`, `GetDeviceDetails`, `GetDeviceStatus`, `ReserveDevice`

- **CompilationService**: `CompileCircuit`, `OptimizeCircuit`, `ValidateCircuit` (*optional in MVP; may be internal-only*)

### Public REST API (Optional, via FastAPI/Flask adapter)

- **Endpoints**: `/api/v1/jobs`, `/api/v1/devices`

- **Content-Type**: JSON

- **Adapter**: Translates REST ↔ gRPC using generated converters.

### Internal gRPC Clients

- **Kernel Gateway**: Internal service defined in RFC 0004 Appendix A (`KernelGateway.EnqueueJob`, etc.)

- **Compiler Service**: Direct calls to `eigen-compiler` for compilation requests.

- **Metrics Endpoint**: `/metrics` (Prometheus format) for scraping.

### Configuration File (`config/server.yaml`)

- Defines server ports, auth providers, rate limits, backend connection endpoints.

## Inputs / Outputs

| **Input** | **Source** | **Description** |
|-------------------|-------------------|-------------------|
| Client gRPC/REST Request | External client | Job submission, status queries, device reservations. |
| API Key / JWT Token | HTTP/gRPC Header | Provided via `Authorization` header. |
| JobSpec (YAML/JSON) | Client payload | Validated and forwarded to Kernel. |
| Security Context | Internal (from Auth) | User ID, roles, tenant for downstream propagation. |

---

| **Output** | **Destination** | **Description** |
|-------------------|-------------------|-------------------|
| gRPC/REST Response | Client | Job ID, status, results, or error. |
| Internal gRPC Request | Kernel/Compiler / stdout | Translated and enriched client request. |
| Security Metadata | gRPC Headers | `x-eigen-sub`, `x-eigen-roles`, `traceparent` |
| Metrics & Logs | Prometheus/Log Aggregator | Request counts, latency, errors, audit trails. |

## Storage / State

- **API Key / Token Cache**: In-memory cache (e.g., Redis) for validated tokens (optional, TTL-based).

- **Rate Limit Counters**: Stored in-memory or Redis for request throttling.

- **Device List Cache**: Short-lived cache (seconds) for `ListDevices` responses to reduce load on Kernel/Driver Manager.

- **No Persistent State**: System API is stateless; all job/device state is maintained by Kernel and QFS.

## Failure Modes

| **Failure** | **Detection** | **Mitigation** |
|-------------------|-------------------|-------------------|
| Invalid/Malformed Request | Input validation | Return `INVALID_ARGUMENT` (gRPC status `3`) with details. |
| Authentication Failure | Auth interceptor | Return `UNAUTHENTICATED` (gRPC status `16`). |
| Authorization Failure | RBAC check | Return `PERMISSION_DENIED` (gRPC status `7`). |
| Kernel/Compiler Unavailable | Health check / gRPC timeout | Return `UNAVAILABLE` (gRPC status `14`); retry logic (if applicable). |
| Rate Limit Exceeded | Rate limiter | Return `RESOURCE_EXHAUSTED` (gRPC status `8`) with retry-after hint. |
| Payload Too Large | Request size check | Reject with `INVALID_ARGUMENT` before processing. |

## Observability

### Metrics (Prometheus)

- `eigen_api_requests_total{method,endpoint,status}`

- `eigen_api_request_duration_seconds{method,endpoint}`

- `eigen_api_active_requests`

- `eigen_api_authentication_failures_total{reason}`

- `eigen_api_rate_limit_exceeded_total`

### Logs (Structured JSON)
```json
{
  "timestamp": "2026-01-10T10:30:00Z",
  "level": "INFO",
  "service": "system-api",
  "trace_id": "abc123",
  "span_id": "def456",
  "method": "SubmitJob",
  "endpoint": "/eigen_api.v1.JobService/SubmitJob",
  "user": "user@example.com",
  "job_id": "job-xyz",
  "duration_ms": 150,
  "status_code": "OK"
}
```

### Traces (OpenTelemetry/W3C TraceContext)

- Injects/extracts `traceparent` header in all gRPC/REST requests.

- Spans cover: request handling, auth, validation, forwarding, response.

---

## Implementation Notes for MVP

1. **gRPC Server**: Primary interface. Use async gRPC (grpc.aio) with interceptors for auth, logging, metrics.

2. **REST Adapter**: Optional but recommended for ease of testing. Use FastAPI with auto-generated OpenAPI docs.

3. **Authentication**: Simple API-key validation (symmetric tokens) or JWT. OIDC is post-MVP.

4. **Authorization**: Static RBAC roles (`admin`, `user`, `readonly`) defined in configuration.

5. **Streaming**: `StreamJobUpdates` is implemented via polling Kernel (as per RFC 0004) to keep Kernel simple.

6. **Error Handling**: All errors mapped to standard gRPC status codes; structured details in `google.rpc.Status`.

7. **Configuration**: YAML-based; environment variables for secrets (API keys, JWT secret).

8. **Deployment**: Single container; scaled horizontally via load balancer if needed.