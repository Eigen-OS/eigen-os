use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use resource_manager::{
    plan_split, AdmissionPolicy, DispatchReasonCode, FairnessPolicy, ScheduledJob, Scheduler,
    DEVICE_SCORE_VERSION, MULTI_DEVICE_EXECUTION_CONTRACT_VERSION, REBALANCING_POLICY_VERSION,
    SCHEDULER_DECISION_VERSION,
};
use serde_json::{json, Value};

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

    let expected: BTreeSet<String> = serde_json::from_value(fixture("dispatch_reason_codes_v2_1_0.json"))
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
fn all_orchestration_contracts_keep_explicit_version_markers() {
    assert_eq!(SCHEDULER_DECISION_VERSION, "2.1.0");
    assert_eq!(DEVICE_SCORE_VERSION, "2.1.0");
    assert_eq!(REBALANCING_POLICY_VERSION, "2.2.0");
    assert_eq!(MULTI_DEVICE_EXECUTION_CONTRACT_VERSION, "2.0.0");
}
