# Product 1.0 Contract Alignment Plan

**Status:** Planning baseline for service-by-service and contract-by-contract implementation commits  
**Target:** Mature Eigen OS Product `1.0.0` contract implementation  
**Inputs:** `docs/architecture/**`, `docs/reference/**`, `proto/**`, current `src/**` implementation snapshot  
**Created:** 2026-06-01

---

## 1. Executive summary

The documentation now describes Product `1.0.0` as a contract-first mature platform, while the repository implementation is still a mixture of MVP, phase closure artifacts, partial service scaffolds, and forward-looking contract fixtures. The next implementation stream should therefore be managed as a **contract alignment program**, not as ad-hoc feature work.

The target product is reached when every normative contract in `docs/reference/` has:

1. a versioned wire/schema representation,
2. an owning service or crate,
3. compatibility/conformance fixtures,
4. runtime validation and canonical errors,
5. observability contract marker metrics,
6. migration notes for breaking or behavior-changing updates,
7. release evidence proving the contract is enforced end-to-end.

The recommended delivery model is **thin vertical contract slices**: each commit or PR should pick one service boundary or one contract surface, update proto/schema/docs/tests together, and include a compatibility report. This keeps the product moving toward maturity while avoiding a large unreviewable rewrite.

---

## 2. Source-of-truth map

| Area | Source of truth | Primary implementation owners |
|---|---|---|
| Public API | `docs/reference/api/grpc-public.md`, `proto/eigen/api/v1/*` | `src/services/system-api`, client SDKs/CLI |
| Internal API | `docs/reference/api/grpc-internal.md`, `proto/eigen/internal/v1/*` | Kernel/QRTX, compiler, optimizer, driver-manager |
| Job input | `docs/reference/jobspec.md` | CLI, System API, Kernel/QRTX |
| Language | `docs/reference/eigen-lang.md` | Eigen-Lang package, compiler |
| AQO | `docs/reference/formats/aqo.md` | compiler, optimizer, QFS-L3 |
| QFS layout | `docs/reference/formats/qfs-layout.md` | `src/rust/crates/qfs`, System API facades, Kernel/QRTX |
| Error semantics | `docs/reference/error-model.md`, `docs/reference/error-mapping.md` | all public/internal services |
| Runtime observability | `docs/reference/orchestration-observability-contract.md`, `docs/reference/intelligent-runtime-observability-contract.md`, `docs/reference/cluster-runtime-observability-contract.md` | observability crate, Kernel/QRTX, Resource Manager, System API |
| Benchmark observability | `docs/reference/benchmark-observability-contract.md` | benchmark-service, observability crate |
| Multi-device execution | `docs/reference/multi-device-execution-contract.md` | Kernel/QRTX, Resource Manager, Driver Manager, QFS |
| Architecture boundaries | `docs/architecture/contract-map.md`, component docs | all service owners |

---

## 3. Current implementation snapshot and main gaps

### 3.1 Repository-level gaps

| Gap | Impact | Required Product 1.0 outcome |
|---|---|---|
| Version mismatch across docs, README, pyproject packages, Rust workspace, proto README, and component contracts | Release identity is ambiguous and cannot be certified as `1.0.0` | Single release/version policy with generated contract manifest and component contract markers |
| Proto contracts are smaller than the reference/API docs | Public and internal APIs cannot fully enforce documented semantics | Proto first-class coverage for all Product 1.0 public/internal methods, envelopes, structured errors, idempotency, auth context, trace context, pagination, and results |
| Several docs reference target files/contract families that are not present yet (`docs/reference/security/authz.md`, REST docs, compiler contract directories, benchmark/observability subdirectories) | Implementation cannot start cleanly for those areas without clarifying canonical specs | Add missing reference docs or remove/redirect stale references before implementation |
| Current implementation mixes MVP ownership shortcuts with target service boundaries | System API and other services still own state/facades that target architecture assigns to Kernel/QRTX, QFS, Resource Manager, or KB | Explicit migration sequence from MVP facades to target owners |
| No unified contract drift matrix | Hard to know whether a commit moves toward or away from Product 1.0 | Machine-readable contract inventory and drift CI gate |

