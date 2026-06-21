use std::fs;
use std::fs::OpenOptions;
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::future::Future;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tempfile::NamedTempFile;

use arrow_array::{ArrayRef, Float64Array, Int64Array, RecordBatch, StringArray};
use arrow_schema::{DataType, Field, Schema};
use parquet::arrow::ArrowWriter;
use parquet::file::properties::WriterProperties;
use thiserror::Error;
use tokio::runtime::Handle;
use tokio::task;


/// Default filesystem root for CircuitFS (QFS-L3).
///
/// For local development/tests, you should override this with a temp directory.
pub const DEFAULT_CIRCUIT_FS_ROOT: &str = "/var/lib/eigen/circuit_fs";

const MINIO_MIRROR_MAX_ATTEMPTS: usize = 3;
const MINIO_MIRROR_BACKOFF_MS: u64 = 50;
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

/// Scientific measurement row embedded into the canonical result envelope.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct ScientificMeasurement {
    pub metric_name: String,
    #[serde(default)]
    pub metric_kind: String,
    pub metric_value: String,
    #[serde(default)]
    pub metric_unit: String,
    #[serde(default)]
    pub stage_id: Option<String>,
    #[serde(default)]
    pub stage_key: Option<String>,
    #[serde(default)]
    pub step_index: Option<i64>,
    #[serde(default)]
    pub trial_index: Option<i64>,
    #[serde(default)]
    pub seed: Option<i64>,
    #[serde(default)]
    pub backend: Option<String>,
    #[serde(default)]
    pub target: Option<String>,
    #[serde(default)]
    pub trace_id: Option<String>,
    #[serde(default)]
    pub traceparent: Option<String>,
    #[serde(default)]
    pub artifact_ref: Option<String>,
    #[serde(default)]
    pub attributes: BTreeMap<String, String>,
}

#[derive(Debug, Error)]
pub enum CircuitFsError {
    #[error("artifact already exists: {path}")]
    AlreadyExists { path: PathBuf },

    #[error("artifact integrity mismatch: {path}")]
    IntegrityMismatch { path: PathBuf },

    #[error("artifact not found: {path}")]
    NotFound { path: PathBuf },

    #[error("failed to mirror artifact to MinIO ({path} -> s3://{bucket}/{key}): {message}")]
    MinioMirrorFailed {
        path: PathBuf,
        bucket: String,
        key: String,
        message: String,
    },

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

    fn resolve_path(&self, path: &Path) -> PathBuf {
        let raw = path.to_string_lossy();
        if let Some(normalized) = raw.strip_prefix("qfs://").or_else(|| raw.strip_prefix("circuitfs://")) {
            self.root.join(normalized.trim_start_matches('/'))
        } else {
            path.to_path_buf()
        }
    }

    pub fn write_bytes(&self, path: impl AsRef<Path>, bytes: &[u8]) -> Result<(), CircuitFsError> {
        atomic_write_bytes(&self.resolve_path(path.as_ref()), bytes)
    }

    pub fn read_bytes(&self, path: impl AsRef<Path>) -> Result<Vec<u8>, CircuitFsError> {
        let path = self.resolve_path(path.as_ref());
        if path.exists() {
            return Ok(fs::read(&path)?);
        }
        if let Some(bytes) = download_path_from_minio(&path)? {
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(path, &bytes)?;
            return Ok(bytes);
        }
        Err(CircuitFsError::NotFound { path: path.to_path_buf() })
    }

    pub fn object_exists(&self, path: impl AsRef<Path>) -> bool {
        let path = self.resolve_path(path.as_ref());
        if path.exists() {
            return true;
        }
        if !minio_enabled() {
            return false;
        }
        path_key(&path)
            .and_then(|key| {
                let bucket = minio_bucket();
                block_on_maybe_in_place(async move {
                    let client = minio_client().await?;
                    Ok::<bool, CircuitFsError>(
                        client
                            .head_object()
                            .bucket(bucket)
                            .key(key)
                            .send()
                            .await
                            .is_ok(),
                    )
                })
                .ok()
            })
            .unwrap_or(false)
    }

