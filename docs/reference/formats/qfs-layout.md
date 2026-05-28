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
| `compile_report.json` | optional | Compiler diagnostics |
| `metadata.json` | optional | Compiler metadata |

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
