//! Internal gRPC server: KernelGateway.

use std::collections::HashMap;
use std::fmt;
use std::net::SocketAddr;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde_json::Value;
use serde_json::json;
use tonic::{Code, Request, Response, Status};
use tracing::Instrument;

use crate::job_store::{JobRecord, JobStore};
use crate::proto::compilation_service_client::CompilationServiceClient;
use crate::proto::driver_manager_service_client::DriverManagerServiceClient;
use crate::proto::kernel_gateway_service_server::{
    KernelGatewayService, KernelGatewayServiceServer,
};
use crate::proto::{
    CalibrateDeviceRequest, CalibrateDeviceResponse, CancelJobRequest, CancelJobResponse,
    EnqueueJobRequest, EnqueueJobResponse, GetJobResultsRequest, GetJobResultsResponse,
    GetJobStatusRequest, GetJobStatusResponse, TaskState, ValidateCircuitRequest,
    ValidateCircuitResponse,
};
use crate::proto::{
    CircuitFormat, CircuitPayload, CompileCircuitRequest, CompileCircuitResponse,
    CompileJobRequest, CompileJobResponse, ExecuteCircuitRequest, ExecuteCircuitResponse,
    GetDeviceStatusRequest, GetDeviceStatusResponse, ListDevicesRequest, ListDevicesResponse,
    compilation_service_server, driver_manager_service_server,
};
use qfs::CircuitFsLocal;
use qrtx::state_machine::{JobEvent, JobState};

/// Runs the kernel gRPC server on the provided address.
pub async fn serve(addr: SocketAddr) -> Result<(), Box<dyn std::error::Error>> {
    let store = JobStore::default();
    let svc = KernelGatewaySvc {
        store,
        deps: PipelineDeps::from_env(),
    };

    tracing::info!(%addr, "kernel gRPC server starting");
    tonic::transport::Server::builder()
        .add_service(KernelGatewayServiceServer::new(svc))
        .serve(addr)
        .await?;
    Ok(())
}

#[derive(Clone)]
struct KernelGatewaySvc {
    store: JobStore,
    deps: PipelineDeps,
}

#[derive(Debug, Clone)]
struct PipelineDeps {
    compiler_endpoint: String,
    driver_endpoint: String,
    default_device_id: String,
    qfs: CircuitFsLocal,
}

impl fmt::Display for PipelineError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {} ({})", self.code, self.summary, self.details)
    }
}

impl std::error::Error for PipelineError {}

impl PipelineDeps {
    fn from_env() -> Self {
        let compiler_addr =
            std::env::var("EIGEN_COMPILER_ADDR").unwrap_or_else(|_| "127.0.0.1:50071".to_string());
        let driver_addr = std::env::var("EIGEN_DRIVER_MANAGER_ADDR")
            .unwrap_or_else(|_| "127.0.0.1:50072".to_string());
        let qfs_root = std::env::var("EIGEN_QFS_ROOT")
            .unwrap_or_else(|_| qfs::DEFAULT_CIRCUIT_FS_ROOT.to_string());

        Self {
            compiler_endpoint: format!("http://{compiler_addr}"),
            driver_endpoint: format!("http://{driver_addr}"),
            default_device_id: std::env::var("EIGEN_DEFAULT_DEVICE_ID")
                .unwrap_or_else(|_| "sim:local".to_string()),
            qfs: CircuitFsLocal::new(qfs_root),
        }
    }
}

#[derive(Debug, Clone, Default)]
struct TraceContext {
    traceparent: Option<String>,
    trace_id: Option<String>,
}

impl TraceContext {
    fn from_request_md(md: &tonic::metadata::MetadataMap) -> Self {
        let traceparent = md
            .get("traceparent")
            .and_then(|v| v.to_str().ok())
            .map(|s| s.to_string());
        let trace_id = md
            .get("trace_id")
            .and_then(|v| v.to_str().ok())
            .map(|s| s.to_string())
            .or_else(|| parse_trace_id(traceparent.as_deref()));
        Self {
            traceparent,
            trace_id,
        }
    }

    fn inject<T>(&self, req: &mut Request<T>) {
        if let Some(tp) = &self.traceparent {
            if let Ok(v) = tp.parse() {
                req.metadata_mut().insert("traceparent", v);
            }
        }
        if let Some(tid) = &self.trace_id {
            if let Ok(v) = tid.parse() {
                req.metadata_mut().insert("trace_id", v);
            }
        }
    }
}

fn parse_trace_id(traceparent: Option<&str>) -> Option<String> {
    let raw = traceparent?;
    let mut parts = raw.split('-');
    let _version = parts.next()?;
    let trace_id = parts.next()?;
    if trace_id.len() == 32 {
        Some(trace_id.to_string())
    } else {
        None
    }
}

#[tonic::async_trait]
impl KernelGatewayService for KernelGatewaySvc {
    async fn enqueue_job(
        &self,
        request: Request<EnqueueJobRequest>,
    ) -> Result<Response<EnqueueJobResponse>, Status> {
        let trace_ctx = TraceContext::from_request_md(request.metadata());
        let req = request.into_inner();

        if req.name.trim().is_empty() {
            return Err(Status::invalid_argument("name is required"));
        }

        let record = self.store.create_job(req.name.clone());
        let job_id = record.job_id.clone();
        let job_id_for_task = job_id.clone();

        let store = self.store.clone_handle();
        let deps = self.deps.clone();
        tokio::spawn(async move {
            let span = tracing::info_span!("job_pipeline", job_id = %job_id_for_task);
            async move {
                if let Err(err) =
                    run_pipeline(store.clone_handle(), deps, &job_id_for_task, req, trace_ctx).await
                {
                    tracing::error!(job_id = %job_id_for_task, error = %err, "job pipeline failed");
                    fail_job(&store, &job_id_for_task, err).await;
                }
            }
            .instrument(span)
            .await;
        });

        Ok(Response::new(EnqueueJobResponse {
            job_id,
            state: TaskState::Pending as i32,
            created_at: Some(ts_now()),
        }))
    }

