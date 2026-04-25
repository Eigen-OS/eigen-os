# Development

This section documents local quality checks, delivery controls, and MVP readiness criteria.

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

## Required gates for `main` (MVP-3)

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

## MVP phase tracking

- MVP-2 RFC package (implemented): [`../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md`](../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md), [`../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md`](../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md), [`../../rfcs/0015-mvp2-conformance-and-ci-gates.md`](../../rfcs/0015-mvp2-conformance-and-ci-gates.md)
- MVP-2 tracking closure: [`mvp-2-tracking-issue.md`](mvp-2-tracking-issue.md)
- MVP-3 execution/runtime plan: [`mvp-3-execution-and-results.md`](mvp-3-execution-and-results.md)
- MVP-3 RFC package (accepted): [`../../rfcs/0016-mvp3-kernel-driver-execution-contract.md`](../../rfcs/0016-mvp3-kernel-driver-execution-contract.md), [`../../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md`](../../rfcs/0017-mvp3-results-retrieval-and-cli-runtime-ux.md), [`../../rfcs/0018-mvp3-runtime-observability-and-release-gates.md`](../../rfcs/0018-mvp3-runtime-observability-and-release-gates.md)
- MVP-3 tracking issue (closed): [`mvp-3-tracking-issue.md`](mvp-3-tracking-issue.md)
- ADR decisions for MVP baseline through MVP-3: [`../adr/README.md`](../adr/README.md)

## Related files

- MVP DoD: [`mvp-definition-of-done.md`](mvp-definition-of-done.md)
- Contract freeze checklist: [`mvp-contract-freeze-checklist.md`](mvp-contract-freeze-checklist.md)
- Repo layout: [`repo-layout.md`](repo-layout.md)
- Eigen-Lang work queue: [`eigen-lang-work-items.md`](eigen-lang-work-items.md)
