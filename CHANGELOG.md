# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning Policy (SemVer)

Eigen OS uses `MAJOR.MINOR.PATCH`:

- **MAJOR**: incompatible API/protocol or behavior changes
- **MINOR**: backward-compatible functionality additions
- **PATCH**: backward-compatible bug fixes and documentation-only corrections

Before `1.0.0`, breaking changes may occur in minor versions. After `1.0.0`, breaking changes require a MAJOR version increment.

## [Unreleased]

### Added

- Phase-8B P8B-01 QRTX DAG resolver + lifecycle idempotency hardening (`system-api` package `0.5.1`) with deterministic DAG reason codes (`DAG_RESOLVE_OK`, `DAG_UNKNOWN_NODE`, `DAG_SELF_DEPENDENCY`, `DAG_CYCLE_DETECTED`), replay-safe lifecycle signal handling for cancel/retry sequencing, and fixture tests for repeated/out-of-order control signals.
- Phase-7 P7-06 RFC package and ADR synchronization closure (`governance-docs` package `0.11.0`) with RFC 0032/0033 accepted status alignment, new ADR 0018/0019 records, synchronized RFC/development pointers, and published Phase-7 readiness + compatibility reports.
- Phase-7 P7-05 tooling baseline integration (`cli` in Rust workspace `0.17.0`) with single-command formatter/linter/unit-test workflow (`scripts/dev/run-tooling-baseline.sh`), CI lint entrypoint (`scripts/ci/lint.sh`), and richer plugin scaffold templates (`README.md`, `src/lib.rs`, `tests/manifest_contract.rs`) that validate by default.
- Phase-6 P6-07 SRE pack for plugin health/trust/sandbox visibility (`runtime-observability` assets `0.3.0`) with stable `eigen_plugin_*` metrics contract (`1.0.0`), plugin runtime Grafana dashboard, Prometheus failure/SLO/trust/sandbox alerts, and deterministic triage + rollback runbook.
- Phase-6 P6-06 GA plugin type implementation pack (`cli` in Rust workspace `0.15.0`) with fixture-backed contract tests for `driver`/`compiler_backend`/`optimizer`, explicit rejection of `scheduler` plugin manifests in Phase-6, and CLI help diagnostics that pin the fixed GA plugin type set.
- Phase-6 P6-05 Sigstore/Cosign trust gate (`cli` in Rust workspace `0.14.0`) with default fail-closed unsigned-plugin rejection, keyless-public Fulcio identity + Rekor evidence enforcement, and private/air-gapped trust-profile support via explicit trust-root references.
- Phase-6 P6-04 plugin compatibility matrix and load-time gate (`cli` in Rust workspace `0.13.0`) with deterministic core/plugin-api/eigen-lang evaluation, explicit remediation diagnostics for unsupported tuples, and manifest contract extension requiring `eigen_lang_version` plus `2.0.0` plugin API/schema markers.
- Phase-6 P6-02 plugin discovery/registration/activation lifecycle (`cli` in Rust workspace `0.12.0`) with deterministic activation ordering, fail-closed conflict diagnostics, explicit lifecycle states (`DISCOVERED -> REGISTERED -> VALIDATED -> ACTIVE/ERROR`), and activation command surface (`eigen plugin activate`).
- Phase-5 P5-09 ADR synchronization and release meta package (`governance-docs` package `0.10.1`) with implemented RFC status updates for RFC 0026/0027/0028, synchronized ADR set (ADR 0014/0015/0016), and published Phase-5 release readiness + compatibility docs.
- README information architecture refresh for Phase-5 closure: clearer audience/value/status sections, updated milestone matrix through Phase-5, and direct links to closure artifacts.
- Phase-5 P5-08 RFC package for distributed contracts accepted and indexed (`governance-docs` package `0.10.0`) covering RFC 0026/0027/0028 with explicit accepted statuses, compatibility + test-plan sections, and synchronized roadmap/development doc links.
- Phase-5 P5-07 determinism and replay gate for distributed scheduling (`resource-manager` package `0.10.1`) with assignment + lease + retry replay fixture coverage, deterministic lease-expiry sweep ordering, drift-path diagnostics, and CI gating for distributed scheduling artifact regressions.
- Phase-5 P5-06 SRE pack for cluster health and queue reliability (`runtime-observability` assets `0.2.0`) with stable `eigen_cluster_*` metrics contract (`1.0.0`), control-plane -> queue -> worker Grafana dashboard, Prometheus reliability alerts, and deterministic triage/rollback runbook.
- Phase-5 P5-05 Eigen-Lang distributed execution metadata + topology hints (`eigen-compiler` package `0.4.0`) with deterministic distributed target validation, explicit distributed metadata version markers (`1.0.0`), AQO distributed execution envelope emission, and conformance fixtures for compatibility protection.
- Phase-5 P5-03 pluggable distributed queue layer and delivery semantics v1 (`resource-manager` package `0.10.0`) with provider-neutral queue adapter contract (`enqueue`/`lease`/`ack`/`requeue`), deterministic lease-expiration redelivery, explicit dead-letter records, and compatibility fixtures for queue lease/dead-letter version markers.
- Phase-5 P5-02 worker node service and remote execution contract (`resource-manager` package `0.9.0`) with deterministic worker lifecycle API (`start`/`heartbeat`/`complete`/`cancel`), runtime artifact materialization metadata contract, timeout transitions, and idempotent duplicate-delivery handling.
- Phase-5 P5-01 cluster runtime control-plane core (`resource-manager` package `0.8.0`) with deterministic `--cluster` bootstrap discovery artifact, worker registration/capability handshake DTOs, and assignment artifacts carrying explicit contract/version + lineage metadata.
- Phase-4 P4-09 ADR synchronization and release meta package (`governance-docs` package `0.9.0`) with implemented RFC status updates for RFC 0023/0024/0025, synchronized ADR set (ADR 0011/0012/0013), and published Phase-4 release readiness + compatibility docs.
- Phase-4 P4-08 RFC package for intelligent-runtime contracts accepted and indexed (`governance-docs` package `0.8.0`) covering RFC 0023/0024/0025 with explicit statuses, compatibility sections, and benchmark/test-plan sections.
- Phase-4 P4-07 deterministic replay quality gate (`resource-manager` package `0.7.0`) with recorded decision-replay fixtures for scoring/policy/explain artifacts, drift-detection diagnostics, and CI gate script for deterministic runtime regression blocking.
- Phase-4 P4-06 intelligent runtime observability pack (`runtime-observability` assets `0.1.0`) with stable `eigen_runtime_*` metrics contract (`1.0.0`), decision-flow dashboard, Prometheus alerts, and triage/rollback runbook.
- Phase-4 P4-02 scheduling policy engine and policy bundles (`resource-manager` package `0.5.0`) with versioned `PolicyBundle` schema (`1.0.0`), deterministic precedence-based resolution, and safe fallback artifacts for missing/invalid policy inputs.
- Phase-4 P4-05 Eigen-Lang runtime-intelligence compile hints/diagnostics (`cli` in Rust workspace `0.6.0`) with deterministic unsupported-target/policy-conflict diagnostics, explicit hint metadata versions, and explainability-linked execution annotations in AQO metadata.
- Phase-3 P3-08 reproducibility and determinism quality gate (`benchmark-service` package `0.7.0`) with versioned reproducibility policy thresholds (`1.0.0`), deterministic snapshot consistency checks, bounded metric variance checks, and CI drift diagnostics.
- Phase-3 P3-07 benchmark observability pack (`benchmark-service` package `0.6.0`) with stable `eigen_bench_*` metrics contract (`1.0.0`), benchmark lifecycle dashboard, Prometheus alerts, and triage runbook.
- Phase-3 P3-06 CLI benchmark UX: `eigen benchmark run` and `eigen benchmark compare` (Rust CLI package `0.4.0`) with stable JSON/human output modes, explicit output version markers, and compatibility fixtures.
- Phase-3 P3-05 benchmark history API (`/benchmarks/history`) and trend queries (`benchmark-service` package `0.5.0`) with validated time-range filters, deterministic pagination, and stable ordering guarantees.
- Phase-3 P3-03 benchmark run API contract (`/benchmarks/run`) and compatibility fixtures (`benchmark-service` package `0.3.0`) with stable request/response/error envelopes and explicit artifact version markers.
- Phase-3 P3-01 benchmark-service core (`benchmark-service` package `0.1.0`) with run lifecycle state machine, idempotent start/retry semantics, and immutable deterministic snapshot metadata.
- RFC 0020 and ADR 0008 for benchmark run lifecycle contract governance.
- Phase-3 P3-09 RFC package for benchmark contracts (run lifecycle, dataset ingestion, compare/history) with explicit statuses and indexed docs links (RFC 0020/0021/0022).
- Phase-3 P3-02 QSBench-compatible dataset ingestion pipeline (`benchmark-service` package `0.2.0`) with manifest schema validation, checksum/provenance verification, and queryable dataset version catalog.

