# JobSpec v1.0 (job.yaml)

**Document status:** Normative  
**Subsystem:** Public API, Runtime Controller, Scheduler, Packaging System, Distributed Runtime, Security Layer, Observability Layer  
**Contract version:** `1.0.0`

`job.yaml` is the canonical declarative workload descriptor used across:

- CLI submission,
- SDK orchestration,
- CI/CD pipelines,
- distributed runtime scheduling,
- benchmark execution,
- hybrid quantum/classical execution,
- cluster orchestration,
- replay/reproducibility flows,
- policy-aware runtime execution,
- observability and explainability systems.

This document defines the normative JobSpec contract for Eigen OS `1.x`.

---

# 1. Purpose

JobSpec standardizes how workloads are:

- declared,
- packaged,
- validated,
- compiled,
- scheduled,
- executed,
- observed,
- reproduced,
- audited,
- replayed,
- secured.

The contract is designed to support:

- local execution,
- cluster execution,
- hybrid workloads,
- distributed runtime execution,
- multi-backend scheduling,
- deterministic replay,
- explainability,
- secure artifact handling,
- policy-aware orchestration,
- backend portability,
- runtime introspection.

---

# 2. Contract Version

## API Version

```yaml
apiVersion: eigen.os/v1
```

## Resource Kind

```yaml
kind: QuantumJob
```

Future-compatible kinds MAY include:

```yaml
HybridWorkflow
DistributedJob
BenchmarkJob
PipelineJob
ReplayJob
```

---

# 3. Design Principles

## 3.1 Declarative Execution

JobSpec describes desired execution state rather than procedural execution steps.

## 3.2 Deterministic Packaging

Equivalent source inputs MUST produce identical:

- packaging manifests,
- hashes,
- canonical serialization,
- AQO generation inputs.

## 3.3 Portable Runtime Semantics

JobSpecs MUST behave consistently across:

- local runtime,
- distributed runtime,
- replay environments,
- backend providers,
- simulator environments.

## 3.4 Secure-by-Default

Unsafe execution behavior is prohibited by default.

The system MUST reject:

- path traversal,
- symlink escape,
- ambiguous execution sources,
- unsigned remote artifacts when signature enforcement is enabled,
- unsupported runtime capabilities.

## 3.5 Reproducibility

JobSpecs MUST contain sufficient metadata for:

- deterministic replay,
- auditability,
- explainability,
- runtime lineage reconstruction.

## 3.6 Explicit Runtime Intent

Runtime behavior MUST be explicitly represented through structured configuration.

Implicit runtime behavior is prohibited where it affects:

- scheduling,
- security,
- observability,
- retry behavior,
- distributed execution semantics.

---

# 4. Minimal Valid JobSpec

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

# 5. Top-Level Structure

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

# 6. Field Matrix

| Field | Required | Type | Description |
|---|---|---|---|
| `apiVersion` | yes | string | API contract version |
| `kind` | yes | string | Resource type |
| `metadata` | yes | object | Stable workload metadata |
| `metadata.name` | yes | string | Stable workload identifier |
| `metadata.namespace` | no | string | Logical execution namespace |
| `metadata.labels` | no | map<string,string> | Indexed bounded metadata |
| `metadata.annotations` | no | map<string,string> | Non-indexed metadata |
| `spec` | yes | object | Execution specification |
| `spec.target` | yes | string | Runtime target |
| `spec.program` | yes | object | Program definition |
| `spec.compiler` | no | object | Compiler behavior |
| `spec.parameters` | no | object | Runtime parameters |
| `spec.dependencies` | no | array<string> | Deterministic dependencies |
| `runtime` | no | object | Runtime execution policy |
| `resources` | no | object | Resource requirements |
| `scheduling` | no | object | Scheduling behavior |
| `observability` | no | object | Telemetry and tracing policy |
| `security` | no | object | Security restrictions |
| `artifacts` | no | object | Artifact retention and persistence |

Unknown top-level fields MUST be rejected with:

```text
INVALID_ARGUMENT
```

---

# 7. Metadata Section

## Structure

```yaml
metadata:
  name: quantum-vqe
  namespace: research

  labels:
    workload: research
    environment: staging

  annotations:
    owner: runtime-team
```

---

## 7.1 metadata.name

### Requirements

- MUST be non-empty,
- MUST be deterministic,
- MUST match regex:

```text
^[a-zA-Z0-9._-]{1,128}$
```

### MUST NOT contain

- whitespace,
- control characters,
- path separators,
- Unicode normalization ambiguities.

