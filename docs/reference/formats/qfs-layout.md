# QFS Layout — MVP (CircuitFS)

## Summary

Defines the stable directory structure and file layout for CircuitFS (Level 3 QFS) in MVP. This provides predictable paths for job artifacts, enabling consistent access by kernel, compiler, and driver‑manager services.

## Motivation

Without a standardized artifact layout:

- Services cannot reliably locate input/output files

- Debugging and artifact inspection becomes ad‑hoc

- Future upgrades may break existing job references

- Data migration and backup strategies become complex

## Goals

- Define canonical paths for all job artifacts

- Ensure deterministic naming based on `job_id`

- Support both flat and hierarchical storage backends

- Enable easy artifact discovery and cleanup

## Non‑Goals

- Advanced QFS features (replication, tiered storage, compression)

- StateStore (Level 2) or LiveQubitManager (Level 1) layouts

- Multi‑version artifact retention policies

## Directory Structure

### Root Path Convention
```text
/circuit_fs/{job_id}/
```

**Where**:

- `circuit_fs` is the mount point or bucket name

- `{job_id}` is the globally unique job identifier (UUID v4 format)

- All paths are case‑sensitive

### MVP Artifact Layout
```text
/circuit_fs/{job_id}/
├── input/
│   ├── job.yaml                    # Resolved JobSpec (without inline program)
│   └── program.eigen.py            # Original Eigen‑Lang source
├── compiled/
│   ├── circuit.aqo.json           # Canonical AQO JSON (required)
│   ├── circuit.aqo.pb             # Optional: AQO Protobuf binary
│   └── circuit.qasm               # Optional: QASM3 representation
├── results/
│   ├── counts.json                # Normalized measurement counts
│   ├── metadata.json              # Execution metadata
│   ├── raw_backend_response.json  # Optional: raw backend output
│   └── error.json                 # Optional: structured job error details (MVP helper)
├── logs/
│   ├── kernel.log                 # Kernel pipeline logs
│   ├── compiler.log               # Compilation logs
│   └── driver.log                 # Driver‑manager execution logs
└── meta.json                      # Job metadata and manifest
```

## File Specifications

### 1. `input/job.yaml`

The resolved JobSpec after CLI processing, with the following transformations:

- `spec.program` field removed (source moved to separate file)

- Defaults applied for optional fields

- CLI flags merged into appropriate sections

- All paths resolved to absolute or well‑formed URIs

**Example:**
```yaml
apiVersion: eigen.os/v0.1
kind: QuantumJob
metadata:
  name: vqe-h2
  labels:
    example: "true"
spec:
  target: sim:local
  priority: 50
  compiler_options:
    optimization_level: "1"
  metadata:
    shots: "1024"
    max_iters: "50"
  dependencies: []
```

### 2. `input/program.eigen.py`

Original Eigen‑Lang source bytes, exactly as submitted.

**Note**: Even if submitted inline in JobSpec, the kernel extracts and stores as separate file.

### 3. `compiled/circuit.aqo.json`

Canonical AQO v0.1 JSON representation (RFC 0005). This is the primary compiled artifact.

**Validation**: Must pass AQO v0.1 schema validation.

### 4. `compiled/circuit.qasm` (optional)

OpenQASM 3.0 representation for debugging and interoperability.

### 5. `results/counts.json`

Normalized measurement counts in standard format:
```json
{
  "version": "0.1",
  "format": "bitstring_counts",
  "qubits": 4,
  "shots": 1024,
  "counts": {
    "0000": 245,
    "0001": 127,
    "0010": 98,
    // ... other bitstrings
  },
  "timestamp": "2026-01-10T10:30:00Z"
}
```

**Bitstring ordering**: Most‑significant qubit first (q[0] is leftmost bit).

### 6. `results/metadata.json`

Execution metadata:
```json
{
  "version": "0.1",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "sim:local",
  "execution_time_sec": 12.345,
  "shots": 1024,
  "backend_info": {
    "name": "eigen_simulator",
    "version": "0.1.0"
  },
  "timestamps": {
    "submitted": "2026-01-10T10:00:00Z",
    "started": "2026-01-10T10:01:00Z",
    "completed": "2026-01-10T10:13:45Z"
  }
}
```

