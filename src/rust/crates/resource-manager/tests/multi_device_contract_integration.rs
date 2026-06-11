use resource_manager::{
    merge_partial_results, plan_split, MergePolicy, MergeReasonCode, PartialFailureEnvelope,
    PartialFailureReasonCode, PartialResultEnvelope, SplitPlanError, SplitTask,
    MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
};

#[test]
fn split_planner_builds_versioned_shards_with_parent_references() {
    let tasks = vec![
        SplitTask {
            task_id: "task-001".to_string(),
            compatible_backends: vec!["backend-b".to_string(), "backend-a".to_string()],
        },
        SplitTask {
            task_id: "task-002".to_string(),
            compatible_backends: vec!["backend-b".to_string()],
        },
        SplitTask {
            task_id: "task-003".to_string(),
            compatible_backends: vec!["backend-c".to_string()],
        },
    ];

    let manifest = plan_split(
        "job-parent-42",
        &tasks,
        4,
        1_746_200_000_000,
        "trace-xyz",
    )
    .expect("split plan must be valid");

    assert_eq!(manifest.version, MULTI_DEVICE_EXECUTION_CONTRACT_VERSION);
    assert_eq!(manifest.parent_job_id, "job-parent-42");
    assert_eq!(manifest.created_at_ms, 1_746_200_000_000);
    assert_eq!(manifest.trace_id, "trace-xyz");
    assert_eq!(manifest.shard_plans.len(), 3);

    for shard in &manifest.shard_plans {
        assert_eq!(shard.version, MULTI_DEVICE_EXECUTION_CONTRACT_VERSION);
        assert_eq!(shard.parent_job_id, "job-parent-42");
        assert!(shard.shard_id.starts_with("job-parent-42-shard-"));
        assert_eq!(shard.attempt, 1);
        assert_eq!(shard.lease_timeout_ms, None);
        assert_eq!(shard.resource_profile, None);
        assert_eq!(shard.trace_id, "trace-xyz");
        assert!(shard.lineage_ref.as_deref().unwrap_or("").contains(&shard.shard_id));
    }

    let backend_a = manifest
        .shard_plans
        .iter()
        .find(|shard| shard.backend_id == "backend-a")
        .expect("backend-a shard exists");
    assert_eq!(backend_a.task_ids, vec!["task-001"]);

    let backend_b = manifest
        .shard_plans
        .iter()
        .find(|shard| shard.backend_id == "backend-b")
        .expect("backend-b shard exists");
    assert_eq!(backend_b.task_ids, vec!["task-002"]);

    let backend_c = manifest
        .shard_plans
        .iter()
        .find(|shard| shard.backend_id == "backend-c")
        .expect("backend-c shard exists");
    assert_eq!(backend_c.task_ids, vec!["task-003"]);
}

#[test]
fn split_planner_is_deterministic_for_identical_inputs() {
    let tasks = vec![
        SplitTask {
            task_id: "task-001".to_string(),
            compatible_backends: vec!["backend-b".to_string(), "backend-a".to_string()],
        },
        SplitTask {
            task_id: "task-002".to_string(),
            compatible_backends: vec!["backend-b".to_string()],
        },
    ];

    let first = plan_split("job-parent-42", &tasks, 4, 1_746_200_000_000, "trace-xyz")
        .expect("split plan must be valid");
    let second = plan_split("job-parent-42", &tasks, 4, 1_746_200_000_000, "trace-xyz")
        .expect("split plan must be valid");

    assert_eq!(first, second);
    assert_eq!(first.shard_plans[0].attempt, 1);
    assert_eq!(first.shard_plans[0].trace_id, "trace-xyz");
}

#[test]
fn split_planner_rejects_tasks_without_compatible_backends() {
    let tasks = vec![SplitTask {
        task_id: "task-x".to_string(),
        compatible_backends: vec![],
    }];

    let err = plan_split("job-parent-42", &tasks, 4, 1_746_200_000_000, "trace-xyz")
        .expect_err("planner must reject task");
    assert_eq!(
        err,
        SplitPlanError::EmptyCompatibleBackends {
            task_id: "task-x".to_string()
        }
    );
}

