
//! KernelGateway internal runtime with deterministic DAG orchestration.
//!
//! Product 1.0 Wave 2:
//! - stage-by-stage orchestration DAG
//! - stable stage IDs for tracing and replay
//! - explicit fixture adapters for downstream handoff points
//! - canonical terminal state / error metadata propagation

use std::collections::{BTreeMap, HashMap, VecDeque};
use std::fmt;
use std::net::SocketAddr;
use std::pin::Pin;
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use std::time::Instant;

use parking_lot::Mutex;
use tokio_stream::iter;
use tokio_stream::Stream;
use tonic::{Code, Request, Response, Status};
use tracing::Instrument;

use qfs::CircuitFsLocal;

use crate::proto::kernel_gateway_service_server::{
    KernelGatewayService, KernelGatewayServiceServer,
};
use crate::proto::stream_job_updates_response::JobUpdateEnvelope;
use crate::proto::{
    CancelJobRequest, CancelJobResponse, DispatchRationale, EnqueueJobRequest,
    EnqueueJobResponse, GetDispatchRationaleRequest, GetDispatchRationaleResponse,
    GetJobResultsRequest, GetJobResultsResponse, GetJobStatusRequest, GetJobStatusResponse,
    RequestMetadata, StreamJobUpdatesRequest, StreamJobUpdatesResponse, TaskState,
};

/// Runs the kernel gRPC server on the provided address.
pub async fn serve(addr: SocketAddr) -> Result<(), Box<dyn std::error::Error>> {
    let runtime = Arc::new(KernelRuntimeStore::default());
    let adapters = Arc::new(FixtureAdapters::from_env());
    let svc = KernelGatewaySvc::new(runtime, adapters);

    tracing::info!(%addr, "kernel gRPC server starting");
    tonic::transport::Server::builder()
        .add_service(KernelGatewayServiceServer::new(svc))
        .serve(addr)
        .await?;
    Ok(())
}

#[derive(Clone)]
struct KernelGatewaySvc {
    runtime: Arc<KernelRuntimeStore>,
    adapters: Arc<dyn OrchestrationAdapters>,
}

impl KernelGatewaySvc {
    fn new(runtime: Arc<KernelRuntimeStore>, adapters: Arc<dyn OrchestrationAdapters>) -> Self {
        Self { runtime, adapters }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum DagStageKind {
    ValidateEnqueue,
    Compile,
    Optimize,
    Schedule,
    Execute,
    Persist,
    RecordKnowledgeObservability,
    Finalize,
}

impl DagStageKind {
    const ALL: [DagStageKind; 8] = [
        DagStageKind::ValidateEnqueue,
        DagStageKind::Compile,
        DagStageKind::Optimize,
        DagStageKind::Schedule,
        DagStageKind::Execute,
        DagStageKind::Persist,
        DagStageKind::RecordKnowledgeObservability,
        DagStageKind::Finalize,
    ];

    fn all() -> &'static [DagStageKind] {
        &Self::ALL
    }

    fn index(self) -> u32 {
        match self {
            DagStageKind::ValidateEnqueue => 1,
            DagStageKind::Compile => 2,
            DagStageKind::Optimize => 3,
            DagStageKind::Schedule => 4,
            DagStageKind::Execute => 5,
            DagStageKind::Persist => 6,
            DagStageKind::RecordKnowledgeObservability => 7,
            DagStageKind::Finalize => 8,
        }
    }

    fn key(self) -> &'static str {
        match self {
            DagStageKind::ValidateEnqueue => "validate-enqueue",
            DagStageKind::Compile => "compile",
            DagStageKind::Optimize => "optimize",
            DagStageKind::Schedule => "schedule",
            DagStageKind::Execute => "execute",
            DagStageKind::Persist => "persist",
            DagStageKind::RecordKnowledgeObservability => "record-knowledge-observability",
            DagStageKind::Finalize => "finalize",
        }
    }

    fn stage_state(self) -> TaskState {
        match self {
            DagStageKind::ValidateEnqueue => TaskState::Pending,
            DagStageKind::Compile => TaskState::Compiling,
            DagStageKind::Optimize => TaskState::Optimizing,
            DagStageKind::Schedule => TaskState::Queued,
            DagStageKind::Execute
            | DagStageKind::Persist
            | DagStageKind::RecordKnowledgeObservability => TaskState::Running,
            DagStageKind::Finalize => TaskState::Done,
        }
    }

    fn next_state_after_success(self) -> TaskState {
        match self {
            DagStageKind::ValidateEnqueue => TaskState::Pending,
            DagStageKind::Compile => TaskState::Optimizing,
            DagStageKind::Optimize => TaskState::Queued,
            DagStageKind::Schedule => TaskState::Running,
            DagStageKind::Execute | DagStageKind::Persist | DagStageKind::RecordKnowledgeObservability =>
                TaskState::Running,
            DagStageKind::Finalize => TaskState::Done,
        }
    }
}

impl fmt::Display for DagStageKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.key())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum StageStatus {
    Running,
    Succeeded,
    Failed,
}

#[derive(Debug, Clone)]
struct StageRecord {
    stage_id: String,
    stage_key: String,
    order: u32,
    state_before: TaskState,
    state_after: TaskState,
    status: StageStatus,
    started_at: Timestamp,
    completed_at: Option<Timestamp>,
    input: BTreeMap<String, String>,
    output: BTreeMap<String, String>,
    error_code: Option<String>,
    error_summary: Option<String>,
    error_details_ref: Option<String>,
    replay_token: String,
}

#[derive(Debug, Clone)]
struct NormalizedSubmission {
    contract_version: String,
    request_id: String,
    idempotency_key: String,
    traceparent: String,
    trace_id: String,
    tenant_id: String,
    project_id: String,
    subject: String,
    role: String,
    source_service: String,
    deadline_seconds: Option<u64>,
    deadline_at: Option<Timestamp>,
    name: String,
    program_format: String,
    program: Vec<u8>,
    program_hash: String,
    target: String,
    priority: i32,
    compiler_options: BTreeMap<String, String>,
    metadata_kvs: BTreeMap<String, String>,
    fingerprint: String,
    job_id: String,
}

impl NormalizedSubmission {
    fn from_request(request: &EnqueueJobRequest) -> Result<Self, Status> {
        let metadata = request
            .metadata
            .as_ref()
            .ok_or_else(|| Status::invalid_argument("metadata is required"))?;

        let name = nonempty(&request.name, "name")?;
        let program = request.program.clone();
        if program.is_empty() {
            return Err(Status::invalid_argument("program is required"));
        }

        let program_format = nonempty(&request.program_format, "program_format")?;
        let target = nonempty(&request.target, "target")?;

        let contract_version = nonempty_or_default(&metadata.contract_version, "1.0.0");
        let request_id = nonempty(&metadata.request_id, "metadata.request_id")?;
        let traceparent = nonempty(&metadata.traceparent, "metadata.traceparent")?;
        let tenant_id = nonempty(&metadata.tenant_id, "metadata.tenant_id")?;
        let project_id = nonempty(&metadata.project_id, "metadata.project_id")?;
        let idempotency_key = nonempty_or_default(&metadata.idempotency_key, &request_id);
        let subject = nonempty_or_default(&metadata.subject, "kernel-runtime");
        let role = nonempty_or_default(&metadata.role, "user");
        let source_service = nonempty_or_default(&metadata.source_service, "system-api");
        let deadline_seconds = metadata
            .deadline
            .as_ref()
            .and_then(|d| if d.seconds > 0 || d.nanos > 0 { Some(d.seconds.max(0) as u64) } else { None });
        let deadline_at = metadata
            .deadline
            .as_ref()
            .and_then(|d| normalized_deadline_at(d));
        let compiler_options = canonical_string_map(&request.compiler_options);
        let metadata_kvs = canonical_string_map(&request.metadata_kvs);
        let program_hash = hash_bytes_hex(&program);
        let trace_id = trace_id_from_traceparent(&traceparent)
            .unwrap_or_else(|| stable_trace_id(&request_id, &program_hash));
        let fingerprint = canonical_submission_fingerprint(
            &contract_version,
            &request_id,
            &idempotency_key,
            &traceparent,
            tenant_id.as_str(),
            project_id.as_str(),
            subject.as_str(),
            role.as_str(),
            source_service.as_str(),
            deadline_seconds,
            deadline_at,
            name.as_str(),
            program_format.as_str(),
            &program_hash,
            target.as_str(),
            request.priority,
            &compiler_options,
            &metadata_kvs,
        );
        let job_id = format!("job-{}", &fingerprint);

        Ok(Self {
            contract_version,
            request_id,
            idempotency_key,
            traceparent,
            trace_id,
            tenant_id,
            project_id,
            subject,
            role,
            source_service,
            deadline_seconds,
            name,
            program_format,
            program,
            program_hash,
            target,
            priority: request.priority,
            compiler_options,
            metadata_kvs,
            fingerprint,
            job_id,
        })
    }

    fn summary_map(&self) -> BTreeMap<String, String> {
        BTreeMap::from([
            ("contract_version".to_string(), self.contract_version.clone()),
            ("request_id".to_string(), self.request_id.clone()),
            ("idempotency_key".to_string(), self.idempotency_key.clone()),
            ("tenant_id".to_string(), self.tenant_id.clone()),
            ("project_id".to_string(), self.project_id.clone()),
            ("subject".to_string(), self.subject.clone()),
            ("role".to_string(), self.role.clone()),
            ("source_service".to_string(), self.source_service.clone()),
            ("traceparent".to_string(), self.traceparent.clone()),
            ("trace_id".to_string(), self.trace_id.clone()),
            ("name".to_string(), self.name.clone()),
            ("program_format".to_string(), self.program_format.clone()),
            ("program_hash".to_string(), self.program_hash.clone()),
            ("target".to_string(), self.target.clone()),
            ("priority".to_string(), self.priority.to_string()),
            ("job_id".to_string(), self.job_id.clone()),
            ("fingerprint".to_string(), self.fingerprint.clone()),
            (
                "compiler_options_count".to_string(),
                self.compiler_options.len().to_string(),
            ),
            (
                "metadata_kvs_count".to_string(),
                self.metadata_kvs.len().to_string(),
            ),
            (
                "deadline_seconds".to_string(),
                self.deadline_seconds
                    .map(|v| v.to_string())
                    .unwrap_or_default(),
            ),
            (
                "deadline_at_unix_ms".to_string(),
                self.deadline_at
                    .as_ref()
                    .map(|ts| timestamp_to_ms(ts).to_string())
                    .unwrap_or_default(),
            ),
        ])
    }

    fn stage_input(&self, stage: DagStageKind) -> BTreeMap<String, String> {
        let mut input = self.summary_map();
        input.insert("stage_id".to_string(), stage_id(&self.job_id, stage));
        input.insert("stage_key".to_string(), stage.key().to_string());
        input.insert("stage_index".to_string(), stage.index().to_string());
        input.insert("program_bytes".to_string(), self.program.len().to_string());
        input
    }
}

