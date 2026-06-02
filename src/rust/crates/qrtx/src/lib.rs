//! QRTX (Quantum Real-Time Executive) — MVP kernel primitives + durability extensions.
//!
//! This crate provides:
//! - Deterministic job lifecycle state machine (`state_machine.rs`)
//! - Event-sourced audit trail for deterministic replay (`event_log.rs`)
//!
//! Described in:
//! - `docs/architecture/components/qrtx.md`
//! - `RFC 0007 (QRTX MVP)`

#![forbid(unsafe_code)]

pub mod event_log;
pub mod state_machine;
