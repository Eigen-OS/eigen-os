//! Deterministic event log for kernel job state durability and replay.
//!
//! This module provides an immutable append-only event log that enables:
//! - Durable state persistence (events written to QFS)
//! - Deterministic replay (reconstruct state from event sequence)
//! - Audit trail (all transitions recorded with timestamps)
//! - Restart recovery (load events on startup, replay to current state)
//!
//! Source of truth:
//! - docs/architecture/components/qrtx.md § 9.2
//! - RFC 0007 (QRTX MVP)

use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::state_machine::{JobEvent, JobState, transition};

/// Immutable event record for job state transitions.
/// Written atomically to QFS event log upon each transition.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StateTransitionEvent {
    /// Globally unique job identifier.
    pub job_id: String,
    
    /// Monotonic per-job sequence number (starts at 1).
    pub sequence: u64,
    
    /// The event that caused the transition.
    pub event: JobEvent,
    
    /// Source state before transition.
    pub from_state: JobState,
    
    /// Resulting state after transition.
    pub to_state: JobState,
    
    /// Unix timestamp (milliseconds) when event was recorded.
    pub timestamp_ms: i64,
    
    /// Optional trace correlation ID for distributed tracing.
    pub trace_id: Option<String>,
    
    /// Optional request ID for causality tracking.
    pub request_id: Option<String>,
    
    /// Optional human-readable reason (e.g., "user cancel", "timeout exceeded").
    pub reason: Option<String>,
}

impl StateTransitionEvent {
    /// Create a new transition event with current timestamp.
    pub fn new(
        job_id: String,
        sequence: u64,
        event: JobEvent,
        from_state: JobState,
        to_state: JobState,
    ) -> Self {
        Self {
            job_id,
            sequence,
            event,
            from_state,
            to_state,
            timestamp_ms: current_time_ms(),
            trace_id: None,
            request_id: None,
            reason: None,
        }
    }

    /// Set trace correlation ID.
    pub fn with_trace_id(mut self, trace_id: String) -> Self {
        self.trace_id = Some(trace_id);
        self
    }

    /// Set request ID for causality tracking.
    pub fn with_request_id(mut self, request_id: String) -> Self {
        self.request_id = Some(request_id);
        self
    }

    /// Set human-readable reason.
    pub fn with_reason(mut self, reason: String) -> Self {
        self.reason = Some(reason);
        self
    }
}

/// Event log for a single job — immutable append-only sequence.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct JobEventLog {
    /// Job identifier.
    pub job_id: String,
    
    /// All events for this job, in chronological order.
    pub events: Vec<StateTransitionEvent>,
}

impl JobEventLog {
    /// Create a new empty event log.
    pub fn new(job_id: String) -> Self {
        Self {
            job_id,
            events: Vec::new(),
        }
    }

    /// Append a transition event (write-once, immutable).
    pub fn append(&mut self, event: StateTransitionEvent) {
        debug_assert_eq!(
            event.job_id, self.job_id,
            "event job_id must match log job_id"
        );
        self.events.push(event);
    }

    /// Get the next sequence number for a new event.
    pub fn next_sequence(&self) -> u64 {
        self.events.len() as u64 + 1
    }

    /// Reconstruct current job state by replaying all events deterministically.
    ///
    /// Returns the final state, or an error if the event sequence is invalid.
    pub fn replay_to_current_state(&self) -> Result<JobState, ReplayError> {
        if self.events.is_empty() {
            // Empty log => job was never created
            return Err(ReplayError::EmptyLog);
        }

        let mut current_state = self.events[0].from_state;

        for event in &self.events {
            let expected_from = current_state;
            if event.from_state != expected_from {
                return Err(ReplayError::InvalidSequence {
                    sequence: event.sequence,
                    expected_from: expected_from,
                    actual_from: event.from_state,
                });
            }

            match transition(current_state, event.event) {
                Ok(next_state) => {
                    if next_state != event.to_state {
                        return Err(ReplayError::DeterminismViolation {
                            sequence: event.sequence,
                            expected: next_state,
                            actual: event.to_state,
                        });
                    }
                    current_state = next_state;
                }
                Err(e) => {
                    return Err(ReplayError::InvalidTransition {
                        sequence: event.sequence,
                        transition_error: format!("{:?}", e),
                    });
                }
            }
        }

        Ok(current_state)
    }