#[derive(Debug, Clone)]
struct JobRuntimeRecord {
    job_id: String,
    submission: NormalizedSubmission,
    state: TaskState,
    current_stage: Option<DagStageKind>,
    created_at: Timestamp,
    updated_at: Timestamp,
    deadline_at: Option<Timestamp>,
    completed_at: Option<Timestamp>,
    stage_records: Vec<StageRecord>,
    counts: BTreeMap<String, i64>,
    metadata: BTreeMap<String, String>,
    qfs_result_ref: Option<String>,
    error_code: Option<String>,
    error_summary: Option<String>,
    error_details_ref: Option<String>,
    cancel_requested: bool,
    cancel_reason: Option<String>,
    cancellation_fanout_ref: Option<String>,
    reservation_state: Option<String>,
    retry_attempts: Vec<RetryAttemptRecord>,
    retry_final_reason: Option<String>,
    retry_success_after_retry_total: u32,
}

#[derive(Debug, Clone)]
struct RetryAttemptRecord {
    attempt: u32,
    grpc_code: Code,
    reason_code: String,
    retryable: bool,
    delay_ms: u64,
    elapsed_ms: u64,
    recorded_at: Timestamp,
}

impl JobRuntimeRecord {
    fn stage_label(&self) -> String {
        self.current_stage
            .map(|stage| stage.key().to_string())
            .unwrap_or_else(|| match self.state {
                TaskState::Pending => "pending".to_string(),
                TaskState::Compiling => "compile".to_string(),
                TaskState::Optimizing => "optimize".to_string(),
                TaskState::Queued => "schedule".to_string(),
                TaskState::Running => "execute".to_string(),
                TaskState::Done => "finalize".to_string(),
                TaskState::Error => "error".to_string(),
                TaskState::Cancelled => "cancelled".to_string(),
                TaskState::Timeout => "timeout".to_string(),
                TaskState::Unspecified => "unspecified".to_string(),
            })
    }

    fn progress(&self) -> f32 {
        if self.is_terminal() {
            1.0
        } else {
            (self.stage_records.len() as f32 / DagStageKind::all().len() as f32).min(0.99)
        }
    }

    fn is_terminal(&self) -> bool {
        matches!(
            self.state,
            TaskState::Done | TaskState::Error | TaskState::Cancelled | TaskState::Timeout
        )
    }

    fn snapshot_bytes(&self) -> Vec<u8> {
        let stage_json: Vec<serde_json::Value> = self
            .stage_records
            .iter()
            .map(|stage| {
                serde_json::json!({
                    "stage_id": stage.stage_id,
                    "stage_key": stage.stage_key,
                    "order": stage.order,
                    "state_before": stage.state_before as i32,
                    "state_after": stage.state_after as i32,
                    "status": match stage.status {
                        StageStatus::Running => "running",
                        StageStatus::Succeeded => "succeeded",
                        StageStatus::Failed => "failed",
                    },
                    "started_at": ts_to_json(&stage.started_at),
                    "completed_at": stage.completed_at.as_ref().map(ts_to_json),
                    "input": stage.input,
                    "output": stage.output,
                    "error_code": stage.error_code,
                    "error_summary": stage.error_summary,
                    "error_details_ref": stage.error_details_ref,
                    "replay_token": stage.replay_token,
                })
            })
            .collect();

        serde_json::to_vec(&serde_json::json!({
            "job_id": self.job_id,
            "submission": self.submission.summary_map(),
            "state": self.state as i32,
            "current_stage": self.current_stage.map(|s| s.key()),
            "created_at": ts_to_json(&self.created_at),
            "updated_at": ts_to_json(&self.updated_at),
            "completed_at": self.completed_at.as_ref().map(ts_to_json),
            "stage_records": stage_json,
            "counts": self.counts,
            "metadata": self.metadata,
            "qfs_result_ref": self.qfs_result_ref,
            "error_code": self.error_code,
            "error_summary": self.error_summary,
            "error_details_ref": self.error_details_ref,
            "cancel_requested": self.cancel_requested,
        }))
        .unwrap_or_default()
    }

    fn snapshot_digest(&self) -> String {
        hash_bytes_hex(&self.snapshot_bytes())
    }
}

#[derive(Default)]
struct KernelRuntimeStore {
    jobs: parking_lot::RwLock<BTreeMap<String, JobRuntimeRecord>>,
    request_index: parking_lot::RwLock<BTreeMap<String, String>>,
}

impl KernelRuntimeStore {
    fn create_or_get_job(&self, submission: NormalizedSubmission) -> Result<(JobRuntimeRecord, bool), Status> {
        let mut jobs = self.jobs.write();
        if let Some(existing) = jobs.get(&submission.job_id) {
            if existing.submission.fingerprint != submission.fingerprint {
                return Err(Status::aborted("deterministic job id collision"));
            }
            return Ok((existing.clone(), false));
        }

        let now = ts_now();
        let record = JobRuntimeRecord {
            job_id: submission.job_id.clone(),
            submission: submission.clone(),
            state: TaskState::Pending,
            current_stage: Some(DagStageKind::ValidateEnqueue),
            created_at: now.clone(),
            updated_at: now,
            deadline_at: submission.deadline_at.clone(),
            completed_at: None,
            stage_records: Vec::new(),
            counts: BTreeMap::new(),
            metadata: BTreeMap::new(),
            qfs_result_ref: None,
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            cancel_requested: false,
            cancel_reason: None,
            cancellation_fanout_ref: None,
            reservation_state: Some("held".to_string()),
            retry_attempts: Vec::new(),
            retry_final_reason: None,
            retry_success_after_retry_total: 0,
        };
        jobs.insert(submission.job_id.clone(), record.clone());
        self.request_index
            .write()
            .insert(submission.fingerprint.clone(), submission.job_id.clone());
        Ok((record, true))
    }

    fn get(&self, job_id: &str) -> Option<JobRuntimeRecord> {
        self.jobs.read().get(job_id).cloned()
    }

    fn is_cancel_requested(&self, job_id: &str) -> bool {
        self.jobs
            .read()
            .get(job_id)
            .map(|job| job.cancel_requested)
            .unwrap_or(false)
    }

    fn deadline_expired(&self, job_id: &str) -> bool {
        self.jobs
            .read()
            .get(job_id)
            .and_then(|job| job.deadline_at.as_ref())
            .map(|deadline| timestamp_to_ms(&ts_now()) >= timestamp_to_ms(deadline))
            .unwrap_or(false)
    }

    fn begin_stage(
        &self,
        job_id: &str,
        stage: DagStageKind,
        state_before: TaskState,
        input: BTreeMap<String, String>,
    ) -> Result<String, Status> {
        let stage_id = stage_id(job_id, stage);
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        if job.is_terminal() {
            return Err(Status::failed_precondition("job already terminal"));
        }
        if job.stage_records.iter().any(|record| record.stage_id == stage_id) {
            job.current_stage = Some(stage);
            return Ok(stage_id);
        }

        job.current_stage = Some(stage);
        job.updated_at = ts_now();
        job.stage_records.push(StageRecord {
            stage_id: stage_id.clone(),
            stage_key: stage.key().to_string(),
            order: stage.index(),
            state_before,
            state_after: state_before,
            status: StageStatus::Running,
            started_at: ts_now(),
            completed_at: None,
            input,
            output: BTreeMap::new(),
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            replay_token: String::new(),
        });
        Ok(stage_id)
    }

    fn finish_stage_success(
        &self,
        job_id: &str,
        stage_id: &str,
        state_after: TaskState,
        output: BTreeMap<String, String>,
    ) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        let stage = job
            .stage_records
            .iter_mut()
            .find(|record| record.stage_id == stage_id)
            .ok_or_else(|| Status::failed_precondition("stage record not found"))?;
        stage.status = StageStatus::Succeeded;
        stage.state_after = state_after;
        stage.output = output;
        stage.completed_at = Some(ts_now());
        stage.replay_token = hash_bytes_hex(&stage_digest_bytes(stage));

        job.state = state_after;
        job.updated_at = ts_now();
        if matches!(state_after, TaskState::Done | TaskState::Error | TaskState::Cancelled | TaskState::Timeout) {
            job.completed_at = Some(ts_now());
        }
        Ok(())
    }

    fn finish_stage_failure(
        &self,
        job_id: &str,
        stage_id: &str,
        terminal_state: TaskState,
        error_code: &str,
        error_summary: &str,
        error_details_ref: &str,
    ) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        let stage = job
            .stage_records
            .iter_mut()
            .find(|record| record.stage_id == stage_id)
            .ok_or_else(|| Status::failed_precondition("stage record not found"))?;
        stage.status = StageStatus::Failed;
        stage.state_after = terminal_state;
        stage.error_code = Some(error_code.to_string());
        stage.error_summary = Some(error_summary.to_string());
        stage.error_details_ref = Some(error_details_ref.to_string());
        stage.completed_at = Some(ts_now());
        stage.replay_token = hash_bytes_hex(&stage_digest_bytes(stage));

        job.state = terminal_state;
        job.updated_at = ts_now();
        job.completed_at = Some(ts_now());
        job.error_code = Some(error_code.to_string());
        job.error_summary = Some(error_summary.to_string());
        job.error_details_ref = Some(error_details_ref.to_string());
        Ok(())
    }

    fn set_state(
        &self,
        job_id: &str,
        state: TaskState,
    ) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.state = state;
        job.updated_at = ts_now();
        if matches!(state, TaskState::Done | TaskState::Error | TaskState::Cancelled | TaskState::Timeout) {
            job.completed_at = Some(ts_now());
        }
        Ok(())
    }

    fn set_metadata(
        &self,
        job_id: &str,
        metadata: BTreeMap<String, String>,
    ) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.metadata = metadata;
        job.updated_at = ts_now();
        Ok(())
    }

    fn set_reservation_state(&self, job_id: &str, state: &str) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.reservation_state = Some(state.to_string());
        job.updated_at = ts_now();
        Ok(())
    }

    fn record_retry_attempt(&self, job_id: &str, record: RetryAttemptRecord) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.retry_attempts.push(record);
        job.updated_at = ts_now();
        self.refresh_retry_metadata(job);
        Ok(())
    }

    fn set_retry_final_reason(&self, job_id: &str, reason: &str) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.retry_final_reason = Some(reason.to_string());
        job.updated_at = ts_now();
        self.refresh_retry_metadata(job);
        Ok(())
    }

    fn set_retry_success_after_retry_total(&self, job_id: &str, total: u32) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.retry_success_after_retry_total = total;
        job.updated_at = ts_now();
        self.refresh_retry_metadata(job);
        Ok(())
    }

    fn refresh_retry_metadata(&self, job: &mut JobRuntimeRecord) {
        job.metadata.insert(
            "retry.attempts_total".to_string(),
            job.retry_attempts.len().to_string(),
        );
        job.metadata.insert(
            "retry.retries_total".to_string(),
            job.retry_attempts.len().saturating_sub(1).to_string(),
        );
        job.metadata.insert(
            "retry.success_after_retry_total".to_string(),
            job.retry_success_after_retry_total.to_string(),
        );
        job.metadata.insert(
            "retry.final_reason".to_string(),
            job.retry_final_reason.clone().unwrap_or_default(),
        );
    }

    fn request_cancel(&self, job_id: &str, reason: Option<String>) -> Result<JobRuntimeRecord, Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        if job.is_terminal() {
            return Err(Status::failed_precondition("job already terminal"));
        }
        job.cancel_requested = true;
        job.cancel_reason = reason;
        job.cancellation_fanout_ref = Some(format!("qfs://jobs/{job_id}/control/cancellation.json"));
        job.reservation_state = Some("release_pending".to_string());
        job.updated_at = ts_now();
        Ok(job.clone())
    }

    fn request_deadline_terminalization(&self, job_id: &str) -> Result<JobRuntimeRecord, Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        if job.is_terminal() {
            return Ok(job.clone());
        }
        job.state = TaskState::Timeout;
        job.cancel_requested = true;
        job.cancel_reason = Some("deadline_exceeded".to_string());
        job.cancellation_fanout_ref = Some(format!("qfs://jobs/{job_id}/control/deadline.json"));
        job.reservation_state = Some("released".to_string());
        job.error_code = Some("DEADLINE_EXCEEDED".to_string());
        job.error_summary = Some("deadline exceeded while orchestrating the job".to_string());
        job.error_details_ref = Some(format!("qfs://jobs/{job_id}/errors/deadline.json"));
        job.completed_at = Some(ts_now());
        job.updated_at = ts_now();
        Ok(job.clone())
    }

    fn set_counts(
        &self,
        job_id: &str,
        counts: BTreeMap<String, i64>,
    ) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.counts = counts;
        job.updated_at = ts_now();
        Ok(())
    }

    fn set_qfs_result_ref(&self, job_id: &str, value: String) -> Result<(), Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        job.qfs_result_ref = Some(value);
        job.updated_at = ts_now();
        Ok(())
    }

    fn all_stage_updates(&self, job_id: &str) -> Result<Vec<JobUpdateEnvelope>, Status> {
        let job = self
            .get(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        let total = DagStageKind::all().len().max(1) as f32;

        let mut updates = Vec::new();
        for (idx, stage) in job.stage_records.iter().enumerate() {
            updates.push(JobUpdateEnvelope {
                event_seq: (idx + 1) as u64,
                state: stage.state_after as i32,
                stage: stage.stage_key.clone(),
                progress: (((idx + 1) as f32) / total).min(1.0),
                message: stage
                    .output
                    .get("message")
                    .cloned()
                    .or_else(|| stage.error_summary.clone())
                    .unwrap_or_default(),
                timestamp: Some(stage.completed_at.clone().unwrap_or_else(ts_now)),
            });
        }

        if updates.is_empty() {
            updates.push(JobUpdateEnvelope {
                event_seq: 1,
                state: job.state as i32,
                stage: job.stage_label(),
                progress: job.progress(),
                message: job
                    .error_summary
                    .clone()
                    .unwrap_or_else(|| "job accepted".to_string()),
                timestamp: Some(job.updated_at.clone()),
            });
        }

        Ok(updates)
    }
}

