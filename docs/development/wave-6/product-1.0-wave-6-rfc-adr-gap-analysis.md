# Product 1.0 Wave 6 RFC / ADR Gap Analysis

**Wave:** Product 1.0 Wave 6 — Driver Manager and QDriver final contract  
**Status:** Planning baseline  
**Source of truth:** `docs/architecture/**`, `docs/reference/**`  
**Primary governance baseline:** `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`, `rfcs/0045-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`, `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`, `docs/adr/0031-phase8d-provider-driver-matrix-contract-and-tolerance-profiles.md`

---

## Summary

Wave 6 is already covered at the governance level by the accepted QDriver v1 and provider-matrix RFC/ADR pair. The remaining work is to turn that baseline into an opening package for the repo’s driver-manager implementation, conformance fixtures, and closure evidence.

No new governance decision is required to start the wave, but the docs package should keep the following gaps explicit:

1. the canonical reference for the final QDriver contract must be obvious in `docs/reference/`,
2. the current Driver Manager skeleton must be aligned to the accepted QDriver semantics,
3. provider matrix and tolerance policy artifacts must be treated as release evidence,
4. secrets/sandbox behavior must remain fail-closed,
5. observability and rollback evidence must be captured alongside the driver contract work.

---

## Coverage map

| Gap area | Existing baseline | Wave 6 action |
|---|---|---|
| QDriver final contract | RFC 0044 / ADR 0030 | Reconcile implementation and docs with the accepted contract |
| Provider matrix and tolerance profiles | RFC 0045 / ADR 0031 | Keep parity and rollback policy versioned and enforced |
| Driver Manager architecture boundary | `docs/architecture/components/driver-manager.md` | Keep the implementation aligned to the runtime role |
| Transport / API surface | `docs/reference/api/grpc-internal.md` | Confirm the internal service contract matches the accepted baseline |
| Secrets and sandboxing | Driver Manager architecture spec | Add/strengthen fail-closed provider handling |
| Observability and evidence | observability contracts | Include bounded metrics, traces, and release evidence |

---

## Open documentation tasks

- Decide whether to add a dedicated `docs/reference/api/qdriver.md` or keep the final semantics anchored in `docs/reference/api/grpc-internal.md`.
- Add or update inventory and manifest rows for the Wave 6 contract slice.
- Document simulator parity and provider tolerance as release evidence requirements.
- Add migration notes if any provider-facing behavior changes are tightened.
- Keep the Wave 6 issue pack, compatibility report, release checklist, and exit evidence bundle synchronized with implementation reality.

---

## Exit condition

Wave 6 governance is complete when the opening docs are published, the inventory and manifest rows exist, and the implementation evidence closes the issue pack without introducing undocumented provider-specific behavior.