### 3.2 Service-level gaps

| Component | Current shape | Product 1.0 gaps |
|---|---|---|
| System API | Python public gRPC skeleton plus validation/security/lifecycle helpers | Must become strict public gateway, enforce authn/authz/version/idempotency/deadline/payload policy, delegate lifecycle/results to Kernel, expose REST mirror if kept in contract |
| Kernel/QRTX | Rust crates and internal gateway primitives | Must own canonical lifecycle, orchestration DAG, retries, deadlines, split/merge, queue coordination, QFS persistence, and cross-service tracing |
| Resource Manager | Rust crate with scheduling and contract tests, no dedicated service boundary | Must become explicit scheduling/resource authority or documented embedded kernel module, with queue, reservations, fairness, priority, topology, and explainability contracts |
| Compiler / Eigen-DPDA | Python compiler scaffold with deterministic/golden tests | Must fully implement Eigen-Lang 1.0 allowlist, JobSpec-to-AQO path, AQO schema validation, deterministic metadata, structured errors, and artifact persistence handoff |
| GNN Optimizer | Proto/fixtures/adjacent tests but no production service path | Must deliver optimizer service, model registry/versioning, deterministic fallbacks, optimization trace, confidence/explainability, and quality gates |
| Driver Manager / QDriver | Python driver-manager with simulator and provider-adjacent modules | Must implement final QDriver lifecycle (`Initialize`, `Execute`, `GetStatus`, `Calibrate`, `Cancel`), session pooling, capability registry, sandboxing, secrets access, normalized results/errors |
| QFS | Rust local CircuitFS and checkpoint primitives plus System API facade | Must provide L3 artifact store, L2 checkpoint store, L1 LQM reservation semantics, lineage/provenance, retention, integrity checks, and service-level APIs |
| Knowledge Base | Public proto exists, service implementation is not yet a first-class runtime owner | Must implement record/decision-log APIs, immutability/anonymization/index profile, lineage, vector/structural query, continuous learning integration |
| Benchmark Service | Python lifecycle/reproducibility modules | Must align run API, dataset ingestion, artifact governance, replay, compare/history, observability, and result schemas to contract `1.0.0` |
| Observability | Rust observability crate and many tests/fixtures | Must export contract marker metrics, bounded labels, structured logs, W3C trace continuity, dashboards/alerts/runbooks for every service |
| Security & Isolation | Python security helpers and Rust security module scaffold | Must implement OAuth2/JWT, RBAC/ABAC policy snapshots, mTLS/internal identity, audit store, secrets lifecycle, workload attestation, sandbox enforcement, fail-closed behavior |
| Client SDKs / CLI | Rust CLI and docs; SDKs mostly target docs | Must support packaging, auth metadata, idempotency keys, retries, streaming updates, structured errors, version negotiation, and conformance tests |

---

## 4. Product 1.0 readiness definition

Product `1.0.0` is ready only when all of the following gates pass:

1. **Contract inventory gate:** every `docs/reference/**` contract has an owner, proto/schema, tests, and compatibility status.
2. **Proto/API gate:** public and internal protos match reference docs and pass lint/breaking checks.
3. **Service ownership gate:** System API is public ingress only; Kernel/QRTX is lifecycle authority; QFS owns persistence; Resource Manager owns scheduling/resources; Driver Manager owns provider boundary.
4. **Determinism gate:** identical JobSpec/Eigen-Lang/AQO inputs produce identical normalized outputs or deterministic errors.
5. **Security gate:** public endpoints require TLS/JWT/OAuth2, internal calls use authenticated service identity, authz is fail-closed, and secrets never traverse public contracts.
6. **Observability gate:** every service exports contract marker metrics, bounded labels, structured logs, and trace continuity across the full submit-to-results path.
7. **Conformance gate:** all contract fixtures, golden tests, negative tests, replay tests, and multi-device tests are automated in CI.
8. **Migration gate:** every behavior change has release notes and compatibility/migration guidance.
9. **Operational gate:** local and containerized reference deployments include health checks, dashboards, alerts, and rollback runbooks.
10. **Release evidence gate:** a Product 1.0 evidence bundle records exact versions, test commands, generated schemas, dashboards, and known limitations.