#[derive(Debug, Clone)]
struct KernelStageError {
    grpc_code: Code,
    error_code: &'static str,
    summary: String,
    details_ref: String,
}

impl KernelStageError {
    fn new(grpc_code: Code, error_code: &'static str, summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self {
            grpc_code,
            error_code,
            summary: summary.into(),
            details_ref: details_ref.into(),
        }
    }

    fn invalid(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::InvalidArgument, "VALIDATION_FAILED", summary, details_ref)
    }

    fn compile(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "COMPILER_STAGE_FAILED", summary, details_ref)
    }

    fn optimize(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "OPTIMIZER_STAGE_FAILED", summary, details_ref)
    }

    fn schedule(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "SCHEDULER_STAGE_FAILED", summary, details_ref)
    }

    fn execute(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "EXECUTION_STAGE_FAILED", summary, details_ref)
    }

    fn unavailable(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Unavailable, "EIGEN_EXECUTION_UNAVAILABLE", summary, details_ref)
    }

    fn resource_exhausted(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(
            Code::ResourceExhausted,
            "EIGEN_EXECUTION_RESOURCE_EXHAUSTED",
            summary,
            details_ref,
        )
    }

    fn aborted(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Aborted, "EIGEN_EXECUTION_ABORTED", summary, details_ref)
    }

    fn deadline_exceeded(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(
            Code::DeadlineExceeded,
            "EIGEN_EXECUTION_DEADLINE_EXCEEDED",
            summary,
            details_ref,
        )
    }

    fn invalid_argument(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::InvalidArgument, "EIGEN_EXECUTION_INVALID_ARGUMENT", summary, details_ref)
    }

    fn failed_precondition(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(
            Code::FailedPrecondition,
            "EIGEN_EXECUTION_FAILED_PRECONDITION",
            summary,
            details_ref,
        )
    }

    fn internal(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "EIGEN_EXECUTION_INTERNAL", summary, details_ref)
    }

    fn persist(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "PERSISTENCE_STAGE_FAILED", summary, details_ref)
    }

    fn observability(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "OBSERVABILITY_STAGE_FAILED", summary, details_ref)
    }

    fn finalize(summary: impl Into<String>, details_ref: impl Into<String>) -> Self {
        Self::new(Code::Internal, "FINALIZE_STAGE_FAILED", summary, details_ref)
    }

    fn into_status(self) -> Status {
        Status::new(self.grpc_code, format!("{} ({})", self.summary, self.details_ref))
    }
}

impl fmt::Display for KernelStageError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {} ({})", self.error_code, self.summary, self.details_ref)
    }
}

impl std::error::Error for KernelStageError {}

#[derive(Debug, Clone)]
struct ExecutionOutcome {
    counts: BTreeMap<String, i64>,
    output: BTreeMap<String, String>,
}

#[derive(Debug, Clone)]
struct RetryPolicy {
    max_attempts: u32,
    base_delay: Duration,
    max_delay: Duration,
    max_elapsed: Duration,
    retryable_reasons: Vec<&'static str>,
    non_retryable_reasons: Vec<&'static str>,
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(50),
            max_delay: Duration::from_secs(1),
            max_elapsed: Duration::from_secs(5),
            retryable_reasons: vec![
                "EIGEN_EXECUTION_UNAVAILABLE",
                "EIGEN_EXECUTION_RESOURCE_EXHAUSTED",
                "EIGEN_EXECUTION_ABORTED",
                "EIGEN_EXECUTION_DEADLINE_EXCEEDED",
            ],
            non_retryable_reasons: vec![
                "EIGEN_EXECUTION_INVALID_ARGUMENT",
                "EIGEN_EXECUTION_FAILED_PRECONDITION",
                "EIGEN_EXECUTION_INTERNAL",
                "EIGEN_EXECUTION_UNAUTHENTICATED",
                "EIGEN_EXECUTION_PERMISSION_DENIED",
                "EIGEN_EXECUTION_UNIMPLEMENTED",
            ],
        }
    }
}

impl RetryPolicy {
    fn from_metadata(metadata: &BTreeMap<String, String>) -> Self {
        let mut policy = Self::default();
        if let Some(v) = parse_positive_usize(metadata, "retry.max_attempts") {
            policy.max_attempts = v.clamp(1, 16) as u32;
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.base_delay_ms") {
            policy.base_delay = Duration::from_millis(v as u64);
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.max_delay_ms") {
            policy.max_delay = Duration::from_millis(v as u64);
        }
        if let Some(v) = parse_positive_usize(metadata, "retry.max_elapsed_ms") {
            policy.max_elapsed = Duration::from_millis(v as u64);
        }
        if let Some(v) = metadata.get("retry.retryable_reasons") {
            let parsed = parse_reason_csv(v);
            if !parsed.is_empty() {
                policy.retryable_reasons = parsed;
            }
        }
        if let Some(v) = metadata.get("retry.non_retryable_reasons") {
            let parsed = parse_reason_csv(v);
            if !parsed.is_empty() {
                policy.non_retryable_reasons = parsed;
            }
        }
        policy
    }

    fn is_retryable(&self, err: &KernelStageError) -> bool {
        if self.non_retryable_reasons.iter().any(|reason| *reason == err.error_code) {
            return false;
        }
        if self.retryable_reasons.iter().any(|reason| *reason == err.error_code) {
            return true;
        }
        matches!(
            err.grpc_code,
            Code::Unavailable | Code::ResourceExhausted | Code::Aborted | Code::DeadlineExceeded
        )
    }

    fn backoff_for_attempt(&self, attempt: u32) -> Duration {
        let exp = 1u32.checked_shl(attempt.saturating_sub(1)).unwrap_or(u32::MAX);
        let base_ms = self.base_delay.as_millis().saturating_mul(exp as u128);
        let capped_ms = base_ms.min(self.max_delay.as_millis()) as u64;
        Duration::from_millis(capped_ms)
    }
}

#[tonic::async_trait]
trait OrchestrationAdapters: Send + Sync {
    async fn validate_enqueue(
        &self,
        submission: &NormalizedSubmission,
    ) -> Result<BTreeMap<String, String>, KernelStageError>;

