use std::fs;
use std::path::PathBuf;

use qfs::{
    CHECKPOINT_ENVELOPE_SCHEMA_VERSION, CheckpointEnvelopeV1, CheckpointEnvelopeValidationError,
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
