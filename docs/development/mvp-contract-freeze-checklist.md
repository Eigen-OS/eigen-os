# MVP Contract Freeze — Acceptance Checklist (RFC 0004, 0006, 0011)

> Goal: **freeze the MVP contract** so that implementations (System API / Kernel / Compiler / Driver Manager / CLI) do not “drift apart”. 
> 
>Usage: when all **A**-level items are completed — the RFC can be moved to **Accepted**.
>  
> **B** level — minimal “contract-verification” implementation (skeleton + tests) to guarantee the contract is actually executable.

---

## A) Definition of Done for RFC acceptance (design freeze)

### A0. General requirements for all three RFCs
- [ ] **Single source of truth for contracts**: protobuf/JobSpec/IR are stored in **one place** and referenced by docs/RFC (no copy-paste).
- [ ] All RPCs/formats have explicit versioning (`...v1` in package/namespace).
- [ ] **Unified error model**: external and internal RPCs use **gRPC status codes**, and structural error details — via `google.rpc.Status` + `google.rpc.*` details (BadRequest/ErrorInfo/ResourceInfo, etc.). (gRPC status codes: [https://grpc.io/docs/guides/status-codes/](https://grpc.io/docs/guides/status-codes/)); google.rpc: [https://buf.build/googleapis/googleapis/docs/main:google.rpc](https://buf.build/googleapis/googleapis/docs/main:google.rpc).
- [ ] **Tracing**: mandatory context propagation (W3C TraceContext `traceparent`) via gRPC metadata throughout the entire chain.
- [ ] CI rule: any changes to proto files go through `buf lint` + `buf breaking` (breaking check against main/latest release).
- [ ] Each RFC includes: Goals/Non‑Goals, Semantics, Backward compatibility, Testing plan, Open questions = **empty** or explicitly deferred as “Post‑MVP”.

---

## RFC 0004 — Public gRPC API (eigen_api.v1) + Stream semantics

### A1. JobService/DeviceService/CompilationService contract is frozen
- [ ] List of services and methods = **final for MVP**.
- [ ] For each method, the following are described:
  - [ ] mandatory fields and their meaning
  - [ ] idempotency (e.g.: `client_request_id` or determinism via `job_hash`)
  - [ ] side‑effects (what is created/where it is written)
  - [ ] errors (which gRPC status codes are returned)
- [ ] Distinction between `INVALID_ARGUMENT` vs `FAILED_PRECONDITION` is documented (important for retry logic).

### A2. StreamJobUpdates — clear semantics
- [ ] `JobUpdate` has a **monotonic** `event_seq` (or update_seq) per `job_id`.
- [ ] Order is defined: the client may receive events with gaps in `event_seq` on reconnect, but **can request “from which seq to continue”**.
- [ ] Heartbeat/keepalive behavior in RUNNING is described.
- [ ] Terminal events: DONE/ERROR/CANCELLED/TIMEOUT — **final** and after that the stream is closed/or remains open by rule (to be fixed!).

### A3. ReserveDevice — meaning for MVP (to avoid “magic”)
- [ ] Explicitly stated: ReserveDevice = **reserving a slot/quota in the Kernel scheduler**, not “exclusive hardware lock”.
- [ ] TTL/lease semantics are fixed (expiration → automatic release).
- [ ] Errors: `FAILED_PRECONDITION`/`RESOURCE_EXHAUSTED`/`UNAVAILABLE` — depending on situation, documented.

### A4. Proto inventory: no “hidden public API”
- [ ] In `eigen_api.v1`, there is no `monitoring.proto`/`auth.proto` as part of the public gRPC contract for MVP, or they are:
  - [ ] removed/moved to internal, **or**
  - [ ] marked as unstable and excluded from SDK/CLI generation (but then that is a separate RFC).
- [ ] Monitoring for MVP: `/metrics` (Prometheus scrape), not gRPC.

---

## RFC 0006 — Driver Manager + QDriver (interface between Kernel → DriverManager → Backend)

### A5. DriverManagerService contract is finalized
- [ ] RPC methods: at least `ListDevices`, `GetDeviceStatus`, `ExecuteCircuit` (Calibrate — optional).
- [ ] `ExecuteCircuit` accepts **CircuitPayload** with format `enum + bytes/ref` (IR/QASM/native).
- [ ] If a device does not support a format — `UNIMPLEMENTED` (or `FAILED_PRECONDITION` — but choose one and fix it).

### A6. Results normalization
- [ ] MVP result = `counts: map<bitstring,int64>` + `metadata/timing`.
- [ ] Fixed: “what constitutes a bitstring” (endianness/qubit ordering) — otherwise integration bugs will appear.

### A7. Capability model (minimal)
- [ ] Devices return at least: `device_id`, `backend_type`, `status`, `capabilities` (qubits, supported_formats).
- [ ] If a device does not support a format — `UNIMPLEMENTED` (or `FAILED_PRECONDITION` — but choose one and fix it).

---

## RFC 0011 — Eigen‑Lang submission format v0.1 (what is a “user source”)

### A8. Canonical artifacts and packaging
- [ ] MVP canonical: `program.eigen.py` + `job.yaml`.
- [ ] job.yaml fixes: `entrypoint`, `target`, `shots`, `compiler_options`, `inputs` (refs/uri).
- [ ] CLI computes `sha256(source)` and passes `source_hash`/`entrypoint` to SubmitJob.

### A9. Compiler — AST‑only, no execution of user Python
- [ ] Explicitly stated: compilation = `ast.parse` + AST analysis + IR building (no `exec`/`importlib`/side effects).
- [ ] There is an **allowlist** of allowed constructs (even if minimal), and what to do on violation (INVALID_ARGUMENT + BadRequest FieldViolation).
- [ ] Datasets/large inputs — only refs/uri (no raw bytes in gRPC).

### A10. Storage contract (QFS) for source/IR/results
- [ ] Stable paths are fixed: `input`/, `compiled`/, `results`/, `meta`/ under `job_id`.
- [ ] Fixed: what is canonical IR (AQO JSON) vs optional (AQO PB/QASM).

---

## B) Minimal contract‑verification implementation (to prove executability)

### B0. Protobuf + generation
- [ ] `buf lint` passes.
- [ ] `buf breakin`g is configured to compare against `main` and passes.
- [ ] Client generation (at least 1 language: Python or Rust) passes and builds.

### B1. System API skeleton (public boundary)
- [ ] gRPC server starts with JobService/DeviceService (CompilationService — if kept).
- [ ] At least the following are implemented:
  - [ ] SubmitJob → returns job_id
  - [ ] GetJobStatus → returns state
  - [ ] GetJobResults → returns results
  - [ ] StreamJobUpdates → returns a stream (even if polling‑bridge)

### B2. Kernel skeleton (workflow orchestrator)
- [ ] “job lifecycle” state machine is implemented (Pending→Compiling→Running→Done/Error/Cancelled).
- [ ] Kernel calls Compiler and DriverManager via internal gRPC.

### B3. Compiler skeleton (AST parse → IR)
- [ ] Accepts Eigen‑Lang source, performs `ast.parse`, validates allowlist, builds AQO JSON (minimal set of ops).
- [ ] On violations, returns INVALID_ARGUMENT + BadRequest details.

### B4. Driver Manager + SimulatorDriver
- [ ] There is a SimulatorDriver as a “golden driver”.
- [ ] ExecuteCircuit accepts AQO/QASM and returns counts.
- [ ] Backend errors are simulated via `UNAVAILABLE/RESOURCE_EXHAUSTED/FAILED_PRECONDITION` (with tests).

### B5. End‑to‑end integration test (MVP contract criterion)
**Test: E2E happy path**
- [ ] `eigen-cli submit job.yaml` → OK (job_id)
- [ ] `--watch` receives events with monotonic seq until terminal
- [ ] `eigen-cli results job_id` → counts + metadata
- [ ] Artifacts appear in QFS: source, compiled IR, results.

**Test: Validation fail**
- [ ] Invalid source (disallowed AST node) → INVALID_ARGUMENT + FieldViolation.

**Test: Backend unavailable**
- [ ] Simulated backend unavailability → UNAVAILABLE; JobStatus = ERROR with last error.

### B6. Observability smoke tests
- [ ] Metrics are available at `/metrics`.
- [ ] Trace context `traceparent` is propagated through the chain (verified in logs/exporter).
---

## C) Mini‑matrix “contract is frozen” (what must match between modules)

- [ ] **JobSpec ↔ SubmitJobRequest**: fields and configuration priority are the same (CLI/server).
- [ ] **Compiler output ↔ CircuitPayload**: list of formats matches.
- [ ] **DriverManager results ↔ JobResultsResponse**: counts and metadata have the same structure.
- [ ] **JobStatus mapping**: internal states → external states are unambiguously documented.
- [ ] **Errors**: no success withс `success=false`; all errors — via status codes.

---

## D) What can be “safely deferred” from MVP (to avoid bloating the contract)

- Full‑fledged quotas/multi‑tenant billing
- Real hardware drivers (except simulator)
- Advanced calibration pipelines
- Full KB/GNN/HWE (as subsystems)
- High availability / multi‑region

