# driver-manager (MVP skeleton)

Internal gRPC service implementing `eigen.internal.v1.DriverManagerService`.

Implemented in this milestone:

- Service bootstrap and gRPC server.
- `ListDevices` / `GetDeviceStatus` behavior backed by registered drivers.
- `BaseDriver` (`QDriver`) interface with capability handshake and healthcheck.
- In-memory `DriverRegistry` with device-to-driver lookup.
- Qiskit Runtime adapter hardening baseline with auth resolution, timeout/retry policy, and provider error normalization.
- HTTP endpoints: `/metrics` and `/healthz`.

## Run

```bash
python -m driver_manager.main
```

## Local runbook: enable Qiskit Runtime skeleton

```bash
export DRIVER_MANAGER_QISKIT_RUNTIME_ENABLED=true
export DRIVER_MANAGER_QISKIT_RUNTIME_TOKEN_ENV=IBM_RUNTIME_TOKEN
export DRIVER_MANAGER_QISKIT_RUNTIME_TIMEOUT_SEC=30
export DRIVER_MANAGER_QISKIT_RUNTIME_MAX_RETRIES=2
export DRIVER_MANAGER_QISKIT_RUNTIME_RETRY_BACKOFF_SEC=0.25
export IBM_RUNTIME_TOKEN='<your-token>'
python -m driver_manager.main
curl -s localhost:9092/healthz
```

Secret-ref mode (useful for local secret sync):

```bash
export DRIVER_MANAGER_QISKIT_RUNTIME_ENABLED=true
export DRIVER_MANAGER_QISKIT_RUNTIME_TOKEN_SECRET_REF='ibm/runtime/token'
export DRIVER_MANAGER_SECRETS_JSON='{"ibm/runtime/token":"<your-token>"}'
python -m driver_manager.main
```

## Tests

```bash
pytest src/services/driver-manager/tests -q
```

## Local runbook: enable AWS Braket skeleton

```bash
export DRIVER_MANAGER_AWS_BRAKET_ENABLED=true
export DRIVER_MANAGER_AWS_BRAKET_ACCESS_KEY_ID='<access-key-id>'
export DRIVER_MANAGER_AWS_BRAKET_SECRET_ACCESS_KEY='<secret-access-key>'
export DRIVER_MANAGER_AWS_BRAKET_REGION='us-east-1'
export DRIVER_MANAGER_AWS_BRAKET_TIMEOUT_SEC=30
export DRIVER_MANAGER_AWS_BRAKET_MAX_RETRIES=2
export DRIVER_MANAGER_AWS_BRAKET_RETRY_BACKOFF_SEC=0.25
python -m driver_manager.main
curl -s localhost:9092/healthz
```

Secret-ref mode:

```bash
export DRIVER_MANAGER_AWS_BRAKET_ENABLED=true
export DRIVER_MANAGER_AWS_BRAKET_CREDENTIALS_SECRET_REF='aws/braket/credentials'
export DRIVER_MANAGER_SECRETS_JSON='{"aws/braket/credentials":{"access_key_id":"<id>","secret_access_key":"<secret>"}}'
python -m driver_manager.main
```