---

## 7.2 metadata.namespace

Logical execution namespace.

### Constraints

- MUST match:

```text
^[a-zA-Z0-9._-]{1,64}$
```

### Default

```text
default
```

---

## 7.3 metadata.labels

Labels are indexed metadata.

### Constraints

- bounded cardinality,
- max key length: 64,
- max value length: 128,
- deterministic serialization.

Reserved prefixes:

```text
eigen.os/
runtime.eigen.os/
scheduler.eigen.os/
```

User-defined labels MUST NOT override reserved prefixes.

---

## 7.4 metadata.annotations

Non-indexed metadata.

May contain:

- provenance,
- CI build metadata,
- experiment descriptions,
- external references,
- replay lineage references.

Annotations MUST NOT influence scheduling deterministically unless explicitly mapped into scheduling policy.

---

# 8. Spec Section

## 8.1 Target

```yaml
spec:
  target: sim:local
```

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
runtime:deterministic
```

### Validation Rules

- target MUST be explicitly declared,
- unknown targets MUST fail validation,
- backend aliases MUST resolve through Driver Manager normalization.

---

## 8.2 Program Definition

### File-Based Program

```yaml
spec:
  program:
    path: src/program.eigen.py
    entrypoint: main
```

### Inline Program

```yaml
spec:
  program:
    inline: |
      from eigen_lang import hybrid_program

      @hybrid_program()
      def main():
          return 1
```

### Remote Artifact Program

```yaml
spec:
  program:
    uri: qfs://artifacts/programs/vqe.py
```

### Allowed Source Types

Exactly ONE source type is allowed:

- `path`
- `inline`
- `uri`

Mutual exclusivity is mandatory.

---

## 8.3 Entrypoint

```yaml
entrypoint: main
```

### Default

```text
main
```

### Constraints

- MUST be a valid identifier,
- MUST exist in source,
- MUST reference exactly one executable hybrid entrypoint.

---

## 8.4 Compiler Configuration

```yaml
spec:
  compiler:
    optimization_level: 2
    target_profile: balanced

    defines:
      ENABLE_FUSION: "true"
```

### Supported Optimization Levels

```yaml
0
1
2
3
```

### Supported Profiles

```yaml
balanced
latency
deterministic
debug
aggressive
```

### Compiler Constraints

- compilation MUST be deterministic,
- unsupported profiles MUST fail validation,
- defines MUST remain bounded and serializable.

---

## 8.5 Dependencies

```yaml
spec:
  dependencies:
    - numpy==2.0.0
    - scipy==1.15.0
```

### Dependency Constraints

- MUST be deterministic,
- SHOULD pin exact versions,
- MAY be validated against allowlists,
- MUST NOT contain mutable tags such as `latest`.

---

## 8.6 Parameters

```yaml
spec:
  parameters:
    shots: 1000
    learning_rate: 0.01
```

### Constraints

- parameter values MUST be JSON/YAML serializable,
- unsupported runtime parameter types MUST fail validation,
- parameter names MUST remain deterministic.

---

# 9. Runtime Section

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

## 9.1 Runtime Modes

```yaml
local
distributed
hybrid
benchmark
replay
```

---

## 9.2 Retry Policy

```yaml
retry:
  max_attempts: 3
  backoff: exponential
```

### Allowed Backoff Policies

```yaml
fixed
linear
exponential
```

### Constraints

- `max_attempts` MUST be >= 1,
- retry semantics MUST align with error retryability contract,
- non-retryable failures MUST terminate execution immediately.

---

## 9.3 Timeout Policy

```yaml
timeout:
  queue_seconds: 600
  execution_seconds: 3600
  result_seconds: 300
```

### Constraints

- timeout values MUST be positive integers,
- runtime MAY enforce maximum timeout ceilings,
- exceeded runtime budgets MUST map to:

```text
DEADLINE_EXCEEDED
```

---

## 9.4 Replay Semantics

```yaml
runtime:
  replay:
    enabled: true
    deterministic_seed: 42
```

### Constraints

- replay execution MUST preserve canonical inputs,
- deterministic seeds MUST propagate to runtime execution,
- replay metadata MUST remain audit-visible.

---

# 10. Resources Section

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

## 10.1 CPU and Memory

| Field | Type |
|---|---|
| `cpu` | integer |
| `memory_mb` | integer |

### Constraints

- values MUST be positive,
- runtime MAY enforce quotas,
- over-allocation MAY fail with:

```text
RESOURCE_EXHAUSTED
```

---

## 10.2 GPU Resources

```yaml
gpu:
  count: 2
