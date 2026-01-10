# RFC 0010: eigen-cli MVP: commands, config, UX contracts

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0003,0004

## Summary

Defines CLI command surface for Phase 0 and the UX contract (inputs, outputs, exit codes).

## Motivation

CLI is the first developer touchpoint and the Phase 0 success criterion depends on it.

## Goals

- Specify required commands: submit/status/compile/visualize.
- Define config file and endpoint discovery.
- Define machine-readable outputs for scripting.

## Non-Goals

- Full TUI.
- Advanced batch orchestration.

## Guide-level explanation

Commands:
- `eigen-cli submit --job job.yaml [--watch]`
- `eigen-cli status <job_id> [--json]`
- `eigen-cli result <job_id> [--json]`
- `eigen-cli compile --job job.yaml --out compiled.aqo.json`
- `eigen-cli visualize --job job.yaml --out dag.svg`

**Important:** The `compile` command performs **local compilation** using the Eigen compiler library. It does not make a call to the System API. This allows users to validate and debug circuit compilation without submitting a job.

Config (default): `~/.config/eigen/config.toml`:
- system_api_endpoint
- timeouts
- auth token source.
Exit codes: 0 success, 2 user error, 3 network error, 4 server error.

## Reference-level design

### Interfaces / APIs

CLI uses public gRPC API (RFC 0004).

### Data model

CLI maps JobSpec YAML (RFC 0003) into SubmitJobRequest.

### Error model

CLI must surface gRPC errors with human-readable hints and optional `--verbose` details.

### Security & privacy

Tokens are read from env/config; never printed; redact in logs.

### Observability

CLI logs include `job_id` and `trace_id` if returned. `--debug` enables verbose logging.

### Performance notes

CLI should stream updates rather than poll when `--watch` is enabled.

## Testing plan

CLI golden tests for parsing and output formatting; integration tests against local docker stack.

## Rollout / Migration

Freeze command names for MVP; add new flags compatibly.

## Alternatives considered

- Python-only CLI (postponed: Rust CLI aligns with kernel ecosystem).

## Open questions

- Do we support `--program file.eigen.py` in addition to job.yaml?
- Default output formats for results?