    async fn compile(
        &self,
        submission: &NormalizedSubmission,
        validation_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError>;

    async fn optimize(
        &self,
        submission: &NormalizedSubmission,
        compile_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError>;

    async fn schedule(
        &self,
        submission: &NormalizedSubmission,
        optimize_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError>;

    async fn execute(
        &self,
        submission: &NormalizedSubmission,
        schedule_output: &BTreeMap<String, String>,
    ) -> Result<ExecutionOutcome, KernelStageError>;

    async fn persist(
        &self,
        submission: &NormalizedSubmission,
        execution_output: &ExecutionOutcome,
        stage_records: &[StageRecord],
    ) -> Result<BTreeMap<String, String>, KernelStageError>;

    async fn record_knowledge_observability(
        &self,
        submission: &NormalizedSubmission,
        persist_output: &BTreeMap<String, String>,
        execution_output: &ExecutionOutcome,
    ) -> Result<BTreeMap<String, String>, KernelStageError>;

    async fn finalize(
        &self,
        submission: &NormalizedSubmission,
        observability_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError>;
}

#[derive(Clone)]
struct FixtureAdapters {
    qfs: CircuitFsLocal,
    failure_stage: Option<DagStageKind>,
    hold_stage: Option<DagStageKind>,
    hold_for: Duration,
    execute_script: Arc<Mutex<VecDeque<ExecuteScriptStep>>>,
}

#[derive(Debug, Clone)]
enum ExecuteScriptStep {
    Success,
    Unavailable,
    ResourceExhausted,
    Aborted,
    DeadlineExceeded,
    InvalidArgument,
    FailedPrecondition,
    Internal,
}

impl FixtureAdapters {
    fn from_env() -> Self {
        let qfs_root = std::env::var("EIGEN_QFS_ROOT")
            .unwrap_or_else(|_| qfs::DEFAULT_CIRCUIT_FS_ROOT.to_string());
        let hold_stage = std::env::var("EIGEN_KERNEL_TEST_HOLD_STAGE").ok().and_then(|raw| parse_stage_kind(&raw));
        let hold_for = std::env::var("EIGEN_KERNEL_TEST_HOLD_MS")
            .ok()
            .and_then(|raw| raw.parse::<u64>().ok())
            .map(Duration::from_millis)
            .unwrap_or_default();
        Self {
            qfs: CircuitFsLocal::new(qfs_root),
            failure_stage: None,
            hold_stage,
            hold_for,
            execute_script: Arc::new(Mutex::new(VecDeque::new())),
        }
    }

    fn new(qfs_root: impl AsRef<str>, failure_stage: Option<DagStageKind>) -> Self {
        Self {
            qfs: CircuitFsLocal::new(qfs_root.as_ref()),
            failure_stage,
            hold_stage: None,
            hold_for: Duration::from_millis(0),
            execute_script: Arc::new(Mutex::new(VecDeque::new())),
        }
    }

    fn with_execute_script(
        qfs_root: impl AsRef<str>,
        failure_stage: Option<DagStageKind>,
        execute_script: Vec<ExecuteScriptStep>,
    ) -> Self {
        Self {
            qfs: CircuitFsLocal::new(qfs_root.as_ref()),
            failure_stage,
            hold_stage: None,
            hold_for: Duration::from_millis(0),
            execute_script: Arc::new(Mutex::new(execute_script.into_iter().collect())),
        }
    }

    fn with_no_failure(qfs_root: impl AsRef<str>) -> Self {
        Self::new(qfs_root, None)
    }

    fn maybe_fail(&self, stage: DagStageKind) -> Result<(), KernelStageError> {
        if self.failure_stage == Some(stage) {
            let details_ref = format!("qfs://fixtures/{}-stage-failure.json", stage.key());
            let summary = format!("fixture failure injected at {} stage", stage.key());
            let err = match stage {
                DagStageKind::ValidateEnqueue => KernelStageError::invalid(summary, details_ref),
                DagStageKind::Compile => KernelStageError::compile(summary, details_ref),
                DagStageKind::Optimize => KernelStageError::optimize(summary, details_ref),
                DagStageKind::Schedule => KernelStageError::schedule(summary, details_ref),
                DagStageKind::Execute => KernelStageError::execute(summary, details_ref),
                DagStageKind::Persist => KernelStageError::persist(summary, details_ref),
                DagStageKind::RecordKnowledgeObservability => {
                    KernelStageError::observability(summary, details_ref)
                }
                DagStageKind::Finalize => KernelStageError::finalize(summary, details_ref),
            };
            Err(err)
        } else {
            Ok(())
        }
    }

    fn next_execute_step(&self) -> ExecuteScriptStep {
        self.execute_script
            .lock()
            .pop_front()
            .unwrap_or(ExecuteScriptStep::Success)
    }

    async fn maybe_hold(&self, stage: DagStageKind) {
        if self.hold_stage == Some(stage) && !self.hold_for.is_zero() {
            tokio::time::sleep(self.hold_for).await;
        }
    }
}

#[tonic::async_trait]
impl OrchestrationAdapters for FixtureAdapters {
    async fn validate_enqueue(
        &self,
        submission: &NormalizedSubmission,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::ValidateEnqueue).await;
        self.maybe_fail(DagStageKind::ValidateEnqueue)?;
        let mut output = BTreeMap::from([
            ("message".to_string(), "submission validated".to_string()),
            ("job_id".to_string(), submission.job_id.clone()),
            ("submission_digest".to_string(), submission.fingerprint.clone()),
        ]);
        output.insert(
            "qfs_submission_ref".to_string(),
            format!("qfs://jobs/{}/submission.json", submission.job_id),
        );
        Ok(output)
    }

    async fn compile(
        &self,
        submission: &NormalizedSubmission,
        _validation_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Compile).await;
        self.maybe_fail(DagStageKind::Compile)?;
        Ok(BTreeMap::from([
            ("message".to_string(), "compile stage completed".to_string()),
            (
                "compiled_artifact_ref".to_string(),
                format!("qfs://jobs/{}/artifacts/compiled.aqo", submission.job_id),
            ),
            (
                "compiler_version".to_string(),
                env!("CARGO_PKG_VERSION").to_string(),
            ),
            (
                "compile_digest".to_string(),
                format!("compile-{}", submission.program_hash),
            ),
        ]))
    }

    async fn optimize(
        &self,
        submission: &NormalizedSubmission,
        _compile_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Optimize).await;
        self.maybe_fail(DagStageKind::Optimize)?;
        Ok(BTreeMap::from([
            ("message".to_string(), "optimization stage completed".to_string()),
            (
                "optimized_artifact_ref".to_string(),
                format!("qfs://jobs/{}/artifacts/optimized.aqo", submission.job_id),
            ),
            (
                "optimizer_version".to_string(),
                "fixture-optimizer/1".to_string(),
            ),
            ("optimizer_policy".to_string(), "deterministic".to_string()),
        ]))
    }

    async fn schedule(
        &self,
        submission: &NormalizedSubmission,
        _optimize_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Schedule).await;
        self.maybe_fail(DagStageKind::Schedule)?;
        Ok(BTreeMap::from([
            ("message".to_string(), "resource schedule selected".to_string()),
            ("selected_backend".to_string(), submission.target.clone()),
            ("selected_queue".to_string(), "scheduler:default".to_string()),
            (
                "resource_plan_ref".to_string(),
                format!("qfs://jobs/{}/schedule/plan.json", submission.job_id),
            ),
        ]))
    }

    async fn execute(
        &self,
        submission: &NormalizedSubmission,
        schedule_output: &BTreeMap<String, String>,
    ) -> Result<ExecutionOutcome, KernelStageError> {
        self.maybe_hold(DagStageKind::Execute).await;
        match self.next_execute_step() {
            ExecuteScriptStep::Success => self.maybe_fail(DagStageKind::Execute)?,
            ExecuteScriptStep::Unavailable => {
                return Err(KernelStageError::unavailable(
                    "execution backend unavailable",
                    format!("qfs://fixtures/execute/unavailable-{}.json", submission.job_id),
                ));
            }
            ExecuteScriptStep::ResourceExhausted => {
                return Err(KernelStageError::resource_exhausted(
                    "execution capacity exhausted",
                    format!("qfs://fixtures/execute/resource-exhausted-{}.json", submission.job_id),
                ));
            }
            ExecuteScriptStep::Aborted => {
                return Err(KernelStageError::aborted(
                    "execution aborted by runtime coordination conflict",
                    format!("qfs://fixtures/execute/aborted-{}.json", submission.job_id),
                ));
            }
            ExecuteScriptStep::DeadlineExceeded => {
                return Err(KernelStageError::deadline_exceeded(
                    "execution exceeded deadline",
                    format!("qfs://fixtures/execute/deadline-{}.json", submission.job_id),
                ));
            }
            ExecuteScriptStep::InvalidArgument => {
                return Err(KernelStageError::invalid_argument(
                    "execution request invalid",
                    format!("qfs://fixtures/execute/invalid-{}.json", submission.job_id),
                ));
            }
            ExecuteScriptStep::FailedPrecondition => {
                return Err(KernelStageError::failed_precondition(
                    "execution precondition not met",
                    format!("qfs://fixtures/execute/precondition-{}.json", submission.job_id),
                ));
            }
            ExecuteScriptStep::Internal => {
                return Err(KernelStageError::internal(
                    "execution internal invariant failure",
                    format!("qfs://fixtures/execute/internal-{}.json", submission.job_id),
                ));
            }
        }
        let shots = submission
            .metadata_kvs
            .get("shots")
            .and_then(|raw| raw.parse::<i64>().ok())
            .filter(|v| *v > 0)
            .unwrap_or(1024);

        let mut counts = BTreeMap::new();
        counts.insert("0".to_string(), shots);
        let counts_ref = format!("qfs://jobs/{}/results/counts.json", submission.job_id);
        let execution_ref = format!("qfs://jobs/{}/execution/execution.json", submission.job_id);

        Ok(ExecutionOutcome {
            counts,
            output: BTreeMap::from([
                ("message".to_string(), "execution completed".to_string()),
                ("counts_ref".to_string(), counts_ref),
                ("execution_ref".to_string(), execution_ref),
                (
                    "selected_backend".to_string(),
                    schedule_output
                        .get("selected_backend")
                        .cloned()
                        .unwrap_or_else(|| submission.target.clone()),
                ),
            ]),
        })
    }

    async fn persist(
        &self,
        submission: &NormalizedSubmission,
        execution_output: &ExecutionOutcome,
        stage_records: &[StageRecord],
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Persist).await;
        self.maybe_fail(DagStageKind::Persist)?;
        let artifact = serde_json::json!({
            "job_id": submission.job_id,
            "submission_digest": submission.fingerprint,
            "execution_output": execution_output.output,
            "stage_records": stage_records.iter().map(|stage| serde_json::json!({
                "stage_id": stage.stage_id,
                "stage_key": stage.stage_key,
                "order": stage.order,
                "status": match stage.status {
                    StageStatus::Running => "running",
                    StageStatus::Succeeded => "succeeded",
                    StageStatus::Failed => "failed",
                },
            })).collect::<Vec<_>>(),
        });
        let payload = serde_json::to_vec(&artifact).unwrap_or_default();
        let _ = self.qfs.ensure_job_layout(&submission.job_id);
        let _ = self
            .qfs
            .store_results_bundle(&submission.job_id, &payload, env!("CARGO_PKG_VERSION"));

        Ok(BTreeMap::from([
            ("message".to_string(), "results persisted to qfs".to_string()),
            (
                "qfs_result_ref".to_string(),
                format!("qfs://jobs/{}/results/result.json", submission.job_id),
            ),
            (
                "result_manifest_ref".to_string(),
                format!("qfs://jobs/{}/results/manifest.json", submission.job_id),
            ),
            (
                "artifact_version".to_string(),
                env!("CARGO_PKG_VERSION").to_string(),
            ),
        ]))
    }

    async fn record_knowledge_observability(
        &self,
        submission: &NormalizedSubmission,
        persist_output: &BTreeMap<String, String>,
        execution_output: &ExecutionOutcome,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::RecordKnowledgeObservability).await;
        self.maybe_fail(DagStageKind::RecordKnowledgeObservability)?;
        let payload = serde_json::json!({
            "job_id": submission.job_id,
            "trace_id": submission.trace_id,
            "timeline_ref": format!("qfs://jobs/{}/timeline.jsonl", submission.job_id),
            "qfs_result_ref": persist_output
                .get("qfs_result_ref")
                .cloned()
                .unwrap_or_default(),
            "counts_ref": execution_output
                .output
                .get("counts_ref")
                .cloned()
                .unwrap_or_default(),
            "contract_marker": r#"eigen_kernel_contract_info{version="1.0.0"} 1"#,
        });
        let metrics = serde_json::to_vec(&payload).unwrap_or_default();
        let _ = self
            .qfs
            .store_metrics_json(&submission.job_id, &metrics);

        Ok(BTreeMap::from([
            ("message".to_string(), "knowledge and observability recorded".to_string()),
            (
                "timeline_ref".to_string(),
                format!("qfs://jobs/{}/timeline.jsonl", submission.job_id),
            ),
            (
                "observability_ref".to_string(),
                format!("qfs://jobs/{}/observability/metrics.json", submission.job_id),
            ),
            (
                "trace_ref".to_string(),
                format!("qfs://jobs/{}/trace.json", submission.job_id),
            ),
        ]))
    }

    async fn finalize(
        &self,
        submission: &NormalizedSubmission,
        observability_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Finalize).await;
        self.maybe_fail(DagStageKind::Finalize)?;
        Ok(BTreeMap::from([
            ("message".to_string(), "job finalized".to_string()),
            ("final_state".to_string(), "DONE".to_string()),
            (
                "timeline_ref".to_string(),
                observability_output
                    .get("timeline_ref")
                    .cloned()
                    .unwrap_or_else(|| format!("qfs://jobs/{}/timeline.jsonl", submission.job_id)),
            ),
            (
                "result_ref".to_string(),
                observability_output
                    .get("qfs_result_ref")
                    .cloned()
                    .unwrap_or_else(|| format!("qfs://jobs/{}/results/result.json", submission.job_id)),
            ),
        ]))
    }
}

