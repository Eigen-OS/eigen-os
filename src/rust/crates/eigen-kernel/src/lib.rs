//! Eigen Kernel (MVP).
//!
//! Implements the internal KernelGateway gRPC API and a minimal in-memory job store.
//! Real compilation/execution is intentionally stubbed (see Issue #25).

pub mod job_store;
pub mod rpc;

/// Generated protobuf types for the internal kernel gateway API.
pub mod proto {
    tonic::include_proto!("eigen.internal.v1");
}
