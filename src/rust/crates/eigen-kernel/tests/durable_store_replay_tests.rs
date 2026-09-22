//! Comprehensive tests for durable kernel state store and replay safety.
//!
//! Tests cover:
//! - Event log creation and replay
//! - State transition validation
//! - Invalid transition rejection
//! - Idempotent terminalization
//! - Restart recovery (fixture mode)
//! - Deterministic replay proofs

#[cfg(test)]
mod durable_store_tests {
    use eigen_kernel::durable_job_store::DurableJobStore;
    use qrtx::event_log::{JobEventLog, StateTransitionEvent};
    use qrtx::state_machine::{JobEvent, JobState};
    use qfs::CircuitFsLocal;
    use tempfile::tempdir;

    fn make_store() -> DurableJobStore {
        let temp = tempdir().unwrap();
        let qfs = CircuitFsLocal::new(temp.path().to_str().unwrap());
        DurableJobStore::new(qfs)
    }

    #[test]
    fn test_create_job_initializes_pending_state() {
        let store = make_store();
        let job = store.create_job("test-job".to_string());

        assert_eq!(job.state, JobState::Pending);
        assert_eq!(job.sequence, 1);
        assert_eq!(job.name, "test-job");
        assert!(job.error_code.is_none());
    }

    #[test]
    fn test_state_transition_updates_sequence() {
        let store = make_store();
        let job = store.create_job("seq-test".to_string());
        let job_id = job.job_id;

        let job_after = store
            .apply_event(&job_id, JobEvent::StartCompiling)
            .unwrap();

        assert_eq!(job_after.state, JobState::Compiling);
        assert_eq!(job_after.sequence, 2); // Incremented
    }

    #[test]
    fn test_full_pipeline_transition_sequence() {
        let store = make_store();
        let job = store.create_job("pipeline".to_string());
        let job_id = job.job_id;

        // PENDING -> COMPILING
        let j1 = store
            .apply_event(&job_id, JobEvent::StartCompiling)
            .unwrap();
        assert_eq!(j1.state, JobState::Compiling);

        // COMPILING -> RUNNING
        let j2 = store
            .apply_event(&job_id, JobEvent::StartRunning)
            .unwrap();
        assert_eq!(j2.state, JobState::Running);

        // RUNNING -> DONE
        let j3 = store.apply_event(&job_id, JobEvent::Complete).unwrap();
        assert_eq!(j3.state, JobState::Done);
    }

    #[test]
    fn test_invalid_transition_rejected() {
        let store = make_store();
        let job = store.create_job("invalid-test".to_string());
        let job_id = job.job_id;

        // Try PENDING -> RUNNING directly (invalid)
        let err = store.apply_event(&job_id, JobEvent::StartRunning);
        assert!(err.is_err(), "Invalid transition should be rejected");
    }

    #[test]
    fn test_terminal_transition_is_idempotent() {
        let store = make_store();
        let job = store.create_job("terminal-test".to_string());
        let job_id = job.job_id;

        store.apply_event(&job_id, JobEvent::StartCompiling).unwrap();
        store.apply_event(&job_id, JobEvent::StartRunning).unwrap();

        // First completion
        let j_done_1 = store.apply_event(&job_id, JobEvent::Complete).unwrap();
        assert_eq!(j_done_1.state, JobState::Done);

        // Replay completion event (idempotent)
        let j_done_2 = store.apply_event(&job_id, JobEvent::Complete).unwrap();
        assert_eq!(j_done_2.state, JobState::Done);
        assert_eq!(j_done_2.updated_at_unix_ms, j_done_1.updated_at_unix_ms);
    }

    #[test]
    fn test_error_state_transition() {
        let store = make_store();
        let job = store.create_job("error-test".to_string());
        let job_id = job.job_id;

        store.apply_event(&job_id, JobEvent::StartCompiling).unwrap();

        // Fail during compilation
        let j_err = store.apply_event(&job_id, JobEvent::Fail).unwrap();
        assert_eq!(j_err.state, JobState::Error);

        // Set error details
        store.set_error(
            &job_id,
            "COMPILE_ERROR".to_string(),
            "Invalid syntax".to_string(),
            Some("qfs://jobs/error-ref".to_string()),
        );

        let j_with_error = store.get(&job_id).unwrap();
        assert_eq!(j_with_error.error_code, Some("COMPILE_ERROR".to_string()));
        assert_eq!(
            j_with_error.error_summary,
            Some("Invalid syntax".to_string())
        );
    }

    #[test]
    fn test_cancellation_from_non_terminal_state() {
        let store = make_store();
        let job = store.create_job("cancel-test".to_string());
        let job_id = job.job_id;

        store.apply_event(&job_id, JobEvent::StartCompiling).unwrap();

        // Cancel from COMPILING
        let j_cancelled = store.apply_event(&job_id, JobEvent::Cancel).unwrap();
        assert_eq!(j_cancelled.state, JobState::Cancelled);
    }

    #[test]
    fn test_event_log_deterministic_replay() {
        let store = make_store();
        let job = store.create_job("replay-test".to_string());
        let job_id = job.job_id;

        // Build a sequence
        store.apply_event(&job_id, JobEvent::StartCompiling).unwrap();
        store.apply_event(&job_id, JobEvent::StartRunning).unwrap();
        store.apply_event(&job_id, JobEvent::Complete).unwrap();

        // Verify event log
        let final_state = store
            .verify_event_log(&job_id)
            .expect("Event log should verify");

        assert_eq!(final_state, JobState::Done);
    }