#[test]
fn merge_all_required_reports_missing_and_failed_shards_in_standardized_envelope() {
    let expected = vec![
        "job-parent-42-shard-001".to_string(),
        "job-parent-42-shard-002".to_string(),
        "job-parent-42-shard-003".to_string(),
    ];

    let results = vec![PartialResultEnvelope {
        version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
        parent_job_id: "job-parent-42".to_string(),
        shard_id: "job-parent-42-shard-001".to_string(),
        backend_id: "backend-a".to_string(),
        attempt: 1,
        emitted_at_ms: 1_746_200_000_010,
        trace_id: "trace-xyz".to_string(),
        correlation_id: "corr-123".to_string(),
        payload_ref: "qfs://job-parent-42/shards/001/result.json".to_string(),
        payload_checksum: "sha256:ok1".to_string(),
    }];

    let failures = vec![PartialFailureEnvelope {
        version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
        parent_job_id: "job-parent-42".to_string(),
        shard_id: "job-parent-42-shard-002".to_string(),
        backend_id: "backend-b".to_string(),
        attempt: 2,
        emitted_at_ms: 1_746_200_000_100,
        trace_id: "trace-xyz".to_string(),
        correlation_id: "corr-123".to_string(),
        reason_code: PartialFailureReasonCode::ExecutionTimeout,
        retryable: true,
        message: "backend timeout".to_string(),
    }];

    let merge = merge_partial_results(
        "job-parent-42",
        &expected,
        &results,
        &failures,
        MergePolicy::AllShardsRequired,
    );

    assert_eq!(merge.version, MULTI_DEVICE_EXECUTION_CONTRACT_VERSION);
    assert_eq!(merge.parent_job_id, "job-parent-42");
    assert_eq!(merge.reason_code, MergeReasonCode::MissingExpectedShards);
    assert_eq!(merge.merged_shard_ids, vec!["job-parent-42-shard-001"]);
    assert_eq!(merge.failed_shard_ids, vec!["job-parent-42-shard-002"]);
    assert_eq!(merge.missing_shard_ids, vec!["job-parent-42-shard-003"]);
    assert_eq!(merge.failures.len(), 1);
    assert_eq!(
        merge.failures[0].reason_code,
        PartialFailureReasonCode::ExecutionTimeout
    );
}

#[test]
fn merge_validation_is_deterministic_for_identical_inputs() {
    let expected = vec![
        "job-parent-42-shard-001".to_string(),
        "job-parent-42-shard-002".to_string(),
    ];

    let results = vec![
        PartialResultEnvelope {
            version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
            parent_job_id: "job-parent-42".to_string(),
            shard_id: "job-parent-42-shard-002".to_string(),
            backend_id: "backend-b".to_string(),
            attempt: 1,
            emitted_at_ms: 1_746_200_000_120,
            trace_id: "trace-xyz".to_string(),
            correlation_id: "corr-123".to_string(),
            payload_ref: "qfs://job-parent-42/shards/002/result.json".to_string(),
            payload_checksum: "sha256:ok2".to_string(),
        },
        PartialResultEnvelope {
            version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
            parent_job_id: "job-parent-42".to_string(),
            shard_id: "job-parent-42-shard-001".to_string(),
            backend_id: "backend-a".to_string(),
            attempt: 1,
            emitted_at_ms: 1_746_200_000_010,
            trace_id: "trace-xyz".to_string(),
            correlation_id: "corr-123".to_string(),
            payload_ref: "qfs://job-parent-42/shards/001/result.json".to_string(),
            payload_checksum: "sha256:ok1".to_string(),
        },
    ];

    let first = merge_partial_results(
        "job-parent-42",
        &expected,
        &results,
        &[],
        MergePolicy::AllShardsRequired,
    );
    let second = merge_partial_results(
        "job-parent-42",
        &expected,
        &results,
        &[],
        MergePolicy::AllShardsRequired,
    );

    assert_eq!(first, second);
    assert_eq!(first.reason_code, MergeReasonCode::AllShardsMerged);
    assert_eq!(
        first.merged_shard_ids,
        vec![
            "job-parent-42-shard-001".to_string(),
            "job-parent-42-shard-002".to_string(),
        ]
    );
}

#[test]
fn merge_quorum_succeeds_when_threshold_met() {
    let expected = vec![
        "job-parent-42-shard-001".to_string(),
        "job-parent-42-shard-002".to_string(),
        "job-parent-42-shard-003".to_string(),
    ];

    let results = vec![
        PartialResultEnvelope {
            version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
            parent_job_id: "job-parent-42".to_string(),
            shard_id: "job-parent-42-shard-001".to_string(),
            backend_id: "backend-a".to_string(),
            attempt: 1,
            emitted_at_ms: 1_746_200_000_010,
            trace_id: "trace-xyz".to_string(),
            correlation_id: "corr-123".to_string(),
            payload_ref: "qfs://job-parent-42/shards/001/result.json".to_string(),
            payload_checksum: "sha256:ok1".to_string(),
        },
        PartialResultEnvelope {
            version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
            parent_job_id: "job-parent-42".to_string(),
            shard_id: "job-parent-42-shard-002".to_string(),
            backend_id: "backend-b".to_string(),
            attempt: 1,
            emitted_at_ms: 1_746_200_000_120,
            trace_id: "trace-xyz".to_string(),
            correlation_id: "corr-123".to_string(),
            payload_ref: "qfs://job-parent-42/shards/002/result.json".to_string(),
            payload_checksum: "sha256:ok2".to_string(),
        },
    ];

    let merge = merge_partial_results(
        "job-parent-42",
        &expected,
        &results,
        &[],
        MergePolicy::Quorum {
            min_successful_shards: 2,
        },
    );

    assert_eq!(merge.reason_code, MergeReasonCode::QuorumSatisfied);
    assert_eq!(merge.missing_shard_ids, vec!["job-parent-42-shard-003"]);
}
