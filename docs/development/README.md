# Development

This section documents local quality checks, delivery controls, and MVP readiness criteria.

## Run CI checks locally

The GitHub CI workflow (`.github/workflows/ci.yml`) validates:

1. Rust workspace build + tests.
2. Python components install + tests.
3. Protobuf contract checks (`buf lint` + `buf breaking`).

From repository root:

```bash
# 1) Rust workspace
cd src/rust
cargo build --workspace --locked
cargo test --workspace --locked
cd ../..

# 2) Python components
python3.12 -m pip install -e src/services/system-api[dev]
python3.12 -m pip install -e src/services/driver-manager[dev]
python3.12 -m pip install -e src/services/eigen-compiler

pytest src/services/system-api/tests
pytest src/services/driver-manager/tests
python3.12 -m eigen_compiler.main

# 3) Protobuf contract checks
cd proto
buf lint
buf breaking --against '../.git#branch=main'
```

## Note

- `buf breaking` compares against local branch `main`.
- If `main` is missing locally:

```bash
git fetch origin main:main
```

- CI uses full git history (`fetch-depth: 0`) so breaking checks can compare branch state.

## MVP phase tracking

- MVP-2 RFC package (kickoff): [`../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md`](../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md), [`../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md`](../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md), [`../../rfcs/0015-mvp2-conformance-and-ci-gates.md`](../../rfcs/0015-mvp2-conformance-and-ci-gates.md)
- MVP-2 tracking issue draft: [`mvp-2-tracking-issue.md`](mvp-2-tracking-issue.md)
- ADR decisions for MVP baseline and MVP-2: [`../adr/README.md`](../adr/README.md)
- MVP-2 RFC package (kickoff): [`../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md`](../../rfcs/0013-mvp2-jobspec-parser-submit-contract.md), [`../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md`](../../rfcs/0014-mvp2-eigen-lang-ast-safety-deterministic-aqo.md), [`../../rfcs/0015-mvp2-conformance-and-ci-gates.md`](../../rfcs/0015-mvp2-conformance-and-ci-gates.md)


## Related files

- MVP DoD: [`mvp-definition-of-done.md`](mvp-definition-of-done.md)
- Contract freeze checklist: [`mvp-contract-freeze-checklist.md`](mvp-contract-freeze-checklist.md)
- Repo layout: [`repo-layout.md`](repo-layout.md)
- Eigen-Lang work queue: [`eigen-lang-work-items.md`](eigen-lang-work-items.md)
