//! Security module hooks (MVP scaffold).
//!
//! In Phase 0, System API is responsible for authentication.
//! The kernel will later call into this module for authorization and isolation checks.

/// Placeholder authorization check.
pub fn authorize(_principal: &str, _action: &str) -> bool {
    true
}