---

## 5. Recommended implementation waves

### Wave 0 — Baseline freeze and contract inventory

**Goal:** make the implementation target unambiguous before touching service logic.

#### Work items

1. Create `docs/development/product-1.0-contract-inventory.md` with one row per normative contract.
2. Generate or maintain a machine-readable `contracts/product-1.0/manifest.json` containing:
   - contract name,
   - version,
   - owning component,
   - proto/schema files,
   - conformance tests,
   - implementation status,
   - compatibility status.
3. Decide whether Product 1.0 corresponds to contract version `1.0.0` or the existing Eigen OS `1.3.0` architecture scope in docs; document the distinction between **product release version** and **contract package version**.
4. Fix stale docs/index links before implementation:
   - missing REST reference docs if REST remains target,
   - missing `docs/reference/security/authz.md` reference docs,
   - missing compiler/benchmark/observability subdirectories referenced from architecture docs,
   - README/proto README version statements.
5. Add CI check that fails if reference docs mention a missing canonical file.
6. Add CI check that fails if a Product 1.0 contract has no owner/test mapping.

#### Exit criteria

- All contract owners are known.
- All canonical references resolve.
- Version policy is documented.
- Drift is visible before code changes begin.

---

### Wave 1 — Public API, JobSpec, and error model closure

**Goal:** stabilize the public boundary before moving internals.

#### System API

1. Update `proto/eigen/api/v1/job_service.proto` and `device_service.proto` to match the public API reference exactly.
2. Add common public envelopes:
   - `contract_version`,
   - `request_id`,
   - `idempotency_key`,
   - `trace_context`,
   - `deadline`,
   - `tenant/project` context if multi-tenancy is in Product 1.0 scope.
3. Implement API version negotiation and compatibility rejection.
4. Implement idempotent `SubmitJob` semantics:
   - same key + same normalized request returns same `job_id`,
   - same key + different normalized request returns canonical conflict/precondition error,
   - TTL and persistence policy are configurable.
5. Implement payload limits before forwarding.
6. Normalize all public errors through `docs/reference/error-model.md` and `docs/reference/error-mapping.md`.
7. Add structured `google.rpc.Status` details where supported.
8. Add public contract marker metric.
9. Add public API conformance tests:
   - happy path,
   - validation failures,
   - auth failures,
   - idempotency conflict,
   - retryability mapping,
   - version mismatch.

#### JobSpec

1. Build a complete JobSpec 1.0 parser/normalizer shared by CLI and System API.
2. Add JSON Schema/YAML fixtures for minimal, full, invalid, and future-compatible specs.
3. Enforce deterministic canonicalization and package digest generation.
4. Map JobSpec scheduling/security/observability fields into internal kernel requests.
5. Add migration tests for older accepted JobSpec versions if supported.

#### Client CLI/SDK baseline

1. Update CLI to emit canonical envelopes and trace/idempotency metadata.
2. Add contract tests that submit file-based and inline JobSpec inputs.
3. Define SDK conformance suite before adding more language SDKs.

#### Exit criteria

- Public API behavior is stable and contract-tested.
- All invalid inputs produce canonical errors.
- A public client can submit, watch, cancel, and retrieve results without depending on internal details.

---

### Wave 2 — Kernel/QRTX becomes lifecycle authority

**Goal:** remove MVP lifecycle ownership from System API and make Kernel/QRTX the canonical runtime control plane.

**Planning package:** `docs/development/wave-2/product-1.0-wave-2-execution-plan.md`, `docs/development/wave-2/product-1.0-wave-2-issue-pack.md`, `docs/development/wave-2/product-1.0-wave-2-rfc-adr-gap-analysis.md`, `docs/development/wave-2/product-1.0-wave-2-compatibility-report.md`, `docs/development/wave-2/product-1.0-wave-2-release-readiness-checklist.md`, and `docs/development/wave-2/product-1.0-wave-2-exit-evidence-bundle.md`.

