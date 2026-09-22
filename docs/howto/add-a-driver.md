# How to add a driver

## When to use

Use this runbook when you need to add a new backend to `driver-manager` via the plugin interface.

## Prerequisites

- Python 3.12+ is installed locally.
- The `driver-manager` service dev environment and dependencies are set up.
- The backend authentication type (token/env/secret reference) is known.

## Instructions

1. Implement the driver class in `src/services/driver-manager/src/driver_manager/` based on `BaseDriver`:
   - `initialize(config)`
   - `capability_handshake()`
   - `healthcheck()`
   - `get_devices()`
   - `execute_circuit(...)`
2. Register the driver in bootstrap (`grpc_server.py`) and add the env config.
3. Add smoke tests and initialization tests.
4. Start the service and check `/healthz`: the driver should return `ready=true`, and `capabilities` — should contain the version and handshake features.

## Verification (Qiskit Runtime skeleton)

```bash
export DRIVER_MANAGER_QISKIT_RUNTIME_ENABLED=true
export DRIVER_MANAGER_QISKIT_RUNTIME_TOKEN_ENV=IBM_RUNTIME_TOKEN
export IBM_RUNTIME_TOKEN='<your-token>'
python -m driver_manager.main
curl -s localhost:9092/healthz | jq
pytest src/services/driver-manager/tests/test_qiskit_runtime_driver.py -q
```
