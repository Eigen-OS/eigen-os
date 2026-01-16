//! Observability (MVP placeholder).
//!
//! This crate will provide:
//! - tracing setup + structured logs
//! - metrics (Prometheus/OpenTelemetry)
//! - context propagation helpers (trace_id / request_id)

#![forbid(unsafe_code)]

/// Returns a stable placeholder value.
pub fn hello_observability() -> &'static str {
    "observability"
}
