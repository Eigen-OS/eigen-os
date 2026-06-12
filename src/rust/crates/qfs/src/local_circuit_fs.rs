use std::fs;
use std::fs::OpenOptions;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;
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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResultArtifactDescriptor {
    pub path: String,
    pub content_hash: String,
    pub size_bytes: u64,
}

#[derive(Debug, Error)]
pub enum CircuitFsError {
    #[error("artifact already exists: {path}")]
    AlreadyExists { path: PathBuf },

    #[error("artifact integrity mismatch: {path}")]
    IntegrityMismatch { path: PathBuf },

    #[error("artifact not found: {path}")]
    NotFound { path: PathBuf },

    #[error("invalid job id: {job_id}")]
    InvalidJobId { job_id: String },

    #[error(transparent)]
    Io(#[from] io::Error),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CircuitFsLocal {
    root: PathBuf,
}

impl CircuitFsLocal {
    pub fn new(root: impl AsRef<Path>) -> Self {
        Self { root: root.as_ref().to_path_buf() }
    }

    pub fn root_path(&self) -> &Path {
        &self.root
    }

    pub fn ensure_job_layout(&self, job_id: &str) -> Result<(), CircuitFsError> {
        fs::create_dir_all(self.job_root_path(job_id)?)?;
        fs::create_dir_all(self.compiled_dir_path(job_id)?)?;
        fs::create_dir_all(self.results_dir_path(job_id)?)?;
        fs::create_dir_all(self.observability_dir_path(job_id)?)?;
        fs::create_dir_all(self.logs_dir_path(job_id)?)?;
        fs::create_dir_all(self.meta_dir_path(job_id)?)?;
        fs::create_dir_all(self.release_evidence_dir_path(job_id)?)?;
        Ok(())
    }

    pub fn append_log_line(&self, job_id: &str, stream: &str, line: &str) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;
        let path = self.log_path(job_id, stream)?;
        let parent = path
            .parent()
            .ok_or_else(|| CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidInput, "missing log parent")))?;
        fs::create_dir_all(parent)?;
        let mut fh = OpenOptions::new().create(true).append(true).open(&path)?;
        fh.write_all(line.trim_end_matches('\n').as_bytes())?;
        fh.write_all(b"\n")?;
        fh.flush()?;
        fh.sync_all()?;
        Ok(())
    }

    pub fn store_results_bundle(
        &self,
        job_id: &str,
        payload: &[u8],
        producer_version: &str,
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        let result_path = self.result_json_path(job_id)?;
        let manifest_path = self.result_manifest_path(job_id)?;
        let envelope_path = self.result_envelope_path(job_id)?;

        for path in [result_path.clone(), manifest_path.clone(), envelope_path.clone()] {
            if path.exists() {
                return Err(CircuitFsError::AlreadyExists { path });
            }
        }

        atomic_write_bytes(&result_path, payload)?;

        let created_at_epoch_ms = unix_epoch_ms();
        let envelope = ResultEnvelope {
            artifact_version: "1.0.0".to_string(),
            producer_version: producer_version.to_string(),
            job_id: job_id.to_string(),
            result_ref: "results/result.json".to_string(),
            manifest_ref: "results/manifest.json".to_string(),
            created_at_epoch_ms,
            retention_policy: "pinned".to_string(),
            lineage: CompiledArtifactLineage::default(),
        };
        let envelope_bytes = serde_json::to_vec_pretty(&envelope).map_err(to_io_error)?;
        atomic_write_bytes(&envelope_path, &envelope_bytes)?;

        let manifest = ResultManifest {
            artifact_version: "1.0.0".to_string(),
            producer_version: producer_version.to_string(),
            schema_version: "result_manifest.v1".to_string(),
            created_at_epoch_ms,
            retention_policy: "pinned".to_string(),
            artifacts: vec![ResultArtifactDescriptor {
                path: "results/result.json".to_string(),
                content_hash: content_hash_hex(payload),
                size_bytes: payload.len() as u64,
            }],
        };
        let manifest_bytes = serde_json::to_vec_pretty(&manifest).map_err(to_io_error)?;
        atomic_write_bytes(&manifest_path, &manifest_bytes)?;
        Ok(())
    }

    pub fn store_metrics_json(&self, job_id: &str, metrics: &[u8]) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;
        let path = self.metrics_json_path(job_id)?;
        if path.exists() {
            return Err(CircuitFsError::AlreadyExists { path });
        }
        atomic_write_bytes(&path, metrics)
    }

    fn validate_job_id(job_id: &str) -> Result<(), CircuitFsError> {
        let valid_chars = job_id
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-'));
        let forbidden_segments = job_id.is_empty()
            || job_id == "."
            || job_id == ".."
            || job_id.contains("..")
            || job_id.as_bytes().contains(&0);
        if !valid_chars || forbidden_segments {
            return Err(CircuitFsError::InvalidJobId { job_id: job_id.to_string() });
        }
        Ok(())
    }

    fn observability_dir_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root_path(job_id)?.join("observability"))
    }

    fn logs_dir_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root_path(job_id)?.join("logs"))
    }

    fn meta_dir_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root_path(job_id)?.join("meta"))
    }

    fn release_evidence_dir_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.meta_dir_path(job_id)?.join("release_evidence"))
    }

    fn result_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir_path(job_id)?.join("result.json"))
    }

    fn result_manifest_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir_path(job_id)?.join("manifest.json"))
    }

    fn result_envelope_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir_path(job_id)?.join("envelope.json"))
    }

    fn release_evidence_bundle_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.release_evidence_dir_path(job_id)?.join("bundle.json"))
    }

    fn release_evidence_manifest_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.release_evidence_dir_path(job_id)?.join("manifest.json"))
    }

    fn release_evidence_provenance_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.release_evidence_dir_path(job_id)?.join("provenance.json"))
    }

    fn metrics_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.observability_dir_path(job_id)?.join("metrics.json"))
    }

    fn log_path(&self, job_id: &str, stream: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.logs_dir_path(job_id)?.join(format!("{stream}.jsonl")))
    }

    fn job_root_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Self::validate_job_id(job_id)?;
        Ok(self.root.join("jobs").join(job_id))
    }

    fn compiled_dir_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root_path(job_id)?.join("compiled"))
    }

    fn compiled_aqo_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir_path(job_id)?.join("circuit.aqo.json"))
    }

    fn compiled_metadata_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir_path(job_id)?.join("metadata.json"))
    }

    fn compiled_qasm_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir_path(job_id)?.join("circuit.qasm"))
    }

    fn compiled_report_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir_path(job_id)?.join("compile_report.json"))
    }

    fn results_dir_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root_path(job_id)?.join("results"))
    }
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
    pub artifacts: Vec<ResultArtifactDescriptor>,
}

