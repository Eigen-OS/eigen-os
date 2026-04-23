//! Internal gRPC server: KernelGateway.

use std::collections::HashMap;
use std::net::SocketAddr;
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::json;
use tonic::{Code, Request, Response, Status};
use tracing::Instrument;

use crate::job_store::{JobRecord, JobStore};
use crate::proto::compilation_service_client::CompilationServiceClient;
use crate::proto::driver_manager_service_client::DriverManagerServiceClient;
use crate::proto::kernel_gateway_server::{KernelGateway, KernelGatewayServer};
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
        .add_service(KernelGatewayServer::new(svc))
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

#[tonic::async_trait]
impl KernelGateway for KernelGatewaySvc {
    async fn enqueue_job(
        &self,
        request: Request<EnqueueJobRequest>,
    ) -> Result<Response<EnqueueJobResponse>, Status> {
        let req = request.into_inner();
        if req.name.trim().is_empty() {
            return Err(Status::invalid_argument("name is required"));
        }

        let record = self.store.create_job(req.name);
        let job_id = record.job_id.clone();

        let store = self.store.clone_handle();
        let deps = self.deps.clone();
        tokio::spawn(async move {
            let span = tracing::info_span!("job_pipeline", job_id = %job_id);
            async move {
                if let Err(err) = run_pipeline(store.clone_handle(), deps, &job_id, req).await {
                    tracing::error!(job_id = %job_id, error = %err, "job pipeline failed");
                    fail_job(&store, &job_id, err).await;
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
            JobState::Done | JobState::Error | JobState::Cancelled => false,
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
            metadata: HashMap::from([("results_ref".to_string(), format!("{job_id}/results"))]),
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
) -> Result<(), PipelineError> {
    store
        .apply_event(job_id, JobEvent::StartCompiling)
        .map_err(|e| PipelineError::internal(format!("state transition failed: {e}")))?;

    deps.qfs
        .ensure_job_layout(job_id)
        .map_err(|e| PipelineError::persist(format!("failed to initialize QFS layout: {e}")))?;

    let mut compiler = CompilationServiceClient::connect(deps.compiler_endpoint.clone())
        .await
        .map_err(|e| PipelineError::compile(format!("failed to connect to compiler: {e}")))?;

    let compile_res = compiler
        .compile_job(Request::new(CompileJobRequest {
            job_id: job_id.to_string(),
            language: language_for(&req),
            input: Some(crate::proto::compile_job_request::Input::Source(
                req.program,
            )),
            options: req.compiler_options,
        }))
        .await
        .map_err(PipelineError::from_compile_status)?
        .into_inner();

    let circuit_payload = compile_res.circuit.ok_or_else(|| {
        PipelineError::compile("compiler returned empty circuit payload".to_string())
    })?;

    deps.qfs
        .store_compiled_artifacts(job_id, &circuit_payload.data, None, "remote")
        .map_err(|e| {
            PipelineError::persist(format!("failed to persist compiled artifacts: {e}"))
        })?;

    store
        .apply_event(job_id, JobEvent::FinishCompiling)
        .map_err(|e| PipelineError::internal(format!("state transition failed: {e}")))?;
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

    let execute_res = driver
        .execute_circuit(Request::new(ExecuteCircuitRequest {
            job_id: job_id.to_string(),
            device_id: device_id.clone(),
            payload: Some(circuit_payload),
            shots: parse_shots(&req.metadata),
            options: req.metadata,
        }))
        .await
        .map_err(PipelineError::from_execute_status)?
        .into_inner();

    persist_results(&deps, job_id, &device_id, &execute_res)
        .map_err(|e| PipelineError::persist(format!("failed to persist results: {e}")))?;

    store.set_counts(job_id, execute_res.counts);
    store
        .apply_event(job_id, JobEvent::FinishRunningOk)
        .map_err(|e| PipelineError::internal(format!("state transition failed: {e}")))?;

    Ok(())
}

fn persist_results(
    deps: &PipelineDeps,
    job_id: &str,
    device_id: &str,
    execute_res: &ExecuteCircuitResponse,
) -> Result<(), String> {
    let counts_json = serde_json::to_vec_pretty(&json!({
        "version": "0.1",
        "format": "bitstring_counts",
        "job_id": job_id,
        "counts": execute_res.counts,
    }))
    .map_err(|e| e.to_string())?;

    let metadata_json = serde_json::to_vec_pretty(&json!({
        "version": "0.1",
        "job_id": job_id,
        "device_id": device_id,
        "execution_time_sec": execute_res.execution_time_sec,
        "backend_metadata": execute_res.metadata,
    }))
    .map_err(|e| e.to_string())?;

    deps.qfs
        .store_results_bundle(job_id, &counts_json, &metadata_json)
        .map_err(|e| e.to_string())
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
        err.code.to_string(),
        err.summary.clone(),
        Some("results/error.json".to_string()),
    );

    let qfs = CircuitFsLocal::new(
        std::env::var("EIGEN_QFS_ROOT")
            .unwrap_or_else(|_| qfs::DEFAULT_CIRCUIT_FS_ROOT.to_string()),
    );
    let details = serde_json::to_vec_pretty(&json!({
        "error_code": err.code,
        "error_summary": err.summary,
        "details": err.details,
    }))
    .unwrap_or_else(|_| b"{}".to_vec());
    let _ = qfs.store_error_details_json(job_id, &details);
}

#[derive(Debug)]
struct PipelineError {
    code: &'static str,
    summary: String,
    details: String,
}

impl PipelineError {
    fn compile(details: String) -> Self {
        Self {
            code: "EIGEN_COMPILE_ERROR",
            summary: "Compilation failed".to_string(),
            details,
        }
    }

    fn execute(details: String) -> Self {
        Self {
            code: "EIGEN_EXECUTE_ERROR",
            summary: "Execution failed".to_string(),
            details,
        }
    }

    fn persist(details: String) -> Self {
        Self {
            code: "EIGEN_PERSIST_ERROR",
            summary: "Persisting artifacts failed".to_string(),
            details,
        }
    }

    fn internal(details: String) -> Self {
        Self {
            code: "EIGEN_INTERNAL_ERROR",
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
            code: "EIGEN_INVALID_ARGUMENT",
            summary: "Request validation failed".to_string(),
            details,
        },
        Code::Unavailable => PipelineError {
            code: "EIGEN_BACKEND_UNAVAILABLE",
            summary: "Backend unavailable".to_string(),
            details,
        },
        Code::Unimplemented => PipelineError {
            code: "EIGEN_UNSUPPORTED_TARGET",
            summary: "Unsupported target or format".to_string(),
            details,
        },
        _ => PipelineError {
            code: "EIGEN_INTERNAL_ERROR",
            summary: "Kernel internal error".to_string(),
            details,
        },
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
        JobState::Queued => 0.5,
        JobState::Running => 0.75,
        JobState::Done => 1.0,
        JobState::Error | JobState::Cancelled => 1.0,
    }
}

fn to_proto_state(state: JobState) -> TaskState {
    match state {
        JobState::Pending => TaskState::Pending,
        JobState::Compiling => TaskState::Compiling,
        JobState::Queued => TaskState::Queued,
        JobState::Running => TaskState::Running,
        JobState::Done => TaskState::Done,
        JobState::Error => TaskState::Error,
        JobState::Cancelled => TaskState::Cancelled,
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
    use tempfile::TempDir;
    use tokio::time::{Duration, sleep};

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
            let req = request.into_inner();
            if req.language == "bad" {
                return Err(Status::invalid_argument("bad language"));
            }
            Ok(Response::new(CompileJobResponse {
                job_id: req.job_id,
                circuit: Some(CircuitPayload {
                    format: CircuitFormat::AqoJson as i32,
                    data: br#"{"aqo":"ok"}"#.to_vec(),
                }),
                metadata: HashMap::new(),
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
            if request.get_ref().device_id == "bad-device" {
                return Err(Status::unavailable("backend down"));
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
        assert!(!bundle.counts_json.is_empty());
        assert!(!bundle.metadata_json.is_empty());
    }

    #[tokio::test]
    async fn compile_error_maps_to_error_state() {
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
                assert_eq!(status.error_code, "EIGEN_INVALID_ARGUMENT");
                assert_eq!(status.error_details_ref, "results/error.json");
                return;
            }
            sleep(Duration::from_millis(30)).await;
        }

        panic!("job never transitioned to ERROR state");
    }
}