    pub fn list_refs(&self, prefix: &str) -> Result<Vec<String>, CircuitFsError> {
        let mut refs: Vec<String> = Vec::new();
        let root = self.root.clone();
        if root.exists() {
            let mut stack = vec![root.clone()];
            while let Some(dir) = stack.pop() {
                for entry in fs::read_dir(&dir)? {
                    let entry = entry?;
                    let path = entry.path();
                    if path.is_dir() {
                        stack.push(path);
                        continue;
                    }
                    if path.is_file() {
                        let rel = path
                            .strip_prefix(&root)
                            .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "path escapes qfs root"))?
                            .to_string_lossy()
                            .replace('\\', "/");
                        let qfs_ref = format!("qfs://{rel}");
                        if qfs_ref.starts_with(prefix) {
                            refs.push(qfs_ref);
                        }
                    }
                }
            }
        }
        if minio_enabled() {
            refs.extend(list_refs_from_minio(prefix)?);
        }
        refs.sort();
        refs.dedup();
        Ok(refs)
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
        let bytes = line.trim_end_matches('\n').as_bytes();
        fh.write_all(bytes)?;
        fh.write_all(b"\n")?;
        fh.flush()?;
        fh.sync_all()?;
        if let Err(err) = mirror_path_to_minio(&path, bytes) {
            eprintln!(
                "failed to mirror log line to MinIO: path={} error={}",
                path.display(),
                err
            );
        }
        Ok(())
    }

    pub fn store_results_bundle(
        &self,
        job_id: &str,
        envelope: &ResultEnvelope,
        producer_version: &str,
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        let parquet_path = self.results_parquet_path(job_id)?;
        let result_json_path = self.result_json_path(job_id)?;
        let manifest_path = self.result_manifest_path(job_id)?;
        let envelope_path = self.result_envelope_path(job_id)?;

        for path in [
            parquet_path.clone(),
            result_json_path.clone(),
            manifest_path.clone(),
            envelope_path.clone(),
        ] {
            if self.object_exists(&path) {
                return Err(CircuitFsError::AlreadyExists { path });
            }
        }

        let envelope_bytes = serde_json::to_vec_pretty(envelope).map_err(to_io_error)?;
        let parquet_bytes = write_scientific_results_parquet(envelope)?;
        atomic_write_bytes(&parquet_path, &parquet_bytes)?;
        atomic_write_bytes(&result_json_path, &envelope_bytes)?;
        atomic_write_bytes(&envelope_path, &envelope_bytes)?;

        let manifest = ResultManifest {
            artifact_version: envelope.artifact_version.clone(),
            producer_version: producer_version.to_string(),
            schema_version: "result_manifest.v1".to_string(),
            created_at_epoch_ms: envelope.created_at_epoch_ms,
            retention_policy: envelope.retention_policy.clone(),
            artifacts: vec![
                ResultArtifactDescriptor {
                    path: "results.parquet".to_string(),
                    content_hash: content_hash_hex(&parquet_bytes),
                    size_bytes: parquet_bytes.len() as u64,
                },
                ResultArtifactDescriptor {
                    path: "results/result.json".to_string(),
                    content_hash: content_hash_hex(&envelope_bytes),
                    size_bytes: envelope_bytes.len() as u64,
                },
            ],
        };
        let manifest_bytes = serde_json::to_vec_pretty(&manifest).map_err(to_io_error)?;
        atomic_write_bytes(&manifest_path, &manifest_bytes)?;
        Ok(())
    }

    pub fn store_metrics_json(&self, job_id: &str, metrics: &[u8]) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;
        let path = self.metrics_json_path(job_id)?;
        if self.object_exists(&path) {
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

    fn results_parquet_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root_path(job_id)?.join("results.parquet"))
    }
}

