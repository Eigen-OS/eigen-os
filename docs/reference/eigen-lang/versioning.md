# Eigen‑Lang versioning & compatibility (v0.x policy)

Eigen‑Lang is not stable in v0.x, but we want predictable evolution.

## Version identifiers
- Language spec version: `eigen-lang-spec: 0.1`

## Compatibility promises (MVP)
- Patch (0.1.x): bugfixes, validations, performance; no intentional breaking changes.
- Minor (0.2+): breaking allowed with migration notes; compatibility mode if feasible.

## Change process
User-visible changes require:
1) RFC (proposal + rationale) — similar to PEP/RFC processes.
2) Updated reference docs under `docs/reference/eigen-lang/`.
3) Conformance suite updates.