### 7. meta.json

Job manifest and integrity information:
```json
{
  "version": "0.1",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "created": "2026-01-10T10:00:00Z",
  "status": "COMPLETED",
  "artifacts": [
    {
      "path": "input/job.yaml",
      "sha256": "a1b2c3...",
      "size_bytes": 1024,
      "mime_type": "application/x-yaml"
    },
    {
      "path": "compiled/circuit.aqo.json",
      "sha256": "d4e5f6...",
      "size_bytes": 2048,
      "mime_type": "application/json"
    }
  ],
  "hashes": {
    "program_sha256": "a1b2c3...",  # From SubmitJobRequest
    "aqo_sha256": "d4e5f6...",      # AQO JSON hash
    "results_sha256": "g7h8i9..."   # Combined results hash
  }
}
```

## Access Patterns

### 1. Kernel Pipeline Stages
```text
Validation   → Reads: input/job.yaml, input/program.eigen.py
Compilation  → Writes: compiled/circuit.aqo.json, compiled/circuit.qasm
Execution    → Reads: compiled/circuit.aqo.json
              Writes: results/counts.json, results/metadata.json
Completion   → Writes: meta.json, logs/*.log
```

### 2. System‑API Serving

- `GetJobResults` → Returns `results/counts.json` + `results/metadata.json`

- Future debugging endpoints → Serve any artifact by path

## Implementation Notes

### 1. Storage Backends

**MVP supports:**

- **Local filesystem**: `/var/lib/eigen/circuit_fs/{job_id}/`

- **S3‑compatible**: `s3://eigen-circuit-fs/{job_id}/`

- **In‑memory (testing)**: Temporary directory

### 2. Atomic Writes

To prevent partial reads:
```python
# Write to temporary file, then rename
with tempfile.NamedTemporaryFile(dir=job_dir, delete=False) as tmp:
    json.dump(data, tmp)
    tmp.flush()
    os.fsync(tmp.fileno)
os.rename(tmp.name, "results/counts.json")
```

### 3. Cleanup Policy

- **MVP**: Manual cleanup only

- **Phase 1**: TTL‑based automatic cleanup (configurable per job)

- **Retention**: `meta.json` preserved after artifact cleanup for audit

### 4. Security

- Artifacts are user‑scoped: `/circuit_fs/{user_id}/{job_id}/` (future)

- No sensitive data in artifact names or contents

- Logs redact tokens, credentials, PII

## Error Handling

### Missing Artifacts

- Kernel must validate required artifacts exist before pipeline transition

- Missing `circuit.aqo.json` → `COMPILE_ERROR`

- Missing `results/counts.json` → `EXECUTION_ERROR`

### Corruption Detection

- Store SHA‑256 hashes in `meta.json`

- Optional verification on read (configurable)

- Corrupted files trigger job retry or failure

## Testing Plan

### Unit Tests

- Path generation from `job_id`

- Atomic write/rename operations

- JSON schema validation for all artifact types

### Integration Tests

1. Submit job → verify all artifacts created

2. Simulate partial write → verify job fails cleanly

3. Artifact round‑trip: write → read → verify equality

### Performance Tests

- Concurrent job artifact creation (10+ jobs)

- Large circuit storage (>1MB AQO)

- Directory listing performance (1000+ jobs)

## Future Extensions

### Phase 1

- Symbolic links for common access patterns

- Artifact compression (gzip for JSON files)

- Streaming large results (>100MB)

## Phase 2

- Multi‑part artifacts for very large circuits

- Cross‑job artifact deduplication

- Read‑only snapshot exports

## Phase 3

- Integration with StateStore (checkpoint migration)

- Qubit‑mapped artifact variants

- Federated storage across multiple QFS instances

## Migration Strategy

### v0.1 to v0.2

- Add new optional artifacts in new directories

- Never rename or remove existing artifact paths

- Use `meta.json` version to detect layout version

- Backward compatibility: v0.2 services must read v0.1 layouts

---

**References:**

- RFC 0005: AQO format (defines `circuit.aqo.json` schema)

- RFC 0011: Eigen‑Lang submission (defines `program.eigen.py` format)

- RFC 0007: QRTX MVP (references QFS paths)

- QFS Architecture: Three‑level storage model