**Governance baseline:** `rfcs/0050-product-1.0-kernel-qrtx-lifecycle-authority.md` and `docs/adr/0036-product-1.0-kernel-qrtx-lifecycle-authority.md`.

#### Work items

1. Expand `proto/eigen/internal/v1/kernel_gateway.proto` to cover:
   - enqueue,
   - status,
   - cancel,
   - stream updates or event subscription,
   - results references,
   - dispatch rationale retrieval,
   - deadline/retry policy,
   - normalized security context,
   - trace context.
2. Implement durable or replayable kernel job state store.
3. Define canonical state transitions and enforce invalid transition errors.
4. Move lifecycle mutations out of System API.
5. Add orchestration DAG model:
   - compile,
   - optimize,
   - schedule,
   - execute,
   - persist,
   - record knowledge/observability,
   - finalize.
6. Implement deadline propagation and cancellation fan-out to compiler/optimizer/driver/QFS tasks.
7. Implement retry governance tied to error retryability.
8. Emit orchestration metrics/logs/traces per contract.
9. Add integration tests for:
   - submit-to-results,
   - cancel during queued/compiling/executing,
   - retryable vs non-retryable failure,
   - trace continuity,
   - crash/restart replay if persistence is in scope.

#### Exit criteria

- System API delegates lifecycle to Kernel/QRTX.
- Kernel owns state machine, transition validation, and orchestration traces.
- Runtime behavior is deterministic and observable.

---

### Wave 3 — Compiler, Eigen-Lang, and AQO closure

**Goal:** make compilation a production-grade deterministic contract boundary.

#### Work items

1. Complete Eigen-Lang 1.0 grammar/AST allowlist implementation.
2. Remove ambiguous or undocumented compiler behavior.
3. Add import/function/decorator allowlist enforcement with structured errors.
4. Implement JobSpec-to-compiler request mapping.
5. Validate compiler options, target metadata, and referenced artifacts.
6. Produce AQO with deterministic ordering, metadata, digests, and provenance.
7. Validate AQO against the reference format before returning/persisting.
8. Persist compiler artifacts to QFS-L3 through the target QFS boundary, not ad-hoc local paths.
9. Emit compile traces and metrics:
    - compile duration,
    - validation failures,
    - deterministic digest,
    - compiler contract version.
10. Expand golden suite:
    - minimal circuit,
    - parameterized VQE,
    - invalid syntax,
    - forbidden AST,
    - unsupported target,
    - referenced artifact missing,
    - deterministic repeated compile.
11. Close the Wave 3 contract inventory and compatibility rows for Eigen-Lang, compiler request mapping, AQO canonicalization, and compiler-to-QFS persistence.

#### Exit criteria

- Compiler is pure/deterministic and never executes user code.
- AQO output is schema-validated and reproducible.
- All compiler failures map to canonical errors.
- Wave 3 documentation contains no unresolved `TBD` values for completed items.

---

### Wave 4 — QFS data fabric maturity

**Goal:** provide durable, lineage-aware storage for artifacts, checkpoints, and live qubit/resource coordination.

#### QFS-L3 CircuitFS

1. Implement object-store-backed artifact persistence abstraction (local/S3/MinIO profiles).
2. Store metadata records with content digest, producer, contract version, timestamps, and lineage.
3. Add immutability and retention policy enforcement.
4. Add integrity verification on read.
5. Add migration plan for existing local artifact layout.

#### QFS-L2 State Store

1. Finalize checkpoint envelope schema.
2. Implement checkpoint write/read/delete with atomicity guarantees.
3. Add restore compatibility checks.
4. Add tests for corrupted, missing, and version-incompatible checkpoint envelopes.

#### QFS-L1 Live Qubit Manager

1. Decide whether L1 is owned by QFS crate, Resource Manager, or a split authority.
2. Implement reservation tokens, leases, TTL, and isolation semantics.
3. Add atomic offline failover and stale reservation cleanup.
4. Wire L1 into Kernel scheduling and multi-device execution.

#### Exit criteria

- Runtime artifacts are no longer scattered across service-local state.
- Every result has lineage and provenance.
- Checkpoints and reservations are contract-tested.

---

### Wave 5 — Resource Manager and multi-device execution

