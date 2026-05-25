use std::fs;
use std::path::PathBuf;

use resource_manager::{
    BACKEND_SCORING_CONTRACT_VERSION, BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION,
    BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION, BackendCandidateDescriptor, BackendRuntimeDescriptor,
    BackendScoringProfile, BackendWorkloadDescriptor, ExplainBackendSelectionRequest,
    ExplainPolicyContext, ExplainQuotaSnapshot, ExplainTenantContext, PolicyTransitionReasonCode,
    explain_backend_selection, score_backend_candidates,
};
use serde_json::{Value, json};

fn fixture(path: &str) -> Value {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("explain_contracts");
    let raw = fs::read_to_string(base.join(path)).expect("fixture file must exist");
    serde_json::from_str(&raw).expect("fixture must contain valid json")
}

fn sample_decision() -> resource_manager::BackendScoringDecisionArtifact {
    let workload = BackendWorkloadDescriptor {
        job_type: "qaoa".to_string(),
        priority: 8,
        shots: 4_000,
        circuit_depth: 96,
        circuit_width: 24,
        estimated_runtime_ms: 640,
        noise_sensitivity: 0.55,
        cost_sensitivity: 0.35,
        required_features: vec!["mid-circuit-measure".to_string()],
    };
    let runtime = BackendRuntimeDescriptor {
        current_cluster_load: 0.44,
        retry_count: 0,
        warm_cache_hit: true,
    };
    let candidates = vec![
        BackendCandidateDescriptor {
            backend_id: "sim:cpu-a".to_string(),
            backend_type: "simulator".to_string(),
            qubit_count: 32,
            availability: 0.99,
            queue_length: 4,
            historical_latency_ms: 520,
            historical_success_rate: 0.995,
            historical_fidelity: 0.981,
            error_rate: 0.013,
            calibration_age_sec: 1_200,
            policy_priority: 30,
            capability_rank: 10,
            supported_features: vec!["mid-circuit-measure".to_string()],
        },
        BackendCandidateDescriptor {
            backend_id: "qpu:ion-1".to_string(),
            backend_type: "qpu".to_string(),
            qubit_count: 28,
            availability: 0.87,
            queue_length: 12,
            historical_latency_ms: 1_850,
            historical_success_rate: 0.972,
            historical_fidelity: 0.993,
            error_rate: 0.022,
            calibration_age_sec: 1_900,
            policy_priority: 20,
            capability_rank: 15,
            supported_features: vec!["mid-circuit-measure".to_string()],
        },
        BackendCandidateDescriptor {
            backend_id: "sim:gpu-z".to_string(),
            backend_type: "simulator".to_string(),
            qubit_count: 48,
            availability: 0.94,
            queue_length: 2,
            historical_latency_ms: 450,
            historical_success_rate: 0.997,
            historical_fidelity: 0.975,
            error_rate: 0.018,
            calibration_age_sec: 1_500,
            policy_priority: 25,
            capability_rank: 8,
            supported_features: vec!["mid-circuit-measure".to_string()],
        },
    ];

    score_backend_candidates(
        "backend-selection-decision-001",
        &workload,
        &runtime,
        &candidates,
        &BackendScoringProfile::default(),
    )
}

