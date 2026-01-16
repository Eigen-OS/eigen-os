//! Observability primitives (MVP scaffold).
//!
//! For Phase 0 we keep this crate intentionally minimal.
//! It will evolve into the unified tracing/metrics facade used by kernel services.

/// Emits a structured startup log.
pub fn log_startup(service_name: &str) {
    tracing::info!(service_name, "service starting");
}
