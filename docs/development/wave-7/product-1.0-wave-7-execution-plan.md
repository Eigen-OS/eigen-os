# Product 1.0 Wave 7 Execution Plan

- **Status:** In progress
- Wave: 7
- Scope: Neuro-Symbolic Compiler + GNN Optimizer

## Wave scope

Wave 7 closes the compiler and optimization boundary for Product 1.0 by integrating the existing MVP compiler pipeline with the GNN optimizer contract. The wave aligns Eigen-Lang lowering, AQO/IR normalization, optimizer handoff, deterministic scoring and fallback behavior, replay-safe artifacts, and the validation gates required for release.

Canonical execution path:

Eigen-Lang
  ->
Neuro-Symbolic IR
  ->
AQO
  ->
GNN Optimization
  ->
Execution Plan
  ->
Kernel/QRTX
  ->
QFS Artifacts

1. Align the kernel-facing Driver Manager contract with the final QDriver v1 contract.
2. Preserve the simulator as the canonical reference backend for conformance and parity checks.
3. Normalize execution results, device status, and error semantics across provider adapters.
4. Make session pooling and lifecycle management explicit and testable.
5. Enforce sandbox/process isolation and secret handling for provider credentials.
6. Define tolerance profiles, rollback hooks, and parity gates for the official provider matrix.
7. Publish a planning-time compatibility story for existing MVP-style driver-manager behavior.
8. Keep observability and audit evidence bounded, structured, and replay-friendly.


### Wave 7 compiler/optimizer integration

- Freeze the compiler-side semantics already present in the MVP compiler path.
- Treat GNN optimization as a deterministic contract boundary, not an experimental sidecar.
- Define the compiler → optimizer handoff on AQO / IR payloads and stable identifiers.
- Ensure optimizer decisions remain explainable, replayable, and bounded.
- Tie compiler and optimizer outputs into the same release-evidence chain.

## Deliverables

- Wave 6 issue pack
- Wave 6 RFC / ADR gap analysis
- Wave 7 issue pack
- Wave 7 RFC / ADR gap analysis
- Wave 7 compatibility report
- Wave 7 release readiness checklist
- Wave 7 exit evidence bundle
- Canonical QDriver v1 reference: `docs/reference/api/qdriver.md`
- Inventory row and manifest row for the Driver Manager / QDriver final contract
- Inventory rows and manifest rows for the Neuro-Symbolic Compiler and GNN Optimizer contracts

## Required deliverables

1. Neuro-Symbolic Compiler Contract v1
2. GNN Optimizer Contract v1
3. Compiler ↔ Optimizer Handoff Contract
4. Optimization Explainability Contract
5. Deterministic Compilation Conformance Suite

## Workstream A

Compiler contract freeze

- Eigen-Lang grammar freeze
- semantic validation freeze
- AQO normalization freeze
- compiler error taxonomy freeze

## Workstream B

Optimizer contract freeze

- graph encoding freeze
- scoring API freeze
- policy bundle freeze
- optimizer replay freeze

## Workstream C

Determinism

- identical source
- identical AQO
- identical optimizer result
- identical execution plan

## Workstream D

Observability

- compiler traces
- optimizer traces
- optimization explanation artifacts
- lineage metadata

## Acceptance criteria

- RFC accepted
- ADR accepted
- conformance suite green
- replay deterministic
- optimization explainability available
- manifest synchronized
- inventory synchronized

## Exit criteria

- Product 1.0 compiler boundary frozen
- Product 1.0 optimizer boundary frozen
- no unresolved TODO markers
- compatibility report complete
