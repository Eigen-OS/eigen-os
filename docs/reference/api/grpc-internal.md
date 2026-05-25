# gRPC Internal API (eigen.internal.v1)

This section captures the implemented internal gRPC contracts (used between Eigen OS services) and highlights missing pieces. The canonical `.proto` files (`proto/eigen/internal/v1/*.proto`) are the source of truth.

## 1. Services and Methods

- **KernelGatewayService:** (System API → Kernel)

   - `EnqueueJob(EnqueueJobRequest) → EnqueueJobResponse`

   - `GetJobStatus(GetJobStatusRequest) → GetJobStatusResponse`

   - `CancelJob(CancelJobRequest) → CancelJobResponse`

   - `GetJobResults(GetJobResultsRequest) → GetJobResultsResponse` *State enum: TASK_STATE_(PENDING, COMPILING, QUEUED, RUNNING, DONE, ERROR, CANCELLED, TIMEOUT).*

- **CompilationService:** (Kernel → Compiler)

   - `CompileCircuit(CompileCircuitRequest) → CompileCircuitResponse`

   - `CompileJob(CompileJobRequest) → CompileJobResponse`

   - `OptimizeCircuit(OptimizeCircuitRequest) → OptimizeCircuitResponse` *(stub)*

   - `ValidateCircuit(ValidateCircuitRequest) → ValidateCircuitResponse` *(stub)*

- **DriverManagerService:** (Kernel → Driver Manager)

   - `ListDevices(ListDevicesRequest) → ListDevicesResponse`

   - `GetDeviceStatus(GetDeviceStatusRequest) → GetDeviceStatusResponse`

   - `ExecuteCircuit(ExecuteCircuitRequest) → ExecuteCircuitResponse`

   - `CalibrateDevice(CalibrateDeviceRequest) → CalibrateDeviceResponse`

- **OptimizerService:** (Compiler/Kernel → GNN Optimizer)

   - `OptimizeCircuit(OptimizeCircuitRequest) → OptimizeCircuitResponse`

Common types (`types.proto`) include `CircuitPayload`, `CircuitFormat`, `DeviceInfo`, `DeviceStatus`, etc.

## 2. Detailed Notes

- **KernelGatewayService:**

   - **Implemented:** Submit, status, cancel, results RPCs.

   - **Missing:** There is *no* `PollJobUpdates` RPC here; streaming is done via public API instead.

   - **Auth:** No auth fields in requests (we rely on gRPC metadata for internal trust). We should ensure metadata propagation (user/tenant context) on all calls.

   - **Idempotency:** Not defined here; higher-level (System API) handles idempotency.

- **CompilationService:**

   - **Implemented:** `CompileCircuit`, `CompileJob`. The code returns a `CircuitPayload` and metadata.

   - **Stubbed:** `OptimizeCircuit` and `ValidateCircuit` exist in proto but are currently not implemented (they return UNIMPLEMENTED).

   - **Options:** The `options` map in requests is currently unstructured; we should eventually define specific compiler flags or remove it if unused.

   - **Source refs:** CompileJob can accept `source_ref` but the ownership/timeout is not documented here.

- **DriverManagerService:**

   - **Implemented:** List, status, execute; the response normalizes backend output into `counts`, `execution_time_sec`, etc.

   - **CalibrateDevice:** Exists in proto but the driver manager’s current behavior is unimplemented.

   - **Async exec:** Currently only synchronous unary `ExecuteCircuit`. A future should be an async/streaming interface for long jobs.

   - **Metadata:** We should standardize keys like `"noise_level"` or `"gate_errors"` in `metadata`.

- **OptimizerService:**

   - **Implemented RPC:** `OptimizeCircuit`.

   - **Protocol details:** The request contains a semver envelope for replay (`contract_version`), topology, objective, deterministic seed.

   - **Response:** Echoes seed, plus `fallback_used`/`fallback_reason` if a default algorithm was used, timing metrics (`optimizer_latency_ms`, etc.), and trace ID.

   - **Reason codes:** The proto defines codes like `OPT_INVALID_AQO`, `OPT_TIMEOUT`, etc. These should be used on failure.

   - **Missing:** The actual ML model execution path is not yet wired (only stub).

   - **Thresholds:** There is mention of confidence thresholds (e.g. fallback) but no frozen table of values.

## 3. Cross-cutting

- **Error Model:** Internal APIs use gRPC status codes (no `success=false` fields). We should use standard codes: `INVALID_ARGUMENT`, `NOT_FOUND`, `FAILED_PRECONDITION`, `RESOURCE_EXHAUSTED`, `UNAVAILABLE`, `DEADLINE_EXCEEDED`, `UNIMPLEMENTED`. A global error mapping table (per-RPC and failure type) is not documented yet.

- **Retries:** No common retry budgets are documented; each caller must decide per status. We should define recommended retry behavior for idempotent calls.

- **Observability:** Trace context (W3C `traceparent`) flows by metadata. Metrics exist but naming is not standardized in docs.

- **Security:** Internal calls are currently unsecured (mTLS optional). We should enforce mutual TLS and propagate a service identity token on all hops.

## 4. Action Items

1. **Sync Names:** Update docs and code to consistently use `KernelGatewayService`, `CompilationService`, etc. (vs. legacy names).

2. **Metadata Fields:** Freeze required gRPC metadata keys (e.g. `x-eigen-user`, `x-eigen-tenant`) and enforce them.

3. **Error Table:** Create a reference table mapping each RPC and error condition to gRPC codes.

4. **CI Checks:** Add Buf or custom checks to catch proto changes in CI and verify metadata propagation in tests.

5. **Complete Stubs:** Implement or remove the stub RPCs (`OptimizeCircuit`, `ValidateCircuit`, `CalibrateDevice`).

6. **Opcodes:** Freeze any constant options (like compiler flags keys) that must be interoperable.