#[tonic::async_trait]
impl KernelGatewayService for KernelGatewaySvc {
    type StreamJobUpdatesStream =
        Pin<Box<dyn Stream<Item = Result<StreamJobUpdatesResponse, Status>> + Send + 'static>>;

    async fn enqueue_job(
        &self,
        request: Request<EnqueueJobRequest>,
    ) -> Result<Response<EnqueueJobResponse>, Status> {
        let req = request.into_inner();
        let submission = NormalizedSubmission::from_request(&req)?;
        let (job, created) = self.runtime.create_or_get_job(submission.clone())?;

        if created {
            let runtime = self.runtime.clone();
            let adapters = self.adapters.clone();
            let job_id = job.job_id.clone();
            let submission_for_task = submission.clone();

            tokio::spawn(async move {
                let span = tracing::info_span!("kernel_dag", job_id = %job_id);
                async move {
                    if let Err(err) = run_job_dag(runtime, adapters, job_id, submission_for_task).await {
                        tracing::error!(error = %err, "kernel dag failed");
                    }
                }
                .instrument(span)
                .await;
            });
        }

        Ok(Response::new(EnqueueJobResponse {
            job_id: job.job_id,
            state: job.state as i32,
            created_at: Some(job.created_at.clone()),
        }))
    }

    async fn get_job_status(
        &self,
        request: Request<GetJobStatusRequest>,
    ) -> Result<Response<GetJobStatusResponse>, Status> {
        let job_id = request.into_inner().job_id;
        let job = self
            .runtime
            .get(&job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;

        Ok(Response::new(GetJobStatusResponse {
            job_id: job.job_id.clone(),
            state: job.state as i32,
            stage: job.stage_label(),
            progress: job.progress(),
            message: job
                .stage_records
                .last()
                .and_then(|stage| stage.output.get("message").cloned())
                .or_else(|| job.error_summary.clone())
                .unwrap_or_else(|| "job accepted".to_string()),
            error_code: job.error_code.unwrap_or_default(),
            error_summary: job.error_summary.unwrap_or_default(),
            error_details_ref: job.error_details_ref.unwrap_or_default(),
            updated_at: Some(job.updated_at.clone()),
        }))
    }

    async fn cancel_job(
        &self,
        request: Request<CancelJobRequest>,
    ) -> Result<Response<CancelJobResponse>, Status> {
        let req = request.into_inner();
        let job_id = req.job_id;
        let job = self.runtime.request_cancel(&job_id, Some("deadline exceeded".to_string()))?;
        Ok(Response::new(CancelJobResponse {
            accepted: true,
            reason_code: if job.is_terminal() {
                "CANCELLED".to_string()
            } else {
                "ACCEPTED".to_string()
            },
        }))
    }

    async fn get_job_results(
        &self,
        request: Request<GetJobResultsRequest>,
    ) -> Result<Response<GetJobResultsResponse>, Status> {
        let job_id = request.into_inner().job_id;
        let job = self
            .runtime
            .get(&job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;

        if !job.is_terminal() {
            return Err(Status::failed_precondition("job results are not ready"));
        }

        let counts: HashMap<String, i64> = job.counts.clone().into_iter().collect();
        let metadata: HashMap<String, String> = job.metadata.clone().into_iter().collect();

        Ok(Response::new(GetJobResultsResponse {
            job_id: job.job_id.clone(),
            state: job.state as i32,
            counts,
            metadata,
            error_code: job.error_code.unwrap_or_default(),
            error_summary: job.error_summary.unwrap_or_default(),
            error_details_ref: job.error_details_ref.unwrap_or_default(),
            qfs_result_ref: job.qfs_result_ref.unwrap_or_default(),
            completed_at: job.completed_at,
        }))
    }

    async fn stream_job_updates(
        &self,
        request: Request<StreamJobUpdatesRequest>,
    ) -> Result<Response<Self::StreamJobUpdatesStream>, Status> {
        let job_id = request.into_inner().job_id;
        let updates = self.runtime.all_stage_updates(&job_id)?;
        let stream = iter(updates.into_iter().map(|update| Ok(StreamJobUpdatesResponse { update: Some(update) })));
        Ok(Response::new(Box::pin(stream)))
    }

    async fn get_dispatch_rationale(
        &self,
        request: Request<GetDispatchRationaleRequest>,
    ) -> Result<Response<GetDispatchRationaleResponse>, Status> {
        let job_id = request.into_inner().job_id;
        let job = self
            .runtime
            .get(&job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;

        let mut reason_codes = vec![
            "validate_enqueue".to_string(),
            "compile".to_string(),
            "optimize".to_string(),
            "schedule".to_string(),
            "execute".to_string(),
            "persist".to_string(),
            "record_knowledge_observability".to_string(),
            "finalize".to_string(),
        ];
        if let Some(code) = job.error_code.clone() {
            reason_codes.push(code);
        }

        let rationale = DispatchRationale {
            version: "1.0.0".to_string(),
            policy_version: "wave-2-dag-fixture/1".to_string(),
            reason_codes,
            selected_backend: job.submission.target.clone(),
            selected_queue: "scheduler:default".to_string(),
            attributes: HashMap::from([
                ("job_id".to_string(), job.job_id.clone()),
                ("stage_count".to_string(), job.stage_records.len().to_string()),
                ("snapshot_digest".to_string(), job.snapshot_digest()),
            ]),
            timeline_ref: format!("qfs://jobs/{}/timeline.jsonl", job.job_id),
            logs_ref: format!("qfs://jobs/{}/logs/runtime.json", job.job_id),
            trace_id: job.submission.trace_id.clone(),
            trace_ref: format!("qfs://jobs/{}/trace.json", job.job_id),
        };

        Ok(Response::new(GetDispatchRationaleResponse {
            rationale: Some(rationale),
        }))
    }
}

async fn run_job_dag(
    runtime: Arc<KernelRuntimeStore>,
    adapters: Arc<dyn OrchestrationAdapters>,
    job_id: String,
    submission: NormalizedSubmission,
) -> Result<(), KernelStageError> {
    let mut validation_output = BTreeMap::new();
    let mut compile_output = BTreeMap::new();
    let mut optimize_output = BTreeMap::new();
    let mut schedule_output = BTreeMap::new();
    let mut execution_output = ExecutionOutcome {
        counts: BTreeMap::new(),
        output: BTreeMap::new(),
    };
    let mut persist_output = BTreeMap::new();
    let mut observability_output = BTreeMap::new();

    let validate_stage = DagStageKind::ValidateEnqueue;
    let validate_stage_id = runtime
        .begin_stage(
            &job_id,
            validate_stage,
            validate_stage.stage_state(),
            submission.stage_input(validate_stage),
        )
        .map_err(status_to_stage_error(validate_stage, "begin_validate"))?;
    validation_output = adapters
        .validate_enqueue(&submission)
        .await
        .map_err(|err| stage_error(validate_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Compile, "validate")?;
        return Ok(());
    }

    runtime
        .finish_stage_success(
            &job_id,
            &validate_stage_id,
            validate_stage.next_state_after_success(),
            validation_output.clone(),
        )
        .map_err(status_to_stage_error(validate_stage, "finish_validate"))?;
    runtime
        .set_state(&job_id, DagStageKind::Compile.stage_state())
        .map_err(status_to_stage_error(validate_stage, "set_compile_state"))?;

    if runtime.is_cancel_requested(&job_id) {
        cancel_after_stage(&runtime, &job_id, DagStageKind::Compile, "cancelled before compile")?;
        return Ok(());
    }

    let compile_stage = DagStageKind::Compile;
    let compile_stage_id = runtime
        .begin_stage(
            &job_id,
            compile_stage,
            compile_stage.stage_state(),
            stage_input_from_outputs(&submission, compile_stage, &validation_output),
        )
        .map_err(status_to_stage_error(compile_stage, "begin_compile"))?;
    compile_output = adapters
        .compile(&submission, &validation_output)
        .await
        .map_err(|err| stage_error(compile_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Compile, "compile")?;
        return Ok(());
    }

    runtime
        .finish_stage_success(
            &job_id,
            &compile_stage_id,
            compile_stage.next_state_after_success(),
            compile_output.clone(),
        )
        .map_err(status_to_stage_error(compile_stage, "finish_compile"))?;
    runtime
        .set_state(&job_id, DagStageKind::Optimize.stage_state())
        .map_err(status_to_stage_error(compile_stage, "set_optimize_state"))?;

    if runtime.is_cancel_requested(&job_id) {
        cancel_after_stage(&runtime, &job_id, DagStageKind::Optimize, "cancelled before optimize")?;
        return Ok(());
    }

    let optimize_stage = DagStageKind::Optimize;
    let optimize_stage_id = runtime
        .begin_stage(
            &job_id,
            optimize_stage,
            optimize_stage.stage_state(),
            stage_input_from_outputs(&submission, optimize_stage, &compile_output),
        )
        .map_err(status_to_stage_error(optimize_stage, "begin_optimize"))?;
    optimize_output = adapters
        .optimize(&submission, &compile_output)
        .await
        .map_err(|err| stage_error(optimize_stage, err))?;    

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Optimize, "optimize")?;
        return Ok(());
    }

    runtime
        .finish_stage_success(
            &job_id,
            &optimize_stage_id,
            optimize_stage.next_state_after_success(),
            optimize_output.clone(),
        )
        .map_err(status_to_stage_error(optimize_stage, "finish_optimize"))?;
    runtime
        .set_state(&job_id, DagStageKind::Schedule.stage_state())
        .map_err(status_to_stage_error(optimize_stage, "set_schedule_state"))?;

    if runtime.is_cancel_requested(&job_id) {
        cancel_after_stage(&runtime, &job_id, DagStageKind::Schedule, "cancelled before schedule")?;
        return Ok(());
    }

    let schedule_stage = DagStageKind::Schedule;
    let schedule_stage_id = runtime
        .begin_stage(
            &job_id,
            schedule_stage,
            schedule_stage.stage_state(),
            stage_input_from_outputs(&submission, schedule_stage, &optimize_output),
        )
        .map_err(status_to_stage_error(schedule_stage, "begin_schedule"))?;
    schedule_output = adapters
        .schedule(&submission, &optimize_output)
        .await
        .map_err(|err| stage_error(schedule_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Schedule, "schedule")?;
        return Ok(());
    }

    let mut reservation_metadata = BTreeMap::from([
        ("reservation_state".to_string(), "held".to_string()),
        (
            "resource_plan_ref".to_string(),
            schedule_output
                .get("resource_plan_ref")
                .cloned()
                .unwrap_or_else(|| format!("qfs://jobs/{job_id}/schedule/plan.json")),
        ),
    ]);
    runtime
        .set_metadata(&job_id, reservation_metadata.clone())
        .map_err(status_to_stage_error(schedule_stage, "set_reservation_metadata"))?;

    runtime
        .finish_stage_success(
            &job_id,
            &schedule_stage_id,
            schedule_stage.next_state_after_success(),
            schedule_output.clone(),
        )
        .map_err(status_to_stage_error(schedule_stage, "finish_schedule"))?;
    runtime
        .set_state(&job_id, DagStageKind::Execute.stage_state())
        .map_err(status_to_stage_error(schedule_stage, "set_execute_state"))?;

    if runtime.is_cancel_requested(&job_id) {
        cancel_after_stage(&runtime, &job_id, DagStageKind::Execute, "cancelled before execute")?;
        return Ok(());
    }

    let execute_stage = DagStageKind::Execute;
    let execute_stage_id = runtime
        .begin_stage(
            &job_id,
            execute_stage,
            execute_stage.stage_state(),
            stage_input_from_outputs(&submission, execute_stage, &schedule_output),
        )
        .map_err(status_to_stage_error(execute_stage, "begin_execute"))?;
    execution_output = execute_with_retry(
        &runtime,
        &job_id,
        &execute_stage_id,
        &submission,
        &schedule_output,
        adapters.clone(),
    )
    .await
    .map_err(|err| stage_error(execute_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Execute, "execute")?;
        return Ok(());
    }

    runtime
        .set_counts(&job_id, execution_output.counts.clone())
        .map_err(status_to_stage_error(execute_stage, "set_counts"))?;
    runtime
        .finish_stage_success(
            &job_id,
            &execute_stage_id,
            execute_stage.next_state_after_success(),
            execution_output.output.clone(),
        )
        .map_err(status_to_stage_error(execute_stage, "finish_execute"))?;

    if runtime.is_cancel_requested(&job_id) {
        cancel_after_stage(&runtime, &job_id, DagStageKind::Persist, "cancelled before persist")?;
        return Ok(());
    }

    let persist_stage = DagStageKind::Persist;
    let persist_stage_id = runtime
        .begin_stage(
            &job_id,
            persist_stage,
            persist_stage.stage_state(),
            stage_input_from_outputs(&submission, persist_stage, &execution_output.output),
        )
        .map_err(status_to_stage_error(persist_stage, "begin_persist"))?;
    persist_output = adapters
        .persist(&submission, &execution_output, &runtime.get(&job_id).map(|job| job.stage_records.clone()).unwrap_or_default())
        .await
        .map_err(|err| stage_error(persist_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Persist, "persist")?;
        return Ok(());
    }

    if let Some(result_ref) = persist_output.get("qfs_result_ref").cloned() {
        runtime
            .set_qfs_result_ref(&job_id, result_ref)
            .map_err(status_to_stage_error(persist_stage, "set_result_ref"))?;
    }
    runtime
        .finish_stage_success(
            &job_id,
            &persist_stage_id,
            persist_stage.next_state_after_success(),
            persist_output.clone(),
        )
        .map_err(status_to_stage_error(persist_stage, "finish_persist"))?;

    if runtime.is_cancel_requested(&job_id) {
        cancel_after_stage(
            &runtime,
            &job_id,
            DagStageKind::RecordKnowledgeObservability,
            "cancelled before observability",
        )?;
        return Ok(());
    }

    let observability_stage = DagStageKind::RecordKnowledgeObservability;
    let observability_stage_id = runtime
        .begin_stage(
            &job_id,
            observability_stage,
            observability_stage.stage_state(),
            stage_input_from_outputs(&submission, observability_stage, &persist_output),
        )
        .map_err(status_to_stage_error(observability_stage, "begin_observability"))?;
    observability_output = adapters
        .record_knowledge_observability(&submission, &persist_output, &execution_output)
        .await
        .map_err(|err| stage_error(observability_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::RecordKnowledgeObservability, "observability")?;
        return Ok(());
    }

    runtime
        .set_metadata(&job_id, observability_output.clone())
        .map_err(status_to_stage_error(observability_stage, "set_observability_metadata"))?;
    runtime
        .finish_stage_success(
            &job_id,
            &observability_stage_id,
            observability_stage.next_state_after_success(),
            observability_output.clone(),
        )
        .map_err(status_to_stage_error(observability_stage, "finish_observability"))?;

    let finalize_stage = DagStageKind::Finalize;
    let finalize_stage_id = runtime
        .begin_stage(
            &job_id,
            finalize_stage,
            finalize_stage.stage_state(),
            stage_input_from_outputs(&submission, finalize_stage, &observability_output),
        )
        .map_err(status_to_stage_error(finalize_stage, "begin_finalize"))?;
    let finalize_output = adapters
        .finalize(&submission, &observability_output)
        .await
        .map_err(|err| stage_error(finalize_stage, err))?;

    if runtime.is_cancel_requested(&job_id) || runtime.deadline_expired(&job_id) {
        terminalize_control(&runtime, &job_id, DagStageKind::Finalize, "finalize")?;
        return Ok(());
    }

    runtime
        .finish_stage_success(
            &job_id,
            &finalize_stage_id,
            finalize_stage.next_state_after_success(),
            finalize_output,
        )
        .map_err(status_to_stage_error(finalize_stage, "finish_finalize"))?;

    Ok(())
}

fn stage_input_from_outputs(
    submission: &NormalizedSubmission,
    stage: DagStageKind,
    upstream: &BTreeMap<String, String>,
) -> BTreeMap<String, String> {
    let mut input = submission.stage_input(stage);
    for (key, value) in upstream {
        input.insert(format!("upstream.{key}"), value.clone());
    }
    input
}

fn stage_error(stage: DagStageKind, err: KernelStageError) -> KernelStageError {
    KernelStageError::new(
        err.grpc_code,
        err.error_code,
        format!("{} stage failed: {}", stage.key(), err.summary),
        err.details_ref,
    )
}

fn status_to_stage_error(stage: DagStageKind, action: &'static str) -> impl FnOnce(Status) -> KernelStageError {
    move |status| {
        KernelStageError::new(
            Code::Internal,
            "RUNTIME_STAGE_FAILURE",
            format!("{} stage {} failed", stage.key(), action),
            format!("status::{:?}", status.code()),
        )
    }
}

fn cancel_after_stage(
    runtime: &Arc<KernelRuntimeStore>,
    job_id: &str,
    next_stage: DagStageKind,
    reason: &str,
) -> Result<(), KernelStageError> {
    let terminal_error = KernelStageError::new(
        Code::Cancelled,
        "CANCELLED",
        reason,
        format!("qfs://jobs/{job_id}/errors/cancelled.json"),
    );
    let stage_id = stage_id(job_id, next_stage);
    let input = BTreeMap::from([
        ("job_id".to_string(), job_id.to_string()),
        ("stage_id".to_string(), stage_id.clone()),
        ("reason".to_string(), reason.to_string()),
    ]);
    let _ = runtime.begin_stage(job_id, next_stage, next_stage.stage_state(), input);
    runtime
        .finish_stage_failure(
            job_id,
            &stage_id,
            TaskState::Cancelled,
            terminal_error.error_code,
            &terminal_error.summary,
            &terminal_error.details_ref,
        )
        .map_err(|status| KernelStageError::new(
            Code::Internal,
            "RUNTIME_STAGE_FAILURE",
            format!("cancel terminalization failed: {}", status.message()),
            format!("status::{:?}", status.code()),
        ))?;
    Ok(())
}

fn terminalize_control(
    runtime: &Arc<KernelRuntimeStore>,
    job_id: &str,
    stage: DagStageKind,
    stage_label: &str,
) -> Result<(), KernelStageError> {
    let is_cancel = runtime.is_cancel_requested(job_id);
    let stage_id = stage_id(job_id, stage);
    let reason = if is_cancel {
        "cancelled by request"
    } else {
        "deadline exceeded"
    };
    let terminal_state = if is_cancel { TaskState::Cancelled } else { TaskState::Timeout };
    let error_code = if is_cancel { "CANCELLED" } else { "DEADLINE_EXCEEDED" };
    let error_details_ref = if is_cancel {
        format!("qfs://jobs/{job_id}/errors/cancelled.json")
    } else {
        format!("qfs://jobs/{job_id}/errors/deadline.json")
    };
    runtime
        .finish_stage_failure(
            job_id,
            &stage_id,
            terminal_state,
            error_code,
            &format!("{stage_label} {reason}"),
            &error_details_ref,
        )
        .map_err(|status| KernelStageError::new(
            Code::Internal,
            "RUNTIME_STAGE_FAILURE",
            format!("{stage_label} terminalization failed"),
            format!("status::{:?}", status.code()),
        ))?;
    runtime
        .set_reservation_state(job_id, "released")
        .map_err(|status| KernelStageError::new(
            Code::Internal,
            "RUNTIME_STAGE_FAILURE",
            format!("{stage_label} reservation release failed"),
            format!("status::{:?}", status.code()),
        ))?;
    Ok(())
}

async fn execute_with_retry(
    runtime: &Arc<KernelRuntimeStore>,
    job_id: &str,
    execute_stage_id: &str,
    submission: &NormalizedSubmission,
    schedule_output: &BTreeMap<String, String>,
    adapters: Arc<dyn OrchestrationAdapters>,
) -> Result<ExecutionOutcome, KernelStageError> {
    let policy = RetryPolicy::from_metadata(&submission.metadata_kvs);
    let started = Instant::now();
    let mut attempt: u32 = 0;

    loop {
        attempt = attempt.saturating_add(1);
        let attempt_started = Instant::now();
        let span = tracing::info_span!(
            "execute_attempt",
            job_id = %job_id,
            attempt = attempt,
            stage = "execute"
        );

        let result = async {
            adapters
                .as_ref()
                .execute(submission, schedule_output)
                .await
        }
        .instrument(span)
        .await;

        match result {
            Ok(outcome) => {
                if attempt > 1 {
                    runtime
                        .set_retry_success_after_retry_total(job_id, 1)
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "retry success metadata update failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                }
                return Ok(outcome);
            }
            Err(err) => {
                let retryable = RetryPolicy::default().is_retryable(&err);
                let delay = if retryable { policy.backoff_for_attempt(attempt) } else { Duration::from_millis(0) };
                let elapsed_ms = started.elapsed().as_millis() as u64;
                runtime
                    .record_retry_attempt(
                        job_id,
                        RetryAttemptRecord {
                            attempt,
                            grpc_code: err.grpc_code,
                            reason_code: err.error_code.to_string(),
                            retryable,
                            delay_ms: delay.as_millis() as u64,
                            elapsed_ms,
                            recorded_at: ts_now(),
                        },
                    )
                    .map_err(|status| KernelStageError::new(
                        Code::Internal,
                        "RUNTIME_STAGE_FAILURE",
                        "retry attempt record failed",
                        format!("status::{:?}", status.code()),
                    ))?;

                if runtime.deadline_expired(job_id) {
                    runtime
                        .set_retry_final_reason(job_id, "DEADLINE_EXCEEDED")
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "retry final reason update failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    runtime
                        .finish_stage_failure(
                            job_id,
                            execute_stage_id,
                            TaskState::Timeout,
                            "DEADLINE_EXCEEDED",
                            "execution retry interrupted by deadline",
                            &format!("qfs://jobs/{job_id}/errors/deadline.json"),
                        )
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "deadline terminalization failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    runtime
                        .set_reservation_state(job_id, "released")
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "reservation release after deadline failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    return Err(KernelStageError::deadline_exceeded(
                        "execution retry interrupted by deadline",
                        format!("qfs://jobs/{job_id}/errors/deadline.json"),
                    ));
                }

                if !retryable || attempt >= policy.max_attempts {
                    let final_reason = if retryable { "RETRY_EXHAUSTED" } else { "NON_RETRYABLE" };
                    runtime
                        .set_retry_final_reason(job_id, final_reason)
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "retry final reason update failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    runtime
                        .finish_stage_failure(
                            job_id,
                            execute_stage_id,
                            TaskState::Error,
                            &err.error_code,
                            &err.summary,
                            &err.details_ref,
                        )
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "retry terminalization failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    runtime
                        .set_reservation_state(job_id, "released")
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "reservation release after retry terminalization failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    return Err(err);
                }

                if started.elapsed().saturating_add(delay) > policy.max_elapsed {
                    runtime
                        .set_retry_final_reason(job_id, "DEADLINE_EXCEEDED")
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "retry final reason update failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    runtime
                        .finish_stage_failure(
                            job_id,
                            execute_stage_id,
                            TaskState::Timeout,
                            "DEADLINE_EXCEEDED",
                            "execution retry budget exceeded by elapsed deadline budget",
                            &format!("qfs://jobs/{job_id}/errors/deadline.json"),
                        )
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "retry budget terminalization failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    runtime
                        .set_reservation_state(job_id, "released")
                        .map_err(|status| KernelStageError::new(
                            Code::Internal,
                            "RUNTIME_STAGE_FAILURE",
                            "reservation release after retry budget exhaustion failed",
                            format!("status::{:?}", status.code()),
                        ))?;
                    return Err(KernelStageError::deadline_exceeded(
                        "execution retry budget exceeded by elapsed deadline budget",
                        format!("qfs://jobs/{job_id}/errors/deadline.json"),
                    ));
                }

                tokio::time::sleep(delay).await;
                let elapsed_after_sleep = attempt_started.elapsed().as_millis() as u64;
                tracing::info!(
                    job_id = %job_id,
                    attempt,
                    retryable,
                    grpc_code = ?err.grpc_code,
                    reason_code = %err.error_code,
                    delay_ms = delay.as_millis() as u64,
                    elapsed_ms = elapsed_after_sleep,
                    "retrying execution attempt"
                );
            }
        }
    }
}

