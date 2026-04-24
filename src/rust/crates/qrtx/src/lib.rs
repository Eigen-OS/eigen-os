//! QRTX (Quantum Real-Time Executive) — MVP kernel primitives.
//!
//! This crate currently exposes the deterministic job lifecycle state machine
//! described in RFC 0007 / architecture docs for the MVP pipeline.

#![forbid(unsafe_code)]

pub mod state_machine;

