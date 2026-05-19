# Eigen OS Web Dashboard Skeleton (Phase-8D / P8D-06)

> **Non-GA Surface**
>
> This dashboard is a bootstrap skeleton for ecosystem onboarding only. It is not GA and must be treated as a preview interface.

## Purpose

Provide a minimal web surface for:

- job lifecycle visibility (`SUBMITTED -> RUNNING -> SUCCEEDED|FAILED|CANCELLED`),
- status polling against System API parity routes,
- execution target visibility (simulator/provider profile).

## Contract alignment

This skeleton intentionally maps to existing System API parity constraints:

- `POST /jobs/submit`
- `GET /jobs/{job_id}/status`
- `GET /jobs/{job_id}/results`
- `POST /jobs/{job_id}/cancel`

No new stable payload fields are introduced by the skeleton.

## Simulator walkthrough

1. Start local stack (`deploy/local/dev_env.sh`).
2. Submit `examples/basic/hello_quantum/program.eigen` through existing CLI or REST.
3. Use dashboard skeleton views to render:
   - submission receipt (`job_id`, `trace_id` when present),
   - lifecycle timeline,
   - results summary + target metadata.

Reference walkthrough: `docs/howto/surfaces-dashboard-simulator-walkthrough.md`.
