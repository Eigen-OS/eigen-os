use std::fs;
use std::path::PathBuf;

use resource_manager::{
    BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION, BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION,
    BackendCandidateDescriptor, BackendRuntimeDescriptor, BackendScoringProfile,
    BackendWorkloadDescriptor, CLUSTER_ASSIGNMENT_LINEAGE_VERSION,
    CLUSTER_CONTROL_PLANE_CONTRACT_VERSION, ClusterWorkerRegistration, ClusterWorkerState,
    DISTRIBUTED_QUEUE_CONTRACT_VERSION, ExplainBackendSelectionRequest, ExplainPolicyContext,
    ExplainQuotaSnapshot, ExplainTenantContext, InMemoryQueueAdapter,
    PolicyBundle, PolicyCandidate, PolicyMode, PolicyPriorityMap, PolicyTransitionReasonCode,
    QUEUE_DEAD_LETTER_CONTRACT_VERSION, QUEUE_LEASE_EVENT_VERSION, QueueAdapter,
    QueueTaskEnvelope, UserIntentWeights, assign_cluster_job, explain_backend_selection,
    resolve_policy_bundle, score_backend_candidates,
};
use serde_json::{Value, json};

fn fixture(path: &str) -> Value {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("determinism_gate");
    let raw = fs::read_to_string(base.join(path)).expect("fixture file must exist");
    serde_json::from_str(&raw).expect("fixture must contain valid json")
}

fn mode_from_fixture(value: &str) -> PolicyMode {
    match value {
        "latency" => PolicyMode::Latency,
        "throughput" => PolicyMode::Throughput,
        "cost" => PolicyMode::Cost,
        _ => PolicyMode::Balanced,
    }
}

fn build_workload(value: &Value) -> BackendWorkloadDescriptor {
    BackendWorkloadDescriptor {
        job_type: value["job_type"].as_str().expect("job_type must exist").to_string(),
        priority: value["priority"].as_u64().expect("priority must exist") as u8,
        shots: value["shots"].as_u64().expect("shots must exist"),
        circuit_depth: value["circuit_depth"]
            .as_u64()
            .expect("circuit_depth must exist"),
        circuit_width: value["circuit_width"]
            .as_u64()
            .expect("circuit_width must exist"),
        estimated_runtime_ms: value["estimated_runtime_ms"]
            .as_u64()
            .expect("estimated_runtime_ms must exist"),
        noise_sensitivity: value["noise_sensitivity"]
            .as_f64()
            .expect("noise_sensitivity must exist"),
        cost_sensitivity: value["cost_sensitivity"]
            .as_f64()
            .expect("cost_sensitivity must exist"),
        required_features: value["required_features"]
            .as_array()
            .expect("required_features must exist")
            .iter()
            .map(|feature| feature.as_str().expect("feature must be str").to_string())
            .collect(),
    }
}

fn build_runtime(value: &Value) -> BackendRuntimeDescriptor {
    BackendRuntimeDescriptor {
        current_cluster_load: value["current_cluster_load"]
            .as_f64()
            .expect("current_cluster_load must exist"),
        retry_count: value["retry_count"].as_u64().expect("retry_count must exist") as u32,
        warm_cache_hit: value["warm_cache_hit"]
            .as_bool()
            .expect("warm_cache_hit must exist"),
    }
}

fn build_candidates(value: &Value) -> Vec<BackendCandidateDescriptor> {
    value
        .as_array()
        .expect("candidates must exist")
        .iter()
        .map(|candidate| BackendCandidateDescriptor {
            backend_id: candidate["backend_id"]
                .as_str()
                .expect("backend_id must exist")
                .to_string(),
            backend_type: candidate["backend_type"]
                .as_str()
                .expect("backend_type must exist")
                .to_string(),
            qubit_count: candidate["qubit_count"].as_u64().expect("qubit_count must exist")
                as u32,
            availability: candidate["availability"]
                .as_f64()
                .expect("availability must exist"),
            queue_length: candidate["queue_length"]
                .as_u64()
                .expect("queue_length must exist") as usize,
            historical_latency_ms: candidate["historical_latency_ms"]
                .as_u64()
                .expect("historical_latency_ms must exist"),
            historical_success_rate: candidate["historical_success_rate"]
                .as_f64()
                .expect("historical_success_rate must exist"),
            historical_fidelity: candidate["historical_fidelity"]
                .as_f64()
                .expect("historical_fidelity must exist"),
            error_rate: candidate["error_rate"].as_f64().expect("error_rate must exist"),
            calibration_age_sec: candidate["calibration_age_sec"]
                .as_u64()
                .expect("calibration_age_sec must exist"),
            policy_priority: candidate["policy_priority"]
                .as_i64()
                .expect("policy_priority must exist") as i32,
            capability_rank: candidate["capability_rank"]
                .as_i64()
                .expect("capability_rank must exist") as i32,
            supported_features: candidate["supported_features"]
                .as_array()
                .expect("supported_features must exist")
                .iter()
                .map(|feature| feature.as_str().expect("feature must be str").to_string())
                .collect(),
        })
        .collect()
}