    async fn get_job_status(
        &self,
        request: Request<GetJobStatusRequest>,
    ) -> Result<Response<GetJobStatusResponse>, Status> {
        let job_id = request.into_inner().job_id;
        if job_id.trim().is_empty() {
            return Err(Status::invalid_argument("job_id is required"));
        }
        let rec = self
            .store
            .get(&job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;

        Ok(Response::new(status_from_record(&rec)))
    }

    async fn cancel_job(
        &self,
        request: Request<CancelJobRequest>,
    ) -> Result<Response<CancelJobResponse>, Status> {
        let job_id = request.into_inner().job_id;
        if job_id.trim().is_empty() {
            return Err(Status::invalid_argument("job_id is required"));
        }

        let rec = self
            .store
            .get(&job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;

        let accepted = match rec.state {
            JobState::Done | JobState::Error | JobState::Cancelled | JobState::Timeout => false,
            _ => self.store.apply_event(&job_id, JobEvent::Cancel).is_ok(),
        };

        Ok(Response::new(CancelJobResponse { accepted }))
    }

    async fn get_job_results(
        &self,
        request: Request<GetJobResultsRequest>,
    ) -> Result<Response<GetJobResultsResponse>, Status> {
        let job_id = request.into_inner().job_id;
        if job_id.trim().is_empty() {
            return Err(Status::invalid_argument("job_id is required"));
        }

        let rec = self
            .store
            .get(&job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;

        Ok(Response::new(GetJobResultsResponse {
            job_id: rec.job_id,
            state: to_proto_state(rec.state) as i32,
            counts: rec.counts,
            metadata: rec.results_metadata,
            error_code: rec.error_code.unwrap_or_default(),
            error_summary: rec.error_summary.unwrap_or_default(),
            error_details_ref: rec.error_details_ref.unwrap_or_default(),
            completed_at: if rec.state == JobState::Done {
                Some(ts_from_unix_ms(rec.updated_at_unix_ms))
            } else {
                None
            },
        }))
    }
}

async fn run_pipeline(
    store: JobStore,
    deps: PipelineDeps,
    job_id: &str,
    req: EnqueueJobRequest,
    trace_ctx: TraceContext,
) -> Result<(), PipelineError> {
    let mut results_metadata = HashMap::from([(
        "results_ref".to_string(),
        format!("jobs/{job_id}/results.parquet"),
    )]);

    store
        .apply_event(job_id, JobEvent::StartCompiling)
        .map_err(|e| PipelineError::internal(format!("state transition failed: {e}")))?;

    deps.qfs
        .ensure_job_layout(job_id)
        .map_err(|e| PipelineError::persist(format!("failed to initialize QFS layout: {e}")))?;

    let mut compiler = CompilationServiceClient::connect(deps.compiler_endpoint.clone())
        .await
        .map_err(|e| PipelineError::compile(format!("failed to connect to compiler: {e}")))?;

    let mut compile_req = Request::new(CompileJobRequest {
        job_id: job_id.to_string(),
        language: language_for(&req),
        input: Some(crate::proto::compile_job_request::Input::Source(
            req.program,
        )),
        options: req.compiler_options,
    });
    trace_ctx.inject(&mut compile_req);

    let compile_started = Instant::now();
    let compile_res = compiler
        .compile_job(compile_req)
        .await
        .map_err(PipelineError::from_compile_status)?
        .into_inner();
    let compilation_latency_sec = compile_started.elapsed().as_secs_f64();

    let circuit_payload = compile_res.circuit.ok_or_else(|| {
        PipelineError::compile("compiler returned empty circuit payload".to_string())
    })?;

    deps.qfs
        .store_compiled_artifacts(job_id, &circuit_payload.data, None, "remote")
        .map_err(|e| {
            PipelineError::persist(format!("failed to persist compiled artifacts: {e}"))
        })?;

    store
        .apply_event(job_id, JobEvent::StartRunning)
        .map_err(|e| PipelineError::internal(format!("state transition failed: {e}")))?;

    let mut driver = DriverManagerServiceClient::connect(deps.driver_endpoint.clone())
        .await
        .map_err(|e| PipelineError::execute(format!("failed to connect to driver manager: {e}")))?;

    let device_id = if req.target.trim().is_empty() {
        deps.default_device_id.clone()
    } else {
        req.target.clone()
    };
    let retry_policy = RetryPolicy::from_metadata(&req.metadata);
    let retry_idempotent = is_execute_retry_idempotent(job_id, &req.metadata);
    let mut retry_metrics = RetryMetrics::default();

    let execute_started = Instant::now();
    let execute_res = if should_run_vqe_loop(&circuit_payload, &compile_res.metadata) {
        let vqe_res = run_vqe_loop(
            &mut driver,
            &deps,
            job_id,
            &device_id,
            &circuit_payload,
            &req.metadata,
            &trace_ctx,
            &retry_policy,
            retry_idempotent,
            &mut retry_metrics,
        )
        .await?;
        results_metadata.extend(vqe_res.results_metadata);
        vqe_res.last_execution
    } else {
        execute_with_retry(
            &mut driver,
            || {
                let mut execute_req = Request::new(ExecuteCircuitRequest {
                    job_id: job_id.to_string(),
                    device_id: device_id.clone(),
                    payload: Some(circuit_payload.clone()),
                    shots: parse_shots(&req.metadata),
                    options: req.metadata.clone(),
                });
                trace_ctx.inject(&mut execute_req);
                execute_req
            },
            &retry_policy,
            retry_idempotent,
            &mut retry_metrics,
        )
        .await?
    };
    let job_execution_duration_sec = execute_started.elapsed().as_secs_f64();

    let persisted_metadata = persist_results(
        &deps,
        job_id,
        &device_id,
        &execute_res,
        compilation_latency_sec,
        job_execution_duration_sec,
        &retry_metrics,
    )
    .map_err(|e| {
        PipelineError::persist(format!("failed to persist final execution results: {e}"))
    })?;
    results_metadata.extend(persisted_metadata);

    store.set_results_metadata(job_id, results_metadata);
    store.set_counts(job_id, execute_res.counts.clone());

    store
        .apply_event(job_id, JobEvent::Complete)
        .map_err(|e| PipelineError::internal(format!("state transition failed: {e}")))?;

    Ok(())
}

struct VqeLoopOutcome {
    last_execution: ExecuteCircuitResponse,
    results_metadata: HashMap<String, String>,
}

async fn run_vqe_loop(
    driver: &mut DriverManagerServiceClient<tonic::transport::Channel>,
    deps: &PipelineDeps,
    job_id: &str,
    device_id: &str,
    circuit_payload: &CircuitPayload,
    job_metadata: &HashMap<String, String>,
    trace_ctx: &TraceContext,
    retry_policy: &RetryPolicy,
    retry_idempotent: bool,
    retry_metrics: &mut RetryMetrics,
) -> Result<VqeLoopOutcome, PipelineError> {
    let mut params = initial_params(circuit_payload);
    let max_iters = parse_positive_usize(job_metadata, "max_iters").unwrap_or(10);
    let step_size = parse_positive_f64(job_metadata, "optimizer_step").unwrap_or(0.1);
    let shots = parse_shots(job_metadata);
    let zero_state = "0".repeat(estimate_qubits(circuit_payload));

    let mut metrics: Vec<Value> = Vec::with_capacity(max_iters);
    let mut best_objective = f64::INFINITY;
    let mut best_params = params.clone();
    let mut last_execution = None;

    for iter in 0..max_iters {
        let mut options = job_metadata.clone();
        options.insert("vqe.params".to_string(), serialize_params(&params));
        options.insert("vqe.iteration".to_string(), iter.to_string());

        let execute_res = execute_with_retry(
            driver,
            || {
                let mut execute_req = Request::new(ExecuteCircuitRequest {
                    job_id: job_id.to_string(),
                    device_id: device_id.to_string(),
                    payload: Some(circuit_payload.clone()),
                    shots,
                    options: options.clone(),
                });
                trace_ctx.inject(&mut execute_req);
                execute_req
            },
            retry_policy,
            retry_idempotent,
            retry_metrics,
        )
        .await?;

        let objective = objective_from_counts(&execute_res.counts, &zero_state);
        if objective < best_objective {
            best_objective = objective;
            best_params = params.clone();
        }
        metrics.push(json!({
            "iteration": iter,
            "params": params.clone(),
            "objective": objective,
            "counts": execute_res.counts.clone(),
        }));
        params = update_params(iter, &params, objective, step_size);
        last_execution = Some(execute_res);
    }

    let metrics_json = serde_json::to_vec_pretty(&json!({
        "version": "0.1",
        "kind": "vqe_metrics",
        "optimizer": "simple_gradient_free_step",
        "max_iters": max_iters,
        "iterations": metrics,
        "best_objective": best_objective,
        "best_params": best_params,
    }))
    .map_err(|e| PipelineError::persist(format!("serialize metrics failed: {e}")))?;
    deps.qfs
        .store_metrics_json(job_id, &metrics_json)
        .map_err(|e| PipelineError::persist(format!("store metrics failed: {e}")))?;

    let mut results_metadata = HashMap::from([
        ("vqe.enabled".to_string(), "true".to_string()),
        (
            "vqe.optimizer".to_string(),
            "simple_gradient_free_step".to_string(),
        ),
        ("vqe.iterations".to_string(), max_iters.to_string()),
        (
            "vqe.best_objective".to_string(),
            format!("{best_objective:.8}"),
        ),
        (
            "vqe.best_params".to_string(),
            serialize_params(&best_params),
        ),
        ("vqe.final_params".to_string(), serialize_params(&params)),
        (
            "vqe.metrics_ref".to_string(),
            format!("{job_id}/meta/metrics.json"),
        ),
    ]);

    if let Some(last) = &last_execution {
        results_metadata.insert(
            "vqe.last_counts_keys".to_string(),
            last.counts.len().to_string(),
        );
    }

    Ok(VqeLoopOutcome {
        last_execution: last_execution.ok_or_else(|| {
            PipelineError::execute("vqe loop produced no execution result".to_string())
        })?,
        results_metadata,
    })
}

fn should_run_vqe_loop(
    circuit_payload: &CircuitPayload,
    metadata: &HashMap<String, String>,
) -> bool {
    if metadata
        .get("hybrid_plan_marker")
        .map(|v| v == "minimize")
        .unwrap_or(false)
    {
        return true;
    }
    parse_hybrid_marker(circuit_payload)
}

fn parse_hybrid_marker(circuit_payload: &CircuitPayload) -> bool {
    let parsed: Result<Value, _> = serde_json::from_slice(&circuit_payload.data);
    parsed
        .ok()
        .and_then(|v| {
            v.get("hybrid_plan_marker")
                .and_then(|m| m.get("kind"))
                .and_then(Value::as_str)
                .map(|kind| kind == "minimize")
        })
        .unwrap_or(false)
}

fn initial_params(circuit_payload: &CircuitPayload) -> Vec<f64> {
    let parsed: Result<Value, _> = serde_json::from_slice(&circuit_payload.data);
    let count = parsed
        .ok()
        .and_then(|v| v.get("parameters").and_then(Value::as_array).map(Vec::len))
        .unwrap_or(1)
        .max(1);
    vec![0.1; count]
}

fn estimate_qubits(circuit_payload: &CircuitPayload) -> usize {
    let parsed: Result<Value, _> = serde_json::from_slice(&circuit_payload.data);
    parsed
        .ok()
        .and_then(|v| v.get("qubits").and_then(Value::as_u64))
        .map(|q| q as usize)
        .filter(|q| *q > 0)
        .unwrap_or(1)
}

fn objective_from_counts(counts: &HashMap<String, i64>, zero_state: &str) -> f64 {
    let total: i64 = counts.values().sum();
    if total <= 0 {
        return 1.0;
    }
    let ground = counts.get(zero_state).copied().unwrap_or(0) as f64;
    1.0 - (ground / total as f64)
}

fn update_params(iter: usize, params: &[f64], objective: f64, step: f64) -> Vec<f64> {
    params
        .iter()
        .enumerate()
        .map(|(idx, p)| {
            let direction = if (iter + idx) % 2 == 0 { 1.0 } else { -1.0 };
            p + direction * step * (objective - 0.5)
        })
        .collect()
}

fn serialize_params(params: &[f64]) -> String {
    params
        .iter()
        .map(|v| format!("{v:.6}"))
        .collect::<Vec<_>>()
        .join(",")
}

fn parse_positive_usize(metadata: &HashMap<String, String>, key: &str) -> Option<usize> {
    metadata
        .get(key)
        .and_then(|v| v.parse::<usize>().ok())
        .filter(|v| *v > 0)
}

fn parse_positive_f64(metadata: &HashMap<String, String>, key: &str) -> Option<f64> {
    metadata
        .get(key)
        .and_then(|v| v.parse::<f64>().ok())
        .filter(|v| *v > 0.0)
}

#[derive(Debug, Clone)]
struct RetryPolicy {
    max_attempts: u32,
    max_elapsed: Duration,
    base_delay: Duration,
    max_delay: Duration,
    jitter: Duration,
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            max_elapsed: Duration::from_secs(5),
            base_delay: Duration::from_millis(50),
            max_delay: Duration::from_secs(1),
            jitter: Duration::from_millis(25),
        }
    }
}

impl RetryPolicy {
    fn from_metadata(metadata: &HashMap<String, String>) -> Self {
        let mut policy = Self::default();
        if let Some(v) = parse_positive_usize(metadata, "retry.max_attempts") {
            policy.max_attempts = v.min(u32::MAX as usize) as u32;
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.max_elapsed_ms") {
            policy.max_elapsed = Duration::from_millis(v as u64);
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.base_delay_ms") {
            policy.base_delay = Duration::from_millis(v as u64);
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.max_delay_ms") {
            policy.max_delay = Duration::from_millis(v as u64);
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.jitter_ms") {
            policy.jitter = Duration::from_millis(v as u64);
        }
        if policy.max_attempts == 0 {
            policy.max_attempts = 1;
        }
        policy
    }
}

#[derive(Debug, Default, Clone, Copy)]
struct RetryMetrics {
    attempts: u32,
    retries: u32,
    successes_after_retry: u32,
}

fn is_retryable_code(code: Code) -> bool {
    matches!(
        code,
        Code::Unavailable | Code::DeadlineExceeded | Code::ResourceExhausted | Code::Aborted
    )
}

fn is_execute_retry_idempotent(job_id: &str, metadata: &HashMap<String, String>) -> bool {
    !job_id.trim().is_empty()
        && (metadata.contains_key("client_request_id")
            || metadata.contains_key("vqe.iteration")
            || !metadata.contains_key("non_idempotent"))
}

fn backoff_delay(policy: &RetryPolicy, attempt: u32) -> Duration {
    let exp = 1u32
        .checked_shl(attempt.saturating_sub(1))
        .unwrap_or(u32::MAX);
    let base_ms = policy.base_delay.as_millis().saturating_mul(exp as u128);
    let capped_ms = base_ms.min(policy.max_delay.as_millis()) as u64;
    let jitter_ms = if policy.jitter.is_zero() {
        0
    } else {
        pseudo_random_u64() % (policy.jitter.as_millis() as u64 + 1)
    };
    Duration::from_millis(capped_ms.saturating_add(jitter_ms))
}

fn pseudo_random_u64() -> u64 {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos() as u64;
    nanos ^ nanos.rotate_left(13) ^ 0x9E37_79B9_7F4A_7C15
}

async fn execute_with_retry<F>(
    driver: &mut DriverManagerServiceClient<tonic::transport::Channel>,
    build_request: F,
    policy: &RetryPolicy,
    retry_idempotent: bool,
    metrics: &mut RetryMetrics,
) -> Result<ExecuteCircuitResponse, PipelineError>
where
    F: Fn() -> Request<ExecuteCircuitRequest>,
{
    let started = Instant::now();
    let mut attempt = 0u32;
    loop {
        attempt += 1;
        metrics.attempts += 1;
        match driver.execute_circuit(build_request()).await {
            Ok(resp) => {
                if attempt > 1 {
                    metrics.successes_after_retry += 1;
                }
                return Ok(resp.into_inner());
            }
            Err(status) => {
                let retryable = retry_idempotent && is_retryable_code(status.code());
                let out_of_attempts = attempt >= policy.max_attempts;
                let elapsed = started.elapsed();
                let delay = backoff_delay(policy, attempt);
                let out_of_time = elapsed.saturating_add(delay) > policy.max_elapsed;
                if !retryable || out_of_attempts || out_of_time {
                    return Err(PipelineError::from_execute_status(status));
                }
                metrics.retries += 1;
                tokio::time::sleep(delay).await;
            }
        }
    }
}

fn persist_results(
    deps: &PipelineDeps,
    job_id: &str,
    device_id: &str,
    execute_res: &ExecuteCircuitResponse,
    compilation_latency_sec: f64,
    job_execution_duration_sec: f64,
    retry_metrics: &RetryMetrics,
) -> Result<HashMap<String, String>, String> {
    let counts_json = serde_json::to_vec(&json!({
        "version": "0.1",
        "format": "bitstring_counts",
        "job_id": job_id,
        "counts": execute_res.counts,
    }))
    .map_err(|e| e.to_string())?;

    let metadata_json = serde_json::to_vec(&json!({
        "version": "0.1",
        "job_id": job_id,
        "device_id": device_id,
        "execution_time_sec": execute_res.execution_time_sec,
        "backend_metadata": execute_res.metadata,
        "runtime_metrics": [
            {
                "name": "compilation_latency",
                "value_sec": compilation_latency_sec,
                "labels": {
                    "job_id": job_id,
                    "device_id": device_id,
                    "unit": "seconds",
                }
            },
            {
                "name": "job_execution_duration",
                "value_sec": job_execution_duration_sec,
                "labels": {
                    "job_id": job_id,
                    "device_id": device_id,
                    "unit": "seconds",
                }
            },
            {
                "name": "retry_attempts_total",
                "value": retry_metrics.attempts,
                "labels": {
                    "job_id": job_id,
                    "device_id": device_id,
                    "kind": "execute_circuit",
                }
            },
            {
                "name": "retry_retries_total",
                "value": retry_metrics.retries,
                "labels": {
                    "job_id": job_id,
                    "device_id": device_id,
                    "kind": "execute_circuit",
                }
            },
            {
                "name": "retry_success_after_retry_total",
                "value": retry_metrics.successes_after_retry,
                "labels": {
                    "job_id": job_id,
                    "device_id": device_id,
                    "kind": "execute_circuit",
                }
            }
        ],
    }))
    .map_err(|e| e.to_string())?;

    let parquet_like_payload = serde_json::to_vec(&json!({
        "format": "parquet.v1",
        "counts": serde_json::from_slice::<serde_json::Value>(&counts_json).unwrap_or(json!({})),
        "metadata": serde_json::from_slice::<serde_json::Value>(&metadata_json).unwrap_or(json!({})),
    }))
    .map_err(|e| e.to_string())?;

    let producer_version = env!("CARGO_PKG_VERSION");
    deps.qfs
        .store_results_bundle(job_id, &parquet_like_payload, producer_version)
        .map_err(|e| e.to_string())?;

    Ok(HashMap::from([
        ("artifact_version".to_string(), "1.0.0".to_string()),
        ("producer_version".to_string(), producer_version.to_string()),
        (
            "result_envelope_ref".to_string(),
            format!("jobs/{job_id}/results/result.json"),
        ),
        (
            "result_manifest_ref".to_string(),
            format!("jobs/{job_id}/results/manifest.json"),
        ),
    ]))
}

fn parse_shots(metadata: &HashMap<String, String>) -> i32 {
    metadata
        .get("shots")
        .and_then(|s| s.parse::<i32>().ok())
        .filter(|s| *s > 0)
        .unwrap_or(1024)
}

fn language_for(req: &EnqueueJobRequest) -> String {
    if req.program_format.trim().is_empty() {
        "eigen-lang".to_string()
    } else {
        req.program_format.clone()
    }
}

async fn fail_job(store: &JobStore, job_id: &str, err: PipelineError) {
    let _ = store.apply_event(job_id, JobEvent::Fail);

    store.set_error(
        job_id,
        canonical_grpc_code(err.code).to_string(),
        err.summary.clone(),
        Some("results/error.json".to_string()),
    );

    let qfs = CircuitFsLocal::new(
        std::env::var("EIGEN_QFS_ROOT")
            .unwrap_or_else(|_| qfs::DEFAULT_CIRCUIT_FS_ROOT.to_string()),
    );
    let details = serde_json::to_vec_pretty(&json!({
        "error_code": canonical_grpc_code(err.code),
        "error_summary": err.summary,
        "details": err.details,
    }))
    .unwrap_or_else(|_| b"{}".to_vec());
    let _ = qfs.store_error_details_json(job_id, &details);
}

#[derive(Debug)]
struct PipelineError {
    code: Code,
    summary: String,
    details: String,
}

impl PipelineError {
    fn compile(details: String) -> Self {
        Self {
            code: Code::Internal,
            summary: "Compilation failed".to_string(),
            details,
        }
    }

