//! Eigen QFS (Quantum File System) — MVP implementation.
//!
//! This crate implements **CircuitFS (QFS Level 3)** as a **local filesystem** layout
//! for per-job artifacts.
//!
//! See: `docs/reference/formats/qfs-layout.md`.

#![forbid(unsafe_code)]

mod local_circuit_fs;

pub use local_circuit_fs::{
    CircuitFsError, CircuitFsLocal, ErrorDetails, ResultsBundle, SourceBundle,
};
