# Knowledge Base

- **Phase:** Post-MVP (target capability; not in execution path).
- **Implementation state (verified on 2026-05-08):** no standalone service, crate, RPC contract, or storage schema for Knowledge Base is implemented in the repository.
- **Role in current architecture docs:** conceptual component referenced by architecture/mission materials as a future optimization and learning loop.

## Verification Scope (what was re-checked)

This status was re-validated against:

- Component/architecture docs (`docs/architecture/overview.md`, `docs/architecture/components.md`, `docs/architecture/components/compiler.md`).
- RFC index and active RFC package map (`docs/rfcs-pointer.md`).
- ADR index and accepted ADR set (`docs/adr/README.md` and ADR files in `docs/adr/`).
- Repository implementation paths (`src/`) for executable contracts and runtime wiring.

### Result

Knowledge Base remains **documented as planned** and **not yet implemented**.

---

## Responsibility

### What is implemented now

- No runtime responsibility is assigned to a concrete Knowledge Base module.
- No code path in current MVP/Phase runtime requires a Knowledge Base lookup/update step.

### Target responsibility (tracked for next stage)

- Store reusable artifacts mapping from task/program characteristics to optimization outcomes.
- Support pattern reuse in compilation/runtime planning.
- Provide a learning feedback loop from execution outcomes back into future decisions.

### TODO (Responsibility)

- TODO: freeze v1 responsibility boundaries between Compiler, Intelligent Runtime, and Knowledge Base (who reads/writes which artifact and at which lifecycle stage).
- TODO: define strict scope for OSS baseline (deterministic reuse only vs adaptive model updates).
- TODO: add explicit non-goals for first production release (e.g., no online training in request path, no opaque non-reproducible policy overrides).

---

## Interfaces

### What is implemented now

- No public API endpoint exists for Knowledge Base operations.
- No internal gRPC/protobuf service definition exists for Knowledge Base in current runtime contracts.
- No crate-level or Python package API is wired into kernel/compiler execution flow as `knowledge_base` capability.

### Target interfaces (to be specified)

- Read path for candidate retrieval (e.g., by program signature, backend profile, objective shape).
- Write path for post-run feedback ingestion (metrics, outcome quality, constraints).
- Optional explainability surface to expose why a prior artifact was reused/rejected.

### TODO (Interfaces)

- TODO: publish an RFC for Knowledge Base service contract (API, request/response schema, determinism guarantees, versioning).
- TODO: add ADR that defines whether KB is a separate service or embedded library in existing services.
- TODO: define failure semantics and fallback behavior when KB is unavailable (must preserve deterministic baseline execution).
- TODO: define compatibility policy for KB schemas and migration strategy across releases.

---

## Inputs / Outputs

### What is implemented now

- No executable input/output contract currently references Knowledge Base artifacts.
- Job submission, compilation, scheduling, and execution contracts function without KB-specific fields.

### Planned I/O model (conceptual)

Potential inputs:
- Program/circuit structural signatures.
- Target backend/device capability metadata.
- Historical execution outcomes and quality metrics.

Potential outputs:
- Candidate optimized circuit templates/transform recipes.
- Ranking/prior probabilities for compiler/runtime choices.
- Metadata for explainability and audit trails.

### TODO (Inputs / Outputs)

- TODO: define canonical feature schema for lookup keys (hashing, normalization, version stamping).
- TODO: define output envelope with provenance fields (source run IDs, confidence, timestamp, compatibility window).
- TODO: align I/O fields with Phase-4 explainability contracts and Phase-5 distributed execution metadata.
- TODO: document deterministic fallback when no KB match exists.

---

## Storage / State

### What is implemented now

- No persistent storage layout (tables/buckets/files) is defined for Knowledge Base.
- No retention, compaction, or lifecycle policies are codified.

### Planned storage concerns

- Artifact durability for reusable patterns.
- Separation between raw run telemetry and curated reusable knowledge entries.
- Versioned schema evolution with backward/forward compatibility constraints.

### TODO (Storage / State)

- TODO: choose baseline storage design (single-node SQLite + object artifacts vs service DB + object store hybrid).
- TODO: define schema versioning and migration tooling requirements.
- TODO: define retention policy (TTL, archival tiers, reproducibility-preserving snapshots).
- TODO: define data integrity controls (checksums, provenance chain, immutable audit records).

---

## Failure Modes

### What is implemented now

- No runtime failure mode exists because KB is not active in current execution path.

### Expected failure classes (for future implementation)

- Lookup miss / low-confidence match.
- Corrupt or incompatible stored artifact.
- Stale knowledge causing degraded optimization.
- Storage/service outage or latency spikes.

### TODO (Failure Modes)

- TODO: define error taxonomy and mapping to existing public/internal error model.
- TODO: specify circuit/runtime fallback policy per failure class.
- TODO: define safety guardrails to prevent unsafe or non-deterministic reuse.
- TODO: add conformance and chaos scenarios validating degradation behavior.

---

## Observability
### What is implemented now

- No KB-specific metrics/logs/traces are emitted.

### Planned observability model

- Match-rate and miss-rate metrics.
- Reuse impact metrics (latency, fidelity/quality improvement, cost reduction).
- Drift/freshness indicators and confidence distribution.
- Trace annotations linking decisions to knowledge entry provenance.

### TODO (Observability)

- TODO: define minimal metric set and SLOs (availability, p95 lookup latency, safe fallback rate).
- TODO: define log schema for auditability (why candidate was selected/rejected).
- TODO: define tracing attributes compatible with Phase-5 topology tracing contracts.
- TODO: add release gates and fixture-based validation for KB observability.

---

## RFC / ADR Alignment Check (2026-05-08)

### RFC status

- Current implemented RFC packages (MVP-2, MVP-3, Phase-3/4/5) do not introduce an implemented Knowledge Base contract.
- Phase-6/7 RFC packages focus on plugin ecosystem, versioning policy, and developer experience; no accepted executable KB contract is present.
- Historical language scope notes KB integration as Post-MVP direction (not MVP requirement).

### ADR status

- No accepted ADR currently defines a concrete Knowledge Base architecture, contract, or operational policy.
- Existing ADR set is synchronized around implemented MVP/Phase contracts, but KB remains outside that accepted implementation baseline.

### TODO (RFC/ADR)

- TODO: create dedicated KB RFC series (service contract, data model, safety/determinism policy, observability/release gates).
- TODO: land synchronized ADR package once KB RFCs move to Accepted/Implemented.
- TODO: add KB to RFC↔ADR gap-analysis workflow documents before implementation starts.

---

## Execution-Path Status Snapshot

As of 2026-05-08, the system can be treated as operating in **KB-disabled baseline mode**:

- Compiler/runtime decisions execute via currently implemented deterministic and policy-based contracts.
- No persistent knowledge reuse loop modifies compile/runtime outcomes.
- Future KB work can be introduced incrementally only after RFC/ADR contract freeze.

## Next-Stage Checklist (implementation preparation)

- TODO: draft KB architecture RFC v1 and circulate for review.
- TODO: decide deployment shape (service vs library) and publish ADR.
- TODO: define schemas + migrations + provenance/audit model.
- TODO: define deterministic integration points with compiler/runtime.
- TODO: define observability + conformance + release-readiness gates.
- TODO: update `docs/architecture/overview.md` and component index once KB reaches implementation milestones.
