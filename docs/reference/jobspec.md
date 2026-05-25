# JobSpec v1.0 (job.yaml)

**Status:** Stable public submission contract for Eigen OS workloads.

`job.yaml` is the canonical declarative workload descriptor used across:

- CLI submission,
- SDK orchestration,
- CI/CD pipelines,
- distributed runtime scheduling,
- benchmark execution,
- hybrid quantum/classical execution,
- cluster orchestration,
- replay/reproducibility flows.

This document defines the normative JobSpec contract for Eigen OS `1.x`.

---

## 1. Purpose

JobSpec standardizes how workloads are:

- declared,
- packaged,
- validated,
- compiled,
- scheduled,
- executed,
- observed,
- reproduced,
- audited.

The contract is designed to support:

- local execution,
- cluster execution,
- hybrid workloads,
- distributed runtime execution,
- multi-backend scheduling,
- deterministic replay,
- explainability,
- secure artifact handling,
- policy-aware orchestration.

---

## 2. Contract Version

### API Version

```yaml
apiVersion: eigen.os/v1
```

### Resource Kind

```yaml
kind: QuantumJob
```

Future compatible kinds MAY include:

```yaml
HybridWorkflow
DistributedJob
BenchmarkJob
PipelineJob
```

---

## 3. Core Design Principles

### 3.1 Declarative Execution

JobSpec describes desired execution state, not execution procedure.

### 3.2 Deterministic Packaging

Equivalent source inputs MUST produce identical packaging artifacts and hashes.

### 3.3 Portable Runtime Semantics

JobSpecs MUST behave consistently across:

- local runtime,
- cluster runtime,
- cloud execution,
- replay environments.

### 3.4 Secure-by-Default

Unsafe path traversal, unbounded inline artifacts, and ambiguous execution behavior are prohibited.

### 3.5 Reproducibility

JobSpecs MUST contain sufficient metadata for deterministic replay and auditability.

---

## 4. Minimal Valid JobSpec

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  name: quantum-vqe-example

spec:
  target: sim:local

  program:
    path: program.eigen.py
```

---

## 5. Top-Level Structure

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  ...

spec:
  ...

runtime:
  ...

resources:
  ...

scheduling:
  ...

observability:
  ...

security:
  ...

artifacts:
  ...
```

---

## 6. Field Matrix

| **Field** | **Required** | **Type** | **Description** |
|-------------------|-------------------|-------------------|-------------------|
| `apiVersion` | yes | string | API contract version |
| `kind` | yes | string | Resource type |
| `metadata` | yes | object | Object metadata |
| `metadata.name` | yes | string | Stable workload identifier |
| `metadata.labels` | no | map<string,string> | Bounded labels |
| `metadata.annotations` | no | map<string,string> | Non-indexed metadata |
| `spec` | yes | object | Execution specification |
| `spec.target` | yes | string | Execution target |
| `spec.program` | yes | object | Program source definition |
| `runtime` | no | object | Runtime behavior |
| `resources` | no | object | Resource requirements |
| `scheduling` | no | object | Scheduling constraints |
| `observability` | no | object | Telemetry configuration |
| `security` | no | object | Security restrictions |
| `artifacts` | no | object | Artifact persistence rules |

---

## 7. Metadata Section

### Structure

```yaml
metadata:
  name: quantum-vqe
  labels:
    workload: research
    environment: staging

  annotations:
    owner: runtime-team
```

---

`metadata.name`

### Requirements

- MUST be non-empty
- MUST be deterministic
- MUST match regex:

```text
^[a-zA-Z0-9._-]{1,128}$
```

### MUST NOT contain

- whitespace,
- control characters,
- path separators,
- unicode normalization ambiguities.

---

`metadata.labels`

Labels are indexed metadata.

### Constraints

- bounded cardinality,
- max key length: 64,
- max value length: 128.

Reserved prefixes:

```text
eigen.os/
runtime.eigen.os/
scheduler.eigen.os/
```

---

`metadata.annotations`

Non-indexed metadata.

May contain:

- provenance,
- CI build info,
- external references,
- experiment descriptions.

---

## 8. Spec Section

### 8.1 Target

```yaml
spec:
  target: sim:local
```

---

### Supported Target Classes

#### Local Simulator

