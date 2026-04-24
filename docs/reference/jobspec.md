# JobSpec v0.1 (`job.yaml`)

## Summary

`job.yaml` is the MVP-2 input format used by CLI and System API to build canonical `SubmitJobRequest`.

## Required structure

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: <non-empty string>
spec:
  target: <non-empty string>
  # source definition (choose one):
  # - spec.program: inline source
  # - spec.program_path: relative path (defaults to program.eigen.py when omitted)
```

## Field matrix

| Field | Required | Type | Rules |
|---|---|---|---|
| `apiVersion` | yes | string | must be `eigen.os/v0.1` |
| `kind` | yes | string | must be `QuantumJob` |
| `metadata.name` | yes | string | non-empty |
| `spec.target` | yes | string | non-empty |
| `spec.program` | conditional | string | inline source, cannot be set with `spec.program_path` |
| `spec.program_path` | conditional | string | safe relative path only; default `program.eigen.py` |
| `spec.entrypoint` | no | string | default `main`, must be non-empty when set |
| `spec.priority` | no | int | range `[0,100]`, default `50` |
| `spec.compiler_options` | no | map<string,string> | optional |
| `spec.metadata` | no | map<string,string> | optional |
| `spec.dependencies` | no | list<string> | optional |


## Canonical mapping to `SubmitJobRequest`

- `metadata.name` → `name`
- `spec.target` → `target`
- `spec.priority` → `priority` (default 50)
- `spec.compiler_options` → `compiler_options`
- `spec.metadata` → `metadata` (merged with internal `jobspec_yaml` snapshot)
- `spec.dependencies` → `dependencies`
- `spec.program` or resolved `spec.program_path` → `eigen_lang.source`
- `spec.entrypoint` (or default) → `eigen_lang.entrypoint`
- SHA-256 of source bytes → `eigen_lang.sha256`

Unknown keys are ignored in v0.1.

## Security and validation rules

- Absolute paths and path traversal (`..`) are rejected for `spec.program_path`.
- `spec.program` and `spec.program_path` cannot be set together.
- Parsed `job.yaml` and source are size-limited by runtime security config.
- Validation failures return `INVALID_ARGUMENT` with field-level violations.

## Examples

### Inline program source

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-inline
spec:
  program: |
    from eigen_lang import hybrid_program

    @hybrid_program()
    def main():
        return 1
  target: sim:local
  entrypoint: main
  priority: 50
  metadata:
    shots: "1024"
```

### File-backed source

```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-file
spec:
  program_path: program.eigen.py
  entrypoint: run
  target: sim:local
```
