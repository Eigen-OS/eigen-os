//! Durable job state store with QFS persistence and deterministic replay.
//!
//! This module extends the MVP in-memory JobStore with:
//! - Event-sourced state transitions (immutable append-only log)
//! - QFS-backed durability (all events written to `qfs://jobs/<job_id>/state/events.jsonl`)
//! - Deterministic recovery (replay event log on startup)
//! - Audit trail (all transitions recorded with trace context)
//!
//! Contract:
//! - `docs/architecture/components/qrtx.md` § 9.2
//! - ADR: Kernel Durable State & Event Sourcing (TBD)

use std::collections::HashMap;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

use parking_lot::RwLock;
use uuid::Uuid;

use qrtx::event_log::{JobEventLog, StateTransitionEvent};
use qrtx::state_machine::{JobEvent, JobState, TransitionError, transition};
use qfs::CircuitFsLocal;

/// A stored job record (extended from MVP) with QFS persistence.
#[derive(Debug, Clone)]
pub struct DurableJobRecord {
    pub job_id: String,
    pub name: String,
    pub state: JobState,
    pub created_at_unix_ms: i64,
    pub updated_at_unix_ms: i64,
    pub error_code: Option<String>,
    pub error_summary: Option<String>,
    pub error_details_ref: Option<String>,
    pub counts: HashMap<String, i64>,
    pub results_metadata: HashMap<String, String>,
    
    /// Event sequence number (for next transition).
    pub sequence: u64,
    
    /// Trace correlation ID (if available).
    pub trace_id: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct DurableJobReplaySnapshot {
    job_id: String,
    name: String,
    created_at_unix_ms: i64,
    updated_at_unix_ms: i64,
    trace_id: Option<String>,
    sequence: u64,
    state: JobState,
    error_code: Option<String>,
    error_summary: Option<String>,
    error_details_ref: Option<String>,
    counts: HashMap<String, i64>,
    results_metadata: HashMap<String, String>,
}

/// Durable job store with QFS persistence and event replay capability.
pub struct DurableJobStore {
    /// In-memory cache of job records (reconstructed from event logs on startup).
    records: std::sync::Arc<RwLock<HashMap<String, DurableJobRecord>>>,
    
    /// QFS handle for persistent event storage.
    qfs: CircuitFsLocal,
    