```yaml
sim:local
```

#### Distributed Runtime

```yaml
cluster:auto
cluster:gpu
cluster:quantum
```

#### Backend Alias

```yaml
ibm:qpu
aws:braket
azure:quantum
```

#### Policy-Based Runtime Routing

```yaml
runtime:auto
runtime:latency
runtime:cost
runtime:availability
```

---

### 8.2 Program Definition

#### File-Based Program

```yaml
spec:
  program:
    path: src/program.eigen.py
    entrypoint: main
```

---

#### Inline Program

```yaml
spec:
  program:
    inline: |
      from eigen import hybrid_program

      @hybrid_program()
      def main():
          return 1
```

---

#### Remote Artifact Program

```yaml
spec:
  program:
    uri: qfs://artifacts/programs/vqe.py
```

---

#### Program Rules

Exactly ONE source type is allowed:

- `path`
- `inline`
- `uri`

Mutual exclusivity is mandatory.

---

#### Entrypoint

```yaml
entrypoint: main
```

#### Default

```yaml
main
```

#### Constraints

- MUST be a valid identifier,
- MUST exist in source,
- MUST reference exactly one executable hybrid entrypoint.

---

### 8.3 Compiler Configuration

```yaml
spec:
  compiler:
    optimization_level: 2
    target_profile: balanced

    defines:
      ENABLE_FUSION: "true"
```

---

#### Supported Optimization Levels

```yaml
0
1
2
3
```

---

#### Supported Profiles

```yaml
balanced
latency
deterministic
debug
aggressive
```

---

### 8.4 Dependencies

```yaml
spec:
  dependencies:
    - numpy==2.0.0
    - scipy==1.15.0
```

#### Dependency Constraints

- MUST be deterministic,
- SHOULD pin versions,
- MAY be validated against allowlists.

---

### 8.5 Parameters

```yaml
spec:
  parameters:
    shots: 1000
    learning_rate: 0.01
```

---

## 9. Runtime Section

```yaml
runtime:
  mode: distributed

  retry:
    max_attempts: 3
    backoff: exponential

  timeout:
    execution_seconds: 3600
```

---

### 9.1 Runtime Modes

```yaml
local
distributed
hybrid
benchmark
replay
```

---

### 9.2 Retry Policy

```yaml
retry:
  max_attempts: 3
  backoff: exponential
```

---

#### Allowed Backoff Policies

```yaml
fixed
linear
exponential
```

---

### 9.3 Timeout Policy

```yaml
timeout:
  queue_seconds: 600
  execution_seconds: 3600
  result_seconds: 300
```

---

## 10. Resources Section

```yaml
resources:
  cpu: 8
  memory_mb: 16384

  gpu:
    count: 1

  quantum:
    qubits: 32
```

---

### 10.1 CPU and Memory

| **Field** | **Type** |
|---|---|
| `cpu` | integer |
| `memory_mb` | integer |

---

### 10.2 GPU Resources

```yaml
gpu:
  count: 2
```

---

### 10.3 Quantum Resources

```yaml
quantum:
  qubits: 64
```

---

## 11. Scheduling Section

```yaml
scheduling:
  priority: 50

  policy:
    mode: balanced

  affinity:
    region: us-east
```

---

### 11.1 Priority

Range:

```text
0-100
```

Default:

```text
50
```

---

### 11.2 Policy Modes

```yaml
balanced
latency
cost
availability
deterministic
compliance
```

---

### 11.3 Affinity Rules

```yaml
affinity:
  region: us-east
  accelerator: gpu
```

---

## 12. Observability Section

```yaml
observability:
  tracing: true
  metrics: true
  explainability_level: L2_OPERATOR
```

#### Explainability Levels

```yaml
L1_USER
L2_OPERATOR
L3_FORENSIC
```

---

## 13. Security Section

```yaml
security:
  sandbox: strict

  filesystem:
    readonly: true

  network:
    mode: disabled
```

---

### 13.1 Sandbox Modes

```yaml
disabled
standard
strict
```

---

### 13.2 Filesystem Policy

```yaml
filesystem:
  readonly: true
```

---

### 13.3 Network Policy

```yaml
network:
  mode: disabled
```

Allowed values:

```yaml
disabled
restricted
enabled
```

---