### Phase-6: SRE Pack for Plugin Health, Trust, and Sandbox Violations (P6-07)

- **Version impact:** MINOR (adds Phase-6 plugin observability contract/assets; observability asset pack advanced to `0.3.0`).
- **Compatibility:** Additive; plugin lifecycle/trust/sandbox semantics remain unchanged while `eigen_plugin_*` metrics are introduced with explicit marker `eigen_plugin_observability_contract_info{version="1.0.0"}`.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/plugin_runtime_sre_dashboard.json`, load `monitoring/metrics/prometheus/plugin-runtime-alerts.yaml`, and adopt `docs/howto/plugin-runtime-observability-runbook.md`.

### Phase-6: GA Plugin Type Implementation Pack (P6-06)

- **Version impact:** MINOR (new GA plugin type contract fixtures and diagnostics; Rust workspace advanced to `0.15.0`).
- **Compatibility:** Additive and policy-tightening for plugin manifest validation; Phase-6 GA plugin type surface remains fixed to `driver`, `compiler_backend`, `optimizer`, and `scheduler` declarations are rejected.
- **Migration notes:** Scheduler policy extensions must remain core-configurable (non-plugin) for Phase-6; plugin authors should keep `plugin_api_version` and `eigen_os_compatibility` markers and use only GA plugin types.

### Phase-6: Sigstore/Cosign Trust Gate (P6-05)

- **Version impact:** MINOR (new trust-policy enforcement capability; Rust workspace advanced to `0.14.0`).
- **Compatibility:** Additive for signed artifacts; default policy now rejects unsigned plugins and validates profile-specific trust evidence (`keyless-public`, `private`, `airgap`).
- **Migration notes:** Plugin manifests must include `signature_bundle_ref`; `keyless-public` artifacts must include `signer_identity` + `rekor_log_index`; `private`/`airgap` profiles must include `trust_root_ref`.

### Phase-6: Plugin Compatibility Matrix and Load-Time Gate (P6-04)

- **Version impact:** MAJOR for plugin contract (`plugin_api_version` and `manifest_schema_version` moved to `2.0.0`); MINOR for CLI package (`0.13.0`).
- **Compatibility:** Runtime now enforces deterministic compatibility across `(core_version, plugin_api_version, eigen_lang_version)` and blocks unsupported tuples with actionable remediation hints.
- **Migration notes:** Update plugin manifests to include `eigen_lang_version`, bump `plugin_api_version` to `2.0.0`, and keep `eigen_os_compatibility` aligned with supported core ranges.

### Phase-6: Plugin Discovery, Registration, and Activation Lifecycle (P6-02)

- **Version impact:** MINOR (new plugin activation lifecycle capability; Rust workspace advanced to `0.12.0`).
- **Compatibility:** Additive; existing plugin scaffold/validate/package flows remain supported while lifecycle activation orchestration is added.
- **Migration notes:** Plugin artifacts must keep `plugin_api_version` and `eigen_os_compatibility` markers; activation now fails closed for duplicate `(plugin_type, plugin_id)` collisions and API-version mismatches.

### Phase-3: RFC Package for Contracts (P3-09)

- **Version impact:** MINOR (governance package completion; benchmark-service package advanced to `0.8.0`).
- **Compatibility:** No payload or behavior break; stable contract baselines remain `1.0.0` for run (`state/snapshot`), dataset ingestion (`manifest/ingestion`), compare (`comparison/methodology`), and history (`history_contract_version`).
- **Migration notes:** No mandatory migration. Teams should pin and validate explicit version markers in run snapshots, ingestion artifacts, compare outputs, and history entries.

### Phase-5: RFC Package for Distributed Contracts (P5-08)

- **Version impact:** MINOR (governance package advancement; governance-docs package advanced to `0.10.0`).
- **Compatibility:** No contract payload break; distributed control-plane, queue/delivery, and topology/tracing artifacts remain at stable `1.0.0` baselines with explicit status transition from `Draft` to `Accepted`.
- **Migration notes:** No mandatory migration. Teams should pin explicit version markers in assignment, lease, and topology artifacts and track ADR synchronization when RFCs move to `Implemented`.

### Phase-5: Cluster Runtime Control Plane Core v1 (P5-01)

- **Version impact:** MINOR (new distributed control-plane artifact family; Rust workspace package advanced to `0.8.0`).
- **Compatibility:** Additive; existing single-node scheduler/scoring/policy contracts remain unchanged while new cluster control-plane and assignment lineage contracts are introduced at `1.0.0`.
- **Migration notes:** No mandatory migration for non-cluster deployments. Cluster consumers should pin `CLUSTER_CONTROL_PLANE_CONTRACT_VERSION` and `CLUSTER_ASSIGNMENT_LINEAGE_VERSION`, validate deterministic worker discovery ordering, and consume fallback metadata for node-loss reassignment diagnostics.

### Phase-5: Worker Node Service and Remote Execution Contract (P5-02)

- **Version impact:** MINOR (new worker-node distributed execution artifacts; Rust workspace package advanced to `0.9.0`).
- **Compatibility:** Additive; existing cluster assignment and scheduler contracts remain unchanged while new worker lifecycle and artifact materialization contracts are introduced at `1.0.0`.
- **Migration notes:** No mandatory migration. Distributed worker/queue integrations should pin `WORKER_NODE_EXECUTION_CONTRACT_VERSION` and `WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION`, treat duplicate `idempotency_key` deliveries as replay-safe, and honor deterministic timeout/cancellation terminalization.

### Phase-5: Pluggable Queue Layer and Delivery Semantics v1 (P5-03)

- **Version impact:** MINOR (new provider-neutral distributed queue contract surface; Rust workspace package advanced to `0.10.0`).
- **Compatibility:** Additive; existing scheduler, cluster control-plane assignment, and worker execution contracts remain unchanged while queue envelope (`1.0.0`), lease-event (`1.0.0`), and dead-letter (`1.0.0`) contracts are introduced.
- **Migration notes:** No mandatory migration for single-node flows. Distributed deployments should pin `DISTRIBUTED_QUEUE_CONTRACT_VERSION`, `QUEUE_LEASE_EVENT_VERSION`, and `QUEUE_DEAD_LETTER_CONTRACT_VERSION`, and ensure external providers enforce visibility timeout + dead-letter policy aligned with retry budgets.

### Phase-5: SRE Pack for Cluster Health and Queue Reliability (P5-06)

- **Version impact:** MINOR (adds distributed runtime observability contract/assets; observability asset pack advanced to `0.2.0`).
- **Compatibility:** Additive; existing `eigen_orch_*`, `eigen_bench_*`, and `eigen_runtime_*` contracts remain unchanged while `eigen_cluster_*` metrics are introduced with explicit marker `eigen_cluster_runtime_contract_info{version="1.0.0"}`.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/cluster_runtime_sre_dashboard.json`, load `monitoring/metrics/prometheus/cluster-runtime-alerts.yaml`, and adopt `docs/howto/cluster-runtime-observability-runbook.md`.