/// Represents the “results bundle” artifacts stored in QFS.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResultsBundle {
    /// Versioned envelope describing the durable result artifact contract.
    pub envelope: ResultEnvelope,
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
    #[serde(default = "default_scientific_schema_version")]
    pub schema_version: String,
    pub producer_version: String,
    pub job_id: String,
    #[serde(default)]
    pub workload_kind: String,
    pub result_ref: String,
    pub manifest_ref: String,
    #[serde(default)]
    pub created_at_epoch_ms: u64,
    #[serde(default)]
    pub retention_policy: String,
    #[serde(default)]
    pub lineage: CompiledArtifactLineage,
    #[serde(default)]
    pub context: BTreeMap<String, String>,
    #[serde(default)]
    pub summary: BTreeMap<String, String>,
    #[serde(default)]
    pub measurements: Vec<ScientificMeasurement>,
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
            if self.object_exists(&path) {
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
            if self.object_exists(&path) {
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

fn default_scientific_schema_version() -> String {
    "scientific_result_bundle.v1".to_string()
}

fn content_hash_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn normalize_nonempty(value: &str, fallback: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        fallback.to_string()
    } else {
        trimmed.to_string()
    }
}

fn write_scientific_results_parquet(envelope: &ResultEnvelope) -> Result<Vec<u8>, CircuitFsError> {
    let row_count = envelope.measurements.len();
    let context_json = serde_json::to_string(&envelope.context).map_err(to_io_error)?;
    let summary_json = serde_json::to_string(&envelope.summary).map_err(to_io_error)?;

    let mut job_id = Vec::with_capacity(row_count);
    let mut workload_kind = Vec::with_capacity(row_count);
    let mut schema_version = Vec::with_capacity(row_count);
    let mut record_kind = Vec::with_capacity(row_count);
    let mut metric_name = Vec::with_capacity(row_count);
    let mut metric_value_f64 = Vec::with_capacity(row_count);
    let mut metric_value_text = Vec::with_capacity(row_count);
    let mut metric_unit = Vec::with_capacity(row_count);
    let mut stage_id = Vec::with_capacity(row_count);
    let mut stage_key = Vec::with_capacity(row_count);
    let mut step_index = Vec::with_capacity(row_count);
    let mut trial_index = Vec::with_capacity(row_count);
    let mut seed = Vec::with_capacity(row_count);
    let mut backend = Vec::with_capacity(row_count);
    let mut target = Vec::with_capacity(row_count);
    let mut trace_id = Vec::with_capacity(row_count);
    let mut traceparent = Vec::with_capacity(row_count);
    let mut artifact_ref = Vec::with_capacity(row_count);
    let mut created_at_epoch_ms = Vec::with_capacity(row_count);
    let mut context_json_col = Vec::with_capacity(row_count);
    let mut summary_json_col = Vec::with_capacity(row_count);
    let mut attributes_json_col = Vec::with_capacity(row_count);

    for measurement in &envelope.measurements {
        job_id.push(envelope.job_id.clone());
        workload_kind.push(envelope.workload_kind.clone());
        schema_version.push(envelope.schema_version.clone());
        record_kind.push(normalize_nonempty(&measurement.metric_kind, "measurement"));
        metric_name.push(measurement.metric_name.clone());
        match measurement.metric_value.parse::<f64>() {
            Ok(value) => {
                metric_value_f64.push(Some(value));
                metric_value_text.push(None);
            }
            Err(_) => {
                metric_value_f64.push(None);
                metric_value_text.push(Some(measurement.metric_value.clone()));
            }
        }
        metric_unit.push(if measurement.metric_unit.trim().is_empty() { None } else { Some(measurement.metric_unit.clone()) });
        stage_id.push(measurement.stage_id.clone());
        stage_key.push(measurement.stage_key.clone());
        step_index.push(measurement.step_index);
        trial_index.push(measurement.trial_index);
        seed.push(measurement.seed);
        backend.push(measurement.backend.clone());
        target.push(measurement.target.clone());
        trace_id.push(measurement.trace_id.clone());
        traceparent.push(measurement.traceparent.clone());
        artifact_ref.push(measurement.artifact_ref.clone());
        created_at_epoch_ms.push(Some(envelope.created_at_epoch_ms as i64));
        context_json_col.push(Some(context_json.clone()));
        summary_json_col.push(Some(summary_json.clone()));
        attributes_json_col.push(Some(serde_json::to_string(&measurement.attributes).map_err(to_io_error)?));
    }

    let schema = Arc::new(Schema::new(vec![
        Field::new("job_id", DataType::Utf8, false),
        Field::new("workload_kind", DataType::Utf8, false),
        Field::new("schema_version", DataType::Utf8, false),
        Field::new("record_kind", DataType::Utf8, false),
        Field::new("metric_name", DataType::Utf8, false),
        Field::new("metric_value_f64", DataType::Float64, true),
        Field::new("metric_value_text", DataType::Utf8, true),
        Field::new("metric_unit", DataType::Utf8, true),
        Field::new("stage_id", DataType::Utf8, true),
        Field::new("stage_key", DataType::Utf8, true),
        Field::new("step_index", DataType::Int64, true),
        Field::new("trial_index", DataType::Int64, true),
        Field::new("seed", DataType::Int64, true),
        Field::new("backend", DataType::Utf8, true),
        Field::new("target", DataType::Utf8, true),
        Field::new("trace_id", DataType::Utf8, true),
        Field::new("traceparent", DataType::Utf8, true),
        Field::new("artifact_ref", DataType::Utf8, true),
        Field::new("created_at_epoch_ms", DataType::Int64, true),
        Field::new("context_json", DataType::Utf8, true),
        Field::new("summary_json", DataType::Utf8, true),
        Field::new("attributes_json", DataType::Utf8, true),
    ]));

    let batch = RecordBatch::try_new(
        schema.clone(),
        vec![
            Arc::new(StringArray::from(job_id)) as ArrayRef,
            Arc::new(StringArray::from(workload_kind)) as ArrayRef,
            Arc::new(StringArray::from(schema_version)) as ArrayRef,
            Arc::new(StringArray::from(record_kind)) as ArrayRef,
            Arc::new(StringArray::from(metric_name)) as ArrayRef,
            Arc::new(Float64Array::from(metric_value_f64)) as ArrayRef,
            Arc::new(StringArray::from(metric_value_text)) as ArrayRef,
            Arc::new(StringArray::from(metric_unit)) as ArrayRef,
            Arc::new(StringArray::from(stage_id)) as ArrayRef,
            Arc::new(StringArray::from(stage_key)) as ArrayRef,
            Arc::new(Int64Array::from(step_index)) as ArrayRef,
            Arc::new(Int64Array::from(trial_index)) as ArrayRef,
            Arc::new(Int64Array::from(seed)) as ArrayRef,
            Arc::new(StringArray::from(backend)) as ArrayRef,
            Arc::new(StringArray::from(target)) as ArrayRef,
            Arc::new(StringArray::from(trace_id)) as ArrayRef,
            Arc::new(StringArray::from(traceparent)) as ArrayRef,
            Arc::new(StringArray::from(artifact_ref)) as ArrayRef,
            Arc::new(Int64Array::from(created_at_epoch_ms)) as ArrayRef,
            Arc::new(StringArray::from(context_json_col)) as ArrayRef,
            Arc::new(StringArray::from(summary_json_col)) as ArrayRef,
            Arc::new(StringArray::from(attributes_json_col)) as ArrayRef,
        ],
    )
    .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidData, err)))?;

    let tempdir = NamedTempFile::new_in(std::env::temp_dir())?;
    let temp_path = tempdir.path().to_path_buf();
    let writer_file = tempdir.reopen()?;
    let mut writer = ArrowWriter::try_new(writer_file, schema, Some(WriterProperties::builder().build()))
        .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidData, err)))?;
    writer
        .write(&batch)
        .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidData, err)))?;
    writer
        .close()
        .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidData, err)))?;
    Ok(fs::read(temp_path)?)
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
    // Local persistence is authoritative; MinIO mirroring should still be attempted,
    // but failures are surfaced in logs so the object-store path can be diagnosed.
    if let Err(err) = mirror_path_to_minio(path, bytes) {
        eprintln!(
            "failed to mirror artifact to MinIO: path={} error={}",
            path.display(),
            err
        );
    }
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