fn parse_positive_usize(metadata: &BTreeMap<String, String>, key: &str) -> Option<usize> {
    metadata
        .get(key)
        .and_then(|v| v.parse::<usize>().ok())
        .filter(|v| *v > 0)
}

fn parse_reason_csv(raw: &str) -> Vec<&'static str> {
    raw.split(',')
        .map(|v| v.trim())
        .filter(|v| !v.is_empty())
        .filter_map(|v| match v {
            "EIGEN_EXECUTION_UNAVAILABLE" => Some("EIGEN_EXECUTION_UNAVAILABLE"),
            "EIGEN_EXECUTION_RESOURCE_EXHAUSTED" => Some("EIGEN_EXECUTION_RESOURCE_EXHAUSTED"),
            "EIGEN_EXECUTION_ABORTED" => Some("EIGEN_EXECUTION_ABORTED"),
            "EIGEN_EXECUTION_DEADLINE_EXCEEDED" => Some("EIGEN_EXECUTION_DEADLINE_EXCEEDED"),
            "EIGEN_EXECUTION_INVALID_ARGUMENT" => Some("EIGEN_EXECUTION_INVALID_ARGUMENT"),
            "EIGEN_EXECUTION_FAILED_PRECONDITION" => Some("EIGEN_EXECUTION_FAILED_PRECONDITION"),
            "EIGEN_EXECUTION_INTERNAL" => Some("EIGEN_EXECUTION_INTERNAL"),
            "EIGEN_EXECUTION_UNAUTHENTICATED" => Some("EIGEN_EXECUTION_UNAUTHENTICATED"),
            "EIGEN_EXECUTION_PERMISSION_DENIED" => Some("EIGEN_EXECUTION_PERMISSION_DENIED"),
            "EIGEN_EXECUTION_UNIMPLEMENTED" => Some("EIGEN_EXECUTION_UNIMPLEMENTED"),
            _ => None,
        })
        .collect()
}

