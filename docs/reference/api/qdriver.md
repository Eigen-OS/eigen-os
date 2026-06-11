# QDriver API v1 Final Contract

**Status:** Canonical reference for Wave 6  
**Version:** 1.0.0  
**Scope:** Final provider-side semantics projected through the Driver Manager transport boundary  
**Source of truth:** `docs/architecture/components/driver-manager.md`, `docs/reference/api/grpc-internal.md`, `rfcs/0044-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`, `docs/adr/0030-phase8d-qdriver-api-v1-final-contract-and-conformance-semantics.md`

---

## 1. Purpose

QDriver v1 is the frozen contract for provider execution semantics. It is not a public API. It defines the final provider-facing behavior that the kernel-facing Driver Manager must project without exposing provider SDK details, provider-native error payloads, or backend-specific transport quirks.

This reference is the canonical semantic baseline for Wave 6.

---

## 2. Normative method set

QDriver v1 exposes the following semantic operations:

```text
Initialize
Execute
GetStatus
Calibrate
Cancel
```

### 2.1 Initialize

Initializes a backend session and performs deterministic capability negotiation.

MUST:

- complete a versioned capability handshake,
- reject incompatible versions deterministically,
- fail closed when the requested backend profile is unsupported,
- avoid leaking provider-specific SDK state into the kernel boundary.

### 2.2 Execute

Executes the requested workload with normalized results.

MUST:

- preserve deterministic behavior for equivalent inputs,
- normalize counts, timing, and metadata,
- return canonical Eigen OS gRPC statuses for backend failures,
- avoid surfacing provider-native payloads directly.

### 2.3 GetStatus

Returns the backend/device status snapshot.

MUST:

- provide bounded metadata only,
- preserve stable field names and deterministic ordering,
- reject unknown device identifiers with a canonical missing-resource error.

### 2.4 Calibrate

Performs a calibration action when the backend supports it.

MAY:

- return `UNIMPLEMENTED` when calibration is not supported by the selected provider class.

### 2.5 Cancel

Cancels an in-flight execution or a pending backend action.

MUST:

- be idempotent,
- propagate cancellation deterministically through the Driver Manager transport boundary,
- preserve stable error mapping if the backend cannot honor cancellation in time.

---

## 3. Capability negotiation and compatibility

- Capability descriptors are additive-only for minor versions.
- Unsupported capability selection MUST fail closed.
- Version / compatibility mismatch MUST be deterministic and documented.
- No provider-specific behavior may escape the canonical contract.

Recommended status mapping:

| Condition | Canonical status |
|---|---|
| Unsupported capability | `UNIMPLEMENTED` |
| Unsupported backend / profile | `FAILED_PRECONDITION` |
| Version mismatch | `FAILED_PRECONDITION` |
| Backend outage / unavailable provider | `UNAVAILABLE` |
| Cancel unavailable / too late to honor | `FAILED_PRECONDITION` |

---

## 4. Transport and metadata

The final contract is projected over the kernel-facing gRPC transport and MUST preserve:

- gRPC over HTTP/2,
- Protocol Buffers v3 serialization,
- trace context propagation,
- request identity / correlation metadata,
- bounded response metadata.

The transport layer MUST remain stable across equivalent inputs and MUST not introduce nondeterministic field ordering.

---

## 5. Relation to DriverManagerService

`DriverManagerService` is the kernel-facing transport projection of QDriver v1.

| QDriver semantic | Kernel-facing transport projection |
|---|---|
| `Initialize` | service bootstrap / session creation |
| `Execute` | `ExecuteCircuit` |
| `GetStatus` | `GetDeviceStatus` |
| `Calibrate` | `CalibrateDevice` |
| `Cancel` | kernel cancellation fan-out |

This document is the canonical reference for the final semantics, even where the current transport surface uses legacy MVP method names.
