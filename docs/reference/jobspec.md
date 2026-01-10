# JobSpec v0.1 (job.yaml)

## Summary

Defines the MVP job specification format consumed by `eigen‑cli submit` and mapped to `SubmitJobRequest`. It is a human‑editable YAML file that describes runtime settings, target devices, and input references.

## Motivation

We need a stable, human‑editable job spec so users can run the first end‑to‑end workflow without learning internal protobuf types.

## Goals

- Provide a minimal YAML schema that maps cleanly to `SubmitJobRequest`

- Keep extensibility without breaking v0.1 clients

- Support one canonical source packaging method for Eigen‑Lang

## Non‑Goals

- Full type‑safe schema for all algorithm families (Phase 1)

- Workflow orchestration DSL (separate feature)

## Guide‑level explanation

### Canonical user source packaging (MVP)

MVP defines a single canonical way to submit Eigen‑Lang:

- `program.eigen.py` — Eigen‑Lang source file (Python DSL)

- `job.yaml` — JobSpec describing runtime settings and input references

### JobSpec fields (v0.1)

| **Field** | **Required** | **Type** | **Description** |
|-------------------|-------------------|-------------------|-------------------|
| `apiVersion` | Yes | string | Must be `eigen.os/v0.1` |
| `kind` | Yes | string | Must be `QuantumJob` |
| `metadata.name` | Yes | string | Job name (unique within user scope) |
| `metadata.labels` | No | map<string,string> | Arbitrary labels for filtering |
| `metadata.annotations` | No | map<string,string> | Non‑identifying metadata |
| `spec.program` | Yes | string | Inline Eigen‑Lang source (or reference) |
| `spec.target` | Yes | string | Device target, e.g., `sim:local` |
| `spec.priority` | No | int32 | Priority (0–100, default 50) |
| `spec.compiler_options` | No | map<string,string> | Compiler flags, e.g., `optimization_level: "1"` |
| `spec.metadata` | No | map<string,string> | Free‑form runtime settings (e.g., `shots: "1024"`) |
| `spec.dependencies` | No | list<string> | URIs of input datasets/artifacts |

**Note**: `spec.program` can be either:

- An inline string of Eigen‑Lang source

- A file reference (future extension)

## Example: minimal job.yaml
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
        q = allocate_qubits(2)
        h(q[0])
        cnot(q[0], q[1])
        m = measure(q)
        return m
  target: sim:local
  priority: 50
  compiler_options:
    optimization_level: "1"
  metadata:
    shots: "1024"
    max_iters: "50"
```

## Example: with external source and input references
```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: qaoa-maxcut
spec:
  program_path: program.eigen.py  # optional, default is program.eigen.py
  entrypoint: qaoa_circuit        # required if multiple @hybrid_program functions
  target: ibmq:quito
  dependencies:
    - s3://my-bucket/data/hamiltonian.json
    - https://example.org/params.bin
  metadata:
    shots: "5000"
    p: "4"
```

## Mapping to SubmitJobRequest

`eigen‑cli` maps the YAML fields as follows:

- `spec.program` → `SubmitJobRequest.program` (oneof `eigen_lang_source`)

- `spec.target` → `SubmitJobRequest.target`

- `spec.priority` → `SubmitJobRequest.priority`

- `spec.compiler_options` → `SubmitJobRequest.compiler_options`

- `spec.metadata` → `SubmitJobRequest.metadata`

- `spec.dependencies` → `SubmitJobRequest.dependencies`

## Reference‑level design

### Data model

**Top‑level structure:**
```yaml
apiVersion: string
kind: string
metadata:
  name: string
  labels?: map<string,string>
  annotations?: map<string,string>
spec:
  program: string                # required
  target: string                 # required
  priority?: int32
  compiler_options?: map<string,string>
  metadata?: map<string,string>
  dependencies?: list<string>
```

**Compatibility**: Unknown keys MUST be ignored by v0.1 readers.

### Error model

- **CLI schema errors**: Local validation, user‑friendly messages, exit code 2

- **Server‑side validation errors**: Return gRPC status `INVALID_ARGUMENT` with structured details

### Security & privacy

No secrets should be placed in `job.yaml`. Credentials are provided via environment variables or CLI configuration.

## Observability

- CLI logs the `job_id` and `trace_id` when available

- System‑API and Kernel emit logs with `job_id` and `trace_id` for all stages

## Performance notes

YAML parsing cost is negligible compared to compilation and execution.

## Testing plan

Golden tests for YAML → `SubmitJobRequest` mapping, including tolerance for unknown keys.

## Rollout / Migration

- v0.1 job spec is frozen for MVP

- Any breaking change requires a new `apiVersion` (v0.2 or v1.0)

- Backward‑compatible extensions (new optional fields) are allowed

## Alternatives considered

- **JSON‑only**: Rejected—YAML is more user‑friendly for multi‑line source code

- **Embedding protobuf directly**: Rejected—too low‑level for MVP

## Open questions

- Should `shots` become a typed top‑level field in v0.2?

- Should `program` support file references in v0.1 or wait for v0.2?

---

**References:**

    RFC 0004: Public gRPC API v0.1 (SubmitJobRequest mapping)

    RFC 0011: Eigen‑Lang submission format (program.eigen.py + job.yaml packaging)