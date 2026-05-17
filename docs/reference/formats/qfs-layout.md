# QFS Layout — Current MVP Contract (CircuitFS)

- Phase: MVP
- Status date: **2026-05-17**
- Scope: stable artifact layout used by runtime/kernel and System API result retrieval.

## Summary

This document fixes the **actual** QFS Level-3 (CircuitFS) layout contract currently used in the repository and highlights the gaps that are still open. It supersedes older flat-layout examples and aligns with current architecture/component docs.

## Motivation
Without a frozen, implementation-aligned layout:
- services cannot reliably find artifacts across pipeline stages;
- API compatibility (especially `GetJobResults`) drifts from runtime outputs;
- migration and cleanup logic become brittle;
- RFC/ADR reconciliation becomes hard to audit.

## Goals

- Define canonical per-job paths and required files for MVP.
- Document which files are **required vs optional**.
- Capture current compatibility behavior for legacy artifacts.
- Explicitly list what is still missing from a full QFS vision.

## Non-Goals

- Level-1 (`LiveQubitManager`) and Level-2 (`StateStore`) runtime semantics.
- Full standalone QFS gRPC service design/contract.
- Content-addressed storage and dedup policy design.

## Canonical Root and Job Scope

```text
{qfs_root}/{job_id}/
```

Where:

- `{qfs_root}` defaults to `/var/lib/eigen/circuit_fs` in kernel wiring (override via `EIGEN_QFS_ROOT`);
- `{job_id}` is a UUID-like unique job identifier;
- all artifact paths are case-sensitive and job-scoped.

## Canonical MVP Artifact Layout (as implemented)

```text
{qfs_root}/{job_id}/
├── input/
│   ├── job.yaml                    # resolved JobSpec (required)
│   ├── program.eigen.py            # submitted Eigen-Lang source (required)
│   └── metadata.json               # source hashes/schema (optional but expected)
├── compiled/
│   ├── circuit.aqo.json            # canonical AQO JSON (required)
│   ├── circuit.aqo.pb              # protobuf AQO (optional)
│   ├── circuit.qasm                # OpenQASM representation (optional)
│   └── metadata.json               # compile-stage metadata (optional)
├── results/
│   ├── result.json                 # result envelope with refs/versioning (optional in legacy)
│   ├── manifest.json               # artifact manifest/checksums (optional in legacy)
│   └── error.json                  # structured execution error payload (optional)
├── results.parquet                 # canonical result payload for APIs (required for completed jobs)
├── logs/
│   ├── kernel.log                  # optional runtime logs
│   ├── compiler.log                # optional compile logs
│   └── driver.log                  # optional backend/driver logs
└── meta/
    └── job.json                    # optional job metadata summary
```

> Note: historical `meta.json` (at root) appears in older docs/examples. Current component docs describe a `meta/` directory. Consumers should treat `meta/` as canonical for new artifacts and remain tolerant to legacy root-level metadata naming.

## File-Level Contract

### Required for successful compile/execute flow

1. `input/job.yaml`
2. `input/program.eigen.py`
3. `compiled/circuit.aqo.json`
4. `results.parquet` (for successful jobs with retrievable results)

### Optional / versioned helpers

- `input/metadata.json`, `compiled/metadata.json`
- `compiled/circuit.aqo.pb`, `compiled/circuit.qasm`
- `results/result.json`, `results/manifest.json`, `results/error.json`
- `logs/*`, `meta/job.json`

## Access Patterns (Current Pipeline)

```text
Validation  -> reads input/job.yaml + input/program.eigen.py
Compile     -> writes compiled/circuit.aqo.json (+ optional compiled/*)
Execute     -> reads compiled/circuit.aqo.json
               writes results.parquet (+ optional results/result.json, results/manifest.json, results/error.json)
Finalize    -> may write logs/* and meta/job.json
```

System API result retrieval consumes `results.parquet` as canonical payload and may surface envelope/manifest references when present.

## Compatibility and Migration

Current behavior should preserve read compatibility for legacy jobs where only `results.parquet` exists:

- `GetJobResults` remains usable from `results.parquet` alone;
- envelope/manifest can be absent for older artifacts;
- readers should not fail solely due to missing optional metadata files.

## Validation Rules (MVP minimum)

- `job_id` path segment must be validated before filesystem operations.
- Writes should be atomic where helper APIs provide atomic semantics.
- `compiled/circuit.aqo.json` must remain schema-compatible with current AQO reference.
- Missing optional files must not break result retrieval when required files exist.

## Phase-8B QFS-L3 Hardening Additions (`1.0.0`, MINOR)

- Strict layout validation now returns deterministic diagnostics in the stable form
  `MISSING_REQUIRED:qfs://jobs/{job_id}/...` for required refs.
- Metadata envelopes for indexed artifacts validate deterministic fields:
  `qfs_ref`, `job_id`, `trace_id`, `stage`, `artifact_type`,
  `created_at_epoch_ms`, `retention_until_epoch_ms`.
- Trace-linked lookup path support is defined as:
  - `trace_id -> [qfs_ref...]`
  - `job_id -> [qfs_ref...]`
- Retention cleanup reason codes are frozen:
  - `RETENTION_EXPIRED`
  - `ORPHAN_NOT_INDEXED`
## Gaps / What Is Missing

The following are not yet fully specified or uniformly enforced and should be tracked as system gaps:

1. No standalone internal `QfsService` gRPC contract in-repo.
2. No unified cross-language `ArtifactHandle { hash, size, path }` contract.
3. No global immutable/no-overwrite write policy enforced on every write path.
4. No formal content-addressed deduplication feature.
5. No frozen QFS metrics/tracing contract dedicated to artifact operations.
6. No conformance suite that verifies distributed consistency semantics.

## RFC / ADR Reconciliation Notes

- MVP scope remains aligned with RFC positioning where Level-1/Level-2 QFS parts are stubbed/not production.
- The concrete path layout has evolved from older flat examples to nested directories (`input/`, `compiled/`, `results/`, `meta/`).
- A dedicated ADR for the current split architecture (Rust CircuitFS + System API QFS store facade) is still needed for closure.

## Change Control

Any breaking layout change must:

1. update this document and component architecture docs in the same change;
2. define backward-compatibility behavior for previously persisted jobs;
3. include conformance tests for read compatibility.