    fn execute(details: String) -> Self {
        Self {
            code: Code::Internal,
            summary: "Execution failed".to_string(),
            details,
        }
    }

    fn persist(details: String) -> Self {
        Self {
            code: Code::Internal,
            summary: "Persisting artifacts failed".to_string(),
            details,
        }
    }

    fn internal(details: String) -> Self {
        Self {
            code: Code::Internal,
            summary: "Kernel internal error".to_string(),
            details,
        }
    }

    fn from_compile_status(status: Status) -> Self {
        map_status(status, "compile")
    }

    fn from_execute_status(status: Status) -> Self {
        map_status(status, "execute")
    }
}

fn map_status(status: Status, stage: &str) -> PipelineError {
    let details = format!(
        "{stage} RPC failed: {} ({})",
        status.message(),
        status.code()
    );
    match status.code() {
        Code::InvalidArgument => PipelineError {
            code: Code::InvalidArgument,
            summary: "Request validation failed".to_string(),
            details,
        },
        Code::ResourceExhausted => PipelineError {
            code: Code::ResourceExhausted,
            summary: "Backend resource exhausted".to_string(),
            details,
        },
        Code::DeadlineExceeded => PipelineError {
            code: Code::DeadlineExceeded,
            summary: "Backend call timed out".to_string(),
            details,
        },
        Code::Cancelled => PipelineError {
            code: Code::Cancelled,
            summary: "Backend call cancelled".to_string(),
            details,
        },
        Code::NotFound => PipelineError {
            code: Code::NotFound,
            summary: "Requested resource was not found".to_string(),
            details,
        },
        Code::PermissionDenied => PipelineError {
            code: Code::PermissionDenied,
            summary: "Permission denied by backend".to_string(),
            details,
        },
        Code::Unavailable => PipelineError {
            code: Code::Unavailable,
            summary: "Backend unavailable".to_string(),
            details,
        },
        Code::Unimplemented => PipelineError {
            code: Code::Unimplemented,
            summary: "Unsupported target or format".to_string(),
            details,
        },
        _ => PipelineError {
            code: Code::Internal,
            summary: "Kernel internal error".to_string(),
            details,
        },
    }
}

fn canonical_grpc_code(code: Code) -> &'static str {
    match code {
        Code::Ok => "OK",
        Code::Cancelled => "CANCELLED",
        Code::Unknown => "UNKNOWN",
        Code::InvalidArgument => "INVALID_ARGUMENT",
        Code::DeadlineExceeded => "DEADLINE_EXCEEDED",
        Code::NotFound => "NOT_FOUND",
        Code::AlreadyExists => "ALREADY_EXISTS",
        Code::PermissionDenied => "PERMISSION_DENIED",
        Code::ResourceExhausted => "RESOURCE_EXHAUSTED",
        Code::FailedPrecondition => "FAILED_PRECONDITION",
        Code::Aborted => "ABORTED",
        Code::OutOfRange => "OUT_OF_RANGE",
        Code::Unimplemented => "UNIMPLEMENTED",
        Code::Internal => "INTERNAL",
        Code::Unavailable => "UNAVAILABLE",
        Code::DataLoss => "DATA_LOSS",
        Code::Unauthenticated => "UNAUTHENTICATED",
    }
}