/// Release-evidence bundle persisted under `meta/release_evidence/`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReleaseEvidenceBundle {
    pub artifact_version: String,
    pub schema_version: String,
    pub producer_version: String,
    pub job_id: String,
    pub compiler_contract_version: String,
    pub optimizer_contract_version: String,
    pub request_id: String,
    pub trace_id: String,
    pub traceparent: String,
    pub source_sha256: String,
    pub aqo_sha256: String,
    #[serde(default)]
    pub optimized_aqo_sha256: Option<String>,
    pub compiled_artifact_ref: String,
    pub optimized_artifact_ref: String,
    pub manifest_ref: String,
    pub provenance_report_ref: String,
    #[serde(default)]
    pub created_at_epoch_ms: u64,
}

/// Artifact manifest for release evidence bundles.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReleaseEvidenceManifest {
    pub artifact_version: String,
    pub producer_version: String,
    pub schema_version: String,
    #[serde(default)]
    pub created_at_epoch_ms: u64,
    #[serde(default)]
    pub retention_policy: String,
    #[serde(default)]
    pub artifacts: Vec<ResultArtifactDescriptor>,
}

/// Provenance report tying release evidence back to compile and optimization runs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReleaseEvidenceProvenanceReport {
    pub artifact_version: String,
    pub schema_version: String,
    pub job_id: String,
    pub request_id: String,
    pub trace_id: String,
    pub traceparent: String,
    pub compiler_stage_id: String,
    pub optimizer_stage_id: String,
    pub compiler_run_id: String,
    pub optimizer_run_id: String,
    pub compiler_artifact_ref: String,
    pub optimized_artifact_ref: String,
    pub compiler_lineage: CompiledArtifactLineage,
    #[serde(default)]
    pub optimized_aqo_sha256: Option<String>,
}

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

        let compiled_paths: [PathBuf; 4] = [
            compiled_aqo_path.clone(),
            compiled_metadata_path.clone(),
            compiled_qasm_path.clone(),
            compiled_report_path.clone(),
        ];
        for path in compiled_paths {
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

    pub fn store_release_evidence_bundle_v1(
        &self,
        job_id: &str,
        bundle: &ReleaseEvidenceBundle,
        manifest: &ReleaseEvidenceManifest,
        provenance_report: &ReleaseEvidenceProvenanceReport,
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        let bundle_path = self.release_evidence_bundle_path(job_id)?;
        let manifest_path = self.release_evidence_manifest_path(job_id)?;
        let provenance_path = self.release_evidence_provenance_path(job_id)?;

        for path in [bundle_path.clone(), manifest_path.clone(), provenance_path.clone()] {
            if path.exists() {
                return Err(CircuitFsError::AlreadyExists { path });
            }
        }

        let bundle_bytes = serde_json::to_vec_pretty(bundle).map_err(to_io_error)?;
        let manifest_bytes = serde_json::to_vec_pretty(manifest).map_err(to_io_error)?;
        let provenance_bytes = serde_json::to_vec_pretty(provenance_report).map_err(to_io_error)?;

        atomic_write_bytes(&bundle_path, &bundle_bytes)?;
        atomic_write_bytes(&manifest_path, &manifest_bytes)?;
        atomic_write_bytes(&provenance_path, &provenance_bytes)?;
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

fn atomic_write_bytes(path: &Path, bytes: &[u8]) -> Result<(), CircuitFsError> {
    let parent = path
        .parent()
        .ok_or_else(|| CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidInput, "missing parent directory")))?;
    fs::create_dir_all(parent)?;
    let mut tmp = NamedTempFile::new_in(parent)?;
    tmp.write_all(bytes)?;
    tmp.flush()?;
    tmp.as_file().sync_all()?;
    tmp.persist(path)
        .map_err(|err| CircuitFsError::Io(err.error))?;
    Ok(())
}

