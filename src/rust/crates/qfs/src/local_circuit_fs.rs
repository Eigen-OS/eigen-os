use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use sha2::Sha256;
use tempfile::NamedTempFile;

/// Default filesystem root for CircuitFS (QFS-L3).
///
/// For local development/tests, you should override this with a temp directory.
pub const DEFAULT_CIRCUIT_FS_ROOT: &str = "/var/lib/eigen/circuit_fs";

/// Represents the “source bundle” artifacts stored in QFS.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBundle {
    pub job_yaml: String,
    pub program_eigen_py: Vec<u8>,
}

/// Represents the “results bundle” artifacts stored in QFS.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResultsBundle {
    /// Apache Parquet payload stored at `/jobs/{job_id}/results.parquet`.
    pub parquet: Vec<u8>,
    /// Versioned envelope describing the durable result artifact contract.
    pub envelope: ResultEnvelope,
    /// Integrity manifest for the durable result artifacts.
    pub manifest: ResultManifest,
}

/// Represents compilation outputs stored under `compiled/`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompiledArtifacts {
    pub aqo_json: Vec<u8>,
    pub qasm: Option<Vec<u8>>,
    pub compile_report_json: Option<Vec<u8>>,
    pub metadata: CompiledMetadata,
}

/// Provenance/lineage for compiler outputs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct CompiledArtifactLineage {
    #[serde(default)]
    pub request_id: Option<String>,
    #[serde(default)]
    pub source_ref: Option<String>,
    #[serde(default)]
    pub source_sha256: Option<String>,
}

/// Explicit inputs used to write canonical compiler artifacts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompiledArtifactProvenance {
    pub producer_identity: String,
    pub contract_version: String,
    pub compiler_version: String,
    pub created_at: String,
    pub lineage: CompiledArtifactLineage,
}

/// Metadata for source bundle artifacts.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceMetadata {
    pub version: String,
    pub schema_version: String,
    pub job_yaml_hash: String,
    pub program_hash: String,
}

/// Metadata for compiler outputs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompiledMetadata {
    pub version: String,
    pub schema_version: String,
    pub compiler_version: String,
    #[serde(default)]
    pub producer_identity: String,
    #[serde(default)]
    pub retention_policy: String,
    pub contract_version: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub source_sha256: String,
    pub aqo_hash: String,
    #[serde(default)]
    pub qasm_hash: Option<String>,
    #[serde(default)]
    pub diagnostics_hash: Option<String>,
    #[serde(default)]
    pub lineage: CompiledArtifactLineage,
}

/// Versioned result envelope persisted under `results/result.json`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResultEnvelope {
    pub artifact_version: String,
    pub producer_version: String,
    pub job_id: String,
    pub result_ref: String,
    pub manifest_ref: String,
    #[serde(default)]
    pub created_at_epoch_ms: u64,
    #[serde(default)]
    pub retention_policy: String,
    #[serde(default)]
    pub lineage: CompiledArtifactLineage,
}

/// Durable artifact manifest for runtime outputs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResultManifest {
    pub artifact_version: String,
    pub producer_version: String,
    pub schema_version: String,
    #[serde(default)]
    pub created_at_epoch_ms: u64,
    #[serde(default)]
    pub retention_policy: String,
    #[serde(default)]
    pub artifacts: Vec<ResultArtifact>,
}

/// ... existing content omitted for brevity ...

impl CircuitFsLocal {
    pub fn store_compiled_artifacts_v1(
        &self,
        job_id: &str,
        aqo_json: &[u8],
        qasm: Option<&[u8]>,
        compile_report_json: Option<&[u8]>,
        provenance: CompiledArtifactProvenance,
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        let compiled_aqo_path = self.compiled_aqo_json_path(job_id)?;
        let compiled_metadata_path = self.compiled_metadata_path(job_id)?;
        let compiled_qasm_path = self.compiled_qasm_path(job_id)?;
        let compiled_report_path = self.compiled_report_path(job_id)?;

        for path in [
            compiled_aqo_path.clone(),
            compiled_metadata_path.clone(),
            compiled_qasm_path.clone(),
            compiled_report_path.clone(),
        ] {
            if path.exists() {
                return Err(CircuitFsError::AlreadyExists { path });
            }
        }

        atomic_write_bytes(&compiled_aqo_path, aqo_json)?;
        if let Some(qasm_bytes) = qasm {
            atomic_write_bytes(&compiled_qasm_path, qasm_bytes)?;
        }
        if let Some(report_bytes) = compile_report_json {
            atomic_write_bytes(&compiled_report_path, report_bytes)?;
        }

        let metadata = CompiledMetadata {
            version: "1.0.0".to_string(),
            schema_version: "compiled_artifacts.v1".to_string(),
            compiler_version: provenance.compiler_version.clone(),
            producer_identity: provenance.producer_identity,
            retention_policy: "pinned".to_string(),
            contract_version: provenance.contract_version,
            created_at: provenance.created_at,
            source_sha256: provenance
                .lineage
                .source_sha256
                .clone()
                .unwrap_or_default(),
            aqo_hash: content_hash_hex(aqo_json),
            qasm_hash: qasm.map(content_hash_hex),
            diagnostics_hash: compile_report_json.map(content_hash_hex),
            lineage: provenance.lineage,
        };

        let bytes = serde_json::to_vec_pretty(&metadata).map_err(to_io_error)?;
        atomic_write_bytes(&compiled_metadata_path, &bytes)?;
        Ok(())
    }
}

fn verify_result_manifest(
    parquet_path: &Path,
    envelope_path: &Path,
    manifest_path: &Path,
    parquet: &[u8],
    envelope: &ResultEnvelope,
    manifest: &ResultManifest,
) -> Result<(), CircuitFsError> {
    verify_hash(parquet_path, &content_hash_hex(parquet), parquet)?;
    if !envelope.result_ref.is_empty() {
        let envelope_bytes = serde_json::to_vec_pretty(envelope).map_err(to_io_error)?;
        verify_hash(envelope_path, &content_hash_hex(&envelope_bytes), &envelope_bytes)?;
    }
    if !manifest.artifacts.is_empty() {
        let manifest_bytes = serde_json::to_vec_pretty(manifest).map_err(to_io_error)?;
        verify_hash(manifest_path, &content_hash_hex(&manifest_bytes), &manifest_bytes)?;
    }
    for artifact in &manifest.artifacts {
        let actual_bytes: Vec<u8> = match artifact.path.as_str() {
            "results.parquet" => parquet.to_vec(),
            "results/result.json" => serde_json::to_vec_pretty(envelope).map_err(to_io_error)?,
            _ => continue,
        };

        let actual_hash = content_hash_hex(&actual_bytes);
        if actual_hash != artifact.content_hash {
            return Err(CircuitFsError::IntegrityMismatch {
                path: parquet_path.to_path_buf(),
            });
        }
    }
    Ok(())
}

fn to_io_error(err: serde_json::Error) -> CircuitFsError {
    CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidData, err))
}

fn content_hash_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}
