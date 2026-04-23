# RFC Compliance Audit (codebase vs `rfcs/`)

Date: 2026-04-23

## Scope

- Reviewed RFCs in `rfcs/0001`–`0012`.
- Reviewed implementation and tests in:
  - `src/services/system-api`
  - `src/services/eigen-compiler`
  - `src/services/driver-manager`
  - `src/rust/apps/cli`
  - `proto/`

## Executive summary

Current status is **partially compliant** with MVP RFC set.

- **Strongly aligned:** public proto layout, JobService/DeviceService surface, stream sequencing behavior, compiler AST-only safety checks, basic auth + input validation hooks, observability JSON logs + `/metrics`, JobSpec v0.1 shape in CLI parser.
- **Partially aligned / gaps:** API includes `CompilationService` in public RFC while separate submission RFCs suggest internal-only ambiguity; some RFC-mandated CI checks (Buf lint/breaking) are not evident here; kernel-level requirements from RFC 0007 are only partially represented in current tree.
- **Critical hygiene issue fixed in this audit:** RFC 0002 contained unresolved merge-conflict markers and was normalized.

## Compliance matrix

### RFC 0001 (RFC process)

**Status: Partial**

- RFC files and template exist.
- Process mechanics like linking tracking issues/owners/status transitions are not consistently enforced by code/CI in this repo snapshot.

### RFC 0002 (architecture boundaries)

**Status: Partial**

- Service graph artifacts exist (`system-api`, `eigen-compiler`, `driver-manager`, kernel crate/protos).
- End-to-end orchestration appears scaffolded/stubbed in service code; not all kernel orchestration guarantees from RFC text are verifiable as implemented.
- **Fixed now:** removed merge-conflict markers from RFC 0002 file so architecture spec is readable and machine-auditable.

### RFC 0003 (JobSpec v0.1)

**Status: Mostly compliant (CLI layer)**

- CLI parser validates `apiVersion=eigen.os/v0.1`, `kind=QuantumJob`, required fields, and preserves extensibility via tolerant parsing of unknown keys.
- Mapping to submission request with `eigen_lang` payload and sha256 packaging is implemented.

### RFC 0004 (public gRPC API)

**Status: Mostly compliant (surface + behavior), partial (kernel gateway in runtime)**

- Public proto tree provides JobService + DeviceService + CompilationService and internal gateway proto.
- System API implementation includes submit/status/cancel/stream/results and device operations.
- Stream updates are ordered and use monotonic `event_seq`; terminal state handling exists in stub flow.
- Full production kernel gateway wiring remains partially stubbed in this snapshot.

### RFC 0005 (AQO)

**Status: Partial**

- Compiler emits deterministic JSON AQO (`sort_keys=True`) with versioned payload and mandatory measurement op.
- MVP gate set is represented in compiler stubs (`RX/RY/RZ/CX/MEASURE`) with params support.
- Full AQO schema validation and broader operation set constraints from RFC are not fully evident.

### RFC 0006 (QDriver API)

**Status: Partial**

- Internal driver-manager proto/services exist and simulator driver tests are present.
- Plugin/driver architecture scaffolding exists.
- Full compliance to execution/result metadata contracts appears incomplete or dependent on runtime not fully verifiable in current environment.

### RFC 0007 (QRTX MVP)

**Status: Partial / not fully verifiable**

- Kernel crates exist; internal gateway proto exists.
- Required lifecycle/pipeline/QFS persistence guarantees are not fully confirmed due rust workspace build failure in current environment (see checks section).

### RFC 0008 (observability)

**Status: Mostly compliant (system-api slice)**

- Structured JSON logging includes key fields.
- Prometheus-style `/metrics` endpoint exists with request count and duration metrics.
- Trace context extraction via `traceparent` metadata is implemented.
- Cross-service completeness (kernel/driver-manager metric families from RFC examples) is only partial in this snapshot.

### RFC 0009 (security/isolation)

**Status: Partial**

- System API has auth modes (`allow_all`, static token), authn enforcement, payload size limits, and validation routing to INVALID_ARGUMENT.
- Permission matrix / role-based authorization and kernel isolation hook semantics are only partially represented.

### RFC 0010 (eigen-cli MVP)

**Status: Partial**

- CLI crate + JobSpec submit-path implementation exists.
- Full command surface (`status/result/compile/visualize`) and explicit exit-code contract from RFC are not fully confirmed in this audit pass.

### RFC 0011/0012 (Eigen-Lang submission + language contract)

**Status: Mostly compliant in compiler safety core, partial overall**

- Compiler uses AST parsing only and does not execute user code.
- Forbidden imports/calls and dynamic control-flow rejection are implemented.
- Deterministic output hashing and metadata are present.
- Some language conformance details remain MVP-stub-level and need fuller conformance-suite enforcement across CI.

## Evidence highlights

- Public/internal proto split and services: `proto/eigen/api/v1/*`, `proto/eigen/internal/v1/*`.
- AST-only compilation and safety checks: `src/services/eigen-compiler/src/eigen_compiler/compiler.py`.
- Compile request validation and size limits: `src/services/eigen-compiler/src/eigen_compiler/validation.py`.
- System API validation, authn hooks, observability, streaming semantics: `src/services/system-api/src/system_api/{validation.py,security.py,observability.py,grpc_impl.py}`.
- CLI JobSpec parser and submit mapping: `src/rust/apps/cli/src/jobspec.rs`.

## Recommended follow-ups

1. Add/enable CI conformance gates explicitly tied to RFC clauses (Buf lint/breaking, language conformance, stream-order contract tests).
2. Complete kernel RFC 0007 validation once rust workspace build issues are resolved.
3. Harmonize RFC 0004 vs RFC 0011/0012 on whether `CompilationService` is public in MVP and freeze one position.
4. Expand security from authn baseline to RFC 0009 role-permission enforcement and auditable deny metrics.
