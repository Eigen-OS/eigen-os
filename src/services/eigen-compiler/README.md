# Eigen Compiler (MVP)

MVP frontend security baseline:

- Parses Eigen-Lang source via Python AST (never executes user code).
- Rejects forbidden imports/calls (e.g. `os`, `subprocess`, `open`, `eval`).
- Enforces source and AST resource limits.

Environment configuration:

- `EIGEN_COMPILER_MAX_SOURCE_BYTES` (default: `262144`)
- `EIGEN_COMPILER_MAX_AST_NODES` (default: `50000`)
- `EIGEN_COMPILER_MAX_AST_DEPTH` (default: `200`)