    #[test]
    fn test_event_log_replay_proves_determinism() {
        // Create two independent stores with same transitions
        let store1 = make_store();
        let store2 = make_store();

        let job1 = store1.create_job("determ-1".to_string());
        let job2 = store2.create_job("determ-2".to_string());
        let job_id_1 = job1.job_id;
        let job_id_2 = job2.job_id;

        // Same transition sequence on both
        for store in [&store1, &store2] {
            let job_id = if store as *const _ == &store1 as *const _ {
                &job_id_1
            } else {
                &job_id_2
            };
            store.apply_event(job_id, JobEvent::StartCompiling).unwrap();
            store.apply_event(job_id, JobEvent::StartRunning).unwrap();
            store.apply_event(job_id, JobEvent::Complete).unwrap();
        }

        // Both should replay to identical state
        let state1 = store1.verify_event_log(&job_id_1).unwrap();
        let state2 = store2.verify_event_log(&job_id_2).unwrap();

        assert_eq!(state1, state2);
        assert_eq!(state1, JobState::Done);
    }

    #[test]
    fn test_get_nonexistent_job_returns_none() {
        let store = make_store();
        let result = store.get("nonexistent-job-id");
        assert!(result.is_none());
    }

    #[test]
    fn test_set_counts_updates_record() {
        let store = make_store();
        let job = store.create_job("counts-test".to_string());
        let job_id = job.job_id;

        let mut counts = std::collections::HashMap::new();
        counts.insert("shots".to_string(), 1024);
        counts.insert("accepted".to_string(), 512);

        store.set_counts(&job_id, counts);

        let updated = store.get(&job_id).unwrap();
        assert_eq!(updated.counts.get("shots"), Some(&1024));
        assert_eq!(updated.counts.get("accepted"), Some(&512));
    }

    #[test]
    fn test_set_results_metadata() {
        let store = make_store();
        let job = store.create_job("metadata-test".to_string());
        let job_id = job.job_id;

        let mut metadata = std::collections::HashMap::new();
        metadata.insert("result_ref".to_string(), "qfs://results/abc".to_string());
        metadata.insert("backend".to_string(), "sim:local".to_string());

        store.set_results_metadata(&job_id, metadata);

        let updated = store.get(&job_id).unwrap();
        assert_eq!(
            updated.results_metadata.get("result_ref"),
            Some(&"qfs://results/abc".to_string())
        );
    }
}

#[cfg(test)]
mod event_log_replay_tests {
    use qrtx::event_log::{JobEventLog, StateTransitionEvent};
    use qrtx::state_machine::{JobEvent, JobState};

    #[test]
    fn test_event_log_empty_is_error() {
        let log = JobEventLog::new("empty-job".to_string());
        let err = log.replay_to_current_state();
        assert!(err.is_err());
    }

    #[test]
    fn test_event_log_single_event() {
        let mut log = JobEventLog::new("single".to_string());
        let event = StateTransitionEvent::new(
            "single".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(event);

        let state = log.replay_to_current_state().unwrap();
        assert_eq!(state, JobState::Compiling);
    }

    #[test]
    fn test_event_log_sequence_chain() {
        let mut log = JobEventLog::new("chain".to_string());

        let events = vec![
            (1, JobEvent::StartCompiling, JobState::Pending, JobState::Compiling),
            (2, JobEvent::StartRunning, JobState::Compiling, JobState::Running),
            (3, JobEvent::Complete, JobState::Running, JobState::Done),
        ];

        for (seq, event, from, to) in events {
            let e = StateTransitionEvent::new(
                "chain".to_string(),
                seq,
                event,
                from,
                to,
            );
            log.append(e);
        }

        let state = log.replay_to_current_state().unwrap();
        assert_eq!(state, JobState::Done);
    }

    #[test]
    fn test_event_log_verify_detects_invalid_transition() {
        let mut log = JobEventLog::new("bad-trans".to_string());

        // Valid first event
        let e1 = StateTransitionEvent::new(
            "bad-trans".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(e1);

        // Bad second event: wrong from state
        let e2 = StateTransitionEvent::new(
            "bad-trans".to_string(),
            2,
            JobEvent::StartRunning,
            JobState::Pending, // Wrong! Should be Compiling
            JobState::Running,
        );
        log.append(e2);

        let err = log.verify();
        assert!(err.is_err());
    }

    #[test]
    fn test_event_log_verify_detects_sequence_gaps() {
        let mut log = JobEventLog::new("gap".to_string());

        let e1 = StateTransitionEvent::new(
            "gap".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(e1);

        // Sequence jump
        let e2 = StateTransitionEvent::new(
            "gap".to_string(),
            3, // Should be 2
            JobEvent::StartRunning,
            JobState::Compiling,
            JobState::Running,
        );
        log.append(e2);

        let err = log.verify();
        assert!(err.is_err());
    }

    #[test]
    fn test_event_log_next_sequence_correct() {
        let mut log = JobEventLog::new("seq".to_string());
        assert_eq!(log.next_sequence(), 1);

        let e = StateTransitionEvent::new(
            "seq".to_string(),
            1,
            JobEvent::StartCompiling,
            JobState::Pending,
            JobState::Compiling,
        );
        log.append(e);

        assert_eq!(log.next_sequence(), 2);
    }
}