fn build_policy_bundle(value: &Value) -> PolicyBundle {
    PolicyBundle {
        policy_bundle_id: value["policy_bundle_id"]
            .as_str()
            .expect("policy_bundle_id must exist")
            .to_string(),
        policy_bundle_version: value["policy_bundle_version"]
            .as_str()
            .expect("policy_bundle_version must exist")
            .to_string(),
        policy_mode: mode_from_fixture(value["policy_mode"].as_str().expect("policy_mode")),
        policy_priority_map: PolicyPriorityMap {
            hard_constraints: value["policy_priority_map"]["hard_constraints"]
                .as_u64()
                .expect("hard_constraints must exist") as u16,
            correctness: value["policy_priority_map"]["correctness"]
                .as_u64()
                .expect("correctness must exist") as u16,
            user_intent: value["policy_priority_map"]["user_intent"]
                .as_u64()
                .expect("user_intent must exist") as u16,
            operational_optimization: value["policy_priority_map"]["operational_optimization"]
                .as_u64()
                .expect("operational_optimization must exist") as u16,
            learning_hints: value["policy_priority_map"]["learning_hints"]
                .as_u64()
                .expect("learning_hints must exist") as u16,
        },
        user_intent_weights: UserIntentWeights {
            fidelity: value["user_intent_weights"]["fidelity"]
                .as_f64()
                .expect("fidelity must exist"),
            latency: value["user_intent_weights"]["latency"]
                .as_f64()
                .expect("latency must exist"),
            cost: value["user_intent_weights"]["cost"]
                .as_f64()
                .expect("cost must exist"),
            throughput: value["user_intent_weights"]["throughput"]
                .as_f64()
                .expect("throughput must exist"),
            determinism: value["user_intent_weights"]["determinism"]
                .as_f64()
                .expect("determinism must exist"),
            debuggability: value["user_intent_weights"]["debuggability"]
                .as_f64()
                .expect("debuggability must exist"),
        },
    }
}

fn build_policy_candidates(value: &Value) -> Vec<PolicyCandidate> {
    value
        .as_array()
        .expect("policy candidates must exist")
        .iter()
        .map(|candidate| PolicyCandidate {
            candidate_id: candidate["candidate_id"]
                .as_str()
                .expect("candidate_id must exist")
                .to_string(),
            hard_constraint_satisfied: candidate["hard_constraint_satisfied"]
                .as_bool()
                .expect("hard_constraint_satisfied must exist"),
            correctness_score: candidate["correctness_score"]
                .as_f64()
                .expect("correctness_score must exist"),
            fidelity_score: candidate["fidelity_score"]
                .as_f64()
                .expect("fidelity_score must exist"),
            latency_ms: candidate["latency_ms"].as_u64().expect("latency_ms must exist"),
            cost_units: candidate["cost_units"].as_u64().expect("cost_units must exist"),
            throughput_qps: candidate["throughput_qps"]
                .as_u64()
                .expect("throughput_qps must exist"),
            deterministic: candidate["deterministic"]
                .as_bool()
                .expect("deterministic must exist"),
            debuggability_score: candidate["debuggability_score"]
                .as_f64()
                .expect("debuggability_score must exist"),
            learning_hint_score: candidate["learning_hint_score"]
                .as_f64()
                .expect("learning_hint_score must exist"),
        })
        .collect()
}

