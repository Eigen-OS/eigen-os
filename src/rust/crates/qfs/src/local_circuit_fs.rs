use std::fs;
use std::hash::{Hash, Hasher};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
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
}

/// Durable artifact manifest for runtime outputs.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResultManifest {
    pub artifact_version: String,
    pub producer_version: String,
    pub schema_version: String,
    pub artifacts: Vec<ResultArtifactDescriptor>,
}

/// Single artifact record within `results/manifest.json`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResultArtifactDescriptor {
    pub path: String,
    pub content_hash: String,
    pub size_bytes: u64,
}

/// Error details artifact (for async job failures).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErrorDetails {
    /// A short human-readable summary.
    pub summary: String,
    /// Structured details in JSON (stack traces, backend payloads, etc.).
    pub details_json: Vec<u8>,
}

#[derive(thiserror::Error, Debug)]
pub enum CircuitFsError {
    #[error("artifact not found: {path}")]
    NotFound { path: PathBuf },

    #[error("invalid job_id: {job_id}")]
    InvalidJobId { job_id: String },

    #[error("artifact already exists: {path}")]
    AlreadyExists { path: PathBuf },

    #[error(transparent)]
    Io(#[from] io::Error),
}

/// MVP implementation of CircuitFS on a local filesystem.
#[derive(Debug, Clone)]
pub struct CircuitFsLocal {
    root: PathBuf,
}

impl CircuitFsLocal {
    /// Creates a CircuitFS instance with the provided root directory.
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// Creates a CircuitFS instance with the default root directory.
    pub fn new_default() -> Self {
        Self::new(DEFAULT_CIRCUIT_FS_ROOT)
    }

    /// Returns the configured CircuitFS root.
    pub fn root(&self) -> &Path {
        &self.root
    }

    // ----------------------------
    // Path helpers
    // ----------------------------

    /// `/circuit_fs/{job_id}/`
    pub fn job_root(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        validate_job_id(job_id)?;
        Ok(self.root.join(job_id))
    }

    /// `/circuit_fs/{job_id}/input/`
    pub fn input_dir(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("input"))
    }