fn verify_hash(path: &Path, expected: &str, actual: &[u8]) -> Result<(), CircuitFsError> {
    let actual_hash = content_hash_hex(actual);
    if actual_hash != expected {
        return Err(CircuitFsError::IntegrityMismatch {
            path: path.to_path_buf(),
        });
    }
    Ok(())
}

fn unix_epoch_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    fn read_json(path: &Path) -> serde_json::Value {
        let bytes = fs::read(path).expect("read json");
        serde_json::from_slice(&bytes).expect("parse json")
    }

    #[test]
    fn store_compiled_artifacts_uses_canonical_paths_and_metadata() {
        let tempdir = tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tempdir.path());

        let provenance = CompiledArtifactProvenance {
            producer_identity: "compiler-service".to_string(),
            contract_version: "1.0.0".to_string(),
            compiler_version: "1.0.0".to_string(),
            created_at: "2026-06-12T00:00:00Z".to_string(),
            lineage: CompiledArtifactLineage {
                request_id: Some("req-123".to_string()),
                source_ref: Some("qfs://jobs/job-123/input/program.eigen.py".to_string()),
                source_sha256: Some("deadbeef".to_string()),
            },
        };

        fs.store_compiled_artifacts_v1(
            "job-123",
            br#"{"aqo":"ok"}"#,
            Some(b"OPENQASM 3;"),
            Some(br#"{"status":"ok"}"#),
            provenance,
        )
        .expect("store compiled artifacts");

        let job_root = tempdir.path().join("jobs").join("job-123");
        assert!(job_root.join("compiled/circuit.aqo.json").exists());
        assert!(job_root.join("compiled/circuit.qasm").exists());
        assert!(job_root.join("compiled/compile_report.json").exists());
        assert!(job_root.join("compiled/metadata.json").exists());

        let metadata = read_json(&job_root.join("compiled/metadata.json"));
        assert_eq!(metadata["version"], "1.0.0");
        assert_eq!(metadata["schema_version"], "compiled_artifacts.v1");
        assert_eq!(metadata["compiler_version"], "1.0.0");
        assert_eq!(metadata["producer_identity"], "compiler-service");
        assert_eq!(metadata["contract_version"], "1.0.0");
        assert_eq!(metadata["lineage"]["request_id"], "req-123");
        assert_eq!(metadata["lineage"]["source_ref"], "qfs://jobs/job-123/input/program.eigen.py");
    }

    #[test]
    fn store_release_evidence_bundle_writes_bundle_manifest_and_provenance() {
        let tempdir = tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tempdir.path());

        let bundle = ReleaseEvidenceBundle {
            artifact_version: "1.0.0".to_string(),
            schema_version: "release_evidence_bundle.v1".to_string(),
            producer_version: "1.0.0".to_string(),
            job_id: "job-456".to_string(),
            compiler_contract_version: "1.0.0".to_string(),
            optimizer_contract_version: "1.0.0".to_string(),
            request_id: "req-456".to_string(),
            trace_id: "trace-456".to_string(),
            traceparent: "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01".to_string(),
            source_sha256: "sha256:1111".to_string(),
            aqo_sha256: "sha256:2222".to_string(),
            optimized_aqo_sha256: Some("sha256:3333".to_string()),
            compiled_artifact_ref: "qfs://jobs/job-456/compiled/circuit.aqo.json".to_string(),
            optimized_artifact_ref: "qfs://jobs/job-456/optimizer/optimized_aqo.json".to_string(),
            manifest_ref: "qfs://jobs/job-456/meta/release_evidence/manifest.json".to_string(),
            provenance_report_ref: "qfs://jobs/job-456/meta/release_evidence/provenance.json".to_string(),
            created_at_epoch_ms: 1_717_000_000_000,
        };
        let manifest = ReleaseEvidenceManifest {
            artifact_version: "1.0.0".to_string(),
            producer_version: "1.0.0".to_string(),
            schema_version: "release_evidence_manifest.v1".to_string(),
            created_at_epoch_ms: 1_717_000_000_001,
            retention_policy: "pinned".to_string(),
            artifacts: vec![
                ResultArtifactDescriptor {
                    path: "meta/release_evidence/bundle.json".to_string(),
                    content_hash: "sha256:aaaa".to_string(),
                    size_bytes: 123,
                },
                ResultArtifactDescriptor {
                    path: "meta/release_evidence/provenance.json".to_string(),
                    content_hash: "sha256:bbbb".to_string(),
                    size_bytes: 456,
                },
            ],
        };
        let provenance = ReleaseEvidenceProvenanceReport {
            artifact_version: "1.0.0".to_string(),
            schema_version: "release_evidence_provenance.v1".to_string(),
            job_id: "job-456".to_string(),
            request_id: "req-456".to_string(),
            trace_id: "trace-456".to_string(),
            traceparent: "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01".to_string(),
            compiler_stage_id: "stage-compile".to_string(),
            optimizer_stage_id: "stage-optimize".to_string(),
            compiler_run_id: "run-compile".to_string(),
            optimizer_run_id: "run-optimize".to_string(),
            compiler_artifact_ref: "qfs://jobs/job-456/compiled/circuit.aqo.json".to_string(),
            optimized_artifact_ref: "qfs://jobs/job-456/optimizer/optimized_aqo.json".to_string(),
            compiler_lineage: CompiledArtifactLineage {
                request_id: Some("req-456".to_string()),
                source_ref: Some("qfs://jobs/job-456/input/program.eigen.py".to_string()),
                source_sha256: Some("deadbeef".to_string()),
            },
            optimized_aqo_sha256: Some("sha256:3333".to_string()),
        };

        fs.store_release_evidence_bundle_v1("job-456", &bundle, &manifest, &provenance)
            .expect("store release evidence bundle");

        let job_root = tempdir.path().join("jobs").join("job-456");
        assert!(job_root.join("meta/release_evidence/bundle.json").exists());
        assert!(job_root.join("meta/release_evidence/manifest.json").exists());
        assert!(job_root.join("meta/release_evidence/provenance.json").exists());

        let bundle_json = read_json(&job_root.join("meta/release_evidence/bundle.json"));
        assert_eq!(
            bundle_json["compiled_artifact_ref"],
            "qfs://jobs/job-456/compiled/circuit.aqo.json"
        );
        assert_eq!(
            bundle_json["manifest_ref"],
            "qfs://jobs/job-456/meta/release_evidence/manifest.json"
        );
        assert_eq!(
            bundle_json["provenance_report_ref"],
            "qfs://jobs/job-456/meta/release_evidence/provenance.json"
        );

        let provenance_json = read_json(&job_root.join("meta/release_evidence/provenance.json"));
        assert_eq!(provenance_json["compiler_stage_id"], "stage-compile");
        assert_eq!(provenance_json["optimizer_stage_id"], "stage-optimize");
        assert_eq!(provenance_json["compiler_lineage"]["request_id"], "req-456");
    }

    #[test]
    fn replay_safe_job_ids_reject_path_traversal_and_invalid_segments() {
        let tempdir = tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tempdir.path());

        for job_id in ["", ".", "..", "bad/segment", "bad..segment", "bad\\segment"] {
            let err = fs.ensure_job_layout(job_id).expect_err("invalid job id must fail");
            match err {
                CircuitFsError::InvalidJobId { job_id: rejected } => assert_eq!(rejected, job_id),
                other => panic!("unexpected error: {other:?}"),
            }
        }

        let err = fs
            .ensure_job_layout("bad\0segment")
            .expect_err("invalid null byte job id must fail");
        match err {
            CircuitFsError::InvalidJobId { job_id: rejected } => assert_eq!(rejected, "bad\0segment"),
            other => panic!("unexpected error: {other:?}"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct ErrorDetails {
    pub code: String,
    pub summary: String,
    pub detail: String,
}
