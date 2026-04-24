# QRTX (Quantum Real-Time Executive)

Rust crate with MVP kernel primitives for Eigen OS.

## MVP scope (current)

Aligned with:
- `docs/architecture/components/qrtx.md`
- `rfcs/0007-qrtx-mvp.md`

Implemented in this crate now:
- Deterministic task lifecycle state machine (`state_machine.rs`).
- Canonical MVP states:
  `Pending → Validating → Compiling → Queued → Allocating → Executing → Completing → Completed`
  plus terminal states `Failed`, `Cancelled`, `Timeout`.
- Optional executing sub-states enum for stage-level observability.

## Out of scope for this crate in MVP

The following are **not implemented here** and must not be treated as available runtime features:
- Full DAG orchestration.
- Noise-aware / topology-aware / predictive scheduling.
- Checkpointing and migration.
- Multi-tenant fairness/quotas.

Those items are planned for later phases and are tracked in architecture docs/RFCs.

## Run tests
```bash
cargo test -p qrtx --manifest-path src/rust/Cargo.toml
```
