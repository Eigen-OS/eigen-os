# Product 1.0 Wave 2 Compatibility Report

**Status:** W2-03 complete, other issues pending
**Scope:** Kernel/QRTX lifecycle authority, internal API alignment, System API delegation, orchestration DAG, cancellation/deadline/retry semantics, and observability evidence
**Version policy:** `docs/development/product-1.0-version-policy.md`
**Issue pack:** `docs/development/product-1.0-wave-2-issue-pack.md`
**Evidence bundle:** `docs/development/product-1.0-wave-2-exit-evidence-bundle.md`
**Created:** 2026-06-02
**Updated:** 2026-06-02 (W2-03 completion)

---

## 1. Compatibility rules

Wave 2 changes follow these rules:

1. Internal API changes that remove, rename, or change documented KernelGateway methods, fields, metadata requirements, lifecycle states, event semantics, retry/deadline behavior, or result-references are **breaking** (MAJOR).
2. Kernel state-machine changes that alter accepted transitions, terminal-state precedence, replay semantics, or invalid-transition errors are **breaking** unless only additive and backward-compatible.
3. Public `eigen.api.v1` behavior from Wave 1 must remain compatible. Any public breaking change requires a separate public RFC/ADR and must not be hidden in Wave 2.
4. Additive internal fields, metrics, event types, or trace attributes use `MINOR` when old consumers continue to function.
5. Documentation-only or non-semantic fixes use `PATCH` or `NONE` according to the Product 1.0 version policy.
6. Every breaking change requires migration notes, release notes, conformance fixture updates, and exit evidence.
7. Every changed Product 1.0 contract mapping must update `contracts/product-1.0/manifest.json` and `docs/development/product-1.0-contract-inventory.md` in the same implementation PR.

---

## 2. Issue compatibility ledger

| Issue | Version Impact | Affected Interfaces | Compatibility | Breaking Marker | Migration Notes | Release Notes Draft | Evidence |
|---|---|---|---|---|---|---|---|
| W2-01 Internal KernelGateway contract matrix and canonical state machine | TBD | Internal API; Kernel state; Compatibility matrix | TBD | TBD | TBD | TBD | W2-E01 |
| W2-02 Durable/replayable kernel job state store and transition validator | TBD | Kernel state; Migration docs | TBD | TBD | TBD | TBD | W2-E02 |
| **W2-03 System API lifecycle delegation cutover to Kernel/QRTX** | **PATCH** | **Internal API (eigen.internal.v1 RequestMetadata); System API implementation; Kernel state** | **Backward-compatible** | **false** | **MVP System API state store deprecated; all state managed by Kernel; no public API changes** | **Added: KernelGatewayClient adapter; Changed: SubmitJob, GetStatus, Cancel delegate to Kernel; Fixed: lifecycle consistency** | **W2-E03** |
| W2-04 Product 1.0 orchestration DAG control-plane skeleton | TBD | Kernel state; Internal API; Trace context | TBD | TBD | TBD | TBD | W2-E04 |
| W2-05 Deadline propagation and cancellation fan-out | TBD | Internal API; Kernel state; Metrics; Trace context | TBD | TBD | TBD | TBD | W2-E05 |
| W2-06 Retry governance tied to canonical retryability | TBD | Kernel state; Internal API; Metrics; Error mapping | TBD | TBD | TBD | TBD | W2-E06 |
| W2-07 Orchestration observability and trace continuity gate | TBD | Metrics; Trace context; Compatibility matrix | TBD | TBD | TBD | TBD | W2-E07 |
| W2-08 Wave 2 compatibility report, migration notes, and exit evidence bundle | TBD | Compatibility matrix; Migration docs | TBD | TBD | TBD | TBD | W2-E08 |

---

## 3. W2-03 Detailed Compatibility Analysis

### Version Impact: PATCH

Public `eigen.api.v1` API interface is unchanged. Internal implementation delegates to Kernel/QRTX without altering public contract semantics, error model, idempotency, or observable behavior.

### Affected Interfaces

1. **Internal API**: `eigen.internal.v1.KernelGatewayService`
   - Expanded with `RequestMetadata` message for normalized context
   - All public requests mapped through normalized metadata
   - No breaking changes to existing proto (additive only)

2. **System API Implementation** (`src/services/system-api`)
   - `grpc_impl.py` service methods now delegate to Kernel
   - `kernel_client.py` new adapter for delegation
   - `grpc_delegation.py` delegation handler
   - `lifecycle.py` state mapping utilities

3. **Kernel State Ownership**
   - System API no longer owns or mutates job lifecycle state
   - Kernel/QRTX is single source of truth
   - Deterministic, replayable state transitions

### Compatibility Statement

**Backward-compatible for Wave 1 public contracts:**

- ✓ Public `eigen.api.v1.JobService` methods unchanged
- ✓ Public `eigen.api.v1` request/response messages unchanged
- ✓ Public error model compliance maintained
- ✓ Public idempotency semantics preserved
- ✓ Wave 1 public conformance tests pass unchanged
- ✓ Public-only metadata fields never leaked to Kernel

**Breaking Marker: false** (for public API)

Internal changes do not require public RFC/ADR approval. Wave 2 RFC 0050 and ADR 0036 authorize internal MAJOR changes when necessary for architecture alignment.

### Migration Notes

**For downstream services (Wave 3+):**

- Compiler, Optimizer, Driver Manager, QFS must integrate through Kernel/QRTX lifecycle, not System API
- Kernel is the canonical job state authority
- System API acts as public gateway only

**For operators:**

- MVP System API state store (file-based idempotency store) is deprecated
- All job state now owned by Kernel
- Existing Wave 1 jobs remain queryable through System API delegation path
- No action required; delegation is transparent to Wave 1 clients

---

## 4. Required migration-note content for MAJOR internal changes

(N/A for W2-03; Version Impact is PATCH)

---

## 5. Closure requirements

W2-03 closure requirements:

- ✓ No TBD values in W2-03 row
- ✓ Version Impact, Compatibility, Breaking Marker all defined
- ✓ Migration notes documented
- ✓ Release notes drafted
- ✓ Evidence links provided (W2-E03)
- ✓ Wave 1 regression test evidence included
- ✓ Public API compatibility proven
- ✓ Metadata normalization verified
- ✓ Trace context propagation confirmed
