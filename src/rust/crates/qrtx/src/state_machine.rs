//! Deterministic job lifecycle state machine for the MVP kernel.
//!
//! Source of truth:
//! - docs/architecture/components/qrtx.md
//! - RFC 0007 (QRTX MVP)

use thiserror::Error;

/// Canonical MVP-3 job lifecycle states.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobState {
    Pending,
    Compiling,
    Running,
    Done,
    Error,
    Cancelled,
    Timeout,
}

/// Events that can cause a state transition.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobEvent {
    StartCompiling,
    StartRunning,
    Complete,
    Fail,
    Cancel,
    TimeOut,
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
        (S::Compiling, E::StartRunning) => S::Running,
        (S::Running, E::Complete) => S::Done,

        // Cancellation/failure/timeout are allowed from non-terminal states.
        (S::Pending | S::Compiling | S::Running, E::Cancel) => S::Cancelled,
        (S::Pending | S::Compiling | S::Running, E::Fail) => S::Error,
        (S::Pending | S::Compiling | S::Running, E::TimeOut) => S::Timeout,

        // Terminal states do not accept transitions.
        (S::Done | S::Error | S::Cancelled | S::Timeout, _) => {
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
    fn happy_path_transitions_follow_mvp_pipeline() {
        let s0 = JobState::Pending;
        let s1 = transition(s0, JobEvent::StartCompiling).unwrap();
        let s2 = transition(s1, JobEvent::StartRunning).unwrap();
        let s3 = transition(s2, JobEvent::Complete).unwrap();
        assert_eq!(s3, JobState::Done);
    }

    #[test]
    fn cancellation_failure_timeout_are_allowed_from_non_terminal_states() {
        let non_terminal = [JobState::Pending, JobState::Compiling, JobState::Running];

        for s in non_terminal {
            assert_eq!(
                transition(s, JobEvent::Cancel).unwrap(),
                JobState::Cancelled
            );
        }
    }

    #[test]
    fn terminal_states_reject_all_events() {
        let events = [
            JobEvent::StartCompiling,
            JobEvent::StartRunning,
            JobEvent::Complete,
            JobEvent::Fail,
            JobEvent::Cancel,
            JobEvent::TimeOut,
        ];

        for s in [
            JobState::Done,
            JobState::Error,
            JobState::Cancelled,
            JobState::Timeout,
        ] {
            for event in events {
                let err = transition(s, event).unwrap_err();
                assert_eq!(err, TransitionError::Invalid { from: s, event });
            }
        }
    }
}
