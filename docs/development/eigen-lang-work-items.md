# Eigen‑Lang (MVP) — work items

## Contract artifacts
- [ ] RFC 0012 accepted
- [ ] Complete reference docs: syntax/semantics/allowlist/mapping/versioning/conformance

## Compiler frontend
- [ ] AST parse + limits (bytes/nodes/depth)
- [ ] Import validator (only eigen_lang)
- [ ] Call resolver (only eigen_lang stdlib symbols)
- [ ] Allowlist enforcement + clear diagnostics
- [ ] Deterministic AQO JSON emitter

## CI
- [ ] Run conformance suite on every PR
- [ ] Golden changes require explicit approval

## Tooling
- [ ] CLI packaging: sha256 + entrypoint + job.yaml merge rules
