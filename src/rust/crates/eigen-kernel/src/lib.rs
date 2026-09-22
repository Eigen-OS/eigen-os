//! Eigen Kernel (Phase-1: Durable State).
//!
//! Implements the internal KernelGateway gRPC API with:
//! - Durable job state store (QFS-backed event log)
//! - Deterministic state replay on restart
//! - Single-authority state machine
//! - Audit trail for all transitions
//! - Audit trail for all transitions

pub mod durable_job_store;
pub mod job_store;
pub mod rpc;

/// Generated protobuf types for the internal kernel gateway API.
pub mod proto {
    tonic::include_proto!("eigen.internal.v1");
}
