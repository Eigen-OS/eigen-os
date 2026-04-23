//! QRTX (Quantum Real-Time Executive) — MVP placeholder.
//!
//! In MVP-1, QRTX provides a deterministic job lifecycle state machine and
//! minimal scheduling primitives.

#![forbid(unsafe_code)]

pub mod state_machine;

pub fn hello_qrtx() -> &'static str {
    "qrtx"
}