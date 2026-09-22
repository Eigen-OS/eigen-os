# ADR 0027 — Kernel Durable State & Event Sourcing (Product 1.0)

**Status:** Accepted  
**Date:** 2026-06-02  
**Deciders:** Runtime Team  
**Affected Components:** Kernel/QRTX, QFS  

---

## Context

The MVP kernel stores job state in memory only. This creates several Product 1.0 blockers:

1. **No crash recovery** — state is lost on restart
2. **No deterministic replay** — cannot verify execution was valid
3. **No audit trail** — cannot trace decision history
4. **No durability proof** — cannot satisfy compliance requirements

Product 1.0 requires "durable/replayable kernel job state store and transition validator" (#482).

---

## Decision

Implement **event-sourced durable state** for kernel jobs:

### Architecture

1. **Event Log (Immutable)**: All state transitions recorded as events in `qfs://jobs/<job_id>/state/events.jsonl`
   - Each event: `{ sequence, from_state, event, to_state, timestamp, trace_id, ... }`
   - Written atomically to QFS on each transition

2. **In-Memory Cache**: Job records cached in memory for fast access
   - Reconstructed from event logs on startup
   - Single source of truth is event log, not cache

3. **Deterministic Replay**: `replay_to_current_state()` function
   - Validates all events are valid transitions
   - Detects sequence gaps, state inconsistencies, determinism violations
   - Proves job state can be reconstructed from log

### Components

- **`qrtx/src/event_log.rs`**: `StateTransitionEvent`, `JobEventLog`, replay logic
- **`eigen-kernel/src/durable_job_store.rs`**: `DurableJobStore`, QFS persistence
- **Backward compat**: MVP `JobStore` remains (can coexist during migration)

---

## Implementation Details

### Event Log Structure

```rust
pub struct StateTransitionEvent {
    pub job_id: String,
    pub sequence: u64,              // Monotonic per-job
    pub event: JobEvent,            // The triggering event
    pub from_state: JobState,       // State before transition
    pub to_state: JobState,         // State after transition
    pub timestamp_ms: i64,          // Wall-clock timestamp
    pub trace_id: Option<String>,   // Distributed tracing context
    pub request_id: Option<String>, // Causality tracking
    pub reason: Option<String>,     // Human-readable reason
}
```

## QFS Layout

```text
qfs://jobs/<job_id>/state/events.jsonl   (append-only event log)
qfs://jobs/<job_id>/input/job.yaml       (existing: submission)
qfs://jobs/<job_id>/compiled/...         (existing: compiler outputs)
qfs://jobs/<job_id>/results/...          (existing: results/errors)
```

### Replay Guarantees

1. **Deterministic:** Same event log → identical final state (proven by unit tests)
2. **Validating:** Invalid transitions rejected at record time
3. **Auditable:** All decisions timestamped and traced
4. **Recoverable:** Lost in-memory state reconstructed from log on startup


### Restart Recovery (Phase-1)

Current: Stub implementation (fixture mode, no recovery)
Future: Scan QFS jobs/, load events.jsonl, replay each