### Phase-5: Eigen-Lang Distributed Execution Metadata and Hints (P5-05)

- **Version impact:** MINOR (adds distributed compile metadata/hints and deterministic validation; `eigen-compiler` package advanced to `0.4.0`).
- **Compatibility:** Additive; existing AQO core fields remain unchanged while distributed metadata and AQO `distributed_execution` envelope fields are added under explicit `1.0.0` markers.
- **Migration notes:** No mandatory migration. Consumers should pin `metadata.distributed.execution_metadata_version`, `metadata.distributed.topology_hints_version`, and `aqo.distributed_execution.version` before relying on distributed-target/topology hint behavior.

### Phase-5: Determinism and Replay Gate for Distributed Scheduling (P5-07)

- **Version impact:** PATCH (distributed queue delivery determinism bug fix + replay quality gate expansion; Rust workspace package advanced to `0.10.1`).
- **Compatibility:** Backward compatible. Cluster control-plane (`1.0.0`) and lineage (`1.0.0`) contracts are unchanged; distributed queue envelope, lease event, and dead-letter artifact markers advance from `1.0.0` to `1.0.1` for deterministic retry-ordering fix coverage.
- **Migration notes:** No mandatory migration. CI should run `scripts/ci/check-runtime-decision-determinism.sh`; distributed consumers should pin `DISTRIBUTED_QUEUE_CONTRACT_VERSION`, `QUEUE_LEASE_EVENT_VERSION`, and `QUEUE_DEAD_LETTER_CONTRACT_VERSION` at `1.0.1` and validate replay drift diagnostics for assignment/lease/retry transitions.

