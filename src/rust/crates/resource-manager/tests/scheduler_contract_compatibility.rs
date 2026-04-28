use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use resource_manager::{
    AdmissionPolicy, BACKEND_SCORING_CONTRACT_VERSION, BACKEND_SCORING_PROFILE_SCHEMA_VERSION,
    CLUSTER_ASSIGNMENT_LINEAGE_VERSION, CLUSTER_CONTROL_PLANE_CONTRACT_VERSION,
    WORKER_NODE_EXECUTION_CONTRACT_VERSION, WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION,
    ClusterWorkerRegistration, ClusterWorkerState, DEVICE_SCORE_VERSION, DispatchReasonCode,
    FairnessPolicy,
    MULTI_DEVICE_EXECUTION_CONTRACT_VERSION, REBALANCING_POLICY_VERSION,
    SCHEDULER_DECISION_VERSION, ScheduledJob, Scheduler, assign_cluster_job, plan_split,
};
use serde_json::{Value, json};

fn fixture(path: &str) -> Value {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("scheduler_contracts");
    let raw = fs::read_to_string(base.join(path)).expect("fixture file must exist");
    serde_json::from_str(&raw).expect("fixture must contain valid json")
}

#[test]
fn scheduler_decision_contract_matches_golden_fixture() {
    let mut scheduler = Scheduler::new(AdmissionPolicy::default(), FairnessPolicy::default());
    scheduler.submit(ScheduledJob {
        job_id: "job-contract-001".to_string(),
        tenant_id: "tenant-a".to_string(),
        project_id: "project-a".to_string(),
        priority: 7,
    });
    let decision = scheduler.dispatch_next();

    let snapshot = json!({
        "version": decision.version,
        "selected_job_id": decision.selected_job_id,
        "selected_tenant_id": decision.selected_tenant_id,
        "selected_project_id": decision.selected_project_id,
        "selected_priority": decision.selected_priority,
        "queue_depth_after": decision.queue_depth_after,
        "reason_code": format!("{:?}", decision.reason_code),
    });

    assert_eq!(snapshot, fixture("scheduler_decision_v2_1_0.json"));
}

#[test]
fn dispatch_reason_codes_match_golden_fixture() {
    let current = BTreeSet::from([
        format!("{:?}", DispatchReasonCode::QueueEmpty),
        format!("{:?}", DispatchReasonCode::WeightedFairness),
        format!("{:?}", DispatchReasonCode::StarvationPrevention),
        format!("{:?}", DispatchReasonCode::DeviceScore),
        format!("{:?}", DispatchReasonCode::DeviceScoreTieBreak),
    ]);

    let expected: BTreeSet<String> =
        serde_json::from_value(fixture("dispatch_reason_codes_v2_1_0.json"))
            .expect("reason-code fixture must be an array of strings");

    assert_eq!(current, expected);
}

#[test]
fn split_plan_manifest_contract_matches_golden_fixture() {
    let manifest = plan_split(
        "job-parent-compat-01",
        &[
            resource_manager::SplitTask {
                task_id: "task-a".to_string(),
                compatible_backends: vec!["backend-b".to_string(), "backend-a".to_string()],
            },
            resource_manager::SplitTask {
                task_id: "task-b".to_string(),
                compatible_backends: vec!["backend-b".to_string()],
            },
        ],
        4,
    )
    .expect("split plan fixture scenario must be valid");

    let shard_plans: Vec<Value> = manifest
        .shard_plans
        .iter()
        .map(|shard| {
            json!({
                "version": shard.version,
                "parent_job_id": shard.parent_job_id,
                "shard_id": shard.shard_id,
                "backend_id": shard.backend_id,
                "task_ids": shard.task_ids,
            })
        })
        .collect();

    let snapshot = json!({
        "version": manifest.version,
        "parent_job_id": manifest.parent_job_id,
        "scheduler_decision_version": manifest.scheduler_decision_version,
        "shard_plans": shard_plans,
    });

    assert_eq!(snapshot, fixture("split_plan_manifest_v2_0_0.json"));
}

#[test]
fn cluster_assignment_contract_matches_golden_fixture() {
    let assignment = assign_cluster_job(
        "cluster-contract-01",
        "job-contract-cluster-01",
        11,
        1_746_200_000_000,
        &[
            ClusterWorkerRegistration {
                worker_id: "worker-b".to_string(),
                state: ClusterWorkerState::Ready,
                capability_tags: vec!["qpu".to_string(), "gpu".to_string()],
                max_parallel_tasks: 8,
                current_load: 3,
            },
            ClusterWorkerRegistration {
                worker_id: "worker-a".to_string(),
                state: ClusterWorkerState::Ready,
                capability_tags: vec!["qpu".to_string()],
                max_parallel_tasks: 4,
                current_load: 1,
            },
            ClusterWorkerRegistration {
                worker_id: "worker-x".to_string(),
                state: ClusterWorkerState::Offline,
                capability_tags: vec!["qpu".to_string()],
                max_parallel_tasks: 4,
                current_load: 0,
            },
        ],
        &["qpu".to_string()],
        &[],
    )
    .expect("cluster assignment fixture scenario must be valid");

    let snapshot = json!({
        "cluster_contract_version": assignment.cluster_contract_version,
        "assignment_id": assignment.assignment_id,
        "job_id": assignment.job_id,
        "candidate_workers": assignment.candidate_workers,
        "selected_worker_id": assignment.selected_worker_id,
        "assignment_trace": assignment.assignment_trace,
        "lineage": {
            "lineage_version": assignment.lineage.lineage_version,
            "cluster_id": assignment.lineage.cluster_id,
            "assignment_id": assignment.lineage.assignment_id,
            "assignment_sequence": assignment.lineage.assignment_sequence,
            "assignment_epoch_ms": assignment.lineage.assignment_epoch_ms,
        },
        "fallback_applied": assignment.fallback_applied,
        "fallback_reason": assignment.fallback_reason,
    });

    assert_eq!(snapshot, fixture("cluster_assignment_v1_0_0.json"));
}

#[test]
fn all_orchestration_contracts_keep_explicit_version_markers() {
    assert_eq!(SCHEDULER_DECISION_VERSION, "2.1.0");
    assert_eq!(DEVICE_SCORE_VERSION, "2.1.0");
    assert_eq!(BACKEND_SCORING_CONTRACT_VERSION, "1.0.0");
    assert_eq!(BACKEND_SCORING_PROFILE_SCHEMA_VERSION, "1.0.0");
    assert_eq!(REBALANCING_POLICY_VERSION, "2.2.0");
    assert_eq!(MULTI_DEVICE_EXECUTION_CONTRACT_VERSION, "2.0.0");
    assert_eq!(CLUSTER_CONTROL_PLANE_CONTRACT_VERSION, "1.0.0");
    assert_eq!(CLUSTER_ASSIGNMENT_LINEAGE_VERSION, "1.0.0");
    assert_eq!(WORKER_NODE_EXECUTION_CONTRACT_VERSION, "1.0.0");
    assert_eq!(WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION, "1.0.0");
}
