//! Eigen Kernel (MVP).
//!
//! Implements the internal KernelGateway gRPC API and a minimal in-memory job store.
//! Compiles and executes jobs through internal gRPC integrations with
//! eigen-compiler and driver-manager.

pub mod job_store;
pub mod rpc;

/// Generated protobuf types for the internal kernel gateway API.
pub mod proto {
    tonic::include_proto!("eigen.internal.v1");
}
