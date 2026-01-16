//! Eigen QFS (Quantum File System) - MVP scaffold.
//!
//! For Phase 0, QFS-L3 is a local filesystem layout for per-job artifacts.
//! This crate will eventually provide:
//! - canonical paths for artifacts by `job_id`
//! - atomic writes and basic metadata
//! - retention policies

/// Returns the canonical directory name for a job.
pub fn job_dir(job_id: &str) -> String {
    format!("jobs/{job_id}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn job_dir_is_stable() {
        assert_eq!(job_dir("abc"), "jobs/abc");
    }
}
