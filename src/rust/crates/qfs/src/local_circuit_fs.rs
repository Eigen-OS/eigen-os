use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

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
    /// Normalized measurement counts.
    pub counts_json: Vec<u8>,
    /// Execution metadata.
    pub metadata_json: Vec<u8>,
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

    /// `/circuit_fs/{job_id}/meta.json`
    pub fn meta_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.job_root(job_id)?.join("meta.json"))
    }

    /// `/circuit_fs/{job_id}/input/job.yaml`
    pub fn job_yaml_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.input_dir(job_id)?.join("job.yaml"))
    }

    /// `/circuit_fs/{job_id}/input/program.eigen.py`
    pub fn program_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.input_dir(job_id)?.join("program.eigen.py"))
    }

    /// `/circuit_fs/{job_id}/compiled/circuit.aqo.json`
    pub fn compiled_aqo_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.compiled_dir(job_id)?.join("circuit.aqo.json"))
    }

    /// `/circuit_fs/{job_id}/results/counts.json`
    pub fn counts_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir(job_id)?.join("counts.json"))
    }

    /// `/circuit_fs/{job_id}/results/metadata.json`
    pub fn metadata_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir(job_id)?.join("metadata.json"))
    }

    /// `/circuit_fs/{job_id}/results/error.json`
    ///
    /// Optional: structured details of a job failure.
    pub fn error_json_path(&self, job_id: &str) -> Result<PathBuf, CircuitFsError> {
        Ok(self.results_dir(job_id)?.join("error.json"))
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
        self.ensure_job_layout(job_id)?;
        atomic_write_bytes(&self.compiled_aqo_json_path(job_id)?, aqo_json)?;
        Ok(())
    }

    /// Loads `compiled/circuit.aqo.json`.
    pub fn load_compiled_aqo_json(&self, job_id: &str) -> Result<Vec<u8>, CircuitFsError> {
        read_bytes_not_found(&self.compiled_aqo_json_path(job_id)?)
    }

    /// Stores results bundle under `results/`.
    pub fn store_results_bundle(
        &self,
        job_id: &str,
        counts_json: &[u8],
        metadata_json: &[u8],
    ) -> Result<(), CircuitFsError> {
        self.ensure_job_layout(job_id)?;

        // The results files are hot-read by APIs, so we always use atomic writes.
        atomic_write_bytes(&self.counts_json_path(job_id)?, counts_json)?;
        atomic_write_bytes(&self.metadata_json_path(job_id)?, metadata_json)?;

        Ok(())
    }

    /// Loads `results/counts.json` + `results/metadata.json`.
    pub fn load_results_bundle(&self, job_id: &str) -> Result<ResultsBundle, CircuitFsError> {
        let counts_json = read_bytes_not_found(&self.counts_json_path(job_id)?)?;
        let metadata_json = read_bytes_not_found(&self.metadata_json_path(job_id)?)?;

        Ok(ResultsBundle {
            counts_json,
            metadata_json,
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

#[cfg(test)]
mod tests {
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
        assert_eq!(fs.job_yaml_path(job_id).unwrap(), root.join("input").join("job.yaml"));
        assert_eq!(
            fs.program_path(job_id).unwrap(),
            root.join("input").join("program.eigen.py")
        );
        assert_eq!(
            fs.compiled_aqo_json_path(job_id).unwrap(),
            root.join("compiled").join("circuit.aqo.json")
        );
        assert_eq!(fs.counts_json_path(job_id).unwrap(), root.join("results").join("counts.json"));
        assert_eq!(
            fs.metadata_json_path(job_id).unwrap(),
            root.join("results").join("metadata.json")
        );
        assert_eq!(fs.error_json_path(job_id).unwrap(), root.join("results").join("error.json"));
        assert_eq!(fs.meta_json_path(job_id).unwrap(), root.join("meta.json"));
    }

    #[test]
    fn atomic_write_replaces_existing_file() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-1";

        fs.ensure_job_layout(job_id).unwrap();
        let p = fs.counts_json_path(job_id).unwrap();

        fs::write(&p, b"old").unwrap();
        fs.store_results_bundle(job_id, b"new", b"meta").unwrap();

        assert_eq!(fs::read(&p).unwrap(), b"new");
    }

    #[test]
    fn store_and_load_helpers_roundtrip() {
        let (_dir, fs) = tmp_fs();
        let job_id = "job-2";

        fs.store_source_bundle(job_id, "apiVersion: eigen.os/v0.1\n", b"print('hi')")
            .unwrap();
        fs.store_compiled_aqo_json(job_id, br#"{"version":"0.1"}"#).unwrap();
        fs.store_results_bundle(job_id, br#"{"counts":{}}"#, br#"{"meta":true}"#)
            .unwrap();
        fs.store_error_details_json(job_id, br#"{"error":"boom"}"#).unwrap();

        let src = fs.load_source_bundle(job_id).unwrap();
        assert!(src.job_yaml.contains("apiVersion"));
        assert_eq!(src.program_eigen_py, b"print('hi')");

        let aqo = fs.load_compiled_aqo_json(job_id).unwrap();
        assert_eq!(aqo, br#"{"version":"0.1"}"#);

        let res = fs.load_results_bundle(job_id).unwrap();
        assert_eq!(res.counts_json, br#"{"counts":{}}"#);
        assert_eq!(res.metadata_json, br#"{"meta":true}"#);

        let err = fs.load_error_details_json(job_id).unwrap();
        assert_eq!(err, br#"{"error":"boom"}"#);
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
}
