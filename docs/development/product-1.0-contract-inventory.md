# Product 1.0 Contract Inventory

**Status:** Wave 3-aligned inventory with concrete Kernel/QRTX, compiler, and QFS slice mappings
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`
**Version policy:** `docs/development/product-1.0-version-policy.md`
**Machine-readable manifest:** `contracts/product-1.0/manifest.json`
**Source of truth:** `docs/architecture/**`, `docs/reference/**`
**Created:** 2026-06-01

---

## 1. Status vocabulary

Implementation status values are `documented`, `partial`, `planned`, and `implemented`. Compatibility status values are `frozen-for-wave-0`, `needs-alignment`, `planned`, and `compatible`. Definitions are maintained in `docs/development/product-1.0-version-policy.md`.

---

## 2. Product 1.0 normative contract inventory

| Contract | Version | Owning component | Canonical source | Proto/schema files | Conformance tests / gate | Implementation status | Compatibility status |
|---|---:|---|---|---|---|---|---|
| Public gRPC API (`eigen.api.v1`) | `1.0.0` target on namespace `v1` | System API; client SDKs/CLI | `docs/reference/api/grpc-public.md`; `docs/architecture/components/system-api.md` | `proto/eigen/api/v1/job_service.proto`; `proto/eigen/api/v1/device_service.proto`; `proto/eigen/api/v1/types.proto`; `proto/eigen/api/v1/knowledge_base_service.proto` | `src/services/system-api/tests/test_public_envelope_versioning.py`; `src/services/system-api/tests/test_idempotency.py`; `src/services/system-api/tests/test_public_error_conformance.py`; `src/services/system-api/tests/test_observability_smoke.py`; `src/rust/apps/cli/tests/`; `buf lint`; `buf breaking` | implemented | compatible |
| Internal gRPC API (`eigen.internal.v1`) | `1.0.0` target on namespace `v1` | Kernel/QRTX; compiler; driver-manager; optimizer | `docs/reference/api/grpc-internal.md`; `docs/architecture/components/qrtx.md` | `proto/eigen/internal/v1/kernel_gateway.proto`; `proto/eigen/internal/v1/compilation_service.proto`; `proto/eigen/internal/v1/driver_manager_service.proto`; `proto/eigen/internal/v1/optimizer_service.proto`; `proto/eigen/internal/v1/types.proto` | `src/rust/crates/eigen-kernel/tests/` (planned Product 1.0 expansion); `src/services/eigen-compiler/tests/`; `buf lint`; `buf breaking` | partial | needs-alignment |
| JobSpec | `1.0.0` | System API; CLI; Kernel/QRTX; packaging | `docs/reference/jobspec.md` | `docs/reference/schemas/jobspec-1.0.schema.json`; public `SubmitJobRequest` mapping in `proto/eigen/api/v1/job_service.proto` | `src/services/system-api/tests/test_jobspec_parser.py`; `docs/reference/fixtures/jobspec/1.0/`; `src/rust/apps/cli/tests/fixtures/jobspec-valid-minimal.yaml`; `cargo test --manifest-path src/rust/Cargo.toml -p cli` | implemented | compatible |
| Eigen-Lang | `1.0.0` | Compiler / Eigen-DPDA | `docs/reference/eigen-lang.md`; `docs/architecture/components/compiler.md` | Planned grammar/schema artifacts; compiler service proto in `proto/eigen/internal/v1/compilation_service.proto` | `src/services/eigen-compiler/tests/test_conformance_suite.py` | partial | needs-alignment |
| AQO format | `1.0.0` | Compiler; optimizer; QFS; Kernel/QRTX | `docs/reference/formats/aqo.md` | Planned AQO schema under `specs/` or `contracts/product-1.0/`; `proto/eigen/internal/v1/types.proto` circuit payload mapping | `src/services/eigen-compiler/tests/test_conformance_suite.py` (planned AQO golden expansion) | partial | needs-alignment |
| QFS layout (CircuitFS) | `1.0.0` | QFS; Kernel/QRTX; System API facades | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | Planned storage manifest schema under `contracts/product-1.0/` | `src/rust/crates/qfs/tests/` (planned Product 1.0 layout conformance) | partial | needs-alignment |
| Canonical error model | `1.0.0` | All public/internal services | `docs/reference/error-model.md` | `google.rpc.Status` public detail mapping; `proto/eigen/api/v1/types.proto`; `proto/eigen/api/v1/job_service.proto` | `src/services/system-api/tests/test_public_error_conformance.py`; `src/services/system-api/tests/test_validation_errors.py`; `src/services/eigen-compiler/tests/`; `src/services/driver-manager/tests/` | partial; Wave 1 public-boundary slice implemented | compatible for Wave 1 public-boundary slice |
| Error mapping matrix | `1.0.0` | All public/internal services | `docs/reference/error-mapping.md` | `docs/reference/error-mapping.md`; `google.rpc.ErrorInfo` / `BadRequest` / `PreconditionFailure` / `QuotaFailure` public detail mappings | `src/services/system-api/tests/test_public_error_conformance.py`; `src/rust/crates/eigen-kernel/tests/` | partial; Wave 1 public-boundary slice implemented | compatible for Wave 1 public-boundary slice |
| Orchestration observability | `3.1.0` | Observability; Kernel/QRTX; Resource Manager; System API | `docs/reference/orchestration-observability-contract.md`; `docs/architecture/components/observability.md` | Prometheus/OpenTelemetry metric contract; System API public API contract marker metrics | `src/services/system-api/tests/test_observability_smoke.py`; `src/rust/crates/eigen-kernel/tests/` | partial; Wave 1 public-boundary slice implemented | compatible for Wave 1 public-boundary slice |
| Intelligent runtime observability | `2.1.0` | Observability; scheduler; policy engine; driver-manager | `docs/reference/intelligent-runtime-observability-contract.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `scripts/ci/check-phase9a-gates.sh`; planned Product 1.0 exporter conformance | documented | needs-alignment |
| Cluster runtime observability | `1.0.0` | Distributed runtime; Kernel/QRTX; Resource Manager | `docs/reference/cluster-runtime-observability-contract.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `scripts/ci/check-phase8b-gates.sh`; planned Product 1.0 exporter conformance | documented | needs-alignment |
| Benchmark observability | `1.0.0` | Benchmark service; Observability | `docs/reference/benchmark-observability-contract.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `scripts/ci/check-phase8c-gates.sh`; `scripts/ci/check-benchmark-reproducibility.sh` | partial | needs-alignment |
| Multi-device execution | `3.1.0` | Kernel/QRTX; Resource Manager; Driver Manager; QFS | `docs/reference/multi-device-execution-contract.md` | Internal protos planned for split/merge lifecycle; `proto/eigen/internal/v1/kernel_gateway.proto` target mapping | `src/rust/crates/resource-manager/tests/`; planned split/merge integration tests | documented | needs-alignment |
| Benchmark Run REST API | `1.0.0` | Benchmark service; System API gateway | `docs/reference/api/benchmark-run.md` | `contracts/product-1.0/public-rest.openapi.json` | `src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py`; `src/services/system-api/tests/test_public_error_conformance.py`; `src/services/system-api/tests/test_validation_errors.py` | partial | planned |
| Explain Backend Selection REST API | `1.0.0` | System API; intelligent runtime; Resource Manager | `docs/reference/api/explain-backend-selection.md` | `contracts/product-1.0/public-rest.openapi.json` | `src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py`; `src/services/system-api/tests/test_explain_execution_contract.py` | partial | planned |
| Public REST API envelope | `1.0.0` | System API; API gateway | `docs/reference/api/rest-public.md` | `contracts/product-1.0/public-rest.openapi.json` | `src/services/system-api/tests/test_rest_parity_and_compatibility_matrix.py` | partial | planned |
| Authorization and security policy | `1.0.0` | Security & Isolation; System API; all services | `docs/reference/security/authz.md`; `docs/architecture/components/security-isolation.md` | Planned policy schema under `contracts/product-1.0/` | Planned authn/authz conformance in System API/security-module tests | documented | needs-alignment |
| Knowledge Base public API | `1.0.0` | Knowledge Base; System API | `docs/architecture/components/knowledge-base.md` | `proto/eigen/api/v1/knowledge_base_service.proto`; `src/services/system-api/src/system_api/knowledge_base.py` | `src/services/system-api/tests/test_knowledge_base_service.py`; `src/services/system-api/tests/test_knowledge_base_contract_fixture.py`; `src/services/benchmark-service/tests/test_run_lifecycle.py` | implemented | compatible |
| Component architecture boundary map | `1.0.0` Product target; architecture scope includes `1.3.0` phase contracts | Architecture governance; all component owners | `docs/architecture/contract-map.md`; `docs/architecture/overview.md`; `docs/architecture/components.md`; `docs/architecture/data-flow.md` | Not applicable | `python3 scripts/ci/check-docs-links.py`; `python3 scripts/ci/check-product-1-0-manifest.py` | documented | frozen-for-wave-0 |
| Compiler contract (`eigen.internal.v1` compiler slice) | `1.0.0` target | Compiler; System API; Kernel/QRTX | `docs/architecture/components/compiler.md`; `docs/reference/eigen-lang.md`; `docs/reference/formats/aqo.md` | `proto/eigen/internal/v1/compilation_service.proto`; compiler request/response types | `src/services/eigen-compiler/tests/test_conformance_suite.py`; language allowlist fixtures; AQO golden suite | partial | needs-alignment |
| Compiler artifact persistence handoff | `1.0.0` target | Compiler; QFS; Kernel/QRTX | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | QFS artifact paths and metadata records | `src/rust/crates/qfs/tests/`; compiler persistence tests | partial | needs-alignment |

---

## 3. Wave 0 notes

- Contract package versions are intentionally mixed because Product `1.0.0` integrates already-versioned contract families rather than renumbering every contract to `1.0.0`.
- `planned` proto/schema entries are acceptable in Wave 0 only when the manifest also records an owner and a conformance-test plan.
- Wave 1+ implementation commits must convert planned mappings into concrete files as contract slices are implemented.

## 4. Wave 3 concrete implementation slices

### 4.1 Compiler-to-QFS artifact slice

- **Proto/schema anchor:** `docs/reference/formats/qfs-layout.md`
- **Runtime implementation:** `src/rust/crates/qfs/src/local_circuit_fs.rs`
- **Coverage:** canonical `compiled/` artifact names, immutable write behavior, compiler metadata, lineage, integrity hashes, optional diagnostics sidecar
- **Conformance evidence:** compiled-artifact round-trip, missing-sidecar, and duplicate-write tests

### 4.2 Compiler contract slice

- **Proto/schema anchor:** `docs/architecture/components/compiler.md`
- **Runtime implementation:** `src/services/eigen-compiler`
- **Coverage:** AQO persistence handoff, metadata handoff, sidecar authoritative/advisory boundary
- **Conformance evidence:** compiler-to-QFS integration tests

### 4.2 Compiler request shaping slice

- **Proto/schema anchor:** `proto/eigen/internal/v1/compilation_service.proto`
- **Runtime implementation:** `src/services/eigen-compiler`
- **Coverage:** canonical request metadata, source precedence, deterministic request digest, option canonicalization, JobSpec-to-compiler input mapping
- **Conformance evidence:** compiler request mapping tests and deterministic digest fixtures

### 4.3 Compiler safety slice

- **Proto/schema anchor:** compiler safety rules in `docs/reference/eigen-lang.md` and `docs/architecture/components/compiler.md`
- **Runtime implementation:** `src/services/eigen-compiler`
- **Coverage:** internal request validation, forbidden construct rejection, unsupported target rejection, missing source-reference handling
- **Conformance evidence:** parser/validator fixtures and canonical error tests

### 4.4 Wave 3 documentation sync artifacts

- **Compatibility report:** `docs/development/wave-3/product-1.0-wave-3-compatibility-report.md`
- **Exit evidence:** `docs/development/wave-3/product-1.0-wave-3-exit-evidence-bundle.md`
- **Release readiness:** `docs/development/wave-3/product-1.0-wave-3-release-readiness-checklist.md`
- **Governance review:** `docs/development/wave-3/product-1.0-wave-3-rfc-adr-gap-analysis.md`
- **Coverage:** closure-level mapping for W3-06/W3-07/W3-08, with the parent plan, inventory, evidence bundle, and handoff notes synchronized to the compiler/AQO/QFS slices

## 5. Wave 2 concrete implementation slices

### 5.1 Kernel/QRTX orchestration slice

- **Proto/schema anchor:** `proto/eigen/internal/v1/kernel_gateway.proto`
- **Runtime implementation:** `src/rust/crates/eigen-kernel/src/rpc.rs`
- **Coverage:** deterministic orchestration DAG, stable stage IDs, cancellation/deadline propagation, bounded retry governance, and trace-aware terminalization
- **Conformance evidence:** embedded KernelGateway unit tests in `src/rust/crates/eigen-kernel/src/rpc.rs`

### 5.2 Orchestration observability slice

- **Proto/schema anchor:** orchestration contract marker and bounded metric families in `docs/reference/orchestration-observability-contract.md`
- **Runtime implementation:** `monitoring/metrics/prometheus/exporter.py`
- **Conformance evidence:** `monitoring/metrics/tests/test_stage_observability.py`
- **Coverage:** contract marker emission, bounded-label Prometheus output, and trace/request continuity audit requirements

### 5.3 Wave 2 governance artifacts

- **Compatibility report:** `docs/development/wave-2/product-1.0-wave-2-compatibility-report.md`
- **Release readiness:** `docs/development/wave-2/product-1.0-wave-2-release-readiness-checklist.md`
- **Exit evidence:** `docs/development/wave-2/product-1.0-wave-2-exit-evidence-bundle.md`
- **Gap analysis:** `docs/development/wave-2/product-1.0-wave-2-rfc-adr-gap-analysis.md`

These slices are the concrete mappings the Wave 2 closure record refers to. They do not rename the broader contract families; they document the implemented Kernel/QRTX enforcement points and conformance locations.

### 5.4 Wave 3 concrete implementation slices

- **Compiler safety slice:** Eigen-Lang allowlist, forbidden constructs, deterministic diagnostics
- **Compiler request slice:** JobSpec-to-compiler mapping, request metadata, canonical digests
- **AQO slice:** canonical emission, schema validation, reproducible hashes
- **QFS handoff slice:** compiler artifact persistence through QFS L3 with lineage and integrity metadata
- **Observability slice:** compiler contract marker metrics, bounded labels, trace continuity
