//! In-memory job store (MVP placeholder).
//!
//! TODO: replace with a QFS-backed persistent store.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use parking_lot::RwLock;
use uuid::Uuid;

use qrtx::state_machine::{transition, JobEvent, JobState, TransitionError};

/// A stored job record (MVP subset).
#[derive(Debug, Clone)]
pub struct JobRecord {
    pub job_id: String,
    pub name: String,
    pub state: JobState,
    pub created_at_unix_ms: i64,
    pub updated_at_unix_ms: i64,
    pub error_code: Option<String>,
    pub error_summary: Option<String>,
    pub error_details_ref: Option<String>,
    pub counts: HashMap<String, i64>,
}

#[derive(Debug, Clone)]
pub struct JobStore {
    inner: std::sync::Arc<RwLock<HashMap<String, JobRecord>>>,
}

impl Default for JobStore {
    fn default() -> Self {
        Self {
            inner: std::sync::Arc::new(RwLock::new(HashMap::new())),
        }
    }
}

impl JobStore {
    pub fn create_job(&self, name: String) -> JobRecord {
        let now = unix_ms();
        let job_id = Uuid::new_v4().to_string();
        let record = JobRecord {
            job_id: job_id.clone(),
            name,
            state: JobState::Pending,
            created_at_unix_ms: now,
            updated_at_unix_ms: now,
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            counts: HashMap::new(),
        };
        self.inner.write().insert(job_id.clone(), record.clone());
        record
    }

    pub fn get(&self, job_id: &str) -> Option<JobRecord> {
        self.inner.read().get(job_id).cloned()
    }

    pub fn apply_event(&self, job_id: &str, event: JobEvent) -> Result<JobRecord, TransitionError> {
        let mut guard = self.inner.write();
        let rec = guard.get_mut(job_id).ok_or(TransitionError::Invalid {
            from: JobState::Error,
            event,
        })?;

        let next = transition(rec.state, event)?;
        rec.state = next;
        rec.updated_at_unix_ms = unix_ms();
        Ok(rec.clone())
    }

    pub fn set_error(
        &self,
        job_id: &str,
        code: String,
        summary: String,
        details_ref: Option<String>,
    ) {
        if let Some(rec) = self.inner.write().get_mut(job_id) {
            rec.error_code = Some(code);
            rec.error_summary = Some(summary);
            rec.error_details_ref = details_ref;
            rec.updated_at_unix_ms = unix_ms();
        }
    }

    pub fn set_counts(&self, job_id: &str, counts: HashMap<String, i64>) {
        if let Some(rec) = self.inner.write().get_mut(job_id) {
            rec.counts = counts;
            rec.updated_at_unix_ms = unix_ms();
        }
    }

    pub fn clone_handle(&self) -> Self {
        Self {
            inner: self.inner.clone(),
        }
    }
}

fn unix_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as i64
}
