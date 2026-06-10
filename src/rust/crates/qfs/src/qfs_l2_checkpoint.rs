use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::cmp::Ordering;

pub const CHECKPOINT_ENVELOPE_SCHEMA_VERSION: &str = "1.0.0";
pub const CHECKPOINT_RUNTIME_API_VERSION: &str = "1.1.0";
pub const DEFAULT_MAX_CHECKPOINT_SIZE_BYTES: u64 = 512 * 1024 * 1024;
pub const DEFAULT_MAX_RESTORE_COST_UNITS: u64 = 1_000;

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

    #[serde(default)]
    pub retention: CheckpointRetentionPolicy,

    #[serde(default)]
    pub restore_lineage: CheckpointRestoreLineage,
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

        if self.retention.retention_until_epoch_ms
            < self.retention.created_at_epoch_ms
        {
            return Err(
                CheckpointEnvelopeValidationError::InvalidRetentionWindow
            );
        }

        for segment in &self.payload_refs.state_segments {
            if !segment.content_hash.starts_with("sha256:") {
                return Err(
                    CheckpointEnvelopeValidationError::InvalidContentHashFormat
                );
            }
        }

        self.validate_restore_compatibility(
            CHECKPOINT_RUNTIME_API_VERSION,
        )?;

        Ok(())
    }

    pub fn validate_restore_compatibility(
        &self,
        runtime_version: &str,
    ) -> Result<(), CheckpointEnvelopeValidationError> {
        if let Some(min) = &self.compatibility.min_reader_version {
            if compare_versions(runtime_version, min) == Ordering::Less {
                return Err(
                    CheckpointEnvelopeValidationError::RestoreVersionIncompatible {
                        runtime_version: runtime_version.to_string(),
                        min_supported: Some(min.clone()),
                        max_supported: self.compatibility.max_reader_version.clone(),
                    },
                );
            }
        }

        if let Some(max) = &self.compatibility.max_reader_version {
            if compare_versions(runtime_version, max) == Ordering::Greater {
                return Err(
                    CheckpointEnvelopeValidationError::RestoreVersionIncompatible {
                        runtime_version: runtime_version.to_string(),
                        min_supported: self.compatibility.min_reader_version.clone(),
                        max_supported: Some(max.clone()),
                    },
                );
            }
        }

        Ok(())
    }

    pub fn verify_payload_integrity(
        &self,
        payload: &[u8],
    ) -> Result<(), CheckpointEnvelopeValidationError> {
        let actual = format!("sha256:{:x}", Sha256::digest(payload));
        let expected = self
            .payload_refs
            .state_segments
            .first()
            .map(|s| s.content_hash.clone())
            .unwrap_or_default();

        if actual != expected {
            return Err(CheckpointEnvelopeValidationError::PayloadIntegrityViolation);
        }
        Ok(())
    }

    pub fn evaluate_restore_admission(
        &self,
        policy: &CheckpointBudgetPolicy,
    ) -> Result<(), CheckpointAdmissionRejection> {
        if self.guardrails.declared_size_bytes > policy.max_checkpoint_size_bytes {
            return Err(CheckpointAdmissionRejection::new(
                CheckpointAdmissionReasonCode::SizeBudgetExceeded,
                format!(
                    "declared_size_bytes={} exceeds max_checkpoint_size_bytes={}",
                    self.guardrails.declared_size_bytes, policy.max_checkpoint_size_bytes
                ),
            ));
        }
        if self.guardrails.estimated_restore_cost_units > policy.max_restore_cost_units {
            return Err(CheckpointAdmissionRejection::new(
                CheckpointAdmissionReasonCode::RestoreCostBudgetExceeded,
                format!(
                    "estimated_restore_cost_units={} exceeds max_restore_cost_units={}",
                    self.guardrails.estimated_restore_cost_units, policy.max_restore_cost_units
                ),
            ));
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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct CheckpointRetentionPolicy {
    pub retention_class: String,
    pub created_at_epoch_ms: u64,
    pub retention_until_epoch_ms: u64,
    pub pinned: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct CheckpointRestoreLineage {
    pub restored_from_checkpoint_id: Option<String>,
    pub replay_session_id: Option<String>,
    pub restored_by_runtime_version: Option<String>,
}

#[derive(thiserror::Error, Debug, PartialEq, Eq)]
pub enum CheckpointEnvelopeValidationError {
    #[error("checkpoint schema version mismatch: expected {expected}, got {got}")]
    SchemaVersionMismatch { expected: String, got: String },
    #[error("mandatory trace-link fields must be non-empty")]
    MissingTraceLink,
    #[error("checkpoint retention window invalid")]
    InvalidRetentionWindow,
    #[error("checkpoint payload integrity violation")]
    PayloadIntegrityViolation,
    #[error("checkpoint content hash format invalid")]
    InvalidContentHashFormat,
    #[error(
        "restore runtime version incompatible: runtime={runtime_version} min={min_supported:?} max={max_supported:?}"
    )]
    RestoreVersionIncompatible {
        runtime_version: String,
        min_supported: Option<String>,
        max_supported: Option<String>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointBudgetPolicy {
    pub max_checkpoint_size_bytes: u64,
    pub max_restore_cost_units: u64,
}

impl Default for CheckpointBudgetPolicy {
    fn default() -> Self {
        Self {
            max_checkpoint_size_bytes: DEFAULT_MAX_CHECKPOINT_SIZE_BYTES,
            max_restore_cost_units: DEFAULT_MAX_RESTORE_COST_UNITS,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CheckpointAdmissionRejection {
    pub reason_code: CheckpointAdmissionReasonCode,
    pub hint: String,
}

impl CheckpointAdmissionRejection {
    fn new(reason_code: CheckpointAdmissionReasonCode, hint: String) -> Self {
        Self { reason_code, hint }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CheckpointAdmissionReasonCode {
    SizeBudgetExceeded,
    RestoreCostBudgetExceeded,
}

fn compare_versions(a: &str, b: &str) -> Ordering {
    let parse = |v: &str| {
        v.split('.')
            .map(|s| s.parse::<u64>().unwrap_or(0))
            .collect::<Vec<_>>()
    };

    let av = parse(a);
    let bv = parse(b);

    for i in 0..av.len().max(bv.len()) {
        let left = *av.get(i).unwrap_or(&0);
        let right = *bv.get(i).unwrap_or(&0);

        match left.cmp(&right) {
            Ordering::Equal => continue,
            non_eq => return non_eq,
        }
    }

    Ordering::Equal
}