```

Optional fields MAY include:

```yaml
vendor: nvidia
memory_mb: 8192
```

---

## 10.3 Quantum Resources

```yaml
quantum:
  qubits: 64
```

Optional fields MAY include:

```yaml
backend_family: superconducting
minimum_fidelity: 0.99
```

Quantum requirements MUST remain declarative and MUST NOT expose provider-native implementation details.

---

# 11. Scheduling Section

```yaml
scheduling:
  priority: 50

  policy:
    mode: balanced

  affinity:
    region: us-east
```

---

## 11.1 Priority

Range:

```text
0-100
```

Default:

```text
50
```

---

## 11.2 Policy Modes

```yaml
balanced
latency
cost
availability
deterministic
compliance
```

Scheduling decisions SHOULD remain explainable through runtime observability APIs.

---

## 11.3 Affinity Rules

```yaml
affinity:
  region: us-east
  accelerator: gpu
```

### Constraints

- affinity rules MUST remain bounded,
- unsupported affinity keys MAY fail validation,
- affinity MUST NOT bypass security or policy controls.

---

# 12. Observability Section

```yaml
observability:
  tracing: true
  metrics: true
  explainability_level: L2_OPERATOR
```

### Explainability Levels

```yaml
L1_USER
L2_OPERATOR
L3_FORENSIC
```

### Constraints

- explainability levels MUST align with runtime observability contract,
- tracing identifiers MUST NOT be embedded into labels with unbounded cardinality,
- observability metadata MUST remain export-safe.

---

# 13. Security Section

```yaml
security:
  sandbox: strict

  filesystem:
    readonly: true

  network:
    mode: disabled
```

---

## 13.1 Sandbox Modes

```yaml
disabled
standard
strict
```

### Constraints

- production deployments SHOULD default to `strict`,
- unsupported sandbox modes MUST fail validation.

---

## 13.2 Filesystem Policy

```yaml
filesystem:
  readonly: true
```

### Constraints

- workspace escape is prohibited,
- device-path access is prohibited,
- filesystem permissions MUST remain deterministic.

---

## 13.3 Network Policy

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

### Constraints

- runtime MUST enforce network isolation,
- policy violations MAY fail with:

```text
PERMISSION_DENIED
```

---

## 13.4 Artifact Trust Policy

```yaml
security:
  artifacts:
    require_signatures: true
```

### Constraints

- unsigned artifacts MAY be rejected,
- trust policy enforcement MUST remain deterministic.

---

# 14. Artifacts Section

```yaml
artifacts:
  persist_results: true

  retention:
    days: 30
```

---

## 14.1 Artifact Persistence

Controls durable storage of:

- execution results,
- traces,
- explainability artifacts,
- benchmark outputs,
- runtime telemetry snapshots,
- replay manifests,
- AQO payloads.

---

## 14.2 Retention Rules

### Constraints

- retention MUST be policy-bounded,
- runtime MAY override excessive retention requests,
- expired artifacts MAY be garbage-collected.

---

# 15. Canonical Mapping to SubmitJobRequest

## Mapping Pipeline

```text
job.yaml
  → JobSpec
  → Canonical Manifest
  → Packaging
  → SubmitJobRequest
```

## Canonical Mapping

| JobSpec | SubmitJobRequest |
|---|---|
| `metadata.name` | `name` |
| `metadata.namespace` | `namespace` |
| `spec.target` | `target` |
| `spec.program.*` | `program` |
| `scheduling.priority` | `priority` |
| `runtime.timeout.*` | `timeouts` |
| `resources.*` | `resource_requirements` |
| `observability.*` | `telemetry_policy` |
| `security.*` | `security_policy` |

The canonical manifest MUST be deterministic.

---

# 16. Packaging Rules

## 16.1 Deterministic Packaging

Packaging MUST:

- normalize paths,
- normalize line endings,
- preserve encoding,
- preserve stable hashing behavior,
- preserve deterministic file ordering.

---

## 16.2 Hashing

Program source MUST generate:

```text
SHA-256(source_bytes)
```

Stored in:

```yaml
metadata:
  source_sha256: ...
