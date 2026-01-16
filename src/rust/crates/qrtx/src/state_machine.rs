//! Deterministic job lifecycle state machine for the MVP kernel.
//!
//! Source of truth:
//! - RFC 0007 (QRTX MVP)
//! - Issue #25 acceptance criteria

use thiserror::Error;

/// MVP job lifecycle states exposed to System API via internal gRPC.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobState {
    Pending,
    Compiling,
    Queued,
    Running,
    Done,
    Error,
    Cancelled,
}

/// Events that can cause a state transition.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobEvent {
    Enqueued,
    StartCompiling,
    FinishCompiling,
    StartRunning,
    FinishRunningOk,
    Fail,
    Cancel,
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum TransitionError {
    #[error("invalid transition: {from:?} --{event:?}--> ?")]
    Invalid { from: JobState, event: JobEvent },
}

/// Computes the next state for a given current state and event.
///
/// This function is pure and deterministic and should be the only place
/// where transition rules are encoded.
pub fn transition(from: JobState, event: JobEvent) -> Result<JobState, TransitionError> {
    use JobEvent as E;
    use JobState as S;

    let next = match (from, event) {
        (S::Pending, E::StartCompiling) => S::Compiling,
        (S::Compiling, E::FinishCompiling) => S::Queued,
        (S::Queued, E::StartRunning) => S::Running,
        (S::Running, E::FinishRunningOk) => S::Done,

        // Cancellation is allowed from any non-terminal state.
        (S::Pending | S::Compiling | S::Queued | S::Running, E::Cancel) => S::Cancelled,

        // Failure is allowed from any non-terminal state.
        (S::Pending | S::Compiling | S::Queued | S::Running, E::Fail) => S::Error,

        // Enqueued is a creation event; the record starts in Pending.
        (S::Pending, E::Enqueued) => S::Pending,

        // Terminal states do not accept transitions.
        (S::Done | S::Error | S::Cancelled, _) => {
            return Err(TransitionError::Invalid { from, event });
        }

        // Everything else is invalid.
        _ => {
            return Err(TransitionError::Invalid { from, event });
        }
    };

    Ok(next)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn happy_path_transitions() {
        let s0 = JobState::Pending;
        let s1 = transition(s0, JobEvent::StartCompiling).unwrap();
        let s2 = transition(s1, JobEvent::FinishCompiling).unwrap();
        let s3 = transition(s2, JobEvent::StartRunning).unwrap();
        let s4 = transition(s3, JobEvent::FinishRunningOk).unwrap();
        assert_eq!(s4, JobState::Done);
    }

    #[test]
    fn cancel_is_allowed_from_non_terminal_states() {
        for s in [
            JobState::Pending,
            JobState::Compiling,
            JobState::Queued,
            JobState::Running,
        ] {
            assert_eq!(transition(s, JobEvent::Cancel).unwrap(), JobState::Cancelled);
        }
    }

    #[test]
    fn terminal_states_reject_all_events() {
        for s in [JobState::Done, JobState::Error, JobState::Cancelled] {
            let err = transition(s, JobEvent::Cancel).unwrap_err();
            assert_eq!(err, TransitionError::Invalid { from: s, event: JobEvent::Cancel });
        }
    }
}
