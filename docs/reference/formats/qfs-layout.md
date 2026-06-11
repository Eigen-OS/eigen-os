# QFS Layout (CircuitFS) v1.0

## 1. Overview

QFS (Quantum File System), also referred to as **CircuitFS**, is the canonical filesystem layout and artifact persistence contract used by:

- Kernel runtime,
- Compiler pipeline,
- Driver Manager,
- Scheduler,
- Public APIs,
- Replay systems,
- Audit systems,
- Analytics/export tooling.

QFS defines deterministic artifact organization for:

- submitted jobs,
- compiled AQO artifacts,
- execution outputs,
- logs,
- manifests,
- replay metadata,
- diagnostics,
- checkpoint/restore flows.

The canonical QFS contract version for this document is:

```text
QFS Layout Contract Version: 1.0.0
```

Breaking layout or semantic changes require a MAJOR version bump.

---

## 2. Design Goals

QFS v1.0 guarantees:

- deterministic artifact locations,
- replay-safe execution persistence,
- backend-independent retrieval,
- compatibility across runtime components,
- stable API integrations,
- auditability,
- retention enforcement,
- deterministic cleanup behavior.

QFS is the canonical persistence contract for runtime execution artifacts.

---

## 3. QFS Root Directory

Each submitted job receives a globally unique `job_id`.

All artifacts for a job are stored under: `{qfs_root}/{job_id}/`

Default root: `/var/lib/eigen/circuit_fs`

Override via environment variable: `EIGEN_QFS_ROOT`

---

## 4. Job ID Rules

`job_id` MUST satisfy:

- globally unique,
- deterministic string validation,
- filesystem-safe encoding.

Allowed format: `[a-zA-Z0-9._-]+`

Forbidden:

- `/`
- `\`
- `..`
- null bytes
- path traversal segments

Invalid `job_id` values MUST be rejected before filesystem access.

---

## 5. Canonical Directory Layout

```text
{qfs_root}/{job_id}/
├── input/
│   ├── job.yaml
│   ├── program.eigen.py
│   ├── metadata.json
│   └── request.json
├── compiled/
│   ├── circuit.aqo.json
│   ├── circuit.aqo.pb
│   ├── circuit.qasm
│   ├── compile_report.json
│   ├── compile_report.json
│   └── metadata.json
├── execution/
│   ├── execution_plan.json
│   ├── backend_request.json
│   └── backend_response.json
├── results/
│   ├── result.json
│   ├── manifest.json
│   ├── metrics.json
│   ├── counts.json
│   ├── timeline.json
│   └── error.json
├── checkpoints/
│   ├── checkpoint-0001.bin
│   └── manifest.json
├── logs/
│   ├── kernel.log
│   ├── compiler.log
│   ├── scheduler.log
│   ├── driver.log
│   └── audit.log
├── reservations/
│   ├── reservation.json
│   └── history.jsonl
├── meta/
│   ├── job.json
│   ├── retention.json
│   ├── lineage.json
│   └── tags.json
├── traces/
│   ├── spans.json
│   └── events.json
├── tmp/
└── results.parquet
```

---

## 6. Directory Semantics

### 6.1 `input/`

Contains original submission artifacts.

#### Files

| **File** | **Required** | **Description** |
|-------------|------------|-----------|
| `job.yaml` | yes | Resolved JobSpec |
| `program.eigen.py` | conditional | Eigen-Lang source |
| `metadata.json` | optional | Submission metadata |
| `request.json` | optional | Canonical API request |

#### Notes

- `program.eigen.py` is required only for Eigen-Lang submissions.
- Alternative submission formats MAY omit it.

---

### 6.2 `compiled/`

Contains compiler outputs.

#### Files

| **File** | **Required** | **Description** |
|-------------|------------|-----------|
| `circuit.aqo.json` | yes | Canonical AQO |
| `circuit.aqo.pb` | optional | Binary AQO |
| `circuit.qasm` | optional | OpenQASM export |
| `compile_report.json` | optional | Compiler diagnostics / sidecar report |
| `metadata.json` | yes | Canonical compiler metadata |

#### Metadata requirements

`compiled/metadata.json` MUST include:

- `version` = `1.0.0`
- `schema_version`
- `compiler_version`
- `producer_identity`
- `contract_version`
- `created_at`
- `aqo_hash`
- `qasm_hash` when `circuit.qasm` exists
- `diagnostics_hash` when `compile_report.json` exists
- `lineage` with request/source provenance
- `retention_policy`

The compiler output directory is immutable within a job scope: duplicate writes to the same artifact path MUST be rejected by the persistence layer.
Readers MUST verify stored digests before returning bytes.

---

### 6.3 `execution/`

Contains backend execution planning artifacts.

#### Files

| **File** | **Required** | **Description** |
|-------------|------------|-----------|
| `execution_plan.json` | optional | Scheduler/runtime plan |
| `backend_request.json` | optional | Backend payload |
| `backend_response.json` | optional | Raw backend response |

These files are implementation-specific but standardized in location.

---

### 6.4 `results/`

Contains execution outputs and structured metadata.

#### Files

| **File** | **Required** | **Description** |
|-------------|------------|-----------|
| `result.json` | recommended | Structured execution result |
| `manifest.json` | recommended | Artifact manifest/checksums |
| `metrics.json` | optional | Runtime metrics |
| `counts.json` | optional | Measurement counts |
| `timeline.json` | optional | Event/timing timeline |
| `error.json` | conditional | Failure details |

`error.json` MUST exist for failed terminal executions where structured error details are available.

`results/result.json` and `results/manifest.json` MUST carry immutable lineage and retention metadata.
All result artifacts MUST be content-verified on read.

---

# Checkpoint Envelope Contract (QFS-L2)

Checkpoint persistence MUST use a replay-safe immutable envelope.

Canonical checkpoint envelope:

```yaml
schema_version: "1.0.0"
checkpoint_id: chkpt-001
job_id: job-123
runtime_version: "1.1.0"
payload_refs:
  state_segments:
    - path: qfs://...
      content_hash: sha256:...
      size_bytes: 1024