fn nonempty(value: &str, field: &'static str) -> Result<String, Status> {
    if value.trim().is_empty() {
        Err(Status::invalid_argument(format!("{field} is required")))
    } else {
        Ok(value.trim().to_string())
    }
}

fn nonempty_or_default(value: &str, default: &str) -> String {
    if value.trim().is_empty() {
        default.to_string()
    } else {
        value.trim().to_string()
    }
}

fn canonical_string_map(input: &HashMap<String, String>) -> BTreeMap<String, String> {
    input
        .iter()
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect::<BTreeMap<_, _>>()
}

fn stage_id(job_id: &str, stage: DagStageKind) -> String {
    format!("{job_id}:{:02}-{}", stage.index(), stage.key())
}

fn normalized_deadline_at(deadline: &prost_types::Duration) -> Option<Timestamp> {
    if deadline.seconds <= 0 && deadline.nanos <= 0 {
        return None;
    }
    let now = ts_now();
    let now_ms = timestamp_to_ms(&now);
    let deadline_ms = now_ms
        .saturating_add((deadline.seconds.max(0) as i128) * 1000)
        .saturating_add((deadline.nanos.max(0) as i128) / 1_000_000);
    Some(Timestamp {
        seconds: (deadline_ms / 1000) as i64,
        nanos: ((deadline_ms % 1000) * 1_000_000) as i32,
    })
}

fn timestamp_to_ms(ts: &Timestamp) -> i128 {
    (ts.seconds as i128) * 1000 + (ts.nanos as i128 / 1_000_000)
}

fn parse_stage_kind(value: &str) -> Option<DagStageKind> {
    match value {
        "validate" | "validate_enq" | "validate-enqueue" => Some(DagStageKind::ValidateEnqueue),
        "compile" => Some(DagStageKind::Compile),
        "optimize" => Some(DagStageKind::Optimize),
        "schedule" => Some(DagStageKind::Schedule),
        "execute" => Some(DagStageKind::Execute),
        "persist" => Some(DagStageKind::Persist),
        "observability" | "record-knowledge-observability" => Some(DagStageKind::RecordKnowledgeObservability),
        "finalize" => Some(DagStageKind::Finalize),
        _ => None,
    }
}

fn stage_snapshot_bytes(stage: &StageRecord) -> Vec<u8> {
    serde_json::to_vec(&serde_json::json!({
        "stage_id": stage.stage_id,
        "stage_key": stage.stage_key,
        "order": stage.order,
        "state_before": stage.state_before as i32,
        "state_after": stage.state_after as i32,
        "status": match stage.status {
            StageStatus::Running => "running",
            StageStatus::Succeeded => "succeeded",
            StageStatus::Failed => "failed",
        },
        "started_at": ts_to_json(&stage.started_at),
        "completed_at": stage.completed_at.as_ref().map(ts_to_json),
        "input": stage.input,
        "output": stage.output,
        "error_code": stage.error_code,
        "error_summary": stage.error_summary,
        "error_details_ref": stage.error_details_ref,
        "replay_token": stage.replay_token,
    }))
    .unwrap_or_default()
}


fn stage_digest_bytes(stage: &StageRecord) -> Vec<u8> {
    serde_json::to_vec(&serde_json::json!({
        "stage_id": stage.stage_id,
        "stage_key": stage.stage_key,
        "order": stage.order,
        "state_before": stage.state_before as i32,
        "state_after": stage.state_after as i32,
        "status": match stage.status {
            StageStatus::Running => "running",
            StageStatus::Succeeded => "succeeded",
            StageStatus::Failed => "failed",
        },
        "started_at": ts_to_json(&stage.started_at),
        "completed_at": stage.completed_at.as_ref().map(ts_to_json),
        "input": stage.input,
        "output": stage.output,
        "error_code": stage.error_code,
        "error_summary": stage.error_summary,
        "error_details_ref": stage.error_details_ref,
    }))
    .unwrap_or_default()
}

fn canonical_submission_fingerprint(
    contract_version: &str,
    request_id: &str,
    idempotency_key: &str,
    traceparent: &str,
    tenant_id: &str,
    project_id: &str,
    subject: &str,
    role: &str,
    source_service: &str,
    deadline_seconds: Option<u64>,
    name: &str,
    program_format: &str,
    program_hash: &str,
    target: &str,
    priority: i32,
    compiler_options: &BTreeMap<String, String>,
    metadata_kvs: &BTreeMap<String, String>,
) -> String {
    let mut material = String::new();
    let parts = [
        ("contract_version", contract_version.to_string()),
        ("request_id", request_id.to_string()),
        ("idempotency_key", idempotency_key.to_string()),
        ("traceparent", traceparent.to_string()),
        ("tenant_id", tenant_id.to_string()),
        ("project_id", project_id.to_string()),
        ("subject", subject.to_string()),
        ("role", role.to_string()),
        ("source_service", source_service.to_string()),
        (
            "deadline_seconds",
            deadline_seconds.map(|v| v.to_string()).unwrap_or_default(),
        ),
        ("name", name.to_string()),
        ("program_format", program_format.to_string()),
        ("program_hash", program_hash.to_string()),
        ("target", target.to_string()),
        ("priority", priority.to_string()),
    ];
    for (k, v) in parts {
        material.push_str(k);
        material.push('=');
        material.push_str(&v);
        material.push('|');
    }
    material.push_str("compiler_options=");
    for (k, v) in compiler_options {
        material.push_str(k);
        material.push('=');
        material.push_str(v);
        material.push('|');
    }
    material.push_str("metadata_kvs=");
    for (k, v) in metadata_kvs {
        material.push_str(k);
        material.push('=');
        material.push_str(v);
        material.push('|');
    }
    stable_hash_hex(&material)
}

fn stable_trace_id(request_id: &str, program_hash: &str) -> String {
    let material = format!("{request_id}:{program_hash}");
    stable_hash_hex(&material)
}

fn stable_hash_hex(input: &str) -> String {
    format!("{:016x}", fnv1a64(input.as_bytes()))
}

fn hash_bytes_hex(input: &[u8]) -> String {
    format!("{:016x}", fnv1a64(input))
}

fn fnv1a64(input: &[u8]) -> u64 {
    const OFFSET: u64 = 0xcbf29ce484222325;
    const PRIME: u64 = 0x100000001b3;
    let mut hash = OFFSET;
    for byte in input {
        hash ^= *byte as u64;
        hash = hash.wrapping_mul(PRIME);
    }
    hash
}

fn trace_id_from_traceparent(traceparent: &str) -> Option<String> {
    let mut parts = traceparent.split('-');
    let _version = parts.next()?;
    let trace_id = parts.next()?;
    if trace_id.len() == 32 {
        Some(trace_id.to_string())
    } else {
        None
    }
}

fn ts_now() -> Timestamp {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_else(|_| Duration::from_secs(0));
    Timestamp {
        seconds: duration.as_secs() as i64,
        nanos: duration.subsec_nanos() as i32,
    }
}