fn build_cluster_workers(value: &Value) -> Vec<ClusterWorkerRegistration> {
    value
        .as_array()
        .expect("workers must exist")
        .iter()
        .map(|worker| {
            let state = match worker["state"]
                .as_str()
                .expect("worker state must exist")
            {
                "ready" => ClusterWorkerState::Ready,
                "degraded" => ClusterWorkerState::Degraded,
                "draining" => ClusterWorkerState::Draining,
                "offline" => ClusterWorkerState::Offline,
                _ => ClusterWorkerState::Offline,
            };

            ClusterWorkerRegistration {
                worker_id: worker["worker_id"]
                    .as_str()
                    .expect("worker_id must exist")
                    .to_string(),
                state,
                capability_tags: worker["capability_tags"]
                    .as_array()
                    .expect("capability_tags must exist")
                    .iter()
                    .map(|tag| tag.as_str().expect("capability tag must be str").to_string())
                    .collect(),
                max_parallel_tasks: worker["max_parallel_tasks"]
                    .as_u64()
                    .expect("max_parallel_tasks must exist") as u32,
                current_load: worker["current_load"]
                    .as_u64()
                    .expect("current_load must exist") as u32,
            }
        })
        .collect()
}

fn scoring_snapshot(artifact: &resource_manager::BackendScoringDecisionArtifact) -> Value {
    json!({
        "scoring_contract_version": artifact.scoring_contract_version,
        "profile_schema_version": artifact.profile_schema_version,
        "profile_version": artifact.profile_version,
        "decision_id": artifact.decision_id,
        "selected_backend_id": artifact.selected_backend_id,
        "tie_break_trace": artifact.tie_break_trace,
        "candidates": artifact.candidates.iter().map(|candidate| json!({
            "backend_id": candidate.backend_id,
            "score_millis": candidate.score_millis,
            "eligible": candidate.eligible,
            "ineligibility_reason": candidate.ineligibility_reason,
            "feature_contributions": candidate.feature_contributions.iter().map(|feature| json!({
                "feature": feature.feature,
                "contribution_millis": feature.contribution_millis,
            })).collect::<Vec<_>>()
        })).collect::<Vec<_>>()
    })
}

fn policy_snapshot(artifact: &resource_manager::PolicyResolutionArtifact) -> Value {
    json!({
        "version": artifact.version,
        "policy_bundle_schema_version": artifact.policy_bundle_schema_version,
        "policy_bundle_id": artifact.policy_bundle_id,
        "policy_bundle_version": artifact.policy_bundle_version,
        "policy_mode": format!("{:?}", artifact.policy_mode),
        "selected_candidate_id": artifact.selected_candidate_id,
        "resolution_trace": artifact.resolution_trace,
        "fallback_applied": artifact.fallback_applied,
        "fallback_reason": artifact.fallback_reason,
        "transition_reason_code": format!("{:?}", artifact.transition_reason_code),
        "deterministic_seed": artifact.deterministic_seed,
        "error_code": artifact.error_code.map(|code| format!("{:?}", code)),
    })
}

fn explain_snapshot(response: &resource_manager::ExplainBackendSelectionResponse) -> Value {
    json!({
        "explain_contract_version": response.explain_contract_version,
        "request_version": response.request_version,
        "response_version": response.response_version,
        "scoring_contract_version": response.scoring_contract_version,
        "profile_schema_version": response.profile_schema_version,
        "profile_version": response.profile_version,
        "decision_id": response.decision_id,
        "selected_backend_id": response.selected_backend_id,
        "tie_break_trace": response.tie_break_trace,
        "candidate_scores": response.candidate_scores.iter().map(|candidate| json!({
            "backend_id": candidate.backend_id,
            "score_millis": candidate.score_millis,
            "eligible": candidate.eligible,
            "ineligibility_reason": candidate.ineligibility_reason,
        })).collect::<Vec<_>>(),
        "confidence": {
            "score_margin_millis": response.confidence.score_margin_millis,
            "selected_score_millis": response.confidence.selected_score_millis,
            "runner_up_score_millis": response.confidence.runner_up_score_millis,
            "confidence": response.confidence.confidence,
        }
    })
}

fn assert_replay_snapshot_stable(stage: &str, actual: &Value, expected: &Value) {
    if actual == expected {
        return;
    }

    let mut differing_paths = Vec::new();
    collect_diff_paths("$", actual, expected, &mut differing_paths);
    let joined_paths = differing_paths.join(", ");

    panic!(
        "deterministic replay gate failed for {stage}: drift detected in {joined_paths}; \
possible non-deterministic input or decision branch"
    );
}