#[test]
fn explain_backend_selection_contract_matches_golden_fixture() {
    let decision = sample_decision();
    let request = ExplainBackendSelectionRequest {
        request_version: BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION,
        response_version: BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION,
        decision_id: decision.decision_id.clone(),
        include_rejected_candidates: true,
        tenant_context: ExplainTenantContext {
            tenant_id: "tenant-alpha-001".to_string(),
            project_id: "project-solver-007".to_string(),
            quota_snapshot: ExplainQuotaSnapshot {
                tenant_limit: 200,
                tenant_used: 81,
                project_limit: 80,
                project_used: 42,
                admitted: true,
                reason_code: resource_manager::AdmissionReasonCode::Accepted,
            },
            sensitivity_labels: vec!["tenant_id".to_string(), "project_id".to_string()],
        },
        policy_context: ExplainPolicyContext {
            policy_bundle_id: "balanced".to_string(),
            policy_bundle_version: "1.0.0".to_string(),
            transition_reason_code: PolicyTransitionReasonCode::DeterministicSelection,
            fallback_applied: false,
            fallback_reason: None,
            plugin_trace: vec!["plugin:policy:default:ok".to_string()],
        },
    };

    let response = explain_backend_selection(&request, &decision);

    let snapshot = json!({
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
            "feature_contributions": candidate.feature_contributions.iter().map(|feature| json!({
                "feature": feature.feature,
                "contribution_millis": feature.contribution_millis,
            })).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
        "factor_contributions": response.factor_contributions.iter().map(|factor| json!({
            "backend_id": factor.backend_id,
            "factor": factor.factor,
            "contribution_millis": factor.contribution_millis,
        })).collect::<Vec<_>>(),
        "confidence": {
            "score_margin_millis": response.confidence.score_margin_millis,
            "selected_score_millis": response.confidence.selected_score_millis,
            "runner_up_score_millis": response.confidence.runner_up_score_millis,
            "confidence": response.confidence.confidence,
        },
        "evidence_schema_version": response.evidence_schema_version,
        "decision_provenance": {
            "tenant_context": {
                "tenant_id": response.decision_provenance.tenant_context.tenant_id,
                "project_id": response.decision_provenance.tenant_context.project_id,
                "quota_trace": response.decision_provenance.tenant_context.quota_trace,
                "redactions_applied": response.decision_provenance.tenant_context.redactions_applied,
            },
            "policy_context": {
                "policy_bundle_id": response.decision_provenance.policy_context.policy_bundle_id,
                "policy_bundle_version": response.decision_provenance.policy_context.policy_bundle_version,
                "transition_reason_code": format!("{:?}", response.decision_provenance.policy_context.transition_reason_code),
                "fallback_applied": response.decision_provenance.policy_context.fallback_applied,
                "fallback_reason": response.decision_provenance.policy_context.fallback_reason,
                "plugin_trace": response.decision_provenance.policy_context.plugin_trace,
            },
            "evidence_ids": response.decision_provenance.evidence_ids,
        },
    });

    assert_eq!(snapshot, fixture("backend_selection_explain_v1_1_0.json"));
}

#[test]
fn explain_backend_selection_is_stable_for_identical_decision_artifacts() {
    let decision = sample_decision();
    let request = ExplainBackendSelectionRequest {
        request_version: BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION,
        response_version: BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION,
        decision_id: decision.decision_id.clone(),
        include_rejected_candidates: true,
        tenant_context: ExplainTenantContext {
            tenant_id: "tenant-alpha-001".to_string(),
            project_id: "project-solver-007".to_string(),
            quota_snapshot: ExplainQuotaSnapshot {
                tenant_limit: 200,
                tenant_used: 81,
                project_limit: 80,
                project_used: 42,
                admitted: true,
                reason_code: resource_manager::AdmissionReasonCode::Accepted,
            },
            sensitivity_labels: vec!["tenant_id".to_string(), "project_id".to_string()],
        },
        policy_context: ExplainPolicyContext {
            policy_bundle_id: "balanced".to_string(),
            policy_bundle_version: "1.0.0".to_string(),
            transition_reason_code: PolicyTransitionReasonCode::DeterministicSelection,
            fallback_applied: false,
            fallback_reason: None,
            plugin_trace: vec!["plugin:policy:default:ok".to_string()],
        },
    };

    let first = explain_backend_selection(&request, &decision);
    let second = explain_backend_selection(&request, &decision);

    assert_eq!(first, second);
}

#[test]
fn backend_selection_explain_contract_versions_are_explicit() {
    assert_eq!(BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION, "1.1.0");
    assert_eq!(BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION, "1.1.0");
    assert_eq!(BACKEND_SCORING_CONTRACT_VERSION, "1.0.0");
}