**Goal:** implement mature scheduling/resource contracts and distributed execution semantics.

#### Work items

1. Decide final deployment shape: standalone Resource Manager service vs embedded kernel module with stable internal API.
2. Implement device/resource inventory sourced from Driver Manager and topology metadata.
3. Implement scheduling policy engine:
   - eligibility,
   - scoring,
   - fairness,
   - priority,
   - quota,
   - deadline awareness,
   - policy versioning.
4. Implement reservation lifecycle:
   - create,
   - renew,
   - bind to job/task,
   - release,
   - expire,
   - recover.
5. Implement queue delivery semantics:
   - leases,
   - acknowledgements,
   - redelivery,
   - dead-letter handling,
   - replay.
6. Implement multi-device split/merge envelopes and result aggregation.
7. Implement `GetDispatchRationale` from real scheduling decisions, not static placeholders.
8. Add deterministic replay gate for scheduling decisions.
9. Emit cluster/runtime observability metrics and traces.

#### Exit criteria

- Scheduling decisions are explainable and reproducible.
- Multi-device execution is governed by contract envelopes.
- Queue and worker failures have deterministic recovery behavior.

---

### Wave 6 — Driver Manager and QDriver final contract

**Goal:** make provider execution safe, normalized, and replaceable.

#### Work items

1. Align proto with final QDriver methods:
   - `Initialize`,
   - `Execute`,
   - `GetStatus`,
   - `Calibrate`,
   - `Cancel`.
2. Split Driver Manager responsibilities from provider-specific QDriver implementations.
3. Implement capability registry with versioned device profiles.
4. Implement session pooling and lifecycle governance.
5. Implement normalized result schema and error mapping.
6. Enforce sandbox/process/container isolation policy.
7. Ensure provider secrets are accessed only through the security/secrets module.
8. Implement provider tolerance profiles and parity tests.
9. Add official simulator as the reference conformance backend.
10. Add optional provider drivers only behind explicit configuration and test profiles.

#### Exit criteria

- Kernel can execute through any conformant QDriver without provider-specific code.
- Driver failures are normalized and retryability is correct.
- Secrets and provider SDK behavior do not leak into public contracts.

---

### Wave 7 — GNN Optimizer and intelligent runtime

**Goal:** promote optimizer/intelligent-runtime contracts from fixtures to production path.

#### Work items

1. Implement Optimizer Service server and client wiring from Kernel/QRTX.
2. Define model registry and model version promotion policy.
3. Support deterministic fallback when optimizer is unavailable or confidence is below threshold.
4. Emit optimization candidate traces:
   - objective,
   - score breakdown,
   - topology context,
   - model version,
   - confidence,
   - fallback reason.
5. Add quality regression gates using fixed fixtures.
6. Wire optimizer outputs into compiler/driver execution path.
7. Add intelligent runtime observability marker metrics and dashboards.

#### Exit criteria

- Optimization can be enabled safely without breaking deterministic execution.
- Fallback behavior is explicit, tested, and observable.
- Model quality regressions block release.

---

### Wave 8 — Knowledge Base and continuous learning loop

**Goal:** make operational learning and decision lineage first-class while preserving privacy and immutability.

#### Work items

1. Implement Knowledge Base Service for records and decision logs.
2. Enforce provenance, immutability, anonymization, and index profile contracts.
3. Add structural and vector query implementations or a documented pluggable backend interface.
4. Wire Kernel/Optimizer/Benchmark Service to append decision logs.
5. Implement dataset assembly governance for continuous learning.
6. Add retention/deletion rules and privacy safeguards.
7. Add KB conformance fixtures and compatibility tests.

#### Exit criteria

- Runtime decisions can be audited and queried.
- Training data generation is governed and reproducible.
- Sensitive data is anonymized or rejected by policy.

---

### Wave 9 — Security, identity, policy, and isolation

**Goal:** turn security from MVP helpers into a fail-closed platform boundary.

#### Work items