fn new_runtime() -> Result<tokio::runtime::Runtime, CircuitFsError> {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::Other, err)))
}

fn block_on_maybe_in_place<F, T>(future: F) -> Result<T, CircuitFsError>
where
    F: Future<Output = Result<T, CircuitFsError>>,
{
    if Handle::try_current().is_ok() {
        task::block_in_place(|| Handle::current().block_on(future))
    } else {
        let runtime = new_runtime()?;
        runtime.block_on(future)
    }
}

fn is_retryable_minio_error(message: &str) -> bool {
    let lower = message.to_ascii_lowercase();
    [
        "service error",
        "timeout",
        "timed out",
        "temporarily unavailable",
        "connection refused",
        "connection reset",
        "broken pipe",
        "503",
        "502",
        "504",
    ]
    .iter()
    .any(|needle| lower.contains(needle))
}

async fn ensure_minio_bucket_exists(client: &aws_sdk_s3::Client, bucket: &str) -> Result<(), CircuitFsError> {
    if client.head_bucket().bucket(bucket).send().await.is_ok() {
        return Ok(());
    }

    client
        .create_bucket()
        .bucket(bucket)
        .send()
        .await
        .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::Other, err)))?;

    Ok(())
}

fn minio_enabled() -> bool {
    matches!(
        env::var("EIGEN_QFS_BACKEND").ok().as_deref(),
        Some("s3") | Some("minio")
    ) || env::var("EIGEN_QFS_S3_ENDPOINT").is_ok()
}

