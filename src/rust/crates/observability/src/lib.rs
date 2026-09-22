//! Observability (MVP placeholder).
//!
//! This crate will provide:
//! - tracing setup + structured logs
//! - metrics (Prometheus/OpenTelemetry)
//! - context propagation helpers (trace_id / request_id)

#![forbid(unsafe_code)]

/// Returns a stable placeholder value.
pub fn log_startup(service: &str) {
    tracing::info!(
        service = service,
        pid = std::process::id(),
        "service starting"
    );
}