1. Add missing normative `docs/reference/security/authz.md` or equivalent before coding.
2. Implement JWT/OAuth2 validation at System API.
3. Implement service-to-service identity for internal calls, preferably mTLS/SPIFFE-compatible or a documented local equivalent.
4. Implement RBAC/ABAC policy engine with versioned snapshots.
5. Propagate normalized security context across internal calls.
6. Implement audit event store with tamper-evident metadata.
7. Implement secrets lifecycle integration for providers.
8. Enforce sandbox profiles for compiler/driver/runtime plugin paths.
9. Add fail-closed behavior for authz/policy/secrets failures.
10. Add SAST/DAST/SBOM gates to required release evidence.

#### Exit criteria

- No public call can bypass authentication and authorization.
- Internal calls are attributable to services/workloads.
- Policy and audit decisions are versioned and traceable.

---

### Wave 10 — Observability, operations, and release evidence

**Goal:** make Product 1.0 operable, supportable, and certifiable.

#### Work items

1. Add contract marker metrics for all services.
2. Enforce bounded metric labels in tests.
3. Implement structured JSON logs with required fields.
4. Ensure W3C TraceContext continuity across:
   - CLI/SDK,
   - System API,
   - Kernel,
   - compiler,
   - optimizer,
   - resource manager,
   - driver manager,
   - QFS,
   - benchmark/KB.
5. Add dashboards and alerts for every observability contract.
6. Add runbooks for common failures:
   - queue stall,
   - provider outage,
   - optimizer fallback surge,
   - QFS persistence failure,
   - authz policy outage,
   - trace continuity breakage.
7. Create Product 1.0 release readiness checklist and evidence bundle template.
8. Update README and deployment docs to reflect Product 1.0, not old MVP/phase closure language.

#### Exit criteria

- Operators can diagnose a failed job without reading service-local state.
- Dashboards/alerts match contract metrics.
- Release evidence can be reproduced from CI.

---

## 6. Suggested commit sequencing

Use this sequence for small, reviewable commits:

1. `docs: add product 1.0 contract inventory`
2. `docs: fix stale reference links and version policy`
3. `proto: align public api envelopes with product 1.0`
4. `system-api: enforce public version and idempotency contracts`
5. `system-api: delegate lifecycle reads and writes to kernel gateway`
6. `kernel: implement canonical job state machine and store`
7. `kernel: wire compile-optimize-execute-persist DAG`
8. `compiler: complete eigen-lang allowlist and deterministic aqo metadata`
9. `qfs: implement l3 artifact metadata and integrity checks`
10. `qfs: finalize l2 checkpoint envelopes`
11. `resource-manager: expose scheduling/resource authority boundary`
12. `resource-manager: implement deterministic dispatch rationale`
13. `driver-manager: align qdriver lifecycle methods`
14. `driver-manager: enforce sandbox/secrets/result normalization`
15. `optimizer: implement production optimizer service path`
16. `knowledge-base: implement records and decision logs`
17. `security: implement jwt/oauth2 and policy snapshots`
18. `observability: add marker metrics and bounded labels across services`
19. `ops: add dashboards, alerts, runbooks, release evidence bundle`
20. `release: update product 1.0 README/version metadata`

Each commit should include:

- implementation changes,
- tests/fixtures,
- docs/reference or compatibility report if behavior changes,
- migration note if public behavior changes,
- regenerated proto bindings when proto changes.

---

## 7. What is missing before implementation can start

### 7.1 Decisions needed

1. **Versioning decision:** clarify relationship between Product `1.0.0`, contract `1.0.0`, docs mentioning Eigen OS `1.3.0`, and existing package versions (`0.x`, Rust workspace `0.18.0`).
2. **REST scope decision:** docs mention REST mirrors, but the repo primarily exposes gRPC. Decide whether REST is required for Product 1.0 or should be deferred/removed from contract scope.
3. **Resource Manager deployment decision:** choose standalone service vs embedded kernel module with internal API.
4. **QFS-L1 ownership decision:** decide whether live qubit reservations are owned by QFS, Resource Manager, Kernel, or a split model.
5. **GNN Optimizer maturity decision:** choose whether Product 1.0 requires production ML optimizer or supports deterministic heuristic fallback with GNN behind feature flag.
6. **Knowledge Base backend decision:** choose reference storage/index backend for records, decision logs, and vector/structural queries.
7. **Security policy backend decision:** choose policy language/storage (for example OPA/Rego, Cedar, or custom typed policy snapshots).
8. **Provider support decision:** define Product 1.0 supported backends: simulator only, simulator + Qiskit Runtime, simulator + AWS Braket, or provider plugins as experimental.
9. **Persistence profile decision:** choose required local/dev and production storage profiles for QFS, job state, idempotency state, KB, and audit logs.
10. **Compatibility decision:** define which pre-1.0 JobSpec/API versions are accepted and what migration behavior is promised.

