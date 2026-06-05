//! Eigen QFS (Quantum File System) — MVP implementation.
//!
//! This crate implements **CircuitFS (QFS Level 3)** as a **local filesystem** layout
//! for per-job artifacts.
//!
//! See: `docs/reference/formats/qfs-layout.md`.

#![forbid(unsafe_code)]

mod local_circuit_fs;
mod qfs_l2_checkpoint;

pub use local_circuit_fs::{
    CircuitFsError, CircuitFsLocal, CompiledArtifactLineage, CompiledArtifactProvenance,
    CompiledArtifacts, CompiledMetadata, ErrorDetails,
    ResultArtifactDescriptor, ResultEnvelope, ResultManifest, ResultsBundle, SourceBundle,
    SourceMetadata, DEFAULT_CIRCUIT_FS_ROOT,
};

pub use qfs_l2_checkpoint::{
    CheckpointAdmissionReasonCode, CheckpointAdmissionRejection, CheckpointArtifactRef,
    CheckpointBudgetPolicy, CheckpointCompatibilityWindow, CheckpointEnvelopeV1,
    CheckpointEnvelopeValidationError, CheckpointExtensions, CheckpointGuardrails,
    CheckpointIntegrity, CheckpointPayloadRefs, CheckpointProvenance, CheckpointTraceLinks,
    CHECKPOINT_ENVELOPE_SCHEMA_VERSION, CHECKPOINT_RUNTIME_API_VERSION,
    DEFAULT_MAX_CHECKPOINT_SIZE_BYTES, DEFAULT_MAX_RESTORE_COST_UNITS,
};