    /// `/circuit_fs/{job_id}/compiled/`
    pub fn compiled_dir(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("compiled"))
    }

    /// `/circuit_fs/{job_id}/results/`
    pub fn results_dir(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("results"))
    }

    /// `/circuit_fs/{job_id}/logs/`
    pub fn logs_dir(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("logs"))
    }

    /// `/circuit_fs/{job_id}/meta/`
    pub fn meta_dir(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("meta"))
    }

    /// `/circuit_fs/{job_id}/meta.json`
    pub fn meta_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("meta.json"))
    }

    /// `/circuit_fs/{job_id}/meta/metrics.json`
    pub fn metrics_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.meta_dir(job_id)?.join("metrics.json"))
    }

    /// `/circuit_fs/{job_id}/input/job.yaml`
    pub fn job_yaml_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.input_dir(job_id)?.join("job.yaml"))
    }

    /// `/circuit_fs/{job_id}/input/program.eigen.py`
    pub fn program_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.input_dir(job_id)?.join("program.eigen.py"))
    }

    /// `/circuit_fs/{job_id}/input/metadata.json`
    pub fn input_metadata_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.input_dir(job_id)?.join("metadata.json"))
    }

    /// `/circuit_fs/{job_id}/compiled/circuit.aqo.json`
    pub fn compiled_aqo_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir(job_id)?.join("circuit.aqo.json"))
    }

    /// `/circuit_fs/{job_id}/compiled/circuit.qasm`
    pub fn compiled_qasm_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir(job_id)?.join("circuit.qasm"))
    }

    /// `/circuit_fs/{job_id}/compiled/metadata.json`
    pub fn compiled_metadata_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir(job_id)?.join("metadata.json"))
    }

    /// `/circuit_fs/{job_id}/compiled/compile_report.json`
    pub fn compiled_report_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir(job_id)?.join("compile_report.json"))
    }

    /// `/circuit_fs/{job_id}/results.parquet`
    pub fn results_parquet_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("results.parquet"))
    }

    /// `/circuit_fs/{job_id}/results/error.json`
    ///
    /// Optional: structured details of a job failure.
    pub fn error_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir(job_id)?.join("error.json"))
    }

    /// `/circuit_fs/{job_id}/results/result.json`
    pub fn result_envelope_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir(job_id)?.join("result.json"))
    }

    /// `/circuit_fs/{job_id}/results/manifest.json`
    pub fn result_manifest_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir(job_id)?.join("manifest.json"))
    }

    // ----------------------------
    // Directory initialization
    // ----------------------------

    /// Creates the canonical directory layout for a job.
    pub fn ensure_job_layout(&self, job_id: &str) -> Result<(), CircuitFsError> {
        let job_root = self.job_root(job_id)?;

        // Ensure root exists first.
        fs::create_dir_all(&job_root)?;

        fs::create_dir_all(self.input_dir(job_id)?)?;
        fs::create_dir_all(self.compiled_dir(job_id)?)?;
        fs::create_dir_all(self.results_dir(job_id)?)?;
        fs::create_dir_all(self.logs_dir(job_id)?)?;
        fs::create_dir_all(self.meta_dir(job_id)?)?;

        Ok(())
    }

    // ----------------------------
    // Store / retrieve helpers (MVP)
    // ----------------------------

    /// Stores `input/job.yaml` and `input/program.eigen.py`.
    pub fn store_source_bundle(
        &self,
        job_id: &str,
        job_yaml: &str,
        program_eigen_py: &[u8],
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        atomic_write_bytes(&self.job_yaml_path(job_id)?, job_yaml.as_bytes())?;
        atomic_write_bytes(&self.program_path(job_id)?, program_eigen_py)?;
        let metadata = SourceMetadata {
            version: "0.1".to_string(),
            schema_version: "source_artifacts.v1".to_string(),
            job_yaml_hash: content_hash_hex(job_yaml.as_bytes()),
            program_hash: content_hash_hex(program_eigen_py),
        };
        let bytes = serde_json::to_vec_pretty(&metadata).map_err(to_io_error)?;
        atomic_write_bytes(&self.input_metadata_path(job_id)?, &bytes)?;

        Ok(())
    }

    /// Loads `input/job.yaml` and `input/program.eigen.py`.
    pub fn load_source_bundle(&self, job_id: &str) -> Result<SourceBundle, CircuitFsError> {
        let job_yaml = read_to_string_not_found(&self.job_yaml_path(job_id)?)?;
        let program_eigen_py = read_bytes_not_found(&self.program_path(job_id)?)?;

        Ok(SourceBundle {
            job_yaml,
            program_eigen_py,
        })
    }

    /// Stores `compiled/circuit.aqo.json`.
    pub fn store_compiled_aqo_json(
        &self,
        job_id: &str,
        aqo_json: &[u8],
    ) -> Result<(), CircuitFsError> {
        self.store_compiled_artifacts(job_id, aqo_json, None, "unknown")
    }

    /// Stores compiler outputs under `compiled/` using the v1 contract.
    ///
    /// This is the canonical persistence entrypoint for Wave 3.
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

    /// Loads `compiled/circuit.aqo.json`.
    pub fn load_compiled_aqo_json(&self, job_id: &str) -> Result<Vec<u8>, CircuitFsError> {
        read_bytes_not_found(&self.compiled_aqo_json_path(job_id)?)
    }

    /// Stores compiler outputs under `compiled/` and writes `compiled/metadata.json`.
    ///
    /// Legacy compatibility helper retained for older call sites.
    pub fn store_compiled_artifacts(
        &self,
        job_id: &str,
        aqo_json: &[u8],
        qasm: Option<&[u8]>,
        compiler_version: &str,
    ) -> Result<(), CircuitFsError> {
        let provenance = CompiledArtifactProvenance {
            producer_identity: "eigen-compiler".to_string(),
            contract_version: "1.0.0".to_string(),
            compiler_version: compiler_version.to_string(),
            created_at: "unknown".to_string(),
            lineage: CompiledArtifactLineage::default(),
        };
        self.store_compiled_artifacts_v1(job_id, aqo_json, qasm, None, provenance)
    }

    /// Loads `compiled/circuit.aqo.json`, optional `compiled/circuit.qasm`, and metadata.
    pub fn load_compiled_artifacts(
        &self,
        job_id: &str,
    ) -> Result<CompiledArtifacts, CircuitFsError> {
        let aqo_json = read_bytes_not_found(&self.compiled_aqo_json_path(job_id)?)?;
        let qasm_path = self.compiled_qasm_path(job_id)?;
        let report_path = self.compiled_report_path(job_id)?;
        let metadata_bytes = read_bytes_not_found(&self.compiled_metadata_path(job_id)?)?;
        let metadata: CompiledMetadata =
            serde_json::from_slice(&metadata_bytes).map_err(to_io_error)?;
        let qasm = if metadata.qasm_hash.is_some() {
            Some(read_bytes_not_found(&qasm_path)?)
        } else {
            read_optional_bytes(&qasm_path)?
        };
        let compile_report_json = if metadata.diagnostics_hash.is_some() {
            Some(read_bytes_not_found(&report_path)?)
        } else {
            read_optional_bytes(&report_path)?
        };

        if metadata.qasm_hash.is_some() && qasm.is_none() {
            return Err(CircuitFsError::NotFound { path: qasm_path });
        }
        if metadata.diagnostics_hash.is_some() && compile_report_json.is_none() {
            return Err(CircuitFsError::NotFound { path: report_path });
        }

        Ok(CompiledArtifacts {
            aqo_json,
            qasm,
            compile_report_json,
            metadata,
        })
    }

    /// Stores canonical results artifact under `results.parquet`.
    pub fn store_results_bundle(
        &self,
        job_id: &str,
        parquet_payload: &[u8],
        producer_version: &str,
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        // The results artifact is hot-read by APIs, so we always use atomic writes.
        atomic_write_bytes(&self.results_parquet_path(job_id)?, parquet_payload)?;
        let results_path = self.results_parquet_path(job_id)?;
        atomic_write_bytes(&results_path, parquet_payload)?;

        let result_rel_path = "results.parquet".to_string();
        let manifest_rel_path = "results/manifest.json".to_string();
        let envelope = ResultEnvelope {
            artifact_version: "1.0.0".to_string(),
            producer_version: producer_version.to_string(),
            job_id: job_id.to_string(),
            result_ref: result_rel_path.clone(),
            manifest_ref: manifest_rel_path.clone(),
        };
        let envelope_bytes = serde_json::to_vec_pretty(&envelope).map_err(to_io_error)?;
        let manifest = ResultManifest {
            artifact_version: envelope.artifact_version.clone(),
            producer_version: producer_version.to_string(),
            schema_version: "result_manifest.v1".to_string(),
            artifacts: vec![
                ResultArtifactDescriptor {
                    path: result_rel_path,
                    content_hash: content_hash_hex(parquet_payload),
                    size_bytes: parquet_payload.len() as u64,
                },
                ResultArtifactDescriptor {
                    path: "results/result.json".to_string(),
                    content_hash: content_hash_hex(&envelope_bytes),
                    size_bytes: envelope_bytes.len() as u64,
                },
            ],
        };
        let manifest_bytes = serde_json::to_vec_pretty(&manifest).map_err(to_io_error)?;
        atomic_write_bytes(&self.result_manifest_path(job_id)?, &manifest_bytes)?;
        atomic_write_bytes(&self.result_envelope_path(job_id)?, &envelope_bytes)?;

        Ok(())
    }

    /// Loads `results.parquet`.
    pub fn load_results_bundle(&self, job_id: &str) -> Result<ResultsBundle, CircuitFsError> {
        let parquet = read_bytes_not_found(&self.results_parquet_path(job_id)?)?;
        let envelope = match read_optional_bytes(&self.result_envelope_path(job_id)?)? {
            Some(bytes) => serde_json::from_slice(&bytes).map_err(to_io_error)?,
            None => ResultEnvelope {
                artifact_version: "0.1.0".to_string(),
                producer_version: "unknown".to_string(),
                job_id: job_id.to_string(),
                result_ref: "results.parquet".to_string(),
                manifest_ref: "".to_string(),
            },
        };
        let manifest = match read_optional_bytes(&self.result_manifest_path(job_id)?)? {
            Some(bytes) => serde_json::from_slice(&bytes).map_err(to_io_error)?,
            None => ResultManifest {
                artifact_version: envelope.artifact_version.clone(),
                producer_version: envelope.producer_version.clone(),
                schema_version: "result_manifest.v0".to_string(),
                artifacts: vec![ResultArtifactDescriptor {
                    path: "results.parquet".to_string(),
                    content_hash: content_hash_hex(&parquet),
                    size_bytes: parquet.len() as u64,
                }],
            },
        };

        Ok(ResultsBundle {
            parquet,
            envelope,
            manifest,
        })
    }

    /// Stores structured error details in `results/error.json`.
    ///
    /// NOTE: This is not a replacement for logs; it's a stable, machine-readable
    /// artifact that can be referenced as `error_details_ref` in public APIs.
    pub fn store_error_details_json(
        &self,
        job_id: &str,
        error_json: &[u8],
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;
        atomic_write_bytes(&self.error_json_path(job_id)?, error_json)?;
        Ok(())
    }

    /// Loads structured error details from `results/error.json`.
    pub fn load_error_details_json(&self, job_id: &str) -> Result<Vec<u8>, CircuitFsError> {
        read_bytes_not_found(&self.error_json_path(job_id)?)
    }

    /// Appends a line to a stage log (e.g. `logs/kernel.log`).
    ///
    /// MVP behavior: best-effort append (not atomic), intended for debugging.
    pub fn append_log_line(
        &self,
        job_id: &str,
        log_name: &str,
        line: &str,
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;
        let log_path = self.logs_dir(job_id)?.join(format!("{log_name}.log"));

        let mut f = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)?;
        writeln!(f, "{line}")?;

        Ok(())
    }

    /// Stores loop/runtime metrics at `meta/metrics.json`.
    pub fn store_metrics_json(
        &self,
        job_id: &str,
        metrics_json: &[u8],
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;
        atomic_write_bytes(&self.metrics_json_path(job_id)?, metrics_json)?;
        Ok(())
    }
}