### 7.2 Missing or incomplete artifacts to create first

1. Contract inventory and machine-readable manifest.
2. Product 1.0 release/version policy.
3. Missing reference docs or redirected links for security authz, REST API, compiler contracts, benchmark contracts, and observability contract directories.
4. Proto-to-reference coverage matrix.
5. Service ownership matrix and data ownership matrix.
6. Canonical local deployment topology for Product 1.0.
7. Product 1.0 conformance fixture index.
8. Product 1.0 release readiness checklist and evidence bundle template.

### 7.3 Access/configuration needed for later waves

1. OAuth2/JWT issuer configuration or local test issuer.
2. Internal service identity/mTLS development profile.
3. Object store profile for QFS-L3 (local filesystem and MinIO/S3-compatible).
4. Database choice for job state, idempotency, KB, audit, and metadata.
5. Provider credentials strategy for optional hardware/cloud drivers.
6. Observability stack profile (Prometheus, Grafana, Loki/Elastic, Jaeger/Tempo).
7. CI environment able to run Rust, Python, proto, security, container, and contract-drift gates.

---

## 8. Risk register

| Risk | Probability | Impact | Mitigation |
|---|---:|---:|---|
| Starting implementation before version/ownership decisions | High | High | Complete Wave 0 first |
| Proto drift from reference docs | High | High | Add proto/reference coverage gate |
| System API remains stateful while Kernel also becomes authoritative | Medium | High | Migrate lifecycle ownership in one controlled wave |
| QFS-L1/Resource Manager ownership conflict | Medium | High | Resolve ownership decision before reservations implementation |
| Security contracts implemented inconsistently per service | Medium | High | Central security module, shared test fixtures, fail-closed tests |
| Observability labels become unbounded | Medium | Medium | Bounded-label unit tests and scrape validation |
| Provider-specific behavior leaks into public APIs | Medium | High | Driver Manager normalization tests and simulator reference backend |
| ML optimizer nondeterminism breaks reproducibility | Medium | High | Versioned model registry, deterministic fallback, replay fixtures |

---

## 9. First actionable backlog

These are the immediate tasks recommended before service implementation commits:

1. Add `product-1.0-contract-inventory.md`.
2. Add `contracts/product-1.0/manifest.json`.
3. Add docs link checker for `docs/architecture/**` and `docs/reference/**`.
4. Update root README/proto README to stop advertising old Phase-5/0.1 baseline as current truth.
5. Create a proto/reference coverage report for:
   - public API,
   - internal API,
   - JobSpec,
   - error details,
   - QFS/AQO envelopes,
   - observability markers.
6. Decide Product 1.0 version policy and REST scope.
7. Start Wave 1 with public API envelopes and error model tests.

---

## 10. Recommended first service implementation order

1. **System API + JobSpec + error model** because this stabilizes user-facing behavior.
2. **Kernel/QRTX lifecycle** because it resolves the biggest architecture divergence.
3. **Compiler/AQO** because deterministic artifacts are required by all downstream execution.
4. **QFS-L3/L2** because mature persistence is needed before production execution and replay.
5. **Resource Manager + multi-device** because scheduling depends on stable lifecycle and artifact/state contracts.
6. **Driver Manager/QDriver** because execution normalization depends on scheduling/resource decisions.
7. **Observability/Security cross-cutting closure** should start early as shared libraries/tests, then be completed after major service rewiring.
8. **GNN Optimizer/Knowledge Base/continuous learning** should become production path after deterministic runtime and storage are stable.
