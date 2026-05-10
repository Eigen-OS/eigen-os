# JobSpec v0.1 (`job.yaml`)

## Summary

`job.yaml` is the canonical MVP-2 submission descriptor consumed by the CLI (`eigen submit -f job.yaml`, `eigen compile -f job.yaml`) and mapped to `SubmitJobRequest`.

Current implementation status is **partially strict**:
- top-level contract keys are validated (`apiVersion`, `kind`, `metadata.name`, `spec.target`),
- submission source is currently **file-backed only** (`program.eigen.py` packaging flow),
- unknown keys are tolerated,
- several RFC/ADR-intended validations are not enforced yet (see [Known gaps](#known-gaps-vs-target-state)).

## Minimal structure

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: <non-empty string>
spec:
  target: <non-empty string>
  # source is resolved from file packaging:
  # - spec.program_path (optional)
  # - default path: program.eigen.py
```

## Field matrix (actual behavior)

| Field | Required | Type | Current rules / behavior |
|---|---|---|---|
| `apiVersion` | yes | string | must be exactly `eigen.os/v0.1` |
| `kind` | yes | string | must be exactly `QuantumJob` |
| `metadata.name` | yes | string | must be non-empty |
| `spec.target` | yes | string | must be non-empty |
| `spec.program` | no | string / block | parser accepts, but mapping rejects inline source (`INVALID_ARGUMENT`) |
| `spec.program_path` | no | string | optional; defaults to `program.eigen.py` when omitted |
| `spec.entrypoint` | no | string | default `main`; must be non-empty when provided |
| `spec.priority` | no | int | default `50`; must be in `[0,100]` |
| `spec.compiler_options` | no | map<string,string> | parsed and forwarded |
| `spec.metadata` | no | map<string,string> | parsed and forwarded (plus injected `source_sha256`) |
| `spec.dependencies` | no | list<string> | parsed and forwarded |
| Unknown keys | n/a | any | ignored (no validation error) |

## Canonical mapping to `SubmitJobRequest`

Mapping path: `job.yaml` → `JobSpec` → `SubmitJobRequest`.

- `metadata.name` → `name`
- `spec.target` → `target`
- `spec.priority` → `priority` (default `50`)
- `spec.compiler_options` → `compiler_options`
- `spec.metadata` → `metadata`
- `spec.dependencies` → `dependencies`
- `spec.program_path` (or default `program.eigen.py`) → file read as `program.eigen_lang_source.source`
- `spec.entrypoint` (or default `main`) → `program.eigen_lang_source.entrypoint`
- `SHA-256(source_bytes)` → `program.eigen_lang_source.sha256`
- additionally injected metadata: `source_sha256=<same sha256>`

## Validation and packaging behavior

Validation happens in two phases.

1. **YAML/spec validation (`parse_and_validate_jobspec`)**
   - checks required keys and enum-like constants,
   - applies defaults (`entrypoint=main`, `priority=50`),
   - validates priority range and non-empty entrypoint.

2. **Packaging/mapping validation (`map_to_submit_job_request_with_packaging`)**
   - rejects inline source (`spec.program`),
   - resolves program path relative to `job.yaml` directory,
   - fails if file does not exist or cannot be read,
   - validates source contains exactly one `@hybrid_program`,
   - validates that `def <entrypoint>(` exists in source.

## Examples

### Recommended file-backed source (default program path)

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-file
spec:
  target: sim:local
  entrypoint: main
```

With this form, `program.eigen.py` is expected next to `job.yaml`.

### File-backed source (custom relative path)

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-custom-path
spec:
  program_path: src/program.eigen.py
  target: sim:local
  entrypoint: run```

### Inline source (currently rejected at mapping stage)

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-inline
spec:
  target: sim:local
program: |
    from eigen_lang import hybrid_program

    @hybrid_program()
    def main():
      return 1
```

This may parse, but submission currently fails with `spec.program inline source is not allowed; use job.yaml + program.eigen.py packaging`.

## Known gaps vs target state

The current implementation is intentionally lightweight and does **not yet** enforce several desired invariants:

1. **Path safety checks are incomplete.**
   - `spec.program_path` is not currently restricted against absolute paths or `..` traversal at parser level.

2. **`spec.program`/`spec.program_path` mutual exclusion is not enforced at parser level.**
   - Inline source is simply rejected later in packaging; mixed-mode diagnostics are not yet explicit.

3. **YAML parser is line-based and permissive.**
   - No schema-level type errors for many malformed shapes (beyond supported extracted fields).

4. **Error field name bug for missing `metadata.name`.**
   - Missing job name currently reports violation field as `kind` instead of `metadata.name`.

5. **No size-limit enforcement in this parser module.**
   - Limits described in architecture/security docs are not implemented directly here.

6. **Entrypoint validation is textual.**
   - It checks substring presence (`def <entrypoint>(`) and one `@hybrid_program`, not full AST-level semantic validation.

These items define the main work needed to fully “freeze” and harden the JobSpec contract.
