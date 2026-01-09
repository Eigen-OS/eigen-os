# RFC 0007: QRTX MVP: scheduler, task state machine, execution pipeline

- **Status:** Discussion
- **Authors:** NYankovich
- **Created:** 2026-01-08
- **Target milestone:** Phase 0 (MVP)
- **Tracking issue:** (TBD)
- **Supersedes / Related:** 0002,0003,0004,0006

## Summary

Defines the minimal kernel behavior to run a hybrid job end-to-end with correct lifecycle states and artifacts.

## Motivation

QRTX is the OS 'conductor'. MVP needs a working scheduler + pipeline that integrates compiler and driver-manager.

## Goals

- Implement TaskState machine for MVP.
- Implement pipeline stages: Validation → Compilation → ResourceAllocation → QuantumExecution → ResultProcessing → Completion.
- Persist artifacts/results into QFS with stable paths.

## Non-Goals

- Advanced noise-aware scheduling.
- Multi-device migration and checkpoint/restore (Phase 2).
- Multi-tenant fairness and quotas (Phase 1+).

## Guide-level explanation

**Lifecycle:**
1) system-api forwards job to kernel.
2) kernel validates and schedules.
3) kernel calls compiler to produce AQO/QASM.
4) kernel allocates resources.
5) kernel calls driver-manager ExecuteCircuit.
6) kernel stores results into QFS.
7) system-api serves status + results.

**TaskState enum (canonical):** Pending, Validating, Compiling, Queued, Allocating, Executing, Completing, Completed, Failed, Cancelled, Timeout.
**Executing sub-states:** QuantumInitializing, QuantumRunning, ClassicalRunning, Measuring, PostProcessing.

## Reference-level design

### Interfaces / APIs

Kernel must expose internal API (RFC 0004 Appendix A) to accept jobs and return status/results.
Kernel must implement clients for CompilationService and DriverManagerService.

### Data model

**QFS paths (MVP):**
- `circuit_fs/<job_id>/input.job.yaml`
- `circuit_fs/<job_id>/compiled.aqo.json`
- `circuit_fs/<job_id>/compiled.qasm`
- `circuit_fs/<job_id>/results.json`
- `circuit_fs/<job_id>/meta.json`
StateStore/LiveQubitManager are no-op or stubs in MVP.

### Error model

State transitions must be valid; invalid transitions are kernel bugs.
Pipeline errors are categorized: ValidationError, CompileError, AllocationError, ExecuteError, PersistError.
Errors map to client-visible JobStatus.ERROR with last_error details.

### Security & privacy

Kernel trusts system-api for authn, but enforces isolation checks via Security Module hooks.

### Observability

Kernel emits:
- Job lifecycle counters
- queue depth
- per-stage latency histograms
- execution latency
- driver error rate
Traces span the full pipeline stages.

### Performance notes

Scheduler uses priority queue.
MVP supports small concurrency; avoid global locks on hot path.
Long calls (compile/execute) are async and must not block scheduling loop.

## Testing plan

Unit tests for state machine transitions.
Integration: simulate compiler + driver-manager (test doubles) and assert DONE + stored artifacts.
Failure injection tests: compiler fail, driver fail.

## Rollout / Migration

MVP ships with simulator target `sim:local` and default config for endpoints.

## Alternatives considered

- Single-process kernel+compiler (postponed).
- Use an external workflow engine (rejected for MVP).

## Open questions

- Exact mapping of dependencies DAG in JobSpec v0.1?
- Do we persist intermediate results for iterative workflows (VQE)?
