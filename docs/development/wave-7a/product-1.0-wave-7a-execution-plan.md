# Product 1.0 Wave 7a Execution Plan

**Wave:** Product 1.0 Wave 7a — GNN Optimizer and intelligent runtime
**Status:** Ready for implementation planning
**Created:** 2026-06-12
**Parent plan:** `docs/development/product-1.0-contract-alignment-plan.md`
**Inventory:** `docs/development/product-1.0-contract-inventory.md`
**Version policy:** `docs/development/product-1.0-version-policy.md`
**Sources of truth:** `docs/architecture/**`, `docs/reference/**`

---

## 1. Goal

Wave 7a moves the optimizer and intelligent-runtime surfaces from fixture-backed coverage into the production execution path. The wave does not redefine the optimizer contract; it makes the already-frozen contract operational in the Kernel/QRTX → compiler → optimizer → driver path, with deterministic fallback, explainability, and release evidence.

The intended outcome is a production-safe optimization flow that remains reproducible when the optimizer is unavailable, confidence is low, or the model registry is not promotable. Wave 7a must keep the optimizer contract aligned with the inventory, the manifest, and the observable behavior described in the reference docs.

---

## 2. Normative source map

| Wave 7a area | Canonical source | Implementation surface | Primary evidence |
|---|---|---|---|
| Optimizer service contract | `docs/architecture/components/gnn-optimizer.md`; `docs/reference/api/grpc-internal.md` | `proto/eigen/internal/v1/optimizer_service.proto`; optimizer service server/client wiring | Optimizer conformance and integration tests |
| Compiler ↔ optimizer handoff | `docs/architecture/components/compiler.md`; `docs/architecture/components/neuro-symbolic-core.md`; `docs/reference/formats/aqo.md` | Compiler request/response adapter; Kernel/QRTX orchestration path | Handoff and replay fixture tests |
| Intelligent runtime observability | `docs/reference/intelligent-runtime-observability-contract.md`; `docs/architecture/components/observability.md` | Metrics exporter; dashboard fixtures; alert fixtures | Scrape tests; dashboard snapshot tests |
| Kernel/QRTX orchestration path | `docs/architecture/components/qrtx.md`; `docs/architecture/contract-map.md` | Kernel workflow and adapter hooks | Submit-to-optimize integration tests |
| Release evidence and compatibility | `docs/development/product-1.0-version-policy.md`; `docs/development/product-1.0-contract-inventory.md` | Compatibility report, readiness checklist, exit evidence bundle | Reviewable release package |

---

## 3. Wave 7a scope

### In scope

1. Implement optimizer service server and client wiring from Kernel/QRTX.
2. Define model registry and model version promotion policy.
3. Support deterministic fallback when the optimizer is unavailable or confidence is below threshold.
4. Emit optimization candidate traces:
   - objective,
   - score breakdown,
   - topology context,
   - model version,
   - confidence,
   - fallback reason.
5. Add quality regression gates using fixed fixtures.
6. Wire optimizer outputs into the compiler/driver execution path.
7. Add intelligent runtime observability marker metrics and dashboards.
8. Keep the optimizer contract synchronized with the inventory and manifest rows.

### Out of scope

- Redefining the frozen optimizer public/internal contract shape.
- Introducing new public API surfaces.
- Replacing the compiler contract or AQO format contract.
- Provider-specific driver policy changes beyond optimizer-driven selection data.
- New product release versioning rules.

---

## 4. Delivery sequence

| Step | Issue | Dependency | Outcome |
|---:|---|---|---|
| 1 | W7A-01 Optimizer service server/client wiring and Kernel/QRTX handoff | Wave 7 contract closure | Production-call path exists from Kernel/QRTX into optimizer service |
| 2 | W7A-02 Model registry and version promotion policy | W7A-01 | Promotable model selection is versioned and deterministic |
| 3 | W7A-03 Deterministic fallback and confidence thresholds | W7A-02 | Optimizer failure or low-confidence paths are explicit and reproducible |
| 4 | W7A-04 Optimization candidate traces, metrics, and dashboards | W7A-01 through W7A-03 | Candidate telemetry and operator visibility are present |
| 5 | W7A-05 Quality regression gates, compatibility report, and exit evidence | All W7a issues | Release package is complete and reviewable |

---

## 5. Contract decisions required before implementation

1. **Registry backend:** decide whether the first production registry is in-memory, file-backed, or durable service-backed.
2. **Promotion policy:** define how a model becomes promotable, including version selection, rollback, and quarantine behavior.
3. **Fallback threshold:** choose the minimum confidence and unavailability policy that trigger deterministic fallback.
4. **Trace payload boundaries:** decide which optimization fields are emitted in logs and traces versus retained only in artifacts.
5. **Release gating:** decide which quality regressions fail the wave and which are informational only.

---

## 6. Definition of done

Wave 7a is 100% complete when:

- the optimizer service is callable from the Kernel/QRTX execution path,
- model registry/version selection is deterministic and documented,
- fallback behavior is stable, explicit, and test-covered,
- optimization candidate telemetry is observable and bounded,
- dashboards and alerts exist for the intelligent-runtime surface,
- quality regression fixtures block release when they fail,
- the inventory and manifest remain synchronized with the implemented surfaces,
- the compatibility report, readiness checklist, and exit evidence bundle have no unresolved `TBD` entries.

---

## 7. Handoff to Wave 8

Wave 8 may start when Wave 7a evidence shows the optimizer path is production-safe and the emitted decision artifacts are stable enough to be consumed by the knowledge/learning layer without forcing another contract rewrite. At that point, the runtime decision record can be treated as a governed input rather than a fixture-only output.