fn status_from_record(rec: &JobRecord) -> GetJobStatusResponse {
    GetJobStatusResponse {
        job_id: rec.job_id.clone(),
        state: to_proto_state(rec.state) as i32,
        stage: format!("{:?}", rec.state).to_uppercase(),
        progress: progress_for(rec.state),
        message: String::new(),
        error_code: rec.error_code.clone().unwrap_or_default(),
        error_summary: rec.error_summary.clone().unwrap_or_default(),
        error_details_ref: rec.error_details_ref.clone().unwrap_or_default(),
        updated_at: Some(ts_from_unix_ms(rec.updated_at_unix_ms)),
    }
}

fn progress_for(state: JobState) -> f32 {
    match state {
        JobState::Pending => 0.0,
        JobState::Compiling => 0.25,
        JobState::Running => 0.75,
        JobState::Done | JobState::Error | JobState::Cancelled | JobState::Timeout => 1.0,
    }
}

fn to_proto_state(state: JobState) -> TaskState {
    match state {
        JobState::Pending => TaskState::Pending,
        JobState::Compiling => TaskState::Compiling,
        JobState::Running => TaskState::Running,
        JobState::Done => TaskState::Done,
        JobState::Error => TaskState::Error,
        JobState::Cancelled => TaskState::Cancelled,
        JobState::Timeout => TaskState::Error,
    }
}

