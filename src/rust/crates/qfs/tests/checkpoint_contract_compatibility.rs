use std::fs;
use std::path::PathBuf;

use qfs::{
    CheckpointAdmissionReasonCode, CheckpointBudgetPolicy, CHECKPOINT_ENVELOPE_SCHEMA_VERSION,
    CheckpointEnvelopeV1, CheckpointEnvelopeValidationError,
};
use sha2::{Digest, Sha256};

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

#[test]
fn qfs_l2_checkpoint_restore_compatibility_rejects_unsupported_runtime_version() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must decode");

    let err = envelope
        .validate_restore_compatibility("0.8.0")
        .expect_err("old runtime must be rejected");

    assert!(matches!(
        err,
        CheckpointEnvelopeValidationError::RestoreVersionIncompatible { .. }
    ));
}

#[test]
fn qfs_l2_checkpoint_corrupted_payload_is_rejected() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let mut envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must decode");

    let payload = b"checkpoint-payload";
    envelope.payload_refs.state_segments[0].content_hash =
        format!("sha256:{:x}", Sha256::digest(payload));

    let err = envelope
        .verify_payload_integrity(b"tampered")
        .expect_err("tampered payload must fail");

    assert_eq!(
        err,
        CheckpointEnvelopeValidationError::PayloadIntegrityViolation
    );
}

#[test]
fn qfs_l2_checkpoint_retention_window_validation_is_stable() {
    let raw = fixture("qfs_l2_checkpoint_envelope_v1_0_0.json");
    let mut envelope: CheckpointEnvelopeV1 =
        serde_json::from_str(&raw).expect("fixture must decode");

    envelope.retention.created_at_epoch_ms = 200;
    envelope.retention.retention_until_epoch_ms = 100;

    let err = envelope
        .validate()
        .expect_err("invalid retention must fail");

    assert_eq!(
        err,
        CheckpointEnvelopeValidationError::InvalidRetentionWindow
    );
}