### Phase-4: ADR Synchronization and Release Meta (P4-09)

- **Version impact:** MINOR (governance package completion; governance-docs package advanced to `0.9.0`).
- **Compatibility:** No contract breaking changes; Phase-4 stable contract baselines remain `1.0.0` for scoring, policy, and explainability surfaces with synchronized ADR records.
- **Migration notes:** No mandatory migration. Teams should pin explicit version markers in decision artifacts and explain responses and follow the published Phase-4 readiness/compatibility package.

### Phase-4: Observability Pack for Intelligent Runtime (P4-06)

- **Version impact:** MINOR (adds new intelligent-runtime observability contract/assets; observability asset pack advanced to `0.1.0`).
- **Compatibility:** Additive; existing `eigen_orch_*`, `eigen_stage_*`, and `eigen_bench_*` contracts remain unchanged while `eigen_runtime_*` metrics are introduced with explicit marker `eigen_runtime_contract_info{version="1.0.0"}`.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/intelligent_runtime_dashboard.json`, load `monitoring/metrics/prometheus/intelligent-runtime-alerts.yaml`, and adopt `docs/howto/intelligent-runtime-observability-runbook.md`.

### Phase-4: Scheduling Policy Engine and Policy Bundles (P4-02)

- **Version impact:** MINOR (new scheduling policy contract surface; Rust workspace package advanced to `0.5.0`).
- **Compatibility:** Additive; existing scheduler admission/dispatch and backend scoring contracts remain unchanged.
- **Migration notes:** No mandatory migration for default behavior. Policy adopters should pin `policy_bundle_version` and consume `SCHEDULING_POLICY_*` version markers in decision artifacts.

### Phase-4: Eigen-Lang Runtime-Intelligence Hints and Diagnostics (P4-05)

- **Version impact:** MINOR (new compile metadata and diagnostics; Rust workspace package advanced to `0.6.0`).
- **Compatibility:** Additive; existing AQO core fields remain unchanged while runtime-intelligence metadata/annotations are added and diagnostics are deterministic.
- **Migration notes:** No mandatory migration. Consumers should pin `metadata.runtime_intelligence_hints.version`, `metadata.runtime_intelligence_hints.diagnostics_version`, and `metadata.execution_annotations.version`, and treat `RUNTIME_INTELLIGENCE_DIAGNOSTIC` as compile-time validation feedback.

### Phase-4: Determinism and Reproducibility Gate for Runtime Decisions (P4-07)

- **Version impact:** MINOR (new deterministic replay fixture suite + CI drift gate; Rust workspace package advanced to `0.7.0`).
- **Compatibility:** Additive quality gate only; scoring contract (`1.0.0`), policy bundle schema (`1.0.0`), policy-resolution artifact (`1.0.0`), and explain response/request envelopes (`1.0.0`) remain unchanged.
- **Migration notes:** No API migration required. CI pipelines should execute `scripts/ci/check-runtime-decision-determinism.sh` (or `scripts/test/run-scheduler-contract-compatibility-suite.sh`) to block uncontrolled decision drift and surface field-level diagnostics.

### Phase-3: Reproducibility and Determinism Gate (P3-08)

- **Version impact:** MINOR (adds reproducibility policy contract and CI quality gate; benchmark-service package advanced to `0.7.0`).
- **Compatibility:** Additive; existing `/benchmarks/run`, `/benchmarks/compare`, `/benchmarks/history`, and dataset ingestion contracts remain unchanged.
- **Migration notes:** No mandatory migration. CI should execute `scripts/ci/check-benchmark-reproducibility.sh`; operators can consume gate diagnostics (`code`, `field`, `message`) for drift triage.

### Phase-3: Benchmark Metrics, Dashboards, and Alerts Pack (P3-07)

- **Version impact:** MINOR (adds benchmark observability contract surface and operator assets; benchmark-service package advanced to `0.6.0`).
- **Compatibility:** Additive; existing `/benchmarks/run` (`1.0.0`), `/benchmarks/compare` (`1.0.0`), `/benchmarks/history` (`1.0.0`), and dataset ingestion (`1.0.0`) contracts remain unchanged.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/benchmark_dashboard.json`, load `monitoring/metrics/prometheus/benchmark-alerts.yaml`, and adopt `docs/howto/benchmark-observability-runbook.md`.