integrity:
  checksum_set: sha256
compatibility:
  min_reader_version: "1.0.0"
  max_reader_version: null
retention:
  retention_class: hot|warm|cold
  created_at_epoch_ms: 1715817600000
  retention_until_epoch_ms: 1715904000000
  pinned: true
restore_lineage:
  restored_from_checkpoint_id: chkpt-parent
  replay_session_id: replay-001
  restored_by_runtime_version: "1.1.0"
```

Normative requirements:

- checkpoint writes MUST be atomic;
- checkpoint payloads MUST be immutable once committed;
- restore paths MUST validate compatibility windows before replay;
- checkpoint payload hashes MUST use SHA-256;
- corrupted checkpoint payloads MUST be rejected;
- retention expiry MUST invalidate restore eligibility;
- restore lineage MUST remain replay-stable;
- replay restore operations MUST remain deterministic across retries.

---

### 6.5 `checkpoints/`

Contains checkpoint/restore artifacts.

#### Files

| **File** | **Description** |
|----------|----------|
| `checkpoint-*.bin` | Serialized checkpoints |
| `manifest.json` | Checkpoint manifest |

Checkpoint files are optional.

---

### 6.6 `logs/`

Contains runtime/service logs.

#### Files

| **File** | **Description** |
|----------|----------|
| `kernel.log` | Kernel runtime logs |
| `compiler.log` | Compiler logs |
| `scheduler.log` | Scheduling logs |
| `driver.log` | Backend driver logs |
| `audit.log` | Security/audit events |

Logs are optional unless explicitly required by deployment policy.

---

### 6.7 `meta/`

Contains metadata and indexing structures.

#### Files

| **File** | **Description** |
|----------|----------|
| `job.json` | Job metadata |
| `retention.json` | Retention policy state |
| `lineage.json` | Parent/child relationships |
| `tags.json` | Search/index metadata |

---

### 6.8 `traces/`

Contains structured observability artifacts.

#### Files

| **File** | **Description** |
|----------|----------|
| `spans.json` | Trace spans |
| `events.json` | Structured events |

Optional but recommended.

---

### 6.9 `tmp/`

Temporary workspace directory.

Rules:

- MUST NOT be treated as durable storage.
- MAY be deleted at any time.
- MUST NOT contain canonical artifacts.

---

### 6.9 `reservations/`

Contains durable reservation lifecycle artifacts for compatibility-layer and recovery flows.

#### Files

| **File** | **Required** | **Description** |
|-------------|------------|-----------|
| `reservation.json` | yes | Canonical reservation record with state, owner, device binding, and expiry |
| `history.jsonl` | recommended | Append-only reservation lifecycle history for replay/debug |

#### Notes

- Reservation records MUST be replay-safe and deterministic for identical normalized inputs.
- Expired records MUST remain restorable for audit and recovery.
- The path is used for compatibility-layer persistence until a dedicated
  Resource Manager store exists.

---

## 7. Root-Level Artifacts

### 7.1 `results.parquet`

Canonical analytics/result export artifact.

Required for successful jobs.

Purpose:

- analytics,
- batch export,
- API retrieval,
- offline processing.

If a job succeeds, `results.parquet` MUST exist.

---

## 8. Required Files (v1.0)

### 8.1 Mandatory Core Files

| **File** | **Requirement** |
|----------|----------|
| `input/job.yaml` | mandatory |
| `compiled/circuit.aqo.json` | mandatory |
| `results.parquet` | mandatory for successful jobs |

---

### 8.2 Conditional Files

| **File** | **Condition** |
|----------|----------|
| `program.eigen.py` | Eigen-Lang submissions |
| `error.json` | failed execution |
| `circuit.aqo.pb` | protobuf export enabled |

---

## 9. Access Patterns

### 9.1 Validation Phase

Reads:

```text
input/job.yaml
input/program.eigen.py
compiled/circuit.aqo.json
```

---

### 9.2 Compilation Phase

Writes:

```text
compiled/circuit.aqo.json
compiled/compile_report.json
```

---

### 9.3 Execution Phase

Reads: `compiled/circuit.aqo.json`

Writes:

```text
results.parquet
results/result.json
results/error.json
```

---

### 9.4 API Retrieval Phase

Primary artifact: `results.parquet`

Supplementary artifacts:

```text
results/result.json
results/manifest.json
```

---

## 10. Manifest and Checksum Rules

`manifest.json` SHOULD contain:

- artifact paths,
- sizes,
- content hashes,
- timestamps,
- retention classification.

Recommended hash algorithm: `SHA-256`

Example:

```json
{
  "artifact": "compiled/circuit.aqo.json",
  "sha256": "..."
}
```

---

## 11. Atomicity and Write Guarantees

QFS writers SHOULD implement:

- atomic rename semantics,
- temporary write staging,
- fsync before publish,
- partial-write protection.

Canonical artifacts MUST NOT become externally visible before write completion.

---

## 12. Retention and Cleanup

Retention policies are deployment-defined.

Recommended cleanup reasons:

| **Code** | **Meaning** |
|----------|----------|
| `RETENTION_EXPIRED` | Retention TTL exceeded |
| `ORPHAN_NOT_INDEXED` | Artifact not referenced |
| `MANUAL_PURGE` | Administrative deletion |

Cleanup operations SHOULD be logged.

---

## 13. Compatibility Rules

QFS consumers MUST tolerate missing optional artifacts.

Example:

If only: `results.parquet` exists, APIs MUST still return valid results.

Backward compatibility with older layouts is REQUIRED where feasible.

---

## 14. Migration Rules

Migration tooling MAY:

- generate missing manifests,
- reconstruct metadata,
- convert legacy layouts,
- regenerate checksums.

Migration MUST preserve:

- deterministic artifact paths,
- replay integrity,
- AQO hashes,
- job lineage.

---

## 15. Error Model

### 15.1 Structural Errors

| **Condition** | **Error** |
|----------|----------|
| Missing mandatory artifact | `MISSING_REQUIRED` |
| Invalid AQO schema | `INVALID_ARGUMENT` |
| Corrupted manifest | `DATA_LOSS` |
| Invalid path traversal | `PERMISSION_DENIED` |
| Unsupported artifact version | `FAILED_PRECONDITION` |

---

### 15.2 Deterministic Missing Artifact Format

Required format: `MISSING_REQUIRED:qfs://jobs/{job_id}/...`