fn collect_diff_paths(path: &str, left: &Value, right: &Value, output: &mut Vec<String>) {
    match (left, right) {
        (Value::Object(left_map), Value::Object(right_map)) => {
            let mut keys: Vec<String> = left_map
                .keys()
                .chain(right_map.keys())
                .map(ToString::to_string)
                .collect();
            keys.sort();
            keys.dedup();

            for key in keys {
                let left_value = left_map.get(&key);
                let right_value = right_map.get(&key);
                let child_path = format!("{path}.{key}");
                match (left_value, right_value) {
                    (Some(lv), Some(rv)) => collect_diff_paths(&child_path, lv, rv, output),
                    _ => output.push(child_path),
                }
            }
        }
        (Value::Array(left_array), Value::Array(right_array)) => {
            if left_array.len() != right_array.len() {
                output.push(format!("{path}[len]"));
                return;
            }
            for (idx, (lv, rv)) in left_array.iter().zip(right_array.iter()).enumerate() {
                collect_diff_paths(&format!("{path}[{idx}]"), lv, rv, output);
            }
        }
        _ => {
            if left != right {
                output.push(path.to_string());
            }
        }
    }
}

#[test]
fn deterministic_replay_gate_matches_recorded_artifacts() {
    let replay = fixture("runtime_decision_replay_v1_0_0.json");

    let workload = build_workload(&replay["input"]["workload"]);
    let runtime = build_runtime(&replay["input"]["runtime"]);
    let candidates = build_candidates(&replay["input"]["backend_candidates"]);
    let profile = BackendScoringProfile::default();

    let decision = score_backend_candidates(
        replay["input"]["decision_id"]
            .as_str()
            .expect("decision_id must exist"),
        &workload,
        &runtime,
        &candidates,
        &profile,
    );

    let scoring_actual = scoring_snapshot(&decision);
    assert_replay_snapshot_stable(
        "backend scoring",
        &scoring_actual,
        &replay["expected"]["scoring_artifact"],
    );

    let policy_bundle = build_policy_bundle(&replay["input"]["policy_bundle"]);
    let policy_candidates = build_policy_candidates(&replay["input"]["policy_candidates"]);
    let policy_decision = resolve_policy_bundle(Some(&policy_bundle), &policy_candidates);
    let policy_actual = policy_snapshot(&policy_decision);
    assert_replay_snapshot_stable(
        "policy resolution",
        &policy_actual,
        &replay["expected"]["policy_artifact"],
    );

    let explain_request = ExplainBackendSelectionRequest {
        request_version: BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION,
        response_version: BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION,
        decision_id: decision.decision_id.clone(),
        include_rejected_candidates: true,
        tenant_context: ExplainTenantContext {
            tenant_id: "tenant-replay-001".to_string(),
            project_id: "project-replay-001".to_string(),
            quota_snapshot: ExplainQuotaSnapshot {
                tenant_limit: 100,
                tenant_used: 24,
                project_limit: 50,
                project_used: 9,
                admitted: true,
                reason_code: resource_manager::AdmissionReasonCode::Accepted,
            },
            sensitivity_labels: vec!["tenant_id".to_string(), "project_id".to_string()],
        },
        policy_context: ExplainPolicyContext {
            policy_bundle_id: policy_bundle.policy_bundle_id.clone(),
            policy_bundle_version: policy_bundle.policy_bundle_version.clone(),
            transition_reason_code: PolicyTransitionReasonCode::DeterministicSelection,
            fallback_applied: false,
            fallback_reason: None,
            plugin_trace: vec!["plugin:policy:default:ok".to_string()],
        },
    };
    let explain_response = explain_backend_selection(&explain_request, &decision);
    let explain_actual = explain_snapshot(&explain_response);
    assert_replay_snapshot_stable(
        "explain response",
        &explain_actual,
        &replay["expected"]["explain_response"],
    );

    for _ in 0..3 {
        let replayed_decision = score_backend_candidates(
            replay["input"]["decision_id"]
                .as_str()
                .expect("decision_id must exist"),
            &workload,
            &runtime,
            &candidates,
            &profile,
        );
        assert_eq!(decision, replayed_decision);

        let replayed_policy = resolve_policy_bundle(Some(&policy_bundle), &policy_candidates);
        assert_eq!(policy_decision, replayed_policy);

        let replayed_explain = explain_backend_selection(&explain_request, &decision);
        assert_eq!(explain_response, replayed_explain);
    }
}

