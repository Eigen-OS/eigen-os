# Local deployment (MVP stack)

This directory provides a simple local profile to run the Eigen OS MVP services together

## Services

- `system-api` (`50051`, metrics `9090`)
- `neuro-symbolic-service` (`50081`, metrics `50082`)
- `eigen-kernel` (`50052`)
- `eigen-compiler` (`50071`, metrics `9093`)
- `driver-manager` (`50061`, metrics `9092`)
- `grafana` (`3000`)
- `prometheus` (`9091`)
- `loki` (`3100`, landing page + proxied API)
- `tempo` (`3200`, landing page + proxied API)
- `otel-collector` (OTLP ingest/forwarder on `4317` / `4318`)
- `promtail` (log shipping)

## Start stack

From repository root:

```bash
./deploy/local/dev_env.sh up
```

## Stop stack

```bash
./deploy/local/dev_env.sh down
```

## Observability UI

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9091
- Loki: http://localhost:3100
- Tempo: http://localhost:3200

Grafana is the UI at port `3000`. Loki and Tempo are API services; their host ports now expose a small landing page at `/` so local checks return `200` instead of `404`.

Grafana uses anonymous admin access for local development and provisions the dashboards from `monitoring/dashboards/`.
Traces are wired through OTLP collector → Tempo, while logs are shipped from Docker stdout to Loki through Promtail.

## Configuration

- `local_config.yaml` defines default local endpoints and service wiring.
- `deploy/local/observability/` contains the Grafana, Loki, Tempo, Prometheus and Promtail configs used by the local compose profile.
- Use this profile for smoke checks and local integration validation.
