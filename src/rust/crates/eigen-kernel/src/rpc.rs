//! Internal gRPC server: KernelGateway.

use std::collections::HashMap;
use std::net::SocketAddr;
use std::time::{SystemTime, UNIX_EPOCH};

use tokio::time::{sleep, Duration};
use tonic::{Request, Response, Status};
use tracing::Instrument;

use crate::job_store::{JobRecord, JobStore};
use crate::proto::kernel_gateway_server::{KernelGateway, KernelGatewayServer};
use crate::proto::{
    CancelJobRequest, CancelJobResponse, EnqueueJobRequest, EnqueueJobResponse,
    GetJobResultsRequest, GetJobResultsResponse, GetJobStatusRequest, GetJobStatusResponse,
    TaskState,
};
use qrtx::state_machine::{JobEvent, JobState};

/// Runs the kernel gRPC server on the provided address.
pub async fn serve(addr: SocketAddr) -> Result<(), Box<dyn std::error::Error>> {
    let store = JobStore::default();
    let svc = KernelGatewaySvc { store };

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

        // MVP pipeline simulation: compile -> queue -> run -> done.
        // Deterministic transition rules are enforced by qrtx::state_machine.
        let store = self.store.clone_handle();
        tokio::spawn(async move {
            let span = tracing::info_span!("job_pipeline", job_id = %job_id);
            async move {
                // Start compiling
                if store.apply_event(&job_id, JobEvent::StartCompiling).is_err() {
                    return;
                }
                sleep(Duration::from_millis(50)).await;

                // Finish compiling -> queued
                if store.apply_event(&job_id, JobEvent::FinishCompiling).is_err() {
                    return;
                }
                sleep(Duration::from_millis(50)).await;

                // Start running
                if store.apply_event(&job_id, JobEvent::StartRunning).is_err() {
                    return;
                }
                sleep(Duration::from_millis(50)).await;

                // Finish
                if store.apply_event(&job_id, JobEvent::FinishRunningOk).is_err() {
                    return;
                }

                // Placeholder results.
                let mut counts = HashMap::new();
                counts.insert("0".to_string(), 0);
                store.set_counts(&job_id, counts);
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
            metadata: HashMap::new(),
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
    prost_types::Timestamp { seconds: secs, nanos }
}
