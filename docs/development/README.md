# Development

This section documents local quality checks and ongoing post-MVP planning.

## Run CI checks locally

The GitHub CI workflow (`.github/workflows/ci.yml`) validates:

1. Parser conformance (`tests/test_jobspec_parser.py`).
2. Compiler conformance (`tests/test_conformance_suite.py`).
3. CLI conformance (`cargo test -p cli`).
4. Green-to-Green smoke (`submit -> watch -> results` on `sim:local` + trace/metrics checks).
5. Python component test matrix.
6. Golden fixture review gate (label required when fixtures change).
7. Protobuf contract checks (`buf lint` + `buf breaking`).
8. PR versioning/migration gate for contract changes.
9. Docs tutorial smoke checks for canonical onboarding tutorials.

From repository root:

```bash
# 1) Parser conformance
python3.12 -m pip install -e src/services/system-api[dev]
pytest src/services/system-api/tests/test_jobspec_parser.py

# 2) Compiler conformance
python3.12 -m pip install -e src/services/eigen-compiler grpcio grpcio-tools grpcio-status googleapis-common-protos pytest
pytest src/services/eigen-compiler/tests/test_conformance_suite.py

# 3) CLI conformance
cd src/rust
cargo test -p cli --locked
cd ../..

# 4) Green-to-Green smoke (sim:local + metrics)
pytest src/services/system-api/tests/test_e2e_smoke_submit_watch_results.py
pytest src/services/system-api/tests/test_observability_smoke.py
cd src/rust
cargo test -p eigen-kernel integration_propagates_traceparent_to_compiler_and_driver --locked
cargo test -p eigen-kernel integration_vqe_loop_persists_metrics_and_results_metadata --locked
cd ../..

# 5) Python components
python3.12 -m pip install -e src/services/driver-manager[dev]
pytest src/services/system-api/tests
pytest src/services/driver-manager/tests
python3.12 -m eigen_compiler.main

# 6) Protobuf contract checks
cd proto
buf lint
buf breaking --against '../.git#branch=main'
```

## Tooling baseline command

Use one command for the default formatter/lint/unit-test baseline:

```bash
scripts/dev/run-tooling-baseline.sh
```

Minimal workflow:

- `scripts/dev/run-tooling-baseline.sh`

Full workflow:

- `scripts/dev/run-tooling-baseline.sh`
- `scripts/test/run-integration-tests.sh`
- `scripts/test/run-contract-compatibility-suite.sh`
- `scripts/ci/check-contract-drift.py`

## Required gates for `main`

Configure branch protection so the following CI jobs are **Required**:

- `Parser conformance (JobSpec fixtures)`
- `Compiler conformance (golden + negative)`
- `CLI conformance (submit envelope + parser)`
- `Green-to-Green smoke (sim:local + trace/metrics)`
- `Golden fixture review gate`
- `Protobuf lint + breaking checks`
- `Migration notes gate`
- `Docs tutorial smoke checks`

For fixture updates (`src/services/eigen-compiler/tests/golden/**`, `src/services/system-api/tests/fixtures/jobspec/**`, `src/services/system-api/tests/fixtures/runtime/**`, `src/rust/apps/cli/tests/fixtures/**`):

1. Run `python3 scripts/ci/update-golden-fixtures.py`.
2. Commit regenerated fixture files.
3. Add PR label `golden-fixtures-approved` (maintainer action).
4. Ensure CODEOWNERS review is enabled in branch protection.

## Note

- `buf breaking` compares against local branch `main`.
- If `main` is missing locally:

```bash
git fetch origin main:main
```

- CI uses full git history (`fetch-depth: 0`) so breaking checks can compare branch state.

## Post-MVP planning

