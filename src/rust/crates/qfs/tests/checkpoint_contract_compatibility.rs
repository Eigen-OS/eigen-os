use std::fs;
use std::path::PathBuf;

use qfs::{
    CheckpointAdmissionReasonCode, CheckpointBudgetPolicy, CHECKPOINT_ENVELOPE_SCHEMA_VERSION,
    CheckpointEnvelopeV1, CheckpointEnvelopeValidationError,
};

fn fixture(path: &str) -> String {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("checkpoint_contracts");
    fs::read_to_string(base.join(path)).expect("fixture file must exist")
}

#[test]
fn qfs_l2_checkpoint_envelope_v1_fixture_decodes_and_validates() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must be valid envelope json");

    assert_eq!(envelope.schema_version, CHECKPOINT_ENVELOPE_SCHEMA_VERSION);
    envelope.validate().expect("fixture must pass validation");
}

#[test]
fn qfs_l2_checkpoint_trace_links_are_mandatory() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let mut envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must be valid envelope json");

    envelope.trace_links.dataset_metadata_ref.clear();

    let err = envelope.validate().expect_err("must reject missing trace-link");
    assert_eq!(err, CheckpointEnvelopeValidationError::MissingTraceLink);
}

#[test]
fn qfs_l2_checkpoint_restore_admission_rejects_size_budget_with_stable_reason_code() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must be valid envelope json");

    let policy = CheckpointBudgetPolicy {
        max_checkpoint_size_bytes: 1,
        max_restore_cost_units: u64::MAX,
    };
    let err = envelope
        .evaluate_restore_admission(&policy)
        .expect_err("size budget must be rejected");
    assert_eq!(err.reason_code, CheckpointAdmissionReasonCode::SizeBudgetExceeded);
    assert!(err.hint.contains("declared_size_bytes"));
}

#[test]
fn qfs_l2_checkpoint_restore_admission_rejects_cost_budget_with_stable_reason_code() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must be valid envelope json");

    let policy = CheckpointBudgetPolicy {
        max_checkpoint_size_bytes: u64::MAX,
        max_restore_cost_units: 100,
    };
    let err = envelope
        .evaluate_restore_admission(&policy)
        .expect_err("cost budget must be rejected");
    assert_eq!(
        err.reason_code,
        CheckpointAdmissionReasonCode::RestoreCostBudgetExceeded
    );
    assert!(err.hint.contains("estimated_restore_cost_units"));
}