fn ts_to_json(ts: &Timestamp) -> serde_json::Value {
    serde_json::json!({
        "seconds": ts.seconds,
        "nanos": ts.nanos,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use prost_types::{Duration as ProtoDuration, Timestamp};
    use tokio_stream::StreamExt;
    use tonic::Request;

    fn make_service(failure_stage: Option<DagStageKind>) -> (KernelGatewaySvc, Arc<KernelRuntimeStore>) {
        let runtime = Arc::new(KernelRuntimeStore::default());
        let adapters = Arc::new(FixtureAdapters::new("/tmp/eigen-kernel-test-qfs", failure_stage));
        let svc = KernelGatewaySvc::new(runtime.clone(), adapters);
        (svc, runtime)
    }

    fn make_request(name: &str) -> EnqueueJobRequest {
        let mut compiler_options = HashMap::new();
        compiler_options.insert("optimizer_step".to_string(), "0.1".to_string());

        let mut metadata_kvs = HashMap::new();
        metadata_kvs.insert("shots".to_string(), "128".to_string());

        EnqueueJobRequest {
            metadata: Some(RequestMetadata {
                contract_version: "1.0.0".to_string(),
                request_id: format!("req-{name}"),
                idempotency_key: format!("idem-{name}"),
                traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                tenant_id: "tenant-a".to_string(),
                project_id: "project-a".to_string(),
                subject: "alice".to_string(),
                role: "user".to_string(),
                source_service: "system-api".to_string(),
            }),
            name: name.to_string(),
            program: br#"{"qubits": 1, "parameters": [0.1]}"#.to_vec(),
            program_format: "aqo_json".to_string(),
            target: "sim:local".to_string(),
            priority: 50,
            compiler_options,
            metadata_kvs,
        }
    }

    fn make_status_request(job_id: &str) -> GetJobStatusRequest {
        GetJobStatusRequest {
            metadata: Some(RequestMetadata {
                contract_version: "1.0.0".to_string(),
                request_id: format!("status-{job_id}"),
                idempotency_key: format!("status-{job_id}"),
                traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                tenant_id: "tenant-a".to_string(),
                project_id: "project-a".to_string(),
                subject: "alice".to_string(),
                role: "user".to_string(),
                source_service: "system-api".to_string(),
            }),
            job_id: job_id.to_string(),
        }
    }

    async fn wait_for_terminal(runtime: Arc<KernelRuntimeStore>, job_id: &str) -> JobRuntimeRecord {
        let deadline = tokio::time::Instant::now() + Duration::from_secs(5);
        loop {
            if let Some(job) = runtime.get(job_id) {
                if job.is_terminal() {
                    return job;
                }
            }
            assert!(tokio::time::Instant::now() < deadline, "job did not reach terminal state");
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    }

    #[tokio::test]
    async fn submit_to_results_success_path_records_all_stages() {
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("success")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let job = wait_for_terminal(runtime.clone(), &response.job_id).await;
        assert_eq!(job.state, TaskState::Done);
        assert_eq!(
            job.stage_records.iter().map(|stage| stage.stage_key.clone()).collect::<Vec<_>>(),
            DagStageKind::all().iter().map(|stage| stage.key().to_string()).collect::<Vec<_>>()
        );
        assert!(job.snapshot_digest().len() >= 16);

        let status = svc
            .get_job_status(Request::new(make_status_request(&response.job_id)))
            .await
            .expect("status should succeed")
            .into_inner();
        assert_eq!(status.state, TaskState::Done as i32);
        assert_eq!(status.stage, "finalize");

        let results = svc
            .get_job_results(Request::new(GetJobResultsRequest {
                metadata: Some(RequestMetadata {
                    contract_version: "1.0.0".to_string(),
                    request_id: format!("results-{}", response.job_id),
                    idempotency_key: format!("results-{}", response.job_id),
                    traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                    deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                    tenant_id: "tenant-a".to_string(),
                    project_id: "project-a".to_string(),
                    subject: "alice".to_string(),
                    role: "user".to_string(),
                    source_service: "system-api".to_string(),
                }),
                job_id: response.job_id.clone(),
            }))
            .await
            .expect("results should succeed")
            .into_inner();
        assert_eq!(results.state, TaskState::Done as i32);
        assert!(!results.qfs_result_ref.is_empty());
        assert!(!results.counts.is_empty());
    }

    #[tokio::test]
    async fn submit_to_results_failure_path_marks_error_metadata() {
        let (svc, runtime) = make_service(Some(DagStageKind::Optimize));
        let response = svc
            .enqueue_job(Request::new(make_request("failure")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let job = wait_for_terminal(runtime.clone(), &response.job_id).await;
        assert_eq!(job.state, TaskState::Error);
        assert_eq!(job.error_code.as_deref(), Some("OPTIMIZER_STAGE_FAILED"));
        assert_eq!(
            job.stage_records
                .iter()
                .find(|stage| stage.stage_key == "optimize")
                .and_then(|stage| stage.error_code.as_deref()),
            Some("OPTIMIZER_STAGE_FAILED")
        );

        let results = svc
            .get_job_results(Request::new(GetJobResultsRequest {
                metadata: Some(RequestMetadata {
                    contract_version: "1.0.0".to_string(),
                    request_id: format!("results-{}", response.job_id),
                    idempotency_key: format!("results-{}", response.job_id),
                    traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                    deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                    tenant_id: "tenant-a".to_string(),
                    project_id: "project-a".to_string(),
                    subject: "alice".to_string(),
                    role: "user".to_string(),
                    source_service: "system-api".to_string(),
                }),
                job_id: response.job_id.clone(),
            }))
            .await
            .expect("terminal error results should succeed")
            .into_inner();
        assert_eq!(results.state, TaskState::Error as i32);
        assert_eq!(results.error_code, "OPTIMIZER_STAGE_FAILED");
        assert!(!results.error_summary.is_empty());
    }

    fn make_retry_service(script: Vec<ExecuteScriptStep>) -> (KernelGatewaySvc, Arc<KernelRuntimeStore>) {
        let runtime = Arc::new(KernelRuntimeStore::default());
        let adapters = Arc::new(FixtureAdapters::with_execute_script(
            "/tmp/eigen-kernel-test-qfs",
            None,
            script,
        ));
        let svc = KernelGatewaySvc::new(runtime.clone(), adapters);
        (svc, runtime)
    }

    #[tokio::test]
    async fn retryable_failure_succeeds_after_one_retry() {
        let (svc, runtime) = make_retry_service(vec![
            ExecuteScriptStep::Unavailable,
            ExecuteScriptStep::Success,
        ]);
        let mut req = make_request("retryable-success");
        req.metadata_kvs.insert("retry.max_attempts".to_string(), "3".to_string());
        let response = svc
            .enqueue_job(Request::new(req))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Done);
        assert_eq!(job.retry_attempts.len(), 1);
        assert_eq!(job.retry_success_after_retry_total, 1);
        assert_eq!(
            job.retry_attempts[0].reason_code,
            "EIGEN_EXECUTION_UNAVAILABLE"
        );
    }

    #[tokio::test]
    async fn non_retryable_failure_does_not_retry() {
        let (svc, runtime) = make_retry_service(vec![ExecuteScriptStep::InvalidArgument]);
        let response = svc
            .enqueue_job(Request::new(make_request("non-retryable")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Error);
        assert_eq!(job.retry_attempts.len(), 1);
        assert_eq!(job.retry_final_reason.as_deref(), Some("NON_RETRYABLE"));
    }

    #[tokio::test]
    async fn exhausted_retries_produce_terminal_error_state() {
        let (svc, runtime) = make_retry_service(vec![
            ExecuteScriptStep::Unavailable,
            ExecuteScriptStep::Unavailable,
            ExecuteScriptStep::Unavailable,
        ]);
        let mut req = make_request("exhausted");
        req.metadata_kvs.insert("retry.max_attempts".to_string(), "2".to_string());
        let response = svc
            .enqueue_job(Request::new(req))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Error);
        assert_eq!(job.retry_attempts.len(), 2);
        assert_eq!(job.retry_final_reason.as_deref(), Some("RETRY_EXHAUSTED"));
        assert_eq!(job.error_code.as_deref(), Some("EIGEN_EXECUTION_UNAVAILABLE"));
    }

    #[tokio::test]
    async fn deadline_interrupted_retry_becomes_timeout() {
        let (svc, runtime) = make_retry_service(vec![
            ExecuteScriptStep::Unavailable,
            ExecuteScriptStep::Success,
        ]);
        let mut req = make_request("deadline-interrupted");
        if let Some(metadata) = req.metadata.as_mut() {
            metadata.deadline = Some(ProtoDuration { seconds: 0, nanos: 10_000_000 });
        }
        req.metadata_kvs.insert("retry.base_delay_ms".to_string(), "100".to_string());
        let response = svc
            .enqueue_job(Request::new(req))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Timeout);
        assert_eq!(job.retry_attempts.len(), 1);
        assert_eq!(job.retry_final_reason.as_deref(), Some("DEADLINE_EXCEEDED"));
    }
 }

    fn make_cancel_request(job_id: &str) -> CancelJobRequest {
        CancelJobRequest {
            metadata: Some(RequestMetadata {
                contract_version: "1.0.0".to_string(),
                request_id: format!("cancel-{job_id}"),
                idempotency_key: format!("cancel-{job_id}"),
                traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                tenant_id: "tenant-a".to_string(),
                project_id: "project-a".to_string(),
                subject: "alice".to_string(),
                role: "user".to_string(),
                source_service: "system-api".to_string(),
            }),
            job_id: job_id.to_string(),
        }
    }

    #[tokio::test]
    async fn cancellation_while_queued_releases_reservation() {
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_STAGE", "schedule");
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_MS", "80");
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("queued-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Cancelled);
        assert_eq!(job.reservation_state.as_deref(), Some("released"));
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_STAGE");
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_MS");
    }

    #[tokio::test]
    async fn cancellation_while_compiling_is_deterministic() {
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_STAGE", "compile");
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_MS", "80");
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("compile-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Cancelled);
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_STAGE");
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_MS");
    }

    #[tokio::test]
    async fn cancellation_while_executing_is_deterministic() {
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_STAGE", "execute");
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_MS", "80");
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("execute-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Cancelled);
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_STAGE");
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_MS");
    }

    #[tokio::test]
    async fn cancellation_while_finalizing_keeps_canonical_terminal_state() {
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_STAGE", "finalize");
        std::env::set_var("EIGEN_KERNEL_TEST_HOLD_MS", "80");
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("finalize-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert!(matches!(job.state, TaskState::Cancelled | TaskState::Done));
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_STAGE");
        std::env::remove_var("EIGEN_KERNEL_TEST_HOLD_MS");
    }

    #[tokio::test]
    async fn deadline_expiry_maps_to_timeout_behavior() {
        let mut req = make_request("deadline-timeout");
        if let Some(md) = req.metadata.as_mut() {
            md.deadline = Some(ProtoDuration { seconds: 0, nanos: 1 });
        }
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(req))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Timeout);
        assert_eq!(job.error_code.as_deref(), Some("DEADLINE_EXCEEDED"));
        assert_eq!(job.reservation_state.as_deref(), Some("released"));
    }

    #[tokio::test]
    async fn stream_updates_emit_stage_envelopes_in_order() {
        let (svc, _runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("stream")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let stream = svc
            .stream_job_updates(Request::new(StreamJobUpdatesRequest {
                metadata: Some(RequestMetadata {
                    contract_version: "1.0.0".to_string(),
                    request_id: format!("stream-{}", response.job_id),
                    idempotency_key: format!("stream-{}", response.job_id),
                    traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                    deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                    tenant_id: "tenant-a".to_string(),
                    project_id: "project-a".to_string(),
                    subject: "alice".to_string(),
                    role: "user".to_string(),
                    source_service: "system-api".to_string(),
                }),
                job_id: response.job_id.clone(),
                last_event_seq: 0,
            }))
            .await
            .expect("stream should succeed")
            .into_inner();

        let collected: Vec<_> = stream.collect().await;
        assert!(!collected.is_empty());
        assert_eq!(collected[0].as_ref().unwrap().update.as_ref().unwrap().event_seq, 1);
    }
}