fn ts_now() -> prost_types::Timestamp {
    let ms = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as i64;
    ts_from_unix_ms(ms)
}

fn ts_from_unix_ms(ms: i64) -> prost_types::Timestamp {
    let secs = ms / 1_000;
    let nanos = ((ms % 1_000) * 1_000_000) as i32;
    prost_types::Timestamp {
        seconds: secs,
        nanos,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::proto::compilation_service_server::CompilationServiceServer;
    use crate::proto::driver_manager_service_server::DriverManagerServiceServer;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::{Mutex, OnceLock};
    use tempfile::TempDir;
    use tokio::time::{Duration, sleep};

    #[derive(Clone, Debug, PartialEq, Eq)]
    struct TraceCapture {
        traceparent: Option<String>,
        trace_id: Option<String>,
    }

    fn compiler_trace_store() -> &'static Mutex<Vec<TraceCapture>> {
        static STORE: OnceLock<Mutex<Vec<TraceCapture>>> = OnceLock::new();
        STORE.get_or_init(|| Mutex::new(Vec::new()))
    }

    fn driver_trace_store() -> &'static Mutex<Vec<TraceCapture>> {
        static STORE: OnceLock<Mutex<Vec<TraceCapture>>> = OnceLock::new();
        STORE.get_or_init(|| Mutex::new(Vec::new()))
    }

    fn driver_attempt_counter() -> &'static AtomicUsize {
        static COUNTER: OnceLock<AtomicUsize> = OnceLock::new();
        COUNTER.get_or_init(|| AtomicUsize::new(0))
    }

    #[derive(Default)]
    struct MockCompiler;

    #[tonic::async_trait]
    impl compilation_service_server::CompilationService for MockCompiler {
        async fn compile_circuit(
            &self,
            _request: Request<CompileCircuitRequest>,
        ) -> Result<Response<CompileCircuitResponse>, Status> {
            Err(Status::unimplemented("not used"))
        }

        async fn compile_job(
            &self,
            request: Request<CompileJobRequest>,
        ) -> Result<Response<CompileJobResponse>, Status> {
            let traceparent = request
                .metadata()
                .get("traceparent")
                .and_then(|v| v.to_str().ok())
                .map(|v| v.to_string());
            let trace_id = request
                .metadata()
                .get("trace_id")
                .and_then(|v| v.to_str().ok())
                .map(|v| v.to_string());
            compiler_trace_store().lock().unwrap().push(TraceCapture {
                traceparent,
                trace_id,
            });
            let req = request.into_inner();
            if req.language == "bad" {
                return Err(Status::invalid_argument("bad language"));
            }
            let mut metadata = HashMap::new();
            if let Some(crate::proto::compile_job_request::Input::Source(ref source_bytes)) =
                req.input
            {
                let program_text = String::from_utf8_lossy(source_bytes);
                if program_text.contains("minimize") {
                    metadata.insert("hybrid_plan_marker".to_string(), "minimize".to_string());
                }
            }
            Ok(Response::new(CompileJobResponse {
                job_id: req.job_id,
                circuit: Some(CircuitPayload {
                    format: CircuitFormat::AqoJson as i32,
                    data: br#"{"aqo":"ok"}"#.to_vec(),
                }),
                metadata,
            }))
        }

        async fn optimize_circuit(
            &self,
            _request: Request<crate::proto::OptimizeCircuitRequest>,
        ) -> Result<Response<crate::proto::OptimizeCircuitResponse>, Status> {
            Err(Status::unimplemented("not used"))
        }

        async fn validate_circuit(
            &self,
            _request: Request<ValidateCircuitRequest>,
        ) -> Result<Response<ValidateCircuitResponse>, Status> {
            Err(Status::unimplemented("not used"))
        }
    }

    #[derive(Default)]
    struct MockDriver;

    #[tonic::async_trait]
    impl driver_manager_service_server::DriverManagerService for MockDriver {
        async fn list_devices(
            &self,
            _request: Request<ListDevicesRequest>,
        ) -> Result<Response<ListDevicesResponse>, Status> {
            Err(Status::unimplemented("not used"))
        }

        async fn get_device_status(
            &self,
            _request: Request<GetDeviceStatusRequest>,
        ) -> Result<Response<GetDeviceStatusResponse>, Status> {
            Err(Status::unimplemented("not used"))
        }

        async fn execute_circuit(
            &self,
            request: Request<ExecuteCircuitRequest>,
        ) -> Result<Response<ExecuteCircuitResponse>, Status> {
            driver_attempt_counter().fetch_add(1, Ordering::SeqCst);
            let traceparent = request
                .metadata()
                .get("traceparent")
                .and_then(|v| v.to_str().ok())
                .map(|v| v.to_string());
            let trace_id = request
                .metadata()
                .get("trace_id")
                .and_then(|v| v.to_str().ok())
                .map(|v| v.to_string());
            driver_trace_store().lock().unwrap().push(TraceCapture {
                traceparent,
                trace_id,
            });
            if request.get_ref().device_id == "bad-device" {
                return Err(Status::unavailable("backend down"));
            }
            if let Some(failures) = request
                .get_ref()
                .options
                .get("retry.failures_before_success")
            {
                let fail_n = failures.parse::<usize>().unwrap_or(0);
                let current = driver_attempt_counter().load(Ordering::SeqCst);
                if current <= fail_n {
                    let code = match request
                        .get_ref()
                        .options
                        .get("retry.error_code")
                        .map(|s| s.as_str())
                    {
                        Some("deadline_exceeded") => Code::DeadlineExceeded,
                        Some("resource_exhausted") => Code::ResourceExhausted,
                        Some("invalid_argument") => Code::InvalidArgument,
                        _ => Code::Unavailable,
                    };
                    return Err(Status::new(code, "simulated transient"));
                }
            }
            if let Some(params) = request.get_ref().options.get("vqe.params") {
                let score = params
                    .split(',')
                    .filter_map(|v| v.parse::<f64>().ok())
                    .map(|v| v.abs())
                    .sum::<f64>();
                let good = ((1024.0 - score * 200.0).round() as i64).clamp(0, 1024);
                return Ok(Response::new(ExecuteCircuitResponse {
                    counts: HashMap::from([
                        ("00".to_string(), good),
                        ("11".to_string(), 1024 - good),
                    ]),
                    execution_time_sec: 0.02,
                    metadata: HashMap::from([("backend".to_string(), "simulator".to_string())]),
                }));
            }
            Ok(Response::new(ExecuteCircuitResponse {
                counts: HashMap::from([("00".to_string(), 1024)]),
                execution_time_sec: 0.02,
                metadata: HashMap::from([("backend".to_string(), "simulator".to_string())]),
            }))
        }

        async fn calibrate_device(
            &self,
            _request: Request<CalibrateDeviceRequest>,
        ) -> Result<Response<CalibrateDeviceResponse>, Status> {
            Err(Status::unimplemented("not used"))
        }
    }

    #[tokio::test]
    async fn integration_submit_to_done_and_results_written() {
        driver_attempt_counter().store(0, Ordering::SeqCst);
        let temp_qfs = TempDir::new().unwrap();
        let compiler_addr: SocketAddr = "127.0.0.1:50171".parse().unwrap();
        let driver_addr: SocketAddr = "127.0.0.1:50172".parse().unwrap();

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(CompilationServiceServer::new(MockCompiler))
                .serve(compiler_addr)
                .await
                .unwrap();
        });

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(DriverManagerServiceServer::new(MockDriver))
                .serve(driver_addr)
                .await
                .unwrap();
        });

        sleep(Duration::from_millis(80)).await;

        let svc = KernelGatewaySvc {
            store: JobStore::default(),
            deps: PipelineDeps {
                compiler_endpoint: "http://127.0.0.1:50171".to_string(),
                driver_endpoint: "http://127.0.0.1:50172".to_string(),
                default_device_id: "sim:local".to_string(),
                qfs: CircuitFsLocal::new(temp_qfs.path()),
            },
        };

        let enqueue = svc
            .enqueue_job(Request::new(EnqueueJobRequest {
                name: "test-job".to_string(),
                program: b"x".to_vec(),
                program_format: "eigen-lang".to_string(),
                target: "sim:local".to_string(),
                priority: 1,
                compiler_options: HashMap::new(),
                metadata: HashMap::from([("shots".to_string(), "1024".to_string())]),
            }))
            .await
            .unwrap()
            .into_inner();

        let job_id = enqueue.job_id;

        for _ in 0..30 {
            let status = svc
                .get_job_status(Request::new(GetJobStatusRequest {
                    job_id: job_id.clone(),
                }))
                .await
                .unwrap()
                .into_inner();
            if status.state == TaskState::Done as i32 {
                break;
            }
            sleep(Duration::from_millis(30)).await;
        }

        let status = svc
            .get_job_status(Request::new(GetJobStatusRequest {
                job_id: job_id.clone(),
            }))
            .await
            .unwrap()
            .into_inner();
        assert_eq!(status.state, TaskState::Done as i32);

        let results = svc
            .get_job_results(Request::new(GetJobResultsRequest {
                job_id: job_id.clone(),
            }))
            .await
            .unwrap()
            .into_inner();
        assert_eq!(results.state, TaskState::Done as i32);
        assert_eq!(results.counts.get("00"), Some(&1024));

        let bundle = CircuitFsLocal::new(temp_qfs.path())
            .load_results_bundle(&job_id)
            .unwrap();
        assert!(!bundle.parquet.is_empty());
    }

    #[tokio::test]
    async fn compile_error_maps_to_error_state() {
        driver_attempt_counter().store(0, Ordering::SeqCst);
        let temp_qfs = TempDir::new().unwrap();
        let compiler_addr: SocketAddr = "127.0.0.1:50173".parse().unwrap();
        let driver_addr: SocketAddr = "127.0.0.1:50174".parse().unwrap();

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(CompilationServiceServer::new(MockCompiler))
                .serve(compiler_addr)
                .await
                .unwrap();
        });

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(DriverManagerServiceServer::new(MockDriver))
                .serve(driver_addr)
                .await
                .unwrap();
        });

        sleep(Duration::from_millis(80)).await;

        let svc = KernelGatewaySvc {
            store: JobStore::default(),
            deps: PipelineDeps {
                compiler_endpoint: "http://127.0.0.1:50173".to_string(),
                driver_endpoint: "http://127.0.0.1:50174".to_string(),
                default_device_id: "sim:local".to_string(),
                qfs: CircuitFsLocal::new(temp_qfs.path()),
            },
        };

        let job_id = svc
            .enqueue_job(Request::new(EnqueueJobRequest {
                name: "test-job".to_string(),
                program: b"x".to_vec(),
                program_format: "bad".to_string(),
                target: "sim:local".to_string(),
                priority: 1,
                compiler_options: HashMap::new(),
                metadata: HashMap::new(),
            }))
            .await
            .unwrap()
            .into_inner()
            .job_id;

        for _ in 0..30 {
            let status = svc
                .get_job_status(Request::new(GetJobStatusRequest {
                    job_id: job_id.clone(),
                }))
                .await
                .unwrap()
                .into_inner();
            if status.state == TaskState::Error as i32 {
                assert_eq!(status.error_code, "INVALID_ARGUMENT");
                assert_eq!(status.error_details_ref, "results/error.json");
                return;
            }
            sleep(Duration::from_millis(30)).await;
        }

        panic!("job never transitioned to ERROR state");
    }

    #[tokio::test]
    async fn integration_vqe_loop_persists_metrics_and_results_metadata() {
        driver_attempt_counter().store(0, Ordering::SeqCst);
        let temp_qfs = TempDir::new().unwrap();
        let compiler_addr: SocketAddr = "127.0.0.1:50175".parse().unwrap();
        let driver_addr: SocketAddr = "127.0.0.1:50176".parse().unwrap();

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(CompilationServiceServer::new(MockCompiler))
                .serve(compiler_addr)
                .await
                .unwrap();
        });

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(DriverManagerServiceServer::new(MockDriver))
                .serve(driver_addr)
                .await
                .unwrap();
        });

        sleep(Duration::from_millis(80)).await;

        let svc = KernelGatewaySvc {
            store: JobStore::default(),
            deps: PipelineDeps {
                compiler_endpoint: "http://127.0.0.1:50175".to_string(),
                driver_endpoint: "http://127.0.0.1:50176".to_string(),
                default_device_id: "sim:local".to_string(),
                qfs: CircuitFsLocal::new(temp_qfs.path()),
            },
        };

        let program = br#"
