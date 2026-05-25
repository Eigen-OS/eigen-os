# QFS Layout (CircuitFS) v1.0

Version 1.0 defines the canonical directory and artifact structure (CircuitFS) used by the kernel/runtime to persist job artifacts and by the System API to retrieve execution results.

---

## Job Root Directory

Each submitted job receives a unique `job_id` (UUID-like identifier).

All artifacts associated with the job are stored under:

```text
{qfs_root}/{job_id}/
```

where:

- `{qfs_root}` defaults to:

```text
/var/lib/eigen/circuit_fs
```

or another path configured via:

```text
EIGEN_QFS_ROOT
```

---

## Canonical Directory Layout

```text
{qfs_root}/{job_id}/
├── input/
│   ├── job.yaml
│   ├── program.eigen.py
│   └── metadata.json
├── compiled/
│   ├── circuit.aqo.json
│   ├── circuit.aqo.pb
│   ├── circuit.qasm
│   └── metadata.json
├── results/
│   ├── result.json
│   ├── manifest.json
│   └── error.json
├── results.parquet
├── logs/
│   ├── kernel.log
│   ├── compiler.log
│   └── driver.log
└── meta/
    └── job.json
```

---

## Directory Semantics

`input/`

Contains source input artifacts:

- `job.yaml` — resolved `JobSpec`

- `program.eigen.py` — submitted Eigen-Lang source

- `metadata.json` — optional source hashes/schema metadata

The first two files are mandatory.

---

`compiled/`

Contains compiler output artifacts:

- `circuit.aqo.json` — canonical AQO representation (required)

- `circuit.aqo.pb` — protobuf AQO (optional)

- `circuit.qasm` — OpenQASM export (optional)

- `metadata.json` — compiler metadata (optional)

---

`results/`

Contains execution artifacts:

- `result.json` — structured execution result and metadata

- `manifest.json` — artifact manifest and checksums

- `error.json` — execution failure details (if execution failed)

---

`results.parquet`

Canonical API-facing execution result artifact.

This file is mandatory for successful jobs.

---

`logs/`

Optional runtime logs:

- kernel logs

- compiler logs

- backend/driver logs

---

`meta/`

Optional metadata summaries and indexing artifacts.

---

## Required Files (v1.0)

Mandatory artifacts:

- `input/job.yaml`

- `input/program.eigen.py`

- `compiled/circuit.aqo.json`

- `results.parquet` (for successful jobs)

All other files are optional extensions.

---

## Access Patterns

### Validation

Reads:

- `input/job.yaml`

- `input/program.eigen.py`

### Compilation

Writes:

- `compiled/circuit.aqo.json`

### Execution

Reads:

- compiled/circuit.aqo.json

Writes:

- `results.parquet`

- optional execution artifacts

### API Retrieval

Primary result source:

- `results.parquet`

Additional artifacts:

- `result.json`

- `manifest.json`

may be used for extended metadata and analytics.

---

## Compatibility and Migration

The system must remain compatible with legacy artifacts.

Example:

- if only `results.parquet` exists,

- APIs must still return valid results.

Missing optional files must not break result retrieval when mandatory artifacts are present.

---

## Security and Validation

Required guarantees:

- `job_id` validation before filesystem access

- protection against path traversal (`..`)

- atomic file writes where possible

- strict AQO schema validation

Any structural violations:

- missing mandatory files

- invalid AQO schema

- corrupted metadata

must be treated as deterministic execution or loading failures.

---

## Version 1.0 Additions

Compared to MVP (`v0.1`), version 1.0 finalizes several previously incomplete areas.

### Artifact Organization

Execution artifacts and logs are now consistently grouped under:

- `results/`

- `logs/`

- `meta/`

---

## Structured Result Artifacts

The following artifacts are now standardized:

- `result.json`

- `manifest.json`

These improve indexing, analytics, and client API integrations.

---

## Deterministic Diagnostics

Missing mandatory artifacts now return deterministic errors:

```text
MISSING_REQUIRED:qfs://jobs/{job_id}/...
```

Standardized cleanup reason codes:

- `RETENTION_EXPIRED`

- `ORPHAN_NOT_INDEXED`

---

## Checkpoint/Restore Guardrails (Phase-8B L2)

Checkpoint and restore operations now support deterministic budget validation:

- `SIZE_BUDGET_EXCEEDED`

- `RESTORE_COST_BUDGET_EXCEEDED`

Validation responses include:

- observed value

- allowed limit

- deterministic rejection reason

---

Version 1.0 therefore establishes QFS as the canonical CircuitFS persistence contract for:

- source programs,

- AQO compilation artifacts,

- execution outputs,

- logs,

- metadata,

- analytics-compatible result structures.

Backward compatibility with older artifact layouts remains mandatory.