fn minio_bucket() -> String {
    env::var("EIGEN_QFS_S3_BUCKET").unwrap_or_else(|_| "eigen-qfs".to_string())
}

fn minio_endpoint() -> Option<String> {
    env::var("EIGEN_QFS_S3_ENDPOINT").ok()
}

async fn minio_client() -> Result<aws_sdk_s3::Client, CircuitFsError> {
    let endpoint = minio_endpoint()
        .ok_or_else(|| CircuitFsError::Io(io::Error::new(io::ErrorKind::NotFound, "missing EIGEN_QFS_S3_ENDPOINT")))?;
    let config = aws_config::defaults(aws_config::BehaviorVersion::latest())
        .endpoint_url(endpoint)
        .load()
        .await;
    let s3_config = aws_sdk_s3::config::Builder::from(&config)
        .force_path_style(true)
        .build();
    Ok(aws_sdk_s3::Client::from_conf(s3_config))
}

fn canonicalize_path(path: &Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

fn path_key(path: &Path) -> Option<String> {
    let canonical_path = canonicalize_path(path);
    let mut roots: Vec<PathBuf> = Vec::new();
    for env_name in ["EIGEN_QFS_LOCAL_ROOT", "EIGEN_QFS_ROOT"] {
        if let Ok(root) = env::var(env_name) {
            roots.push(PathBuf::from(root));
        }
    }
    roots.push(PathBuf::from("/var/lib/eigen/circuit_fs"));
    roots.push(PathBuf::from("/tmp/eigen/qfs"));
    for root in roots {
        let canonical_root = canonicalize_path(&root);
        if let Ok(rel) = canonical_path.strip_prefix(&canonical_root) {
            return Some(rel.to_string_lossy().replace('\\', "/"));
        }
    }
    None
}

fn mirror_path_to_minio(path: &Path, bytes: &[u8]) -> Result<(), CircuitFsError> {
    if !minio_enabled() {
        return Ok(());
    }
    let bucket = minio_bucket();
    let key = path_key(path).ok_or_else(|| CircuitFsError::MinioMirrorFailed {
        path: path.to_path_buf(),
        bucket: bucket.clone(),
        key: String::new(),
        message: "path is outside the configured QFS root".to_string(),
    })?;
    block_on_maybe_in_place(async move {
        let client = minio_client().await?;
        let payload_bytes = bytes.to_vec();

        for attempt in 0..MINIO_MIRROR_MAX_ATTEMPTS {
            if let Err(err) = ensure_minio_bucket_exists(&client, &bucket).await {
                let message = err.to_string();
                if attempt + 1 < MINIO_MIRROR_MAX_ATTEMPTS && is_retryable_minio_error(&message) {
                    thread::sleep(Duration::from_millis(MINIO_MIRROR_BACKOFF_MS * (attempt as u64 + 1)));
                    continue;
                }
                return Err(CircuitFsError::MinioMirrorFailed {
                    path: path.to_path_buf(),
                    bucket: bucket.clone(),
                    key: key.clone(),
                    message,
                });
            }

            match client
                .put_object()
                .bucket(bucket.clone())
                .key(key.clone())
                .body(aws_sdk_s3::primitives::ByteStream::from(payload_bytes.clone()))
                .send()
                .await
            {
                Ok(_) => return Ok::<(), CircuitFsError>(()),
                Err(err) => {
                    let message = err.to_string();
                    if attempt + 1 < MINIO_MIRROR_MAX_ATTEMPTS && is_retryable_minio_error(&message) {
                        thread::sleep(Duration::from_millis(MINIO_MIRROR_BACKOFF_MS * (attempt as u64 + 1)));
                        continue;
                    }
                    return Err(CircuitFsError::MinioMirrorFailed {
                        path: path.to_path_buf(),
                        bucket: bucket.clone(),
                        key: key.clone(),
                        message,
                    });
                }
            }
        }

        Err(CircuitFsError::MinioMirrorFailed {
            path: path.to_path_buf(),
            bucket,
            key,
            message: "exhausted MinIO mirror retries".to_string(),
        })
    })
}

fn download_path_from_minio(path: &Path) -> Result<Option<Vec<u8>>, CircuitFsError> {
    if !minio_enabled() {
        return Ok(None);
    }
    let key = match path_key(path) {
        Some(key) => key,
        None => return Ok(None),
    };
    let bucket = minio_bucket();
    block_on_maybe_in_place(async move {
        let client = minio_client().await?;
        match client.get_object().bucket(bucket).key(key).send().await {
            Ok(output) => {
                let data = output
                    .body
                    .collect()
                    .await
                    .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::Other, err)))?;
                Ok(Some(data.into_bytes().to_vec()))
            }
            Err(_) => Ok(None),
        }
    })
}