#[test]
fn drift_diagnostics_identify_changed_input_or_branch() {
    let replay = fixture("runtime_decision_replay_v1_0_0.json");
    let mut drifted = replay["expected"]["scoring_artifact"].clone();
    drifted["selected_backend_id"] = Value::String("backend-drifted".to_string());

    let result = std::panic::catch_unwind(|| {
        assert_replay_snapshot_stable(
            "backend scoring",
            &replay["expected"]["scoring_artifact"],
            &drifted,
        );
    });

    let panic_payload = result.expect_err("drift fixture should fail the gate");
    let panic_message = panic_payload
        .downcast_ref::<String>()
        .map(String::as_str)
        .or_else(|| panic_payload.downcast_ref::<&str>().copied())
        .expect("panic payload must be a string");

    assert!(
        panic_message.contains("selected_backend_id"),
        "diagnostic must include changed field path"
    );
    assert!(
        panic_message.contains("non-deterministic input or decision branch"),
        "diagnostic must explain branch/input drift"
    );
}

#[test]
fn distributed_scheduling_replay_gate_matches_recorded_artifacts() {
    let replay = fixture("distributed_scheduling_replay_v1_0_1.json");

    let workers = build_cluster_workers(&replay["input"]["workers"]);
    let required_tags: Vec<String> = replay["input"]["required_tags"]
        .as_array()
        .expect("required_tags must exist")
        .iter()
        .map(|tag| tag.as_str().expect("required tag must be str").to_string())
        .collect();

    let assignment = assign_cluster_job(
        replay["input"]["cluster_id"]
            .as_str()
            .expect("cluster_id must exist"),
        replay["input"]["job_id"].as_str().expect("job_id must exist"),
        replay["input"]["assignment_sequence"]
            .as_u64()
            .expect("assignment_sequence must exist"),
        replay["input"]["assignment_epoch_ms"]
            .as_u64()
            .expect("assignment_epoch_ms must exist"),
        &workers,
        &required_tags,
        &[],
    )
    .expect("distributed assignment fixture must be valid");

    let mut queue = InMemoryQueueAdapter::new();
    for task in replay["input"]["queue_tasks"]
        .as_array()
        .expect("queue_tasks must exist")
    {
        queue
            .enqueue(QueueTaskEnvelope {
                queue_contract_version: DISTRIBUTED_QUEUE_CONTRACT_VERSION,
                queue_name: task["queue_name"]
                    .as_str()
                    .expect("queue_name must exist")
                    .to_string(),
                task_id: task["task_id"].as_str().expect("task_id must exist").to_string(),
                job_id: assignment.job_id.clone(),
                assignment_id: assignment.assignment_id.clone(),
                idempotency_key: task["idempotency_key"]
                    .as_str()
                    .expect("idempotency_key must exist")
                    .to_string(),
                tenant_id: task["tenant_id"]
                    .as_str()
                    .expect("tenant_id must exist")
                    .to_string(),
                project_id: task["project_id"]
                    .as_str()
                    .expect("project_id must exist")
                    .to_string(),
                attempt: 1,
                max_attempts: task["max_attempts"].as_u64().expect("max_attempts must exist") as u32,
                visibility_timeout_seconds: task["visibility_timeout_seconds"]
                    .as_u64()
                    .expect("visibility_timeout_seconds must exist") as u32,
                enqueued_at_ms: task["enqueued_at_ms"]
                    .as_u64()
                    .expect("enqueued_at_ms must exist"),
            })
            .expect("enqueue must succeed");
    }

    let first_lease = queue
        .lease(
            replay["input"]["queue_name"]
                .as_str()
                .expect("queue_name must exist"),
            "worker-a",
            replay["input"]["first_lease_ms"]
                .as_u64()
                .expect("first_lease_ms must exist"),
        )
        .expect("first lease must succeed")
        .expect("first task should be leased");
    let second_lease = queue
        .lease(
            replay["input"]["queue_name"]
                .as_str()
                .expect("queue_name must exist"),
            "worker-b",
            replay["input"]["second_lease_ms"]
                .as_u64()
                .expect("second_lease_ms must exist"),
        )
        .expect("second lease must succeed")
        .expect("second task should be leased");

    let redelivery_a = queue
        .lease(
            replay["input"]["queue_name"]
                .as_str()
                .expect("queue_name must exist"),
            "worker-c",
            replay["input"]["sweep_expired_ms"]
                .as_u64()
                .expect("sweep_expired_ms must exist"),
        )
        .expect("redelivery lease A must succeed")
        .expect("redelivery A should be available");
    let redelivery_b = queue
        .lease(
            replay["input"]["queue_name"]
                .as_str()
                .expect("queue_name must exist"),
            "worker-d",
            replay["input"]["sweep_expired_ms"]
                .as_u64()
                .expect("sweep_expired_ms must exist"),
        )
        .expect("redelivery lease B must succeed")
        .expect("redelivery B should be available");

    let _ = queue
        .requeue(
            &redelivery_b.lease_id,
            "worker-d",
            "worker-d-requeue",
            replay["input"]["requeue_ms"]
                .as_u64()
                .expect("requeue_ms must exist"),
        )
        .expect("requeue must succeed");
    let dead_letter_lease = queue
        .lease(
            replay["input"]["queue_name"]
                .as_str()
                .expect("queue_name must exist"),
            "worker-e",
            replay["input"]["dead_letter_lease_ms"]
                .as_u64()
                .expect("dead_letter_lease_ms must exist"),
        )
        .expect("dead-letter lease must succeed")
        .expect("task should be redelivered for final attempt");
    let _ = queue
        .requeue(
            &dead_letter_lease.lease_id,
            "worker-e",
            "worker-e-final-requeue",
            replay["input"]["dead_letter_requeue_ms"]
                .as_u64()
                .expect("dead_letter_requeue_ms must exist"),
        )
        .expect("dead-letter requeue must succeed");

    let dead_letter = queue
        .dead_letters()
        .first()
        .expect("dead-letter record must exist");

    let snapshot = json!({
        "assignment": {
            "cluster_contract_version": assignment.cluster_contract_version,
            "lineage_version": assignment.lineage.lineage_version,
            "assignment_id": assignment.assignment_id,
            "selected_worker_id": assignment.selected_worker_id,
            "candidate_workers": assignment.candidate_workers,
            "assignment_trace": assignment.assignment_trace,
        },
        "queue": {
            "queue_contract_version": DISTRIBUTED_QUEUE_CONTRACT_VERSION,
            "lease_event_version": QUEUE_LEASE_EVENT_VERSION,
            "dead_letter_version": QUEUE_DEAD_LETTER_CONTRACT_VERSION,
            "first_lease": {
                "lease_id": first_lease.lease_id,
                "task_id": first_lease.task_id,
                "attempt": first_lease.attempt,
            },
            "second_lease": {
                "lease_id": second_lease.lease_id,
                "task_id": second_lease.task_id,
                "attempt": second_lease.attempt,
            },
            "redelivery_sequence": [
                {
                    "lease_id": redelivery_a.lease_id,
                    "task_id": redelivery_a.task_id,
                    "attempt": redelivery_a.attempt,
                },
                {
                    "lease_id": redelivery_b.lease_id,
                    "task_id": redelivery_b.task_id,
                    "attempt": redelivery_b.attempt,
                }
            ],
            "dead_letter": {
                "task_id": dead_letter.task_id,
                "attempt": dead_letter.attempt,
                "max_attempts": dead_letter.max_attempts,
                "reason": dead_letter.reason,
            },
            "metrics": {
                "queue_enqueued_total": queue.metrics().queue_enqueued_total,
                "queue_lease_acquired_total": queue.metrics().queue_lease_acquired_total,
                "queue_redelivery_total": queue.metrics().queue_redelivery_total,
                "queue_dead_letter_total": queue.metrics().queue_dead_letter_total,
            },
        },
    });

    assert_replay_snapshot_stable(
        "distributed assignment + lease + retry replay",
        &snapshot,
        &replay["expected"],
    );

    assert_eq!(assignment.cluster_contract_version, CLUSTER_CONTROL_PLANE_CONTRACT_VERSION);
    assert_eq!(assignment.lineage.lineage_version, CLUSTER_ASSIGNMENT_LINEAGE_VERSION);
}