// ----------------------------
// Internals
// ----------------------------

fn validate_job_id(job_id: &str) -> Result<(), CircuitFsError> {
    // MVP validation: allow UUIDs and simple test IDs.
    // We disallow path traversal.
    if job_id.is_empty() || job_id.contains('/') || job_id.contains('\\') || job_id.contains("..") {
        return Err(CircuitFsError::InvalidJobId {
            job_id: job_id.to_string(),
        });
    }
    Ok(())
}

fn atomic_write_bytes(path: &Path, bytes: &[u8]) -> Result<(), CircuitFsError> {
    let dir = path
        .parent()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "path has no parent"))?;

    fs::create_dir_all(dir)?;

    // Create a temp file in the same directory to ensure rename is atomic.
    let mut tmp = NamedTempFile::new_in(dir)?;
    tmp.write_all(bytes)?;
    tmp.flush()?;
    tmp.as_file().sync_all()?;

    // Persist performs an atomic rename on supported filesystems.
    tmp.persist(path).map_err(|e| CircuitFsError::Io(e.error))?;
    Ok(())
}

fn read_bytes_not_found(path: &Path) -> Result<Vec<u8>, CircuitFsError> {
    match fs::read(path) {
        Ok(bytes) => Ok(bytes),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Err(CircuitFsError::NotFound {
            path: path.to_path_buf(),
        }),
        Err(e) => Err(CircuitFsError::Io(e)),
    }
}