fn list_refs_from_minio(prefix: &str) -> Result<Vec<String>, CircuitFsError> {
    if !minio_enabled() {
        return Ok(Vec::new());
    }
    let bucket = minio_bucket();
    block_on_maybe_in_place(async move {
        let client = minio_client().await?;
        let key_prefix = prefix.strip_prefix("qfs://").unwrap_or(prefix);
        let resp = client
            .list_objects_v2()
            .bucket(&bucket)
            .prefix(key_prefix)
            .send()
            .await
            .map_err(|err| CircuitFsError::Io(io::Error::new(io::ErrorKind::Other, err)))?;
        let mut refs = Vec::new();
        for item in resp.contents() {
            if let Some(key) = item.key() {
                refs.push(format!("qfs://{key}"));
            }
        }
        refs.sort();
        refs.dedup();
        Ok(refs)
    })
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
    fn store_results_bundle_writes_canonical_results_parquet_and_sidecars() {
        let tempdir = tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tempdir.path());

        let envelope = ResultEnvelope {
            artifact_version: "1.0.0".to_string(),
            schema_version: "scientific_result_bundle.v1".to_string(),
            producer_version: "1.0.0".to_string(),
            job_id: "job-789".to_string(),
            workload_kind: "HybridWorkflow".to_string(),
            result_ref: "results/result.json".to_string(),
            manifest_ref: "results/manifest.json".to_string(),
            created_at_epoch_ms: 1_718_181_234_000,
            retention_policy: "pinned".to_string(),
            lineage: CompiledArtifactLineage {
                request_id: Some("req-789".to_string()),
                source_ref: Some("qfs://jobs/job-789/input/program.eigen.py".to_string()),
                source_sha256: Some("abc123".to_string()),
            },
            context: BTreeMap::from([("target".to_string(), "sim:local".to_string())]),
            summary: BTreeMap::from([("execution_time_sec".to_string(), "0.015573".to_string())]),
            measurements: vec![
                ScientificMeasurement {
                    metric_name: "execution_time_sec".to_string(),
                    metric_kind: "summary".to_string(),
                    metric_value: "0.015573".to_string(),
                    metric_unit: "s".to_string(),
                    stage_id: None,
                    stage_key: None,
                    step_index: Some(0),
                    trial_index: Some(0),
                    seed: Some(7),
                    backend: Some("sim:local".to_string()),
                    target: Some("sim:local".to_string()),
                    trace_id: Some("trace-789".to_string()),
                    traceparent: Some("00-trace-789-parent-01".to_string()),
                    artifact_ref: Some("qfs://jobs/job-789/execution/execution.json".to_string()),
                    attributes: BTreeMap::from([("kind".to_string(), "execution_summary".to_string())]),
                },
                ScientificMeasurement {
                    metric_name: "shot_count".to_string(),
                    metric_kind: "measurement".to_string(),
                    metric_value: "8123".to_string(),
                    metric_unit: "shots".to_string(),
                    stage_id: Some("execute".to_string()),
                    stage_key: Some("execute".to_string()),
                    step_index: Some(5),
                    trial_index: Some(0),
                    seed: Some(7),
                    backend: Some("sim:local".to_string()),
                    target: Some("sim:local".to_string()),
                    trace_id: Some("trace-789".to_string()),
                    traceparent: Some("00-trace-789-parent-01".to_string()),
                    artifact_ref: Some("qfs://jobs/job-789/results/counts.json".to_string()),
                    attributes: BTreeMap::from([("bitstring".to_string(), "00".to_string())]),
                },
            ],
        };
        fs.store_results_bundle("job-789", &envelope, "1.0.0")
            .expect("store results bundle");

        let job_root = tempdir.path().join("jobs").join("job-789");
        assert!(job_root.join("results.parquet").exists());
        assert!(job_root.join("results/result.json").exists());
        assert!(job_root.join("results/envelope.json").exists());
        assert!(job_root.join("results/manifest.json").exists());

        let result_json = read_json(&job_root.join("results/result.json"));
        assert_eq!(result_json["job_id"], "job-789");
        assert_eq!(result_json["schema_version"], "scientific_result_bundle.v1");
        assert_eq!(result_json["workload_kind"], "HybridWorkflow");
        assert_eq!(result_json["result_ref"], "results/result.json");
        assert_eq!(result_json["manifest_ref"], "results/manifest.json");
        assert_eq!(result_json["measurements"].as_array().map(|rows| rows.len()), Some(2));

        let manifest_json = read_json(&job_root.join("results/manifest.json"));
        let artifacts = manifest_json["artifacts"]
            .as_array()
            .expect("artifacts array");
        let artifact_paths: BTreeSet<String> = artifacts
            .iter()
            .filter_map(|artifact| artifact["path"].as_str().map(str::to_string))
            .collect();
        assert!(artifact_paths.contains("results.parquet"));
        assert!(artifact_paths.contains("results/result.json"));

        let parquet_path = job_root.join("results.parquet");
        let parquet_bytes = fs::read(&parquet_path).expect("read parquet");
        assert!(parquet_bytes.starts_with(b"PAR1"));
        assert!(parquet_bytes.ends_with(b"PAR1"));
        let parquet_reader = parquet::file::reader::SerializedFileReader::new(
            std::fs::File::open(&parquet_path).expect("open parquet"),
        )
        .expect("valid parquet");
        let metadata = parquet::file::reader::FileReader::metadata(&parquet_reader);
        assert_eq!(metadata.file_metadata().num_rows(), 2);
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
