# driver-manager (MVP skeleton)

Internal gRPC service implementing `eigen.internal.v1.DriverManagerService`.

Implemented in this milestone:

- Service bootstrap and gRPC server.
- `ListDevices` / `GetDeviceStatus` behavior backed by registered drivers.
- `BaseDriver` (`QDriver`) interface with capability handshake and healthcheck.
- In-memory `DriverRegistry` with device-to-driver lookup.
- Qiskit Runtime and AWS Braket adapter hardening baseline with secret-ref auth resolution, timeout/retry policy, and provider error normalization.
- HTTP endpoints: `/metrics` and `/healthz`.

## Run

```bash
python -m driver_manager.main
```

## Local runbook: enable Qiskit Runtime skeleton

```bash
export DRIVER_MANAGER_QISKIT_RUNTIME_ENABLED=true
export DRIVER_MANAGER_QISKIT_RUNTIME_PROVIDER_CONFIG_VERSION=1.0
export DRIVER_MANAGER_QISKIT_RUNTIME_RUNTIME_ISOLATION=process
export DRIVER_MANAGER_QISKIT_RUNTIME_TOKEN_SECRET_REF=ibm/runtime/token
export DRIVER_MANAGER_QISKIT_RUNTIME_TIMEOUT_SEC=30
export DRIVER_MANAGER_QISKIT_RUNTIME_MAX_RETRIES=2
export DRIVER_MANAGER_QISKIT_RUNTIME_RETRY_BACKOFF_SEC=0.25
export DRIVER_MANAGER_SECRETS_JSON='{"ibm/runtime/token":{"value":"<your-token>","state":"issued"}}'
python -m driver_manager.main
curl -s localhost:9092/healthz
```

Lifecycle-aware secret envelope (Stage-9A):

```json
{
  "ibm/runtime/token": {
    "value": "<your-token>",
    "state": "issued",
    "issued_at": "2026-05-20T00:00:00Z",
    "expires_at": "2026-06-20T00:00:00Z"
  },
  "aws/braket/credentials": {
    "value": {"access_key_id": "<id>", "secret_access_key": "<secret>"},
    "state": "rotated",
    "issued_at": "2026-05-01T00:00:00Z",
    "rotated_at": "2026-05-20T00:00:00Z"
  }
}
```

`state=revoked` or expired `expires_at` entries are denied during retrieval and emitted as audit events (`secret_lifecycle_event`).

## Tests

```bash
pytest src/services/driver-manager/tests -q
```

## Local runbook: enable AWS Braket skeleton

```bash
export DRIVER_MANAGER_AWS_BRAKET_ENABLED=true
export DRIVER_MANAGER_AWS_BRAKET_PROVIDER_CONFIG_VERSION=1.0
export DRIVER_MANAGER_AWS_BRAKET_RUNTIME_ISOLATION=process
export DRIVER_MANAGER_AWS_BRAKET_CREDENTIALS_SECRET_REF=aws/braket/credentials
export DRIVER_MANAGER_AWS_BRAKET_REGION='us-east-1'
export DRIVER_MANAGER_AWS_BRAKET_TIMEOUT_SEC=30
export DRIVER_MANAGER_AWS_BRAKET_MAX_RETRIES=2
export DRIVER_MANAGER_AWS_BRAKET_RETRY_BACKOFF_SEC=0.25
export DRIVER_MANAGER_SECRETS_JSON='{"aws/braket/credentials":{"value":{"access_key_id":"<id>","secret_access_key":"<secret>"},"state":"issued"}}'
python -m driver_manager.main
curl -s localhost:9092/healthz
```

Secret-ref mode:

```bash
export DRIVER_MANAGER_AWS_BRAKET_ENABLED=true
export DRIVER_MANAGER_AWS_BRAKET_PROVIDER_CONFIG_VERSION=1.0
export DRIVER_MANAGER_AWS_BRAKET_RUNTIME_ISOLATION=process
export DRIVER_MANAGER_AWS_BRAKET_CREDENTIALS_SECRET_REF=aws/braket/credentials
export DRIVER_MANAGER_SECRETS_JSON='{"aws/braket/credentials":{"value":{"access_key_id":"<id>","secret_access_key":"<secret>"},"state":"issued"}}'{"access_key_id":"<id>","secret_access_key":"<secret>"}}'
python -m driver_manager.main
```
