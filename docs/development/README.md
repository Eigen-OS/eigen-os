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

- MVP-1 closeout summary and audit: [`mvp-dod-compliance-audit-2026-04-24.md`](mvp-dod-compliance-audit-2026-04-24.md)
- MVP-2 implementation plan (current): [`mvp-2-compilation-pipeline.md`](mvp-2-compilation-pipeline.md)
- ADR decisions for MVP baseline and MVP-2: [`../adr/README.md`](../adr/README.md)

## MVP phase tracking

- MVP-1 closeout summary and audit: [`mvp-dod-compliance-audit-2026-04-24.md`](mvp-dod-compliance-audit-2026-04-24.md)
- MVP-2 implementation plan (current): [`mvp-2-compilation-pipeline.md`](mvp-2-compilation-pipeline.md)

## Related files

- MVP DoD: [`mvp-definition-of-done.md`](mvp-definition-of-done.md)
- Contract freeze checklist: [`mvp-contract-freeze-checklist.md`](mvp-contract-freeze-checklist.md)
- Repo layout: [`repo-layout.md`](repo-layout.md)
