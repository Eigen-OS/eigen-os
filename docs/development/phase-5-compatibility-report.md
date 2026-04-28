# Phase-5 Compatibility Report

- **Status:** Signed for Phase-5 release readiness.
- **Last updated:** 2026-04-28
- **Owner:** Distributed runtime maintainers
- **Release line:** `0.10.1`

## Contract version matrix

Version matrix is **locked** for the `0.10.1` release line.

| Contract surface | Current version | Compatibility notes |
| --- | --- | --- |
| Cluster control-plane contract | `1.0.0` | Assignment/lifecycle semantic changes require MAJOR bump. |
| Cluster assignment lineage schema | `1.0.0` | Removing required lineage fields requires MAJOR bump. |
| Distributed queue envelope contract | `1.0.1` | Delivery semantic changes (lease/ack/requeue) require MAJOR bump. |
| Queue lease event schema | `1.0.1` | Retry-ordering semantic changes require MAJOR bump. |
| Queue dead-letter schema | `1.0.1` | Required dead-letter field removals require MAJOR bump. |
| Distributed topology/tracing contract | `1.0.0` | Required lineage/trace semantic changes require MAJOR bump. |

## Compatibility suite evidence

- Cluster control-plane contract suite: `cargo test -p resource-manager cluster_control_plane_contract`
- Distributed queue contract suite: `cargo test -p resource-manager distributed_queue_contract`
- Distributed topology API suite: `pytest src/services/system-api/tests/test_distributed_topology_contract.py`
- Distributed scheduling determinism suite: `scripts/ci/check-runtime-decision-determinism.sh`
- Golden fixture review gate: `golden-fixtures-approved` label required when stable contract fixtures change.

## Versioning policy compliance

Phase-5 distributed contracts follow mandatory SemVer governance:

1. **MAJOR** for incompatible assignment, delivery, or topology/tracing semantic changes.
2. **MINOR** for backward-compatible optional distributed metadata fields.
3. **PATCH** for deterministic replay/order fixes with no public contract break.
4. Mandatory version markers in cluster/queue/topology artifacts.
5. Deprecation policy: required field removal only after one MINOR release with deprecation marker.

## Migration policy

Every Phase-5 contract-affecting PR must include:

1. **Version impact** (`MAJOR`/`MINOR`/`PATCH`/`NONE`)
2. **Compatibility** statement in the PR description
3. **Migration notes** (actionable steps or explicit `None`)

## Release readiness

Compatibility package and ADR synchronization package are signed. Phase-5 release gate can be marked **Ready**.