```

Hash generation MUST remain stable across supported platforms.

---

## 16.3 Path Rules

### Allowed

- relative paths,
- repository-local paths.

### Forbidden

- absolute paths,
- `..` traversal,
- symlink escape outside workspace,
- device paths,
- runtime-generated mutable source references.

---

## 16.4 Canonical Serialization

Canonical serialization MUST:

- preserve field ordering semantics where applicable,
- avoid nondeterministic YAML emitters,
- normalize Unicode encoding.

---

# 17. Validation Rules

Validation occurs in multiple phases.

---

## 17.1 Schema Validation

Checks:

- required fields,
- field types,
- enums,
- ranges,
- regex constraints,
- unknown field rejection.

---

## 17.2 Packaging Validation

Checks:

- source existence,
- hash determinism,
- path safety,
- artifact accessibility,
- canonical packaging invariants.

---

## 17.3 Semantic Validation

Checks:

- entrypoint existence,
- hybrid program validity,
- dependency consistency,
- runtime compatibility,
- target compatibility,
- replay compatibility.

---

## 17.4 Security Validation

Checks:

- sandbox policy,
- forbidden imports,
- unsafe capabilities,
- artifact policy violations,
- remote artifact trust validation.

---

## 17.5 Runtime Compatibility Validation

Checks:

- backend capability compatibility,
- resource-policy compatibility,
- scheduling-policy compatibility,
- distributed-runtime eligibility.

---

# 18. Error Semantics

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

Unavailable runtime targets MAY use:

```text
UNAVAILABLE
```

Timeout violations MUST use:

```text
DEADLINE_EXCEEDED
```

Error semantics MUST align with:

```text
docs/reference/error-model.md
```

and:

```text
docs/reference/error-mapping.md
```

---

# 19. Example: Minimal Local Job

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

# 20. Example: Distributed Runtime Job

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

# 21. Example: Inline Program Job

```yaml
apiVersion: eigen.os/v1
kind: QuantumJob

metadata:
  name: inline-demo

spec:
  target: sim:local

  program:
    inline: |
      from eigen_lang import hybrid_program

      @hybrid_program()
      def main():
          return 42
```

---

# 22. Example: Secure Replay Job

```yaml
apiVersion: eigen.os/v1
kind: ReplayJob

metadata:
  name: deterministic-replay

spec:
  target: runtime:deterministic

  program:
    uri: qfs://artifacts/jobs/vqe/program.py

runtime:
  mode: replay

  replay:
    enabled: true
    deterministic_seed: 12345

security:
  sandbox: strict

observability:
  tracing: true
  explainability_level: L3_FORENSIC
```

---

# 23. Compatibility Guarantees

The following are stable public contract surfaces:

- field names,
- semantic meanings,
- validation rules,
- packaging semantics,
- hash generation rules,
- target resolution behavior,
- explainability level semantics,
- retry semantics.

MINOR releases MAY add:

- optional fields,
- new runtime modes,
- new scheduling policies,
- new observability metadata.

Breaking changes require:

- MAJOR version increment,
- migration documentation,
- SDK updates,
- conformance test updates.

---

# 24. Conformance Requirements

CI MUST validate:

1. schema correctness,
2. deterministic packaging,
3. stable hashing,
4. path traversal prevention,
5. replay determinism,
6. runtime compatibility validation,
7. security policy enforcement,
8. canonical serialization stability.

Required golden tests:

- minimal JobSpec validation,
- inline program validation,
- invalid target rejection,
- path traversal rejection,
- deterministic hash generation,
- distributed runtime scheduling,
- replay compatibility,
- security sandbox enforcement.

---

# 25. Migration Notes

## From v0.1

### Changes

- structured `program` section,
- inline source officially supported,
- replay semantics added,
- security section added,
- runtime section added,
- observability section added,
- deterministic validation rules formalized,
- path safety enforcement added,
- canonical packaging semantics frozen.

---

# 26. Closure Criteria

The JobSpec contract is considered fully realized only if:

1. schema validation is strict,
2. packaging is deterministic,
3. path traversal is impossible,
4. runtime compatibility checks are enforced,
5. explainability metadata is propagated,
6. security policies are enforced,
7. distributed runtime execution is supported,
8. replay semantics are deterministic,
9. CI validates canonical packaging behavior,
10. runtime observability is attachable to all execution modes.

---

# 27. Invariants

The following MUST remain true:

- JobSpecs are deterministic,
- packaging is reproducible,
- identical source yields identical hashes,
- runtime behavior is portable,
- security validation cannot be bypassed,
- path traversal is impossible,
- replay semantics remain deterministic,
- public field semantics remain backward compatible within a MAJOR version,
- runtime explainability remains attachable to workload execution,
- runtime telemetry integration remains stable across supported runtimes.