    /// Event logs (in-memory cache, synchronized with QFS).
    event_logs: std::sync::Arc<RwLock<HashMap<String, JobEventLog>>>,
}

impl DurableJobStore {
    /// Create a new durable store, optionally loading from QFS.
    pub fn new(qfs: CircuitFsLocal) -> Self {
        Self {
            records: std::sync::Arc::new(RwLock::new(HashMap::new())),
            qfs,
            event_logs: std::sync::Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Recover all jobs from QFS event logs (called on startup).
    ///
    /// Scans `qfs://jobs/*/state/events.jsonl` and replays each job's event sequence.
    pub fn recover_from_qfs(&self) -> Result<usize, Box<dyn std::error::Error>> {

        let mut recovered = 0usize;
        let refs = self.qfs.list_refs("qfs://jobs/")?;
        let mut job_ids = std::collections::BTreeSet::new();
        for qfs_ref in refs {
            let trimmed = qfs_ref.strip_prefix("qfs://").unwrap_or(&qfs_ref);
            let mut parts = trimmed.split('/');
            if matches!(parts.next(), Some("jobs")) {
                if let Some(job_id) = parts.next() {
                    job_ids.insert(job_id.to_string());
                }
            }
        }

        for job_id in job_ids {
            let state_events_ref = format!("qfs://jobs/{job_id}/logs/state_events.jsonl");
            let snapshot_ref = format!("qfs://jobs/{job_id}/logs/replay_snapshot.jsonl");
            let snapshot_bytes = match self.qfs.read_bytes(&snapshot_ref) {
                Ok(bytes) => bytes,
                Err(_) => continue,
            };
            let events_bytes = match self.qfs.read_bytes(&state_events_ref) {
                Ok(bytes) => bytes,
                Err(_) => continue,
            };

            let snapshot_text = String::from_utf8(snapshot_bytes)?;
            let snapshot_line = snapshot_text
                .lines()
                .next()
                .ok_or("missing replay snapshot")?;
            let snapshot: DurableJobReplaySnapshot = serde_json::from_str(snapshot_line)?;

            let mut log = JobEventLog::new(job_id.clone());
            for line in String::from_utf8(events_bytes)?.lines() {
                if line.trim().is_empty() {
                    continue;
                }
                log.append(serde_json::from_str(line)?);
            }
            log.verify().map_err(|e| format!("event log verification failed: {e}"))?;

            let current_state = log.replay_to_current_state().map_err(|e| format!("{e}"))?;
            let record = DurableJobRecord {
                job_id: snapshot.job_id.clone(),
                name: snapshot.name,
                state: current_state,
                created_at_unix_ms: snapshot.created_at_unix_ms,
                updated_at_unix_ms: snapshot.updated_at_unix_ms,
                error_code: snapshot.error_code,
                error_summary: snapshot.error_summary,
                error_details_ref: snapshot.error_details_ref,
                counts: snapshot.counts,
                results_metadata: snapshot.results_metadata,
                sequence: snapshot.sequence,
                trace_id: snapshot.trace_id,
            };

            self.event_logs.write().insert(job_id.clone(), log);
            self.records.write().insert(job_id, record);
            recovered += 1;
        }

        Ok(recovered)
    }

    /// Create a new job (initial state = PENDING).
    pub fn create_job(&self, name: String) -> DurableJobRecord {
        let now = unix_ms();
        let job_id = Uuid::new_v4().to_string();

        let record = DurableJobRecord {
            job_id: job_id.clone(),
            name,
            state: JobState::Pending,
            created_at_unix_ms: now,
            updated_at_unix_ms: now,
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            counts: HashMap::new(),
            results_metadata: HashMap::new(),
            sequence: 1,
            trace_id: None,
        };

        // Initialize event log
        let mut event_logs = self.event_logs.write();
        event_logs.insert(job_id.clone(), JobEventLog::new(job_id.clone()));

        self.records.write().insert(job_id.clone(), record.clone());
        let snapshot = DurableJobReplaySnapshot {
            job_id: job_id.clone(),
            name: record.name.clone(),
            created_at_unix_ms: record.created_at_unix_ms,
            updated_at_unix_ms: record.updated_at_unix_ms,
            trace_id: record.trace_id.clone(),
            sequence: record.sequence,
            state: record.state,
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            counts: HashMap::new(),
            results_metadata: HashMap::new(),
        };
        let snapshot_json = serde_json::to_string(&snapshot).unwrap();
        let _ = self.qfs.append_log_line(&job_id, "replay_snapshot", &snapshot_json);
        record
    }

    /// Get current job record.
    pub fn get(&self, job_id: &str) -> Option<DurableJobRecord> {
        self.records.read().get(job_id).cloned()
    }

    /// Apply a transition event, persisting to QFS and event log.
    pub fn apply_event(
        &self,
        job_id: &str,
        event: JobEvent,
    ) -> Result<DurableJobRecord, TransitionError> {
        let mut records_guard = self.records.write();
        let rec = records_guard
            .get_mut(job_id)
            .ok_or(TransitionError::Invalid {
                from: JobState::Pending,
                event,
            })?;

        // Check if already terminal (idempotent)
        if is_terminal(rec.state) {
            if terminal_state_for_event(event) == Some(rec.state) {
                return Ok(rec.clone());
            }
            return Err(TransitionError::Invalid {
                from: rec.state,
                event,
            });
        }

        // Compute next state
        let next = transition(rec.state, event)?;
        let now = unix_ms();

        // Create transition event
        let transition_event = StateTransitionEvent::new(
            job_id.to_string(),
            rec.sequence,
            event,
            rec.state,
            next,
        )
        .with_trace_id(rec.trace_id.clone().unwrap_or_default());

        // Persist event to QFS event log
        let event_json = serde_json::to_string(&transition_event).unwrap_or_default();
        if let Err(e) = self.qfs.append_log_line(job_id, "state_events", &event_json) {
            tracing::warn!("failed to persist event to QFS: {}", e);
            // Continue anyway (fixture mode tolerance)
        }

        // Update in-memory event log
        if let Some(logs) = self.event_logs.write().get_mut(job_id) {
            logs.append(transition_event);
        }

        // Update record
        rec.state = next;
        rec.updated_at_unix_ms = now;
        rec.sequence += 1;

        Ok(rec.clone())
    }

    /// Set error metadata on a job record.
    pub fn set_error(
        &self,
        job_id: &str,
        code: String,
        summary: String,
        details_ref: Option<String>,
    ) {
        if let Some(rec) = self.records.write().get_mut(job_id) {
            rec.error_code = Some(code);
            rec.error_summary = Some(summary);
            rec.error_details_ref = details_ref;
            rec.updated_at_unix_ms = unix_ms();
        }
    }

    /// Set execution counts.
    pub fn set_counts(&self, job_id: &str, counts: HashMap<String, i64>) {
        if let Some(rec) = self.records.write().get_mut(job_id) {
            rec.counts = counts;
            rec.updated_at_unix_ms = unix_ms();
        }
    }

    /// Set results metadata.
    pub fn set_results_metadata(&self, job_id: &str, metadata: HashMap<String, String>) {
        if let Some(rec) = self.records.write().get_mut(job_id) {
            rec.results_metadata = metadata;
            rec.updated_at_unix_ms = unix_ms();
        }
    }

    /// Get event log for a job (for replay verification).
    pub fn get_event_log(&self, job_id: &str) -> Option<JobEventLog> {
        self.event_logs.read().get(job_id).cloned()
    }

    /// Verify event log consistency (deterministic replay).
    pub fn verify_event_log(&self, job_id: &str) -> Result<JobState, String> {
        let event_logs = self.event_logs.read();
        let log = event_logs
            .get(job_id)
            .ok_or_else(|| format!("No event log for job {}", job_id))?;

        log.verify()
            .map_err(|e| format!("Event log verification failed: {}", e))?;

        log.replay_to_current_state()
            .map_err(|e| format!("Event log replay failed: {}", e))
    }

    /// Clone handle for sharing across async boundaries.
    pub fn clone_handle(&self) -> Self {
        Self {
            records: self.records.clone(),
            qfs: self.qfs.clone(),
            event_logs: self.event_logs.clone(),
        }
    }
}

fn is_terminal(state: JobState) -> bool {
    matches!(
        state,
        JobState::Done | JobState::Error | JobState::Cancelled | JobState::Timeout
    )
}

fn terminal_state_for_event(event: JobEvent) -> Option<JobState> {
    match event {
        JobEvent::Complete => Some(JobState::Done),
        JobEvent::Fail => Some(JobState::Error),
        JobEvent::Cancel => Some(JobState::Cancelled),
        JobEvent::TimeOut => Some(JobState::Timeout),
        _ => None,
    }
}

fn unix_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as i64
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_store() -> DurableJobStore {
        // For tests, use a temp directory
        let temp_dir = tempfile::tempdir().unwrap();
        let qfs = CircuitFsLocal::new(temp_dir.path().to_str().unwrap());
        DurableJobStore::new(qfs)
    }

    #[test]
    fn durable_store_creates_job_with_pending_state() {
        let store = make_store();
        let job = store.create_job("test-job".to_string());

        assert_eq!(job.state, JobState::Pending);
        assert_eq!(job.sequence, 1);
    }

    #[test]
    fn durable_store_records_state_transitions() {
        let store = make_store();
        let job = store.create_job("test-job".to_string());
        let job_id = job.job_id;

        // Transition: PENDING → COMPILING
        let job2 = store
            .apply_event(&job_id, JobEvent::StartCompiling)
            .unwrap();
        assert_eq!(job2.state, JobState::Compiling);
        assert_eq!(job2.sequence, 2);

        // Transition: COMPILING → RUNNING
        let job3 = store
            .apply_event(&job_id, JobEvent::StartRunning)
            .unwrap();
        assert_eq!(job3.state, JobState::Running);
        assert_eq!(job3.sequence, 3);
    }

    #[test]
    fn durable_store_event_log_replay_deterministic() {
        let store = make_store();
        let job = store.create_job("test-job".to_string());
        let job_id = job.job_id;

        store.apply_event(&job_id, JobEvent::StartCompiling).unwrap();
        store.apply_event(&job_id, JobEvent::StartRunning).unwrap();
        store.apply_event(&job_id, JobEvent::Complete).unwrap();

        // Verify event log replays to same state
        let final_state = store.verify_event_log(&job_id).unwrap();
        assert_eq!(final_state, JobState::Done);
    }

    #[test]
    fn durable_store_terminal_transitions_are_idempotent() {
        let store = make_store();
        let job = store.create_job("test-job".to_string());
        let job_id = job.job_id;

        store.apply_event(&job_id, JobEvent::StartCompiling).unwrap();
        store.apply_event(&job_id, JobEvent::StartRunning).unwrap();
        let job_done = store.apply_event(&job_id, JobEvent::Complete).unwrap();

        // Replay terminal event
        let job_done_again = store
            .apply_event(&job_id, JobEvent::Complete)
            .unwrap();

        assert_eq!(job_done.state, job_done_again.state);
        assert_eq!(job_done_again.state, JobState::Done);
    }

    #[test]
    fn durable_store_rejects_invalid_transitions() {
        let store = make_store();
        let job = store.create_job("test-job".to_string());
        let job_id = job.job_id;

        // Try PENDING → RUNNING directly (should fail)
        let err = store.apply_event(&job_id, JobEvent::StartRunning);
        assert!(err.is_err());
    }
}
