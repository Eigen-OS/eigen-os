# Product 1.0 Contract Inventory

**Status:** Wave 0 baseline inventory
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
| Public gRPC API (`eigen.api.v1`) | `1.0.0` target on namespace `v1` | System API; client SDKs/CLI | `docs/reference/api/grpc-public.md`; `docs/architecture/components/system-api.md` | `proto/eigen/api/v1/job_service.proto`; `proto/eigen/api/v1/device_service.proto`; `proto/eigen/api/v1/types.proto` | `src/services/system-api/tests/` (planned Product 1.0 expansion); `src/rust/apps/cli/tests/` (planned envelope conformance); `buf lint`; `buf breaking` | partial | needs-alignment |
| Internal gRPC API (`eigen.internal.v1`) | `1.0.0` target on namespace `v1` | Kernel/QRTX; compiler; driver-manager; optimizer | `docs/reference/api/grpc-internal.md`; `docs/architecture/components/qrtx.md` | `proto/eigen/internal/v1/kernel_gateway.proto`; `proto/eigen/internal/v1/compilation_service.proto`; `proto/eigen/internal/v1/driver_manager_service.proto`; `proto/eigen/internal/v1/optimizer_service.proto`; `proto/eigen/internal/v1/types.proto` | `src/rust/crates/eigen-kernel/tests/` (planned Product 1.0 expansion); `src/services/eigen-compiler/tests/`; `buf lint`; `buf breaking` | partial | needs-alignment |
| JobSpec | `1.0.0` | System API; CLI; Kernel/QRTX; packaging | `docs/reference/jobspec.md` | Planned JSON Schema under `specs/` or `contracts/product-1.0/`; public `SubmitJobRequest` mapping in `proto/eigen/api/v1/job_service.proto` | `src/services/system-api/tests/test_jobspec_parser.py`; `src/rust/apps/cli/tests/fixtures/jobspec-valid-minimal.yaml` | partial | needs-alignment |
| Eigen-Lang | `1.0.0` | Compiler / Eigen-DPDA | `docs/reference/eigen-lang.md`; `docs/architecture/components/compiler.md` | Planned grammar/schema artifacts; compiler service proto in `proto/eigen/internal/v1/compilation_service.proto` | `src/services/eigen-compiler/tests/test_conformance_suite.py` | partial | needs-alignment |
| AQO format | `1.0.0` | Compiler; optimizer; QFS; Kernel/QRTX | `docs/reference/formats/aqo.md` | Planned AQO schema under `specs/` or `contracts/product-1.0/`; `proto/eigen/internal/v1/types.proto` circuit payload mapping | `src/services/eigen-compiler/tests/test_conformance_suite.py` (planned AQO golden expansion) | documented | needs-alignment |
| QFS layout (CircuitFS) | `1.0.0` | QFS; Kernel/QRTX; System API facades | `docs/reference/formats/qfs-layout.md`; `docs/architecture/components/qfs.md` | Planned storage manifest schema under `contracts/product-1.0/` | `src/rust/crates/qfs/tests/` (planned Product 1.0 layout conformance) | partial | needs-alignment |
| Canonical error model | `1.0.0` | All public/internal services | `docs/reference/error-model.md` | Planned structured error detail schema; gRPC status details in public/internal protos | `src/services/system-api/tests/` (planned canonical error expansion); `src/services/eigen-compiler/tests/`; `src/services/driver-manager/tests/` | documented | needs-alignment |
| Error mapping matrix | `1.0.0` | All public/internal services | `docs/reference/error-mapping.md` | Planned machine-readable error matrix under `contracts/product-1.0/` | `src/services/system-api/tests/` (planned mapping conformance); `src/rust/crates/eigen-kernel/tests/` | documented | needs-alignment |
| Orchestration observability | `3.1.0` | Observability; Kernel/QRTX; Resource Manager; System API | `docs/reference/orchestration-observability-contract.md`; `docs/architecture/components/observability.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `src/services/system-api/tests/test_observability_smoke.py`; `src/rust/crates/eigen-kernel/tests/` (planned metric marker conformance) | partial | needs-alignment |
| Intelligent runtime observability | `2.1.0` | Observability; scheduler; policy engine; driver-manager | `docs/reference/intelligent-runtime-observability-contract.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `scripts/ci/check-phase9a-gates.sh`; planned Product 1.0 exporter conformance | documented | needs-alignment |
| Cluster runtime observability | `1.0.0` | Distributed runtime; Kernel/QRTX; Resource Manager | `docs/reference/cluster-runtime-observability-contract.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `scripts/ci/check-phase8b-gates.sh`; planned Product 1.0 exporter conformance | documented | needs-alignment |
| Benchmark observability | `1.0.0` | Benchmark service; Observability | `docs/reference/benchmark-observability-contract.md` | Prometheus/OpenTelemetry metric contract; planned dashboard/alert fixtures | `scripts/ci/check-phase8c-gates.sh`; `scripts/ci/check-benchmark-reproducibility.sh` | partial | needs-alignment |
| Multi-device execution | `3.1.0` | Kernel/QRTX; Resource Manager; Driver Manager; QFS | `docs/reference/multi-device-execution-contract.md` | Internal protos planned for split/merge lifecycle; `proto/eigen/internal/v1/kernel_gateway.proto` target mapping | `src/rust/crates/resource-manager/tests/`; planned split/merge integration tests | documented | needs-alignment |
| Benchmark Run REST API | `1.0.0` | Benchmark service; System API gateway | `docs/reference/api/benchmark-run.md` | Planned OpenAPI/JSON Schema under `contracts/product-1.0/` | `scripts/ci/check-phase8c-gates.sh`; planned REST conformance | documented | planned |
| Explain Backend Selection REST API | `1.0.0` | System API; intelligent runtime; Resource Manager | `docs/reference/api/explain-backend-selection.md` | Planned OpenAPI/JSON Schema under `contracts/product-1.0/` | Planned explainability API conformance in System API / Resource Manager tests | documented | planned |
| Public REST API envelope | `1.0.0` | System API; API gateway | `docs/reference/api/rest-public.md` | Planned OpenAPI under `contracts/product-1.0/` | Planned REST mirror conformance | planned | planned |
| Authorization and security policy | `1.0.0` | Security & Isolation; System API; all services | `docs/reference/security/authz.md`; `docs/architecture/components/security-isolation.md` | Planned policy schema under `contracts/product-1.0/` | Planned authn/authz conformance in System API/security-module tests | documented | needs-alignment |
| Knowledge Base public API | `1.0.0` | Knowledge Base; System API | `docs/architecture/components/knowledge-base.md` | `proto/eigen/api/v1/knowledge_base_service.proto` | Planned KB API conformance tests | partial | planned |
| Component architecture boundary map | `1.0.0` Product target; architecture scope includes `1.3.0` phase contracts | Architecture governance; all component owners | `docs/architecture/contract-map.md`; `docs/architecture/overview.md`; `docs/architecture/components.md`; `docs/architecture/data-flow.md` | Not applicable | `python3 scripts/ci/check-docs-links.py`; `python3 scripts/ci/check-product-1-0-manifest.py` | documented | frozen-for-wave-0 |

---

## 3. Wave 0 notes

- Contract package versions are intentionally mixed because Product `1.0.0` integrates already-versioned contract families rather than renumbering every contract to `1.0.0`.
- `planned` proto/schema entries are acceptable in Wave 0 only when the manifest also records an owner and a conformance-test plan.
- Wave 1+ implementation commits must convert planned mappings into concrete files as contract slices are implemented.