Example: `MISSING_REQUIRED:qfs://jobs/job-123/results.parquet`

---

## 16. Checkpoint/Restore Guardrails (Phase-8B L2)

Checkpoint/restore flows MUST support deterministic validation.

Standardized rejection codes:

| **Code** | **Meaning** |
|----------|----------|
| `SIZE_BUDGET_EXCEEDED` | Artifact too large |
| `RESTORE_COST_BUDGET_EXCEEDED` | Restore budget exceeded |

Validation responses SHOULD include:

- observed value,
- configured limit,
- deterministic rejection reason.

---

## 17. Security Requirements

QFS implementations MUST enforce:

- path traversal protection,
- sandboxed filesystem access,
- job ownership validation,
- strict artifact validation,
- checksum verification where applicable.

QFS artifacts MUST be treated as untrusted input.

---

## 18. Observability Requirements

Recommended telemetry fields:

| **Field** | **Description** |
|----------|----------|
| `job_id` | Job identifier |
| `artifact_path` | QFS artifact |
| `artifact_size_bytes` | Artifact size |
| `artifact_hash` | Content checksum |
| `qfs_operation` | read/write/delete |
| `retention_reason` | Cleanup reason |

---

## 19. Performance Considerations

### 19.1 AQO Caching

Implementations MAY cache:

- parsed AQO,
- compiled execution plans,
- backend translations.

Caches SHOULD use deterministic content hashes.

---

### 19.2 Large Artifact Handling

Large artifacts SHOULD support:

- streaming reads,
- chunked writes,
- lazy loading,
- compression.

---

### 19.3 Parquet Optimization

`results.parquet` SHOULD:

- support column pruning,
- support analytics workloads,
- preserve deterministic schema ordering.

---

## 20. Compliance Requirements

A compliant QFS v1.0 implementation MUST:

- preserve canonical directory structure,
- preserve deterministic artifact naming,
- implement required mandatory artifacts,
- validate AQO before execution,
- protect against path traversal,
- implement deterministic error semantics,
- support replay-safe artifact retrieval.

The canonical `.proto`, AQO, and runtime contracts remain the authoritative source for interoperable execution semantics.

---

## Appendix A. Diagrams

### A.1 Overview

![Overview](https://i.imgur.com/xqvCMow.png)

<details>
<summary>code</summary>

```text
flowchart LR
  subgraph Runtime
    K["Kernel (QRTX)"]
    C[Compiler]
    DM[Driver Manager]
    S[Scheduler/Runtime Controller]
  end

  QFS[(QFS / CircuitFS\nLayout v1.0)]
  API[Public APIs]
  REPLAY[Replay systems]
  AUDIT[Audit systems]
  OBS[Observability]

  K <--> QFS
  C <--> QFS
  DM <--> QFS
  S <--> QFS

  API --> QFS
  REPLAY --> QFS
  AUDIT --> QFS

  K --> OBS
  C --> OBS
  DM --> OBS
  S --> OBS

  note1{{QFS is the canonical\nartifact persistence contract\nfor job-scoped evidence}}
  QFS --- note1
```

</details>

---

### A.2 Canonical Directory Layout

![Canonical Directory Layout](https://i.imgur.com/42kgxnU.png)

<details>
<summary>code</summary>

```text
flowchart TB
  ROOT["{qfs_root}/{job_id}/"] --> IN[input/]
  ROOT --> COMP[compiled/]
  ROOT --> EXEC[execution/]
  ROOT --> RES[results/]
  ROOT --> CK[checkpoints/]
  ROOT --> LOGS[logs/]
  ROOT --> META[meta/]
  ROOT --> TR[traces/]
  ROOT --> TMP[tmp/]
  ROOT --> PARQ["results.parquet"]

  IN --> IN1["job.yaml (MUST)"]
  IN --> IN2["program.eigen.py (conditional)"]
  IN --> IN3["metadata.json (optional)"]
  IN --> IN4["request.json (optional)"]

  COMP --> C1["circuit.aqo.json (MUST)"]
  COMP --> C2["circuit.aqo.pb (optional)"]
  COMP --> C3["circuit.qasm (optional)"]
  COMP --> C4["compile_report.json (optional)"]

  RES --> R1["result.json (recommended)"]
  RES --> R2["manifest.json (recommended)"]
  RES --> R3["error.json (conditional)"]

  TMP --> TNOTE{{tmp/ is non-durable:\nmay be deleted anytime}}
```

</details>

---

### A.3 Access Patterns

![Access Patterns](https://i.imgur.com/ymKVTPG.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
  autonumber
  participant CLI as CLI/SDK
  participant API as System API
  participant K as Kernel (QRTX)
  participant C as Compiler
  participant DM as Driver Manager
  participant QFS as QFS (CircuitFS)

  CLI->>API: SubmitJob
  API->>K: EnqueueJob
  K->>QFS: write input/job.yaml (+ source bundle)
  K->>C: Compile
  C-->>K: AQO (+ diagnostics)
  K->>QFS: write compiled/circuit.aqo.json
  K->>DM: Execute
  DM-->>K: normalized results / error
  K->>QFS: write results.parquet\n(+ results/result.json / results/error.json)
  API->>K: GetJobResults
  K->>QFS: read results.parquet (+ manifest)
  K-->>API: result envelope + refs
  API-->>CLI: response
```

</details>

---

### A.4 Manifest and Checksum Rules

![Manifest and Checksum Rules](https://i.imgur.com/lNQut3t.png)

<details>
<summary>code</summary>

```text
flowchart TB
  A["Artifact produced (e.g., compiled/circuit.aqo.json)"] --> B["Compute sha256(bytes)"]
  B --> C["Record entry in results/manifest.json (path, size, hash, timestamps)"]
  C --> D{Integrity check on read?}
  D -->|yes| E[Recompute sha256\nand compare]
  E -->|match| OK[OK]
  E -->|mismatch| DL[DATA_LOSS / integrity failure]
  D -->|no| N["Best-effort mode (allowed only if policy permits)"]
```

</details>

---

### A.5 Atomicity and Write Guarantees

![Atomicity and Write Guarantees](https://i.imgur.com/BWNyme5.png)

<details>
<summary>code</summary>

```text
flowchart LR
  W[Writer] --> TMP["Write to tmp path (e.g., tmp/<name>.part)"]
  TMP --> FSYNC["fsync/flush (where applicable)"]
  FSYNC --> REN["Atomic publish (rename/multipart finalize)"]
  REN --> VIS["Artifact becomes visible at canonical path"]
  VIS --> R[Readers see either: - old version - new complete version never partial bytes]
```

</details>

---

### A.6 Retention and Cleanup

![Retention and Cleanup](https://i.imgur.com/bPUENLS.png)

<details>
<summary>code</summary>

```text
stateDiagram-v2
  [*] --> Hot: created/published
  Hot --> Warm: age/usage threshold (policy)
  Warm --> Cold: archive tier (policy)
  Hot --> Purged: MANUAL_PURGE
  Warm --> Purged: RETENTION_EXPIRED
  Cold --> Purged: RETENTION_EXPIRED
  Hot --> Orphaned: ORPHAN_NOT_INDEXED
  Orphaned --> Purged: cleanup sweep

  note right of Purged
    Cleanup MUST be logged
    and (where required) audited.
  end note
```

</details>

---

### A.7 Security Requirements

![Security Requirements](https://i.imgur.com/8Re1tNa.png)

<details>
<summary>code</summary>

```text
flowchart TB
  REQ["Incoming qfs access (read/write/list)"] --> VAL["Validate job_id & path (no .., no traversal)"]
  VAL --> AUTH{Ownership / policy check}
  AUTH -->|deny| DENY[PERMISSION_DENIED]
  AUTH -->|allow| IO["Perform IO (store/load/list)"]
  IO --> INTEG{Checksum required?}
  INTEG -->|yes| VERIFY[Verify digest / manifest]
  VERIFY -->|fail| LOSS[DATA_LOSS / integrity failure]
  VERIFY -->|ok| OK[Success]
  INTEG -->|no| OK
```

</details>

---

### A.8 Observability Requirements

![Observability Requirements](https://i.imgur.com/eyTlVHS.png)

<details>
<summary>code</summary>

```text
sequenceDiagram
    autonumber

    participant S as Service (Kernel/Compiler/DM)
    participant Q as QFS
    participant O as Observability

    S->>Q: op(read/write/list/delete)
    Q-->>S: status + bytes/ref

    Q->>O: metrics: qfs_operation, backend, kind
    Q->>O: traces: QFS.<op> (job_id in trace/log only)

    Note over O: job_id/trace_id MUST NOT be metric labels
    Note over O: Allowed in traces & log fields only
```

</details>