### Phase-3: CLI UX run/compare (P3-06)

- **Version impact:** MINOR (adds benchmark CLI surface and stable JSON contracts; Rust CLI package advanced to `0.4.0`).
- **Compatibility:** Additive; existing CLI commands and benchmark service API contracts remain unchanged.
- **Migration notes:** No mandatory migration. Automation consuming benchmark CLI output should pin to `contract_version`/`snapshot_version`/`comparison_version` and prefer `--output json` artifacts.

### Phase-3: History API and Trend Queries (P3-05)

- **Version impact:** MINOR (adds `/benchmarks/history` contract surface and trend query aggregates; package version advanced to `0.5.0`).
- **Compatibility:** Additive; existing `/benchmarks/run` (`1.0.0`), `/benchmarks/compare` (`1.0.0`), and dataset ingestion contracts remain unchanged.
- **Migration notes:** No mandatory migration. Consumers can adopt deterministic cursor pagination (`page_token`) and rely on stable ordering contract `created_at DESC, run_id ASC`.

### Phase-3: Benchmark Service Core v1 (P3-01)

- **Version impact:** MINOR (new service capability + new stable lifecycle contract `1.0.0`).
- **Compatibility:** Additive; no breaking changes to existing runtime services/APIs.
- **Migration notes:** No migration required for existing clients.

