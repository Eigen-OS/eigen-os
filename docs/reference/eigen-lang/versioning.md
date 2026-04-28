# Eigen‑Lang versioning & compatibility (v0.x policy)

Eigen‑Lang is not stable in v0.x, but we want predictable evolution.

## Version identifiers
- Language spec version: `eigen-lang-spec: 0.1`

## Compatibility promises (MVP)
- Patch (0.1.x): bugfixes, validations, performance; no intentional breaking changes.
- Minor (0.2+): breaking allowed with migration notes; compatibility mode if feasible.

## Distributed metadata contract markers (Phase-5)

Distributed compile metadata and AQO topology hints are explicitly versioned:

- `metadata.distributed.execution_metadata_version`
- `metadata.distributed.topology_hints_version`
- `aqo.distributed_execution.version`
- `aqo.distributed_execution.hints.version`

SemVer rules for these distributed artifacts:

- `MAJOR`: incompatible changes to distributed target semantics/lineage expectations.
- `MINOR`: additive optional fields or new hint keys.
- `PATCH`: bug fixes only; no public distributed semantics changes.

## Change process
User-visible changes require:
1) RFC (proposal + rationale) — similar to PEP/RFC processes.
2) Updated reference docs under `docs/reference/eigen-lang/`.
3) Conformance suite updates.
