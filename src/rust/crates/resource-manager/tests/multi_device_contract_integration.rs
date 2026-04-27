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

    let manifest = plan_split("job-parent-42", &tasks, 4).expect("split plan must be valid");

    assert_eq!(manifest.version, MULTI_DEVICE_EXECUTION_CONTRACT_VERSION);
    assert_eq!(manifest.parent_job_id, "job-parent-42");
    assert_eq!(manifest.shard_plans.len(), 3);

    for shard in &manifest.shard_plans {
        assert_eq!(shard.version, MULTI_DEVICE_EXECUTION_CONTRACT_VERSION);
        assert_eq!(shard.parent_job_id, "job-parent-42");
        assert!(shard.shard_id.starts_with("job-parent-42-shard-"));
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
fn split_planner_rejects_tasks_without_compatible_backends() {
    let tasks = vec![SplitTask {
        task_id: "task-x".to_string(),
        compatible_backends: vec![],
    }];

    let err = plan_split("job-parent-42", &tasks, 4).expect_err("planner must reject task");
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
        payload_ref: "qfs://job-parent-42/shards/001/result.json".to_string(),
        payload_checksum: "sha256:ok1".to_string(),
    }];

    let failures = vec![PartialFailureEnvelope {
        version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
        parent_job_id: "job-parent-42".to_string(),
        shard_id: "job-parent-42-shard-002".to_string(),
        backend_id: "backend-b".to_string(),
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
            payload_ref: "qfs://job-parent-42/shards/001/result.json".to_string(),
            payload_checksum: "sha256:ok1".to_string(),
        },
        PartialResultEnvelope {
            version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
            parent_job_id: "job-parent-42".to_string(),
            shard_id: "job-parent-42-shard-002".to_string(),
            backend_id: "backend-b".to_string(),
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
