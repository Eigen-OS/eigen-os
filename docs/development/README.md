# Development

## Run CI checks locally

The GitHub CI workflow (`.github/workflows/ci.yml`) enforces three gate groups:

1. Rust workspace build + tests.
2. Python package install + per-component unit checks.
3. Protobuf contract checks (`buf lint` + `buf breaking`).

Run the same checks locally from the repository root:

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

### Notes

- `buf breaking` compares your branch to `main`. If your local clone does not have `main`, fetch it first:

```bash
git fetch origin main:main
```
- The CI workflow fetches full git history (`fetch-depth: 0`) so the same `buf breaking` command works in pull requests.