- Post-MVP open-source roadmap: [`post-mvp-open-source-roadmap.md`](post-mvp-open-source-roadmap.md)
- Phase 1 runtime plan (completed): [`phase-1-production-runtime.md`](phase-1-production-runtime.md)
- Phase 2 orchestration plan: [`phase-2-orchestration-layer.md`](phase-2-orchestration-layer.md)
- Phase 2 issue pack: [`phase-2-issue-pack.md`](phase-2-issue-pack.md)
- Phase 2 release readiness checklist: [`phase-2-release-readiness-checklist.md`](phase-2-release-readiness-checklist.md)
- Phase 2 compatibility report: [`phase-2-compatibility-report.md`](phase-2-compatibility-report.md)
- Phase 2 migration notes: [`phase-2-migration-notes.md`](phase-2-migration-notes.md)
- Phase 3 benchmarking plan: [`phase-3-benchmarking-platform.md`](phase-3-benchmarking-platform.md)
- Phase 3 issue pack: [`phase-3-issue-pack.md`](phase-3-issue-pack.md)
- Phase 3 RFC/ADR gap analysis: [`phase-3-rfc-adr-gap-analysis.md`](phase-3-rfc-adr-gap-analysis.md)
- Phase 3 release readiness checklist: [`phase-3-release-readiness-checklist.md`](phase-3-release-readiness-checklist.md)
- Phase 3 compatibility report: [`phase-3-compatibility-report.md`](phase-3-compatibility-report.md)
- Phase 4 intelligent runtime plan: [`phase-4-intelligent-runtime.md`](phase-4-intelligent-runtime.md)
- Phase 4 issue pack: [`phase-4-issue-pack.md`](phase-4-issue-pack.md)
- Phase 4 RFC/ADR gap analysis: [`phase-4-rfc-adr-gap-analysis.md`](phase-4-rfc-adr-gap-analysis.md)
- Phase 4 release readiness checklist: [`phase-4-release-readiness-checklist.md`](phase-4-release-readiness-checklist.md)
- Phase 4 compatibility report: [`phase-4-compatibility-report.md`](phase-4-compatibility-report.md)
- Phase 5 distributed execution plan: [`phase-5-distributed-execution.md`](phase-5-distributed-execution.md)
- Phase 5 issue pack: [`phase-5-issue-pack.md`](phase-5-issue-pack.md)
- Phase 5 RFC/ADR gap analysis: [`phase-5-rfc-adr-gap-analysis.md`](phase-5-rfc-adr-gap-analysis.md)
- Phase 5 release readiness checklist: [`phase-5-release-readiness-checklist.md`](phase-5-release-readiness-checklist.md)
- Phase 5 compatibility report: [`phase-5-compatibility-report.md`](phase-5-compatibility-report.md)
- Architecture decisions: [`../adr/README.md`](../adr/README.md)
- RFC package: [`../../rfcs/`](../../rfcs/)
- Phase 6 plugin ecosystem plan: [`phase-6-plugin-ecosystem.md`](phase-6-plugin-ecosystem.md)
- Phase 6 issue pack: [`phase-6-issue-pack.md`](phase-6-issue-pack.md)
- Phase 6 RFC/ADR gap analysis: [`phase-6-rfc-adr-gap-analysis.md`](phase-6-rfc-adr-gap-analysis.md)
- Phase 7 stability and developer experience plan: [`phase-7-stability-and-developer-experience.md`](phase-7-stability-and-developer-experience.md)
- Phase 7 issue pack: [`phase-7-issue-pack.md`](phase-7-issue-pack.md)
- Phase 7 RFC/ADR gap analysis: [`phase-7-rfc-adr-gap-analysis.md`](phase-7-rfc-adr-gap-analysis.md)
- Phase 7 release readiness checklist: [`phase-7-release-readiness-checklist.md`](phase-7-release-readiness-checklist.md)
- Phase 7 compatibility report: [`phase-7-compatibility-report.md`](phase-7-compatibility-report.md)
- Phase 7 API & contract versioning policy (normative): [`../../rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`](../../rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md)
- Phase 7 DX & conformance baseline (normative): [`../../rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md`](../../rfcs/0033-phase7-developer-experience-and-conformance-toolchain-baseline-v1.md)
- Phase 8+ implementation roadmap for TZ v1.1.0: [`phase-8-implementation-roadmap-v1.1.0.md`](phase-8-implementation-roadmap-v1.1.0.md)

- Phase 8A execution plan: [`phase-8a-execution-plan.md`](phase-8a-execution-plan.md)
- Phase 8A issue pack: [`phase-8a-issue-pack.md`](phase-8a-issue-pack.md)
- Phase 8A RFC/ADR gap analysis: [`phase-8a-rfc-adr-gap-analysis.md`](phase-8a-rfc-adr-gap-analysis.md)
- Phase 8A release readiness checklist: [`phase-8a-release-readiness-checklist.md`](phase-8a-release-readiness-checklist.md)
- Phase 8A compatibility report: [`phase-8a-compatibility-report.md`](phase-8a-compatibility-report.md)
- Phase 8B execution plan: [`phase-8b/phase-8b-execution-plan.md`](phase-8b/phase-8b-execution-plan.md)
- Phase 8B issue pack: [`phase-8b/phase-8b-issue-pack.md`](phase-8b/phase-8b-issue-pack.md)
- Phase 8B RFC/ADR gap analysis: [`phase-8b/phase-8b-rfc-adr-gap-analysis.md`](phase-8b/phase-8b-rfc-adr-gap-analysis.md)
- Phase 8B release readiness checklist: [`phase-8b/phase-8b-release-readiness-checklist.md`](phase-8b/phase-8b-release-readiness-checklist.md)
- Phase 8B compatibility report: [`phase-8b/phase-8b-compatibility-report.md`](phase-8b/phase-8b-compatibility-report.md)
- Phase 8B exit evidence bundle: [`phase-8b/phase-8b-exit-evidence-bundle.md`](phase-8b/phase-8b-exit-evidence-bundle.md)
- Phase 8B RFC 0038: [`../../rfcs/0038-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md`](../../rfcs/0038-phase8b-qrtx-scheduling-and-lifecycle-hardening-contract-v1.md)
- Phase 8B RFC 0039: [`../../rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md`](../../rfcs/0039-phase8b-qfs-l2-l3-data-fabric-hardening-contract-v1.md)
- Phase 8B RFC 0040: [`../../rfcs/0040-phase8b-runtime-data-observability-and-slo-gates-v1.md`](../../rfcs/0040-phase8b-runtime-data-observability-and-slo-gates-v1.md)
- Phase 8C execution plan: [`phase-8c/phase-8c-execution-plan.md`](phase-8c/phase-8c-execution-plan.md)
- Phase 8C issue pack: [`phase-8c/phase-8c-issue-pack.md`](phase-8c/phase-8c-issue-pack.md)
- Phase 8C RFC/ADR gap analysis: [`phase-8c/phase-8c-rfc-adr-gap-analysis.md`](phase-8c/phase-8c-rfc-adr-gap-analysis.md)
- Phase 8C release readiness checklist: [`phase-8c/phase-8c-release-readiness-checklist.md`](phase-8c/phase-8c-release-readiness-checklist.md)
- Phase 8C compatibility report: [`phase-8c/phase-8c-compatibility-report.md`](phase-8c/phase-8c-compatibility-report.md)
- Phase 8C exit evidence bundle: [`phase-8c/phase-8c-exit-evidence-bundle.md`](phase-8c/phase-8c-exit-evidence-bundle.md)

## Related files

- Repo layout: [`repo-layout.md`](repo-layout.md)
- Eigen-Lang work queue: [`eigen-lang-work-items.md`](eigen-lang-work-items.md)
- Branching policy: [`BRANCHING.md`](BRANCHING.md)