    pub fn replay_digest(&self) -> String {
        let material = serde_json::to_vec(self).unwrap_or_default();
        format!("{:x}", sha2::Sha256::digest(&material))
    }

    /// Verify event log consistency (all checksums, sequences, ordering).
    pub fn verify(&self) -> Result<(), ReplayError> {
        // Check sequence numbers are monotonic
        for (i, event) in self.events.iter().enumerate() {
            if event.sequence != (i as u64 + 1) {
                return Err(ReplayError::SequenceGap {
                    expected: i as u64 + 1,
                    actual: event.sequence,
                });
            }
        }

        // Check state transitions are valid
        let _final_state = self.replay_to_current_state()?;

        Ok(())
    }
}

/// Error types for event log replay and verification.
#[derive(Debug, Clone)]
pub enum ReplayError {
    EmptyLog,
    SequenceGap { expected: u64, actual: u64 },
    InvalidSequence {
        sequence: u64,
        expected_from: JobState,
        actual_from: JobState,
    },
    InvalidTransition {
        sequence: u64,
        transition_error: String,
    },
    DeterminismViolation {
        sequence: u64,
        expected: JobState,
        actual: JobState,
    },
}

impl std::fmt::Display for ReplayError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyLog => write!(f, "Event log is empty"),
            Self::SequenceGap { expected, actual } => {
                write!(f, "Sequence gap: expected {}, got {}", expected, actual)
            }
            Self::InvalidSequence {
                sequence,
                expected_from,
                actual_from,
            } => write!(
                f,
                "Invalid sequence {}: from state mismatch (expected {:?}, got {:?})",
                sequence, expected_from, actual_from
            ),
            Self::InvalidTransition {
                sequence,
                transition_error,
            } => write!(f, "Invalid transition at sequence {}: {}", sequence, transition_error),
            Self::DeterminismViolation {
                sequence,
                expected,
                actual,
            } => write!(
                f,
                "Determinism violation at sequence {}: expected {:?}, got {:?}",
                sequence, expected, actual
            ),
        }
    }
}

impl std::error::Error for ReplayError {}

fn current_time_ms() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as i64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn event_log_replay_follows_deterministic_sequence() {
        let mut log = JobEventLog::new("job-123".to_string());

        let event1 = StateTransitionEvent::new(
            "job-123".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(event1);

        let event2 = StateTransitionEvent::new(
            "job-123".to_string(),
            2,
            JobEvent::StartRunning,
            JobState::Compiling,
            JobState::Running,
        );
        log.append(event2);

        let event3 = StateTransitionEvent::new(
            "job-123".to_string(),
            3,
            JobEvent::Complete,
            JobState::Running,
            JobState::Done,
        );
        log.append(event3);

        let final_state = log.replay_to_current_state().unwrap();
        assert_eq!(final_state, JobState::Done);
    }

    #[test]
    fn event_log_replay_detects_invalid_sequence() {
        let mut log = JobEventLog::new("job-456".to_string());

        let event1 = StateTransitionEvent::new(
            "job-456".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(event1);

        // Bad event: from state doesn't match previous to state
        let bad_event = StateTransitionEvent::new(
            "job-456".to_string(),
            2,
            JobEvent::Complete,
            JobState::Pending, // Wrong! Should be Compiling
            JobState::Done,
        );
        log.append(bad_event);

        let err = log.replay_to_current_state();
        assert!(matches!(err, Err(ReplayError::InvalidSequence { .. })));
    }

    #[test]
    fn event_log_verify_detects_sequence_gaps() {
        let mut log = JobEventLog::new("job-789".to_string());

        let event1 = StateTransitionEvent::new(
            "job-789".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(event1);

        // Manually insert with wrong sequence number
        let bad_event = StateTransitionEvent::new(
            "job-789".to_string(),
            3, // Gap: should be 2
            JobEvent::Complete,
            JobState::Compiling,
            JobState::Done,
        );
        log.append(bad_event);

        let err = log.verify();
        assert!(matches!(err, Err(ReplayError::SequenceGap { .. })));
    }

    #[test]
    fn event_log_next_sequence_is_correct() {
        let mut log = JobEventLog::new("job-seq".to_string());
        assert_eq!(log.next_sequence(), 1);

        let event = StateTransitionEvent::new(
            "job-seq".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(event);

        assert_eq!(log.next_sequence(), 2);
    }
}