fn read_to_string_not_found(path: &Path) -> Result<String, CircuitFsError> {
    match fs::read_to_string(path) {
        Ok(s) => Ok(s),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Err(CircuitFsError::NotFound {
            path: path.to_path_buf(),
        }),
        Err(e) => Err(CircuitFsError::Io(e)),
    }
}

fn read_optional_bytes(path: &Path) -> Result<Option<Vec<u8>>, CircuitFsError> {
    match fs::read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(CircuitFsError::Io(e)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn store_compiled_artifacts_v1_is_canonical_and_round_trips() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tmp.path());
        let aqo = br#"{"operations":[{"op":"H","q":[0]}],"qubits":1,"version":"1.0.0"}"#;
        let qasm = b"OPENQASM 3.0;\n";
        let report = br#"{"status":"ok"}"#;
        let provenance = CompiledArtifactProvenance {
            producer_identity: "eigen-compiler".to_string(),
            contract_version: "1.0.0".to_string(),
            compiler_version: "1.0.0".to_string(),
            created_at: "2026-06-06T12:00:00Z".to_string(),
            lineage: CompiledArtifactLineage {
                request_id: Some("req-1".to_string()),
                source_ref: Some("jobs/job-1/input/program.eigen.py".to_string()),
                source_sha256: Some("sha256:abc".to_string()),
            },
        };

        fs.store_compiled_artifacts_v1("job-1", aqo, Some(qasm), Some(report), provenance)
            .expect("store");

        let loaded = fs.load_compiled_artifacts("job-1").expect("load");
        assert_eq!(loaded.aqo_json, aqo);
        assert_eq!(loaded.qasm.as_deref(), Some(qasm.as_slice()));
        assert_eq!(loaded.compile_report_json.as_deref(), Some(report.as_slice()));
        assert_eq!(loaded.metadata.version, "1.0.0");
        assert_eq!(loaded.metadata.contract_version, "1.0.0");
        assert_eq!(loaded.metadata.producer_identity, "eigen-compiler");
        assert_eq!(loaded.metadata.lineage.request_id.as_deref(), Some("req-1"));
    }

    #[test]
    fn duplicate_compiled_writes_are_rejected() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tmp.path());
        let aqo = br#"{"operations":[{"op":"H","q":[0]}],"qubits":1,"version":"1.0.0"}"#;
        let provenance = CompiledArtifactProvenance {
            producer_identity: "eigen-compiler".to_string(),
            contract_version: "1.0.0".to_string(),
            compiler_version: "1.0.0".to_string(),
            created_at: "2026-06-06T12:00:00Z".to_string(),
            lineage: CompiledArtifactLineage::default(),
        };

        fs.store_compiled_artifacts_v1("job-1", aqo, None, None, provenance.clone())
            .expect("first write");
        let err = fs
            .store_compiled_artifacts_v1("job-1", aqo, None, None, provenance)
            .expect_err("duplicate write must fail");
        assert!(matches!(err, CircuitFsError::AlreadyExists { .. }));
    }

    #[test]
    fn missing_sidecar_reference_is_reported() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(tmp.path());
        let aqo = br#"{"operations":[{"op":"H","q":[0]}],"qubits":1,"version":"1.0.0"}"#;
        let qasm = b"OPENQASM 3.0;\n";
        let provenance = CompiledArtifactProvenance {
            producer_identity: "eigen-compiler".to_string(),
            contract_version: "1.0.0".to_string(),
            compiler_version: "1.0.0".to_string(),
            created_at: "2026-06-06T12:00:00Z".to_string(),
            lineage: CompiledArtifactLineage::default(),
        };

        fs.store_compiled_artifacts_v1("job-1", aqo, Some(qasm), Some(br#"{"status":"ok"}"#), provenance)
            .expect("store");
        std::fs::remove_file(fs.compiled_qasm_path("job-1").expect("path")).expect("remove qasm");
        let err = fs.load_compiled_artifacts("job-1").expect_err("load must fail");
        assert!(matches!(err, CircuitFsError::NotFound { .. }));
    }
}