## [0.3.0]

### Phase-3: Benchmark Run API Contract Tests (P3-03)

- **Version impact:** MINOR (new `/benchmarks/run` contract surface and conformance fixtures).
- **Compatibility:** Additive; no breaking changes to existing benchmark lifecycle (`1.0.0`) or dataset ingestion (`1.0.0`) contracts.
- **Migration notes:** No mandatory migration. API consumers should validate against the new documented required request fields (`idempotency_key`, `config`) and rely on explicit response version markers.

### Phase-3: Dataset Ingestion Pipeline (P3-02)

- **Version impact:** MINOR (adds new dataset ingestion + catalog capability and stable manifest schema contract `1.0.0`).
- **Compatibility:** Additive; existing benchmark run lifecycle contract `1.0.0` is unchanged.
- **Migration notes:** No mandatory migration. Producers must include `manifest.json` with required provenance/checksum fields for ingestion.

### Added

- Phase-7 P7-05 tooling baseline integration (`cli` in Rust workspace `0.17.0`) with single-command formatter/linter/unit-test workflow (`scripts/dev/run-tooling-baseline.sh`), CI lint entrypoint (`scripts/ci/lint.sh`), and richer plugin scaffold templates (`README.md`, `src/lib.rs`, `tests/manifest_contract.rs`) that validate by default.
- Phase-5 P5-09 ADR synchronization and release meta package (`governance-docs` package `0.10.1`) with implemented RFC status updates for RFC 0026/0027/0028, synchronized ADR set (ADR 0014/0015/0016), and published Phase-5 release readiness + compatibility docs.
- README information architecture refresh for Phase-5 closure: clearer audience/value/status sections, updated milestone matrix through Phase-5, and direct links to closure artifacts.
- Phase-2 orchestration documentation baseline: execution plan and a ready-to-copy GitHub issue pack for scheduler/device-aware/multi-device/batch workstreams.
- Phase-2 release readiness checklist with locked orchestration contract version matrix and signed compatibility/migration package.
- Phase-2 migration notes and release notes template with mandatory `Version impact`, `Compatibility`, and `Migration notes` sections.

### Changed

