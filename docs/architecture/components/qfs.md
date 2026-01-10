# QFS (Quantum Data Fabric) – MVP Summary

- Phase: MVP (Phase 0)

- Status: Architectural blueprint for future phases; MVP implements a minimal subset.

## Responsibility

**MVP Scope**: QFS in MVP is a **simplified CircuitFS** (Level 3) only, focusing on static artifact storage for job execution.
**StateStore (Level 2)** and **LiveQubitManager** (Level 1) **are no-op or stubbed** in MVP (RFC 0007).

### MVP Responsibilities:

- Store and version job artifacts: `program.eigen.py`, `job.yaml`, compiled AQO/QASM, results, metadata.

- Provide deterministic artifact paths: `circuit_fs/<job_id>/<artifact_name>`.

- Serve as the **single source of truth** for compiled circuits and results between kernel, compiler, and system-api.

- Ensure artifact integrity via SHA-256 hashing (optional deduplication).

## Interfaces

- **Internal gRPC API**: `QfsService` (defined in `proto/qfs/service.proto`).

    - `StoreArtifact(StoreArtifactRequest) → ArtifactHandle`

    - `RetrieveArtifact(RetrieveArtifactRequest) → ArtifactResponse`

    - `ListArtifacts(ListArtifactsRequest) → ListArtifactsResponse`

- **Kernel integration**: Kernel calls QFS client library to persist/retrieve artifacts at pipeline stages.

- **File system layout**: Local directory structure with convention:
```text
circuit_fs/
  <job_id>/
    program.eigen.py
    job.yaml
    compiled.aqo.json
    compiled.qasm
    results.json
    meta.json
```

## Inputs / Outputs

- **Inputs:**

    - Job artifacts (bytes + metadata) from kernel pipeline stages.

    - `job_id` as namespace.

- **Outputs:**

    - `ArtifactHandle` with `hash`, `size`, `path`.

    - Retrieved artifact bytes on read.

- **Data formats**: JSON (AQO), YAML (JobSpec), binary (optional).

## Storage / State

- **Backend**: Local filesystem (MVP default). May support S3/minio later.

- **Caching**: Optional in-memory cache for hot artifacts (e.g., compiled circuits).

- **Versioning**: Immutable artifacts per job; no overwrite.

- **State**: Stateless service; persistence is delegated to storage backend.

## Failure Modes

- **Storage backend unavailable**: Returns UNAVAILABLE; kernel retries.

- **Disk full**: Returns RESOURCE_EXHAUSTED.

- **Corrupt artifact**: Integrity check fails (hash mismatch) → INVALID_ARGUMENT.

- **Network partition (future distributed storage**): Read-your-writes consistency best-effort in MVP.

## Observability

- **Metrics**:

    - `qfs_artifact_store_total{type, status}`

    - `qfs_artifact_retrieve_total{type, status}`

    - `qfs_artifact_size_bytes{type}`

    - `qfs_operation_duration_seconds{operation}`

- **Logs**: Include `job_id`, `artifact_hash`, `path`, `size`.

- **Traces**: Span per store/retrieve operation, linked to job trace.

---

**Note**: This MVP summary reflects only the **CircuitFS** component of the full QFS vision. StateStore and LiveQubitManager are planned for Phase 2+.