from eigen_lang import Param, ExpectationValue, hybrid_program, minimize

@hybrid_program
def vqe_program():
    theta1 = Param("theta1")
    theta2 = Param("theta2")
    ExpectationValue("Z0 + Z1")
    minimize(lambda: 0.0, [0.1, 0.2])
"#
        .to_vec();

        let job_id = svc
            .enqueue_job(Request::new(EnqueueJobRequest {
                name: "vqe-2q".to_string(),
                program,
                program_format: "eigen-lang".to_string(),
                target: "sim:local".to_string(),
                priority: 1,
                compiler_options: HashMap::new(),
                metadata: HashMap::from([("max_iters".to_string(), "5".to_string())]),
            }))
            .await
            .unwrap()
            .into_inner()
            .job_id;

        for _ in 0..40 {
            let status = svc
                .get_job_status(Request::new(GetJobStatusRequest {
                    job_id: job_id.clone(),
                }))
                .await
                .unwrap()
                .into_inner();
            if status.state == TaskState::Done as i32 {
                break;
            }
            sleep(Duration::from_millis(30)).await;
        }

        let results = svc
            .get_job_results(Request::new(GetJobResultsRequest {
                job_id: job_id.clone(),
            }))
            .await
            .unwrap()
            .into_inner();
        assert_eq!(results.state, TaskState::Done as i32);
        assert_eq!(
            results.metadata.get("vqe.enabled"),
            Some(&"true".to_string())
        );
        assert_eq!(
            results.metadata.get("vqe.iterations"),
            Some(&"5".to_string())
        );
        assert!(results.metadata.contains_key("vqe.final_params"));
        assert!(results.metadata.contains_key("vqe.best_objective"));
        assert_eq!(
            results.metadata.get("artifact_version"),
            Some(&"1.0.0".to_string())
        );
        assert!(results.metadata.contains_key("producer_version"));
        assert_eq!(
            results.metadata.get("result_envelope_ref"),
            Some(&format!("jobs/{job_id}/results/result.json"))
        );
        assert_eq!(
            results.metadata.get("result_manifest_ref"),
            Some(&format!("jobs/{job_id}/results/manifest.json"))
        );
        assert!(results.counts.contains_key("00"));

        let metrics_path = CircuitFsLocal::new(temp_qfs.path())
            .metrics_json_path(&job_id)
            .unwrap();
        let metrics_raw = std::fs::read(metrics_path).unwrap();
        let metrics_json: serde_json::Value = serde_json::from_slice(&metrics_raw).unwrap();
        assert_eq!(metrics_json["kind"], "vqe_metrics");
        assert_eq!(metrics_json["iterations"].as_array().unwrap().len(), 5);

        let bundle = CircuitFsLocal::new(temp_qfs.path())
            .load_results_bundle(&job_id)
            .unwrap();
        let parquet_payload: serde_json::Value = serde_json::from_slice(&bundle.parquet).unwrap();
        assert_eq!(bundle.envelope.artifact_version, "1.0.0");
        assert_eq!(bundle.envelope.job_id, job_id);
        assert_eq!(bundle.manifest.schema_version, "result_manifest.v1");
        assert_eq!(bundle.manifest.artifacts.len(), 2);
        let runtime_metrics = parquet_payload["metadata"]["runtime_metrics"]
            .as_array()
            .unwrap();
        assert!(runtime_metrics.iter().any(|item| {
            item["name"] == "job_execution_duration"
                && item["labels"]["job_id"] == job_id
                && item["labels"]["device_id"] == "sim:local"
                && item["labels"]["unit"] == "seconds"
        }));
        assert!(runtime_metrics.iter().any(|item| {
            item["name"] == "compilation_latency"
                && item["labels"]["job_id"] == job_id
                && item["labels"]["device_id"] == "sim:local"
                && item["labels"]["unit"] == "seconds"
        }));
    }

    #[tokio::test]
    async fn integration_propagates_trace_id_and_traceparent_to_compiler_and_driver() {
        driver_attempt_counter().store(0, Ordering::SeqCst);
        compiler_trace_store().lock().unwrap().clear();
        driver_trace_store().lock().unwrap().clear();
        let temp_qfs = TempDir::new().unwrap();
        let compiler_addr: SocketAddr = "127.0.0.1:50177".parse().unwrap();
        let driver_addr: SocketAddr = "127.0.0.1:50178".parse().unwrap();

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(CompilationServiceServer::new(MockCompiler))
                .serve(compiler_addr)
                .await
                .unwrap();
        });
        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(DriverManagerServiceServer::new(MockDriver))
                .serve(driver_addr)
                .await
                .unwrap();
        });
        sleep(Duration::from_millis(80)).await;

        let svc = KernelGatewaySvc {
            store: JobStore::default(),
            deps: PipelineDeps {
                compiler_endpoint: "http://127.0.0.1:50177".to_string(),
                driver_endpoint: "http://127.0.0.1:50178".to_string(),
                default_device_id: "sim:local".to_string(),
                qfs: CircuitFsLocal::new(temp_qfs.path()),
            },
        };

        let mut req = Request::new(EnqueueJobRequest {
            name: "trace-propagation".to_string(),
            program: b"x".to_vec(),
            program_format: "eigen-lang".to_string(),
            target: "sim:local".to_string(),
            priority: 1,
            compiler_options: HashMap::new(),
            metadata: HashMap::new(),
        });
        let traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";
        let trace_id = "4bf92f3577b34da6a3ce929d0e0e4736";
        req.metadata_mut()
            .insert("traceparent", traceparent.parse().unwrap());
        req.metadata_mut()
            .insert("trace_id", trace_id.parse().unwrap());

        let job_id = svc.enqueue_job(req).await.unwrap().into_inner().job_id;
        for _ in 0..40 {
            let status = svc
                .get_job_status(Request::new(GetJobStatusRequest {
                    job_id: job_id.clone(),
                }))
                .await
                .unwrap()
                .into_inner();
            if status.state == TaskState::Done as i32 {
                break;
            }
            sleep(Duration::from_millis(30)).await;
        }

        assert!(compiler_trace_store().lock().unwrap().iter().any(|entry| {
            entry.traceparent.as_deref() == Some(traceparent)
                && entry.trace_id.as_deref() == Some(trace_id)
        }));
        assert!(driver_trace_store().lock().unwrap().iter().any(|entry| {
            entry.traceparent.as_deref() == Some(traceparent)
                && entry.trace_id.as_deref() == Some(trace_id)
        }));
    }

    #[test]
    fn retryable_error_matrix_is_classified_correctly() {
        assert!(is_retryable_code(Code::Unavailable));
        assert!(is_retryable_code(Code::DeadlineExceeded));
        assert!(is_retryable_code(Code::ResourceExhausted));
        assert!(is_retryable_code(Code::Aborted));
        assert!(!is_retryable_code(Code::InvalidArgument));
        assert!(!is_retryable_code(Code::PermissionDenied));
        assert!(!is_retryable_code(Code::Unimplemented));
    }

    #[tokio::test]
    async fn integration_retries_transient_failures_and_exposes_retry_metrics() {
        driver_attempt_counter().store(0, Ordering::SeqCst);
        let temp_qfs = TempDir::new().unwrap();
        let compiler_addr: SocketAddr = "127.0.0.1:50179".parse().unwrap();
        let driver_addr: SocketAddr = "127.0.0.1:50180".parse().unwrap();

        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(CompilationServiceServer::new(MockCompiler))
                .serve(compiler_addr)
                .await
                .unwrap();
        });
        tokio::spawn(async move {
            tonic::transport::Server::builder()
                .add_service(DriverManagerServiceServer::new(MockDriver))
                .serve(driver_addr)
                .await
                .unwrap();
        });
        sleep(Duration::from_millis(80)).await;

        let svc = KernelGatewaySvc {
            store: JobStore::default(),
            deps: PipelineDeps {
                compiler_endpoint: "http://127.0.0.1:50179".to_string(),
                driver_endpoint: "http://127.0.0.1:50180".to_string(),
                default_device_id: "sim:local".to_string(),
                qfs: CircuitFsLocal::new(temp_qfs.path()),
            },
        };

        let mut metadata = HashMap::new();
        metadata.insert("retry.failures_before_success".to_string(), "2".to_string());
        metadata.insert("retry.error_code".to_string(), "unavailable".to_string());
        metadata.insert("retry.max_attempts".to_string(), "4".to_string());
        metadata.insert("retry.max_elapsed_ms".to_string(), "2500".to_string());
        metadata.insert("retry.base_delay_ms".to_string(), "5".to_string());
        metadata.insert("retry.jitter_ms".to_string(), "0".to_string());

        let job_id = svc
            .enqueue_job(Request::new(EnqueueJobRequest {
                name: "retry-job".to_string(),
                program: b"x".to_vec(),
                program_format: "eigen-lang".to_string(),
                target: "sim:local".to_string(),
                priority: 1,
                compiler_options: HashMap::new(),
                metadata,
            }))
            .await
            .unwrap()
            .into_inner()
            .job_id;
        for _ in 0..50 {
            let status = svc
                .get_job_status(Request::new(GetJobStatusRequest {
                    job_id: job_id.clone(),
                }))
                .await
                .unwrap()
                .into_inner();
            if status.state == TaskState::Done as i32 {
                break;
            }
            sleep(Duration::from_millis(20)).await;
        }

        let bundle = CircuitFsLocal::new(temp_qfs.path())
            .load_results_bundle(&job_id)
            .unwrap();
        let payload: serde_json::Value = serde_json::from_slice(&bundle.parquet).unwrap();
        let runtime_metrics = payload["metadata"]["runtime_metrics"].as_array().unwrap();
        assert!(
            runtime_metrics
                .iter()
                .any(|m| { m["name"] == "retry_attempts_total" && m["value"] == 3 })
        );
        assert!(
            runtime_metrics
                .iter()
                .any(|m| { m["name"] == "retry_success_after_retry_total" && m["value"] == 1 })
        );
    }
}
