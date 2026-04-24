//! Deterministic job lifecycle state machine for the MVP kernel.
//!
//! Source of truth:
//! - docs/architecture/components/qrtx.md
//! - RFC 0007 (QRTX MVP)

use thiserror::Error;

/// Canonical MVP job lifecycle states.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobState {
    Pending,
    Validating,
    Compiling,
    Queued,
    Allocating,
    Executing,
    Completing,
    Completed,
    Failed,
    Cancelled,
    Timeout,
}

/// Optional MVP execution sub-state while [`JobState::Executing`] is active.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExecutingSubState {
    QuantumInitializing,
    QuantumRunning,
    ClassicalRunning,
    Measuring,
    PostProcessing,
}

/// Events that can cause a state transition.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JobEvent {
    StartValidation,
    FinishValidation,
    StartCompiling,
    FinishCompiling,
    StartAllocating,
    FinishAllocating,
    StartExecuting,
    FinishExecuting,
    StartCompleting,
    FinishCompleting,
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
        (S::Pending, E::StartValidation) => S::Validating,
        (S::Validating, E::FinishValidation) => S::Compiling,
        (S::Compiling, E::FinishCompiling) => S::Queued,
        (S::Queued, E::StartAllocating) => S::Allocating,
        (S::Allocating, E::FinishAllocating) => S::Executing,
        (S::Executing, E::FinishExecuting) => S::Completing,
        (S::Completing, E::FinishCompleting) => S::Completed,

        // Optional explicit start events for stage boundaries.
        (S::Compiling, E::StartCompiling) => S::Compiling,
        (S::Allocating, E::StartAllocating) => S::Allocating,
        (S::Executing, E::StartExecuting) => S::Executing,
        (S::Completing, E::StartCompleting) => S::Completing,

        // Cancellation/failure/timeout are allowed from non-terminal states.
        (
            S::Pending
            | S::Validating
            | S::Compiling
            | S::Queued
            | S::Allocating
            | S::Executing
            | S::Completing,
            E::Cancel,
        ) => S::Cancelled,
        (
            S::Pending
            | S::Validating
            | S::Compiling
            | S::Queued
            | S::Allocating
            | S::Executing
            | S::Completing,
            E::Fail,
        ) => S::Failed,
        (
            S::Pending
            | S::Validating
            | S::Compiling
            | S::Queued
            | S::Allocating
            | S::Executing
            | S::Completing,
            E::TimeOut,
        ) => S::Timeout,

        // Terminal states do not accept transitions.
        (S::Completed | S::Failed | S::Cancelled | S::Timeout, _) => {
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
        let s1 = transition(s0, JobEvent::StartValidation).unwrap();
        let s2 = transition(s1, JobEvent::FinishValidation).unwrap();
        let s3 = transition(s2, JobEvent::FinishCompiling).unwrap();
        let s4 = transition(s3, JobEvent::StartAllocating).unwrap();
        let s5 = transition(s4, JobEvent::FinishAllocating).unwrap();
        let s6 = transition(s5, JobEvent::FinishExecuting).unwrap();
        let s7 = transition(s6, JobEvent::FinishCompleting).unwrap();
        assert_eq!(s7, JobState::Completed);
    }

    #[test]
    fn cancellation_failure_timeout_are_allowed_from_non_terminal_states() {
        let non_terminal = [
            JobState::Pending,
            JobState::Compiling,
            JobState::Queued,
            JobState::Allocating,
            JobState::Executing,
            JobState::Completing,
        ];

        for s in non_terminal {
            assert_eq!(transition(s, JobEvent::Cancel).unwrap(), JobState::Cancelled);
        }
    }

    #[test]
    fn terminal_states_reject_all_events() {
        let events = [
            JobEvent::StartValidation,
            JobEvent::FinishValidation,
            JobEvent::StartCompiling,
            JobEvent::FinishCompiling,
            JobEvent::StartAllocating,
            JobEvent::FinishAllocating,
            JobEvent::StartExecuting,
            JobEvent::FinishExecuting,
            JobEvent::StartCompleting,
            JobEvent::FinishCompleting,
            JobEvent::Fail,
            JobEvent::Cancel,
            JobEvent::TimeOut,
        ];

        for s in [
            JobState::Completed,
            JobState::Failed,
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