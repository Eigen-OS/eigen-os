use std::net::SocketAddr;

use observability::log_startup;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    log_startup("eigen-kernel");

    // Internal kernel gRPC address (System API -> Kernel).
    // Default matches our dev compose conventions.
    let addr: SocketAddr = std::env::var("EIGEN_KERNEL_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:50052".to_string())
        .parse()?;

    eigen_kernel::rpc::serve(addr).await
}