- Phase-1 is marked complete in roadmap and development planning docs with explicit closure date (**2026-04-27**).
- Product/service package versions advanced from `0.2.0` to `0.3.0` for Phase-2 release closure.

### Added

- Phase-7 P7-05 tooling baseline integration (`cli` in Rust workspace `0.17.0`) with single-command formatter/linter/unit-test workflow (`scripts/dev/run-tooling-baseline.sh`), CI lint entrypoint (`scripts/ci/lint.sh`), and richer plugin scaffold templates (`README.md`, `src/lib.rs`, `tests/manifest_contract.rs`) that validate by default.
- Phase-5 P5-09 ADR synchronization and release meta package (`governance-docs` package `0.10.1`) with implemented RFC status updates for RFC 0026/0027/0028, synchronized ADR set (ADR 0014/0015/0016), and published Phase-5 release readiness + compatibility docs.
- README information architecture refresh for Phase-5 closure: clearer audience/value/status sections, updated milestone matrix through Phase-5, and direct links to closure artifacts.
- Project health documentation baseline: `CONTRIBUTING.md`, `SECURITY.md`, and roadmap/project-health alignment.
- Phase-1 release readiness checklist with consolidated security/performance/docs/upgrade gates and locked contract version matrix.
- Contract compatibility runner script: `scripts/test/run-contract-compatibility-suite.sh`.
- Observability v2 per-job timeline persisted to QFS (`qfs_job_timeline`) with explicit timeline schema version (`2.0.0`) and trace correlation metadata (`trace_id`, `trace_ref`).

### Changed

- Documentation now explicitly freezes MVP public API contract version at `0.1`, while clarifying that protobuf `...v1` remains a package/namespace convention.
- Pull request template now requires `Version Impact`, `Affected Interfaces`, and `Migration Notes`.
- CI includes a dedicated Phase-1 contract compatibility suite job.
- AQO simulator driver now enforces mandatory top-level `version` field.
- System API job lifecycle stream now emits detailed stages (`QUEUED` → `COMPILED` → `DISPATCHED` → `RUNNING` → `COMPLETED`) with timestamped event history and trace-aware event messages

### Phase-2: Dispatch Explainability API/CLI

- **Version impact:** MINOR (new backward-compatible RPC + CLI command + docs).
- **Compatibility:** Existing `JobService` methods and reason codes remain intact; dispatch explainability is additive.
- **Migration notes:** No migration required. Clients may optionally call `GetDispatchRationale` and CLI `eigen explain <job_id>`.

### Phase-2: Multi-device Execution Contract (Split/Merge)

- **Version impact:** MINOR (adds a new split/merge contract artifact family and integration coverage).
- **Compatibility:** Existing scheduler admission/dispatch DTOs are unchanged; split/merge envelopes are additive and independently versioned (`2.0.0`).
- **Migration notes:** No mandatory migration. Consumers may start reading `SplitPlanManifest`, `PartialResultEnvelope`, `PartialFailureEnvelope`, and `MergeDecision` artifacts with explicit `version`, `parent_job_id`, and `shard_id` fields.

### Phase-2: Rebalancing and Preemption Safety Rules

- **Version impact:** MINOR (adds rebalance/preemption policy artifacts and idempotent requeue behavior with explicit version marker `2.2.0`).
- **Compatibility:** Existing admission/dispatch reason codes remain intact; new preemption reason codes and metrics are additive. Terminal/preempted status semantics are unchanged.
- **Migration notes:** No mandatory migration. Integrations can optionally consume `RebalancePlan`/`PreemptionDecision` and the new scheduler metrics (`rebalance_trigger_total`, `preemption_attempted_total`, `preempted_total`, `requeued_total`, `requeue_idempotent_hits_total`).

### Phase-2: Orchestration Observability Pack

- **Version impact:** MINOR (adds a new stable observability metric family, orchestrator dashboard, alerts, and runbook).
- **Compatibility:** Existing stage observability metrics remain unchanged; new `eigen_orch_*` metrics are additive and version-marked via `eigen_orch_contract_info{version="2.3.0"}`.
- **Migration notes:** No mandatory migration. Operators should import `monitoring/dashboards/orchestration_dashboard.json`, load `monitoring/metrics/prometheus/orchestrator-alerts.yaml`, and wire orchestrator scrape target (`127.0.0.1:9094`).