## 14. Artifacts Section

```yaml
artifacts:
  persist_results: true

  retention:
    days: 30
```

---

### 14.1 Artifact Persistence

Controls durable storage of:

- execution results,
- traces,
- explain artifacts,
- benchmark outputs,
- runtime telemetry snapshots.

---

## 15. Canonical Mapping to `SubmitJobRequest`

### Mapping Pipeline

```text
job.yaml
  → JobSpec
  → Canonical Manifest
  → Packaging
  → SubmitJobRequest
```

### Canonical Mapping

| **JobSpec** | **SubmitJobRequest** |
|---|---|
| `metadata.name` | `name` |
| `spec.target` | `target` |
| `spec.program.*` | `program` |
| `scheduling.priority` | `priority` |
| `runtime.timeout.*` | `timeouts` |
| `resources.*` | `resource_requirements` |
| `observability.*` | `telemetry_policy` |

---

## 16. Packaging Rules

### Deterministic Packaging

Packaging MUST:

- normalize paths,
- normalize line endings,
- preserve encoding,
- preserve stable hashing behavior.

### Hashing

Program source MUST generate:

```text
SHA-256(source_bytes)
```

Stored in:

```yaml
metadata:
  source_sha256: ...
```

### Path Rules

#### Allowed

- relative paths,
- repository-local paths.

#### Forbidden

- absolute paths,
- `..` traversal,
- symlink escape outside workspace,
- device paths.

---

## 17. Validation Rules

Validation occurs in multiple phases.

### 17.1 Schema Validation

Checks:

- required fields,
- field types,
- enums,
- ranges,
- regex constraints.

---

### 17.2 Packaging Validation

Checks:

- source existence,
- hash determinism,
- path safety,
- artifact accessibility.

---

### 17.3 Semantic Validation

Checks:

- entrypoint existence,
- hybrid program validity,
- dependency consistency,
- runtime compatibility.

---

### 17.4 Security Validation

Checks:

- sandbox policy,
- forbidden imports,
- unsafe capabilities,
- artifact policy violations.

---

## 18. Example: Minimal Local Job

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  name: hello-world

spec:
  target: sim:local

  program:
    path: program.eigen.py
```

---

## 19. Example: Distributed Runtime Job

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  name: distributed-vqe

spec:
  target: cluster:auto

  program:
    path: src/vqe.py
    entrypoint: run

runtime:
  mode: distributed

resources:
  cpu: 16
  memory_mb: 32768

scheduling:
  priority: 80

observability:
  tracing: true
  explainability_level: L2_OPERATOR
```

---

## 20. Example: Inline Program Job

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  name: inline-demo

spec:
  target: sim:local

  program:
    inline: |
      from eigen import hybrid_program

      @hybrid_program()
      def main():
          return 42
```

---

## 21. Error Semantics

Validation failures MUST use:

```text
INVALID_ARGUMENT
```

State-dependent failures MUST use:

```text
FAILED_PRECONDITION
```

Security violations MAY use:

```text
PERMISSION_DENIED
```

Oversized artifacts MAY use:

```text
RESOURCE_EXHAUSTED
```

---

## 22. Compatibility Guarantees

The following are stable public contract surfaces:

- field names,
- semantic meanings,
- validation rules,
- packaging semantics,
- hash generation rules,
- target resolution behavior.

---

## 23. Migration Notes

### From v0.1

#### Changes

- structured `program` section,
- inline source officially supported,
- security section added,
- runtime section added,
- observability section added,
- deterministic validation rules formalized,
- path safety enforcement added.

---

## 24. Closure Criteria

The JobSpec contract is considered fully realized only if:

1. schema validation is strict,
2. packaging is deterministic,
3. path traversal is impossible,
4. runtime compatibility checks are enforced,
5. explainability metadata is propagated,
6. security policies are enforced,
7. distributed runtime execution is supported,
8. CI validates canonical packaging behavior.

---

## 25. Invariants

The following MUST remain true:

- JobSpecs are deterministic,
- packaging is reproducible,
- identical source yields identical hashes,
- runtime behavior is portable,
- security validation cannot be bypassed,
- path traversal is impossible,
- public field semantics remain backward compatible within MAJOR version,
- runtime explainability remains attachable to workload execution.