fn to_io_error(err: serde_json::Error) -> CircuitFsError {
    CircuitFsError::Io(io::Error::new(io::ErrorKind::InvalidData, err))
}

fn content_hash_hex(bytes: &[u8]) -> String {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    bytes.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

#[cfg(test)]
mod layout_tests {
    use super::*;

    fn tmp_fs() -> (tempfile::TempDir, CircuitFsLocal) {
        let dir = tempfile::tempdir().expect("tempdir");
        let fs = CircuitFsLocal::new(dir.path());
        (dir, fs)
    }

    #[test]
    fn path_generation_matches_spec() {
        let (_dir, fs) = tmp_fs();
        let job_id = "550e8400-e29b-41d4-a716-446655440000";

        let root = fs.root().join(job_id);

        assert_eq!(fs.job_root(job_id).unwrap(), root);
        assert_eq!(
            fs.job_yaml_path(job_id).unwrap(),
            root.join("input").join("job.yaml")
        );
        assert_eq!(
            fs.program_path(job_id).unwrap(),
            root.join("input").join("program.eigen.py")
        );
        assert_eq!(
            fs.compiled_aqo_json_path(job_id).unwrap(),
            root.join("compiled").join("circuit.aqo.json")
        );
        assert_eq!(
            fs.compiled_qasm_path(job_id).unwrap(),
            root.join("compiled").join("circuit.qasm")
        );
        assert_eq!(
            fs.compiled_metadata_path(job_id).unwrap(),
            root.join("compiled").join("metadata.json")
        );
        assert_eq!(
            fs.input_metadata_path(job_id).unwrap(),
            root.join("input").join("metadata.json")
        );
        assert_eq!(
            fs.results_parquet_path(job_id).unwrap(),
            root.join("results.parquet")
        );
        assert_eq!(
            fs.error_json_path(job_id).unwrap(),
            root.join("results").join("error.json")
        );
        assert_eq!(fs.meta_json_path(job_id).unwrap(), root.join("meta.json"));
    }

    #[test]
    fn atomic_write_replaces_existing_file() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-1";

        fs.ensure_job_layout(job_id).unwrap();
        let p = fs.results_parquet_path(job_id).unwrap();

        fs::write(&p, b"old").unwrap();
        fs.store_results_bundle(job_id, b"new", "eigen-kernel@0.1.0")
            .unwrap();

        assert_eq!(fs::read(&p).unwrap(), b"new");
    }

    #[test]
    fn store_and_load_helpers_roundtrip() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-2";

        fs.store_source_bundle(job_id, "apiVersion: eigen.os/v0.1\n", b"print('hi')")
            .unwrap();
        fs.store_compiled_aqo_json(job_id, br#"{"version":"0.1"}"#)
            .unwrap();
        fs.store_results_bundle(job_id, b"PAR1....", "eigen-kernel@0.1.0")
            .unwrap();
        fs.store_error_details_json(job_id, br#"{"error":"boom"}"#)
            .unwrap();

        let src = fs.load_source_bundle(job_id).unwrap();
        assert!(src.job_yaml.contains("apiVersion"));
        assert_eq!(src.program_eigen_py, b"print('hi')");

        let aqo = fs.load_compiled_aqo_json(job_id).unwrap();
        assert_eq!(aqo, br#"{"version":"0.1"}"#);

        let res = fs.load_results_bundle(job_id).unwrap();
        assert_eq!(res.parquet, b"PAR1....");
        assert_eq!(res.envelope.artifact_version, "1.0.0");
        assert_eq!(res.envelope.producer_version, "eigen-kernel@0.1.0");
        assert_eq!(res.manifest.schema_version, "result_manifest.v1");
        assert_eq!(res.manifest.artifacts.len(), 2);

        let err = fs.load_error_details_json(job_id).unwrap();
        assert_eq!(err, br#"{"error":"boom"}"#);
    }

    #[test]
    fn store_source_bundle_writes_metadata_hashes() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-source-meta";
        let job_yaml = "apiVersion: eigen.os/v0.1\n";
        let program = b"print('meta')";

        fs.store_source_bundle(job_id, job_yaml, program).unwrap();

        let metadata_bytes = fs::read(fs.input_metadata_path(job_id).unwrap()).unwrap();
        let metadata: SourceMetadata = serde_json::from_slice(&metadata_bytes).unwrap();
        assert_eq!(metadata.version, "0.1");
        assert_eq!(metadata.schema_version, "source_artifacts.v1");
        assert_eq!(
            metadata.job_yaml_hash,
            content_hash_hex(job_yaml.as_bytes())
        );
        assert_eq!(metadata.program_hash, content_hash_hex(program));
    }

    #[test]
    fn compiled_artifacts_roundtrip_with_optional_qasm_and_metadata() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-compiled";
        let aqo = br#"{"version":"0.1","type":"aqo"}"#;
        let qasm = b"OPENQASM 3;\nqubit[1] q;\n";

        fs.store_compiled_artifacts(job_id, aqo, Some(qasm), "eigen-lang@0.1.0")
            .unwrap();
        let compiled = fs.load_compiled_artifacts(job_id).unwrap();

        assert_eq!(compiled.aqo_json, aqo);
        assert_eq!(compiled.qasm, Some(qasm.to_vec()));
        assert_eq!(compiled.metadata.version, "0.1");
        assert_eq!(compiled.metadata.version, "1.0.0");
        assert_eq!(compiled.metadata.schema_version, "compiled_artifacts.v1");
        assert_eq!(compiled.metadata.compiler_version, "eigen-lang@0.1.0");
        assert_eq!(compiled.metadata.aqo_hash, content_hash_hex(aqo));
        assert_eq!(compiled.metadata.qasm_hash, Some(content_hash_hex(qasm)));
    }

    #[test]
    fn invalid_job_id_is_rejected() {
        let (_dir, fs) = tmp_fs();

        let err = fs.ensure_job_layout("../evil").unwrap_err();
        match err {
            CircuitFsError::InvalidJobId { .. } => {}
            other => panic!("unexpected error: {other:?}"),
        }
    }

    #[test]
    fn load_results_bundle_supports_legacy_without_envelope_or_manifest() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-legacy-results";

        fs.ensure_job_layout(job_id).unwrap();
        fs::write(fs.results_parquet_path(job_id).unwrap(), b"legacy").unwrap();

        let bundle = fs.load_results_bundle(job_id).unwrap();
        assert_eq!(bundle.parquet, b"legacy");
        assert_eq!(bundle.envelope.artifact_version, "0.1.0");
        assert_eq!(bundle.envelope.producer_version, "unknown");
        assert_eq!(bundle.manifest.schema_version, "result_manifest.v0");
        assert_eq!(bundle.manifest.artifacts.len(), 1);
    }
}
