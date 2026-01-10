# RFC 0003: JobSpec v0.1 (job.yaml) for eigen-cli submit

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0004,0007

## Summary

Defines the MVP job specification format consumed by eigen-cli and mapped to SubmitJobRequest.

## Motivation

We need a human-editable, stable job spec so users can run the first end-to-end workflow without learning internal protobuf types.

## Goals

- Provide a minimal YAML schema that maps cleanly to SubmitJobRequest.
- Keep extensibility without breaking v0.1 clients.

## Non-Goals

- Full type-safe schema for all algorithm families (Phase 1).
- Workflow orchestration DSL (separate feature).

## Guide-level explanation


### Canonical user source packaging (MVP)

MVP defines a single canonical way to submit Eigen‑Lang:

- `program.eigen.py` — Eigen‑Lang source file (Python DSL)
- `job.yaml` — JobSpec describing runtime settings and input references

Recommended JobSpec additions for clarity (v0.1, optional fields):
- `spec.program_path` (default: `program.eigen.py`)
- `spec.entrypoint` (required for server-side compilation; the `@hybrid_program` function name)
- `spec.program_sha256` (optional; CLI can compute for determinism)
- `spec.inputs` (map of small constants) and `spec.input_refs` (URI refs to datasets/artifacts)

This JobSpec is mapped to `SubmitJobRequest.program` (oneof) and is fully specified in RFC 0011.

A minimal job file:

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-h2
  labels:
    example: "true"
spec:
  program: |
    # Eigen-Lang source
    @hybrid_program
    def main():
        ...
  target: sim:local
  priority: 50
  compiler_options:
    optimization_level: "1"
  metadata:
    shots: "1024"
    max_iters: "50"
```

CLI rules:
- `spec.program` is sent as `SubmitJobRequest.program`.
- `spec.target` → `SubmitJobRequest.target`.
- `spec.priority` → `SubmitJobRequest.priority`.
- `spec.compiler_options` → `SubmitJobRequest.compiler_options` (string map).
- `metadata` is a free-form string map for MVP; Phase 1 formalizes typed fields.

## Reference-level design

### Interfaces / APIs

Mapped to `JobService.SubmitJob(SubmitJobRequest)` as defined in RFC 0004.

### Data model

**Top-level:** `apiVersion`, `kind`, `metadata`, `spec`.
**metadata:** `name` (required), optional `labels`, `annotations`.
**spec:** `program` (required), `target` (required), optional `priority`, `compiler_options`, `metadata`, `dependencies`.

Compatibility: unknown keys MUST be ignored by v0.1 readers.

### Error model

CLI schema errors are local and must be user-friendly.
Server-side validation errors return INVALID_ARGUMENT with details.

### Security & privacy

No secrets in job.yaml. If credentials needed, they are provided via env/config, not JobSpec.

### Observability

CLI emits local logs. system-api/kernel emit job_id and trace_id for all stages.

### Performance notes

YAML parsing cost is negligible vs compilation/execution.

## Testing plan

Golden tests for YAML → SubmitJobRequest mapping; include unknown keys tolerance tests.

## Rollout / Migration

v0.1 job spec is frozen for MVP. Any breaking change requires new apiVersion (v0.2 or v1.0).

## Alternatives considered

- JSON-only (rejected): YAML is more user-friendly.
- Embedding protobuf as input (rejected): too low-level for MVP.

## Open questions

- Do we want an explicit `shots` field in v0.2 (typed) instead of metadata?
- Should `program` accept file path references?
