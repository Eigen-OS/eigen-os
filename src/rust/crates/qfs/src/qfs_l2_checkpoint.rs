use serde::{Deserialize, Serialize};

pub const CHECKPOINT_ENVELOPE_SCHEMA_VERSION: &str = "1.0.0";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointEnvelopeV1 {
    pub schema_version: String,
    pub checkpoint_id: String,
    pub job_id: String,
    pub created_at: String,
    pub runtime_version: String,
    pub payload_refs: CheckpointPayloadRefs,
    pub integrity: CheckpointIntegrity,
    pub provenance: CheckpointProvenance,
    pub trace_links: CheckpointTraceLinks,
    pub guardrails: CheckpointGuardrails,
    #[serde(default)]
    pub compatibility: CheckpointCompatibilityWindow,
    #[serde(default)]
    pub extensions: CheckpointExtensions,
}

impl CheckpointEnvelopeV1 {
    pub fn validate(&self) -> Result<(), CheckpointEnvelopeValidationError> {
        if self.schema_version != CHECKPOINT_ENVELOPE_SCHEMA_VERSION {
            return Err(CheckpointEnvelopeValidationError::SchemaVersionMismatch {
                expected: CHECKPOINT_ENVELOPE_SCHEMA_VERSION.to_string(),
                got: self.schema_version.clone(),
            });
        }
        if self.trace_links.artifact_manifest_ref.is_empty()
            || self.trace_links.dataset_metadata_ref.is_empty()
            || self.trace_links.checkpoint_chain_ref.is_empty()
        {
            return Err(CheckpointEnvelopeValidationError::MissingTraceLink);
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointPayloadRefs {
    pub state_segments: Vec<CheckpointArtifactRef>,
    pub memory_graph_ref: String,
    pub execution_cursor_ref: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointArtifactRef {
    pub path: String,
    pub content_hash: String,
    pub size_bytes: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointIntegrity {
    pub checksum_set: String,
    pub signature_ref: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointProvenance {
    pub compiler_version: String,
    pub optimizer_version: String,
    pub model_version: String,
    pub backend_profile: String,
    pub deterministic_seed: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointTraceLinks {
    pub artifact_manifest_ref: String,
    pub dataset_metadata_ref: String,
    pub checkpoint_chain_ref: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointGuardrails {
    pub declared_size_bytes: u64,
    pub estimated_restore_cost_units: u64,
    pub ttl_class: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct CheckpointCompatibilityWindow {
    pub min_reader_version: Option<String>,
    pub max_reader_version: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct CheckpointExtensions {
    pub extension_keys: Vec<String>,
}

#[derive(thiserror::Error, Debug, PartialEq, Eq)]
pub enum CheckpointEnvelopeValidationError {
    #[error("checkpoint schema version mismatch: expected {expected}, got {got}")]
    SchemaVersionMismatch { expected: String, got: String },
    #[error("mandatory trace-link fields must be non-empty")]
    MissingTraceLink,
}
