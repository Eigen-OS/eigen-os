# neuro-symbolic-service

Internal deployable service for the Neuro-DPDA / Neuro-Symbolic Core advisory boundary.
+
## Contract

- `eigen.internal.v1.NeuroSymbolicService`
- Internal-only access via workload identity metadata
- Deterministic advisory scoring for compilation plans
- Fail-closed behavior when contract, identity, tenant/project scope, or policy evidence is missing

## Run

```bash
export NEURO_SYMBOLIC_INTERNAL_TOKEN=dev-internal-token
export NEURO_SYMBOLIC_ALLOWED_CALLERS=eigen-kernel,eigen-compiler
python -m neuro_symbolic_service.main
```

## Endpoints

- gRPC: `0.0.0.0:50081` by default
- Metrics: `127.0.0.1:50082/metrics`
- Health: `127.0.0.1:50082/healthz`

## Tests

```bash
pytest tests -q
```
