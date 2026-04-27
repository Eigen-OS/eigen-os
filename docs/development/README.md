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

## Required gates for `main`

Configure branch protection so the following CI jobs are **Required**:

- `Parser conformance (JobSpec fixtures)`
- `Compiler conformance (golden + negative)`
- `CLI conformance (submit envelope + parser)`
- `Green-to-Green smoke (sim:local + trace/metrics)`
- `Golden fixture review gate`
- `Protobuf lint + breaking checks`

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
- Architecture decisions: [`../adr/README.md`](../adr/README.md)
- RFC package: [`../../rfcs/`](../../rfcs/)

## Related files

- Repo layout: [`repo-layout.md`](repo-layout.md)
- Eigen-Lang work queue: [`eigen-lang-work-items.md`](eigen-lang-work-items.md)
- Branching policy: [`BRANCHING.md`](BRANCHING.md)
