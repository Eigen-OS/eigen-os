//! Resource manager (MVP placeholder).
//!
//! Future responsibilities:
//! - allocate devices / simulators
//! - enforce per-tenant quotas
//! - implement scheduling hints for QRTX

#![forbid(unsafe_code)]

/// Returns a stable placeholder value.
pub fn hello_resource_manager() -> &'static str {
    "resource-manager"
}
