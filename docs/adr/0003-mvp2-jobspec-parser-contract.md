# ADR 0003: MVP-2 JobSpec parser contract (JobSpec → SubmitJobRequest)

- **Status:** Accepted
- **Date:** 2026-04-24
- **Deciders:** Core architecture maintainers

## Context

MVP-2 requires a deterministic parser/validator that turns `job.yaml` into `SubmitJobRequest` with consistent validation behavior across CLI and services.

## Decision

1. `job.yaml` is parsed into a canonical in-memory representation and then mapped to protobuf `SubmitJobRequest`.
2. Parser validation is mandatory for:
   - `apiVersion`,
   - program path / entrypoint consistency,
   - target device and quantum resource constraints,
   - required submission metadata.
3. Validation failures must map to `INVALID_ARGUMENT` with field-level diagnostics.
4. Fixture-based tests must guarantee deterministic mapping for known inputs.

## Consequences

- Submission behavior becomes stable and testable across environments.
- Regressions are caught via fixture diff tests before merge.
- Downstream services receive normalized requests.

## Related

- MVP-2 plan: `docs/development/mvp-2-compilation-pipeline.md`
- JobSpec reference: `docs/reference/jobspec.md`