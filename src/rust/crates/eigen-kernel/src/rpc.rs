
//! KernelGateway internal runtime with deterministic DAG orchestration.
//!
//! Product 1.0 Wave 2:
//! - stage-by-stage orchestration DAG
//! - stable stage IDs for tracing and replay
//! - explicit downstream adapters for handoff points
//! - canonical terminal state / error metadata propagation

use std::collections::{BTreeMap, BTreeSet, HashMap, VecDeque};
use std::fmt;
use std::fs;
use std::net::SocketAddr;
use std::pin::Pin;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use std::time::Instant;

use parking_lot::Mutex;
use prost_types::{Duration as ProtoDuration, Timestamp};
use tokio_stream::iter;
use tokio_stream::Stream;
use tonic::transport::Endpoint;
use tonic::{Code, Request, Response, Status};
use tracing::Instrument;
use uuid::Uuid;
use sha2::{Digest, Sha256};

use qfs::{
    CircuitFsLocal, CompiledArtifactLineage, CompiledArtifactProvenance, ReleaseEvidenceBundle,
    ReleaseEvidenceManifest, ReleaseEvidenceProvenanceReport, ResultArtifactDescriptor,
    ResultEnvelope, ScientificMeasurement,
};
use resource_manager::{
    SCHEDULER_DECISION_VERSION, SCHEDULING_POLICY_BUNDLE_ID, SCHEDULING_POLICY_BUNDLE_VERSION,
};

use crate::proto::compilation_service_client::CompilationServiceClient;
use crate::proto::driver_manager_service_client::DriverManagerServiceClient;
use crate::proto::kernel_gateway_service_server::{
    KernelGatewayService, KernelGatewayServiceServer,
};
use crate::proto::optimizer_service_client::OptimizerServiceClient;
use crate::proto::stream_job_updates_response::JobUpdateEnvelope;
use crate::proto::{
    CircuitPayload, CompileCircuitRequest, ExecuteCircuitRequest, GraphEncodingContext,
    OptimizationObjective, OptimizerContractEnvelope, OptimizerPolicy,
    OptimizerRankingSemantics, OptimizerServiceOptimizeCircuitRequest, RequestMetadata,
    TopologyContext, CancelJobRequest, CancelJobResponse, DispatchRationale, EnqueueJobRequest,
    WorkloadContract, WorkloadTopology,
    EnqueueJobResponse, GetDispatchRationaleRequest, GetDispatchRationaleResponse,
    GetJobResultsRequest, GetJobResultsResponse, GetJobStatusRequest, GetJobStatusResponse,
    StreamJobUpdatesRequest, StreamJobUpdatesResponse, TaskState,
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
enum StageStatus {
    Running,
    Succeeded,
    Failed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
enum WorkflowBoundaryKind {
    WorkflowStarted,
    StageEntered,
    StageCompleted,
    StageFailed,
    WorkflowCompleted,
}

impl WorkflowBoundaryKind {
    fn key(self) -> &'static str {
        match self {
            Self::WorkflowStarted => "workflow-started",
            Self::StageEntered => "stage-entered",
            Self::StageCompleted => "stage-completed",
            Self::StageFailed => "stage-failed",
            Self::WorkflowCompleted => "workflow-completed",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct WorkflowBoundaryRecord {
    boundary_id: String,
    workflow_id: String,
    job_id: String,
    kind: WorkflowBoundaryKind,
    stage_id: Option<String>,
    stage_key: Option<String>,
    order: Option<u32>,
    state_before: Option<TaskState>,
    state_after: Option<TaskState>,
    input_ref: String,
    output_ref: String,
    artifact_ref: String,
    lineage_ref: String,
    replay_token: String,
    timestamp: Timestamp,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct HybridWorkflowStageNode {
    stage_id: String,
    stage_key: String,
    order: u32,
    state_before: TaskState,
    state_after: TaskState,
    status: StageStatus,
    input_ref: String,
    output_ref: String,
    handoff_ref: String,
    artifact_refs: BTreeMap<String, String>,
    lineage_refs: BTreeMap<String, String>,
    replay_token: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct HybridWorkflowGraph {
    workflow_id: String,
    job_id: String,
    root_lineage_ref: String,
    stages: Vec<HybridWorkflowStageNode>,
    boundaries: Vec<WorkflowBoundaryRecord>,
    final_completion_ref: Option<String>,
    final_failure_ref: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum HybridWorkflowValidationError {
    MissingField { stage_id: String, field: String },
    HandoffMismatch { stage_id: String, expected: String, actual: String },
    StageOrderMismatch { expected: u32, actual: u32 },
    TerminalityMismatch { stage_id: String, expected_terminal: String, actual_terminal: String },
}

impl std::fmt::Display for HybridWorkflowValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingField { stage_id, field } => write!(f, "stage {stage_id} is missing required field {field}"),
            Self::HandoffMismatch { stage_id, expected, actual } => write!(
                f,
                "stage {stage_id} has a handoff mismatch (expected {expected}, got {actual})"
            ),
            Self::StageOrderMismatch { expected, actual } => {
                write!(f, "stage order mismatch (expected {expected}, got {actual})")
            }
            Self::TerminalityMismatch { stage_id, expected_terminal, actual_terminal } => write!(
                f,
                "stage {stage_id} terminality mismatch (expected {expected_terminal}, got {actual_terminal})"
            ),
        }
    }
}

impl std::error::Error for HybridWorkflowValidationError {}

impl HybridWorkflowGraph {
    fn validate(&self) -> Result<(), HybridWorkflowValidationError> {
        if self.workflow_id.is_empty() {
            return Err(HybridWorkflowValidationError::MissingField {
                stage_id: self.job_id.clone(),
                field: "workflow_id".to_string(),
            });
        }
        if self.stages.is_empty() {
            return Err(HybridWorkflowValidationError::MissingField {
                stage_id: self.job_id.clone(),
                field: "stages".to_string(),
            });
        }

        let mut previous_output_ref: Option<String> = None;
        let mut previous_order: Option<u32> = None;
        for stage in self.stages.iter() {
            if stage.order == 0 {
                return Err(HybridWorkflowValidationError::StageOrderMismatch {
                    expected: 1,
                    actual: stage.order,
                });
            }
            if let Some(expected_order) = previous_order {
                let actual_order = stage.order;
                if actual_order <= expected_order {
                    return Err(HybridWorkflowValidationError::StageOrderMismatch {
                        expected: expected_order + 1,
                        actual: actual_order,
                    });
                }
            }
            if stage.input_ref.is_empty() {
                return Err(HybridWorkflowValidationError::MissingField {
                    stage_id: stage.stage_id.clone(),
                    field: "input_ref".to_string(),
                });
            }
            if stage.output_ref.is_empty() {
                return Err(HybridWorkflowValidationError::MissingField {
                    stage_id: stage.stage_id.clone(),
                    field: "output_ref".to_string(),
                });
            }
            if stage.handoff_ref.is_empty() {
                return Err(HybridWorkflowValidationError::MissingField {
                    stage_id: stage.stage_id.clone(),
                    field: "handoff_ref".to_string(),
                });
            }
            let lineage_ref = stage
                .lineage_refs
                .get("workflow_lineage_ref")
                .cloned()
                .ok_or_else(|| HybridWorkflowValidationError::MissingField {
                    stage_id: stage.stage_id.clone(),
                    field: "workflow_lineage_ref".to_string(),
                })?;
            if lineage_ref.is_empty() {
                return Err(HybridWorkflowValidationError::MissingField {
                    stage_id: stage.stage_id.clone(),
                    field: "workflow_lineage_ref".to_string(),
                });
            }
            if previous_order.is_none() {
                let expected_root = self.root_lineage_ref.clone();
                let actual_root = stage
                    .lineage_refs
                    .get("workflow_root_lineage_ref")
                    .cloned()
                    .unwrap_or_default();
                if actual_root != expected_root {
                    return Err(HybridWorkflowValidationError::HandoffMismatch {
                        stage_id: stage.stage_id.clone(),
                        expected: expected_root,
                        actual: actual_root,
                    });
                }
            } else {
                let actual = stage
                    .artifact_refs
                    .get("upstream_output_ref")
                    .cloned()
                    .unwrap_or_default();
                let expected = previous_output_ref.clone().unwrap_or_default();
                if actual != expected {
                    return Err(HybridWorkflowValidationError::HandoffMismatch {
                        stage_id: stage.stage_id.clone(),
                        expected,
                        actual,
                    });
                }
            }

            previous_output_ref = Some(stage.output_ref.clone());
            previous_order = Some(stage.order);
        }

        if self.final_completion_ref.is_none() && self.final_failure_ref.is_none() {
            return Err(HybridWorkflowValidationError::MissingField {
                stage_id: self.job_id.clone(),
                field: "final_completion_ref|final_failure_ref".to_string(),
            });
        }

        Ok(())
    }
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
    artifact_refs: BTreeMap<String, String>,
    lineage_refs: BTreeMap<String, String>,
    handoff_ref: String,
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
    explicit_idempotency_key: bool,
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
    workload_metadata: BTreeMap<String, String>,
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
        let explicit_idempotency_key = !metadata.idempotency_key.trim().is_empty();
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
        let request_workload = metadata
            .workload
            .as_ref();
        let workload_metadata = distributed_workload_metadata(&metadata_kvs, &compiler_options, request_workload)?;
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
            name.as_str(),
            program_format.as_str(),
            &program_hash,
            target.as_str(),
            request.priority,
            &compiler_options,
            &metadata_kvs,
        );
        let job_id = if explicit_idempotency_key {
            format!("job-{}", Uuid::new_v4().simple())
        } else {
            format!("job-{}", &fingerprint)
        };

        Ok(Self {
            contract_version,
            request_id,
            idempotency_key,
            explicit_idempotency_key,
            traceparent,
            trace_id,
            tenant_id,
            project_id,
            subject,
            role,
            source_service,
            deadline_seconds,
            deadline_at,
            name,
            program_format,
            program,
            program_hash,
            target,
            priority: request.priority,
            compiler_options,
            metadata_kvs,
            workload_metadata,
            fingerprint,
            job_id,
        })
    }

    fn summary_map(&self) -> BTreeMap<String, String> {
        let mut summary = BTreeMap::from([
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
        ]);
        summary.extend(self.workload_metadata.clone());
        summary
    }

    fn stage_input(&self, stage: DagStageKind) -> BTreeMap<String, String> {
        let mut input = self.summary_map();
        input.extend(self.workload_metadata.clone());
        input.insert("stage_id".to_string(), stage_id(&self.job_id, stage));
        input.insert("stage_key".to_string(), stage.key().to_string());
        input.insert("stage_index".to_string(), stage.index().to_string());
        input.insert("program_bytes".to_string(), self.program.len().to_string());
        input.insert("workflow_id".to_string(), workflow_id_for(&self.job_id));
        input.insert(
            "workflow_root_lineage_ref".to_string(),
            workflow_root_lineage_ref(&self.job_id),
        );
        input.insert(
            "workflow_stage_input_ref".to_string(),
            workflow_stage_input_ref(&self.job_id, stage),
        );
        input.insert(
            "workflow_stage_handoff_ref".to_string(),
            workflow_stage_handoff_ref(&self.job_id, stage),
        );
        input.insert(
            "workflow_stage_lineage_ref".to_string(),
            workflow_stage_lineage_ref(&self.job_id, stage),
        );
        input
    }
}

fn workflow_id_for(job_id: &str) -> String {
    format!("workflow-{job_id}")
}

fn workflow_root_lineage_ref(job_id: &str) -> String {
    format!("qfs://jobs/{job_id}/workflow/lineage.jsonl")
}

fn workflow_stage_input_ref(job_id: &str, stage: DagStageKind) -> String {
    format!(
        "qfs://jobs/{job_id}/workflow/stages/{:02}-{}-input.json",
        stage.index(),
        stage.key()
    )
}

fn workflow_stage_output_ref(job_id: &str, stage: DagStageKind) -> String {
    format!(
        "qfs://jobs/{job_id}/workflow/stages/{:02}-{}-output.json",
        stage.index(),
        stage.key()
    )
}

fn workflow_stage_lineage_ref(job_id: &str, stage: DagStageKind) -> String {
    format!(
        "qfs://jobs/{job_id}/workflow/stages/{:02}-{}-lineage.json",
        stage.index(),
        stage.key()
    )
}

fn workflow_stage_handoff_ref(job_id: &str, stage: DagStageKind) -> String {
    format!(
        "qfs://jobs/{job_id}/workflow/stages/{:02}-{}-handoff.json",
        stage.index(),
        stage.key()
    )
}

fn workflow_stage_failure_ref(job_id: &str, stage: DagStageKind) -> String {
    format!(
        "qfs://jobs/{job_id}/workflow/stages/{:02}-{}-failure.json",
        stage.index(),
        stage.key()
    )
}

fn workflow_completion_ref(job_id: &str) -> String {
    format!("qfs://jobs/{job_id}/workflow/completion.json")
}

fn workflow_failure_ref(job_id: &str) -> String {
    format!("qfs://jobs/{job_id}/workflow/failure.json")
}

fn workflow_boundary_ref(job_id: &str, stage: DagStageKind, kind: WorkflowBoundaryKind) -> String {
    format!(
        "qfs://jobs/{job_id}/workflow/boundaries/{:02}-{}-{}.json",
        stage.index(),
        stage.key(),
        kind.key()
    )
}

fn required_handoff_fields(stage: DagStageKind) -> &'static [&'static str] {
    match stage {
        DagStageKind::ValidateEnqueue => &[],
        DagStageKind::Compile => &["upstream.qfs_submission_ref"],
        DagStageKind::Optimize => &["upstream.compiled_artifact_ref"],
        DagStageKind::Schedule => &["upstream.optimized_artifact_ref"],
        DagStageKind::Execute => &["upstream.resource_plan_ref", "upstream.selected_backend"],
        DagStageKind::Persist => &["upstream.counts_ref", "upstream.execution_ref"],
        DagStageKind::RecordKnowledgeObservability => &["upstream.qfs_result_ref"],
        DagStageKind::Finalize => &["upstream.observability_ref"],
    }
}

fn workflow_output_ref_for_stage_output(job_id: &str, stage: DagStageKind) -> String {
    workflow_stage_output_ref(job_id, stage)
}

fn persist_stage_output_artifact(
    qfs: &CircuitFsLocal,
    job_id: &str,
    stage: DagStageKind,
    output: &BTreeMap<String, String>,
) -> Result<(), KernelStageError> {
    let output_ref = workflow_output_ref_for_stage_output(job_id, stage);
    let payload = serde_json::to_vec_pretty(output).map_err(|err| {
        KernelStageError::internal(
            format!("failed to serialize {} workflow output: {err}", stage.key()),
            output_ref.clone(),
        )
    })?;
    qfs.write_bytes(&output_ref, &payload).map_err(|err| {
        KernelStageError::internal(
            format!("failed to persist {} workflow output: {err}", stage.key()),
            output_ref.clone(),
        )
    })?;
    Ok(())
}

fn canonical_job_id_for_submission(submission: &NormalizedSubmission) -> String {
    format!("job-{}", submission.fingerprint)
}

fn canonicalize_job_scoped_value(value: &str, actual_job_id: &str, canonical_job_id: &str) -> String {
    if actual_job_id.is_empty() || actual_job_id == canonical_job_id {
        return value.to_string();
    }
    value.replace(actual_job_id, canonical_job_id)
}

fn canonicalize_job_scoped_map(
    input: &BTreeMap<String, String>,
    actual_job_id: &str,
    canonical_job_id: &str,
) -> BTreeMap<String, String> {
    input
        .iter()
        .map(|(key, value)| {
            (
                key.clone(),
                canonicalize_job_scoped_value(value, actual_job_id, canonical_job_id),
            )
        })
        .collect()
}

fn canonicalize_stage_record(
    stage: &StageRecord,
    actual_job_id: &str,
    canonical_job_id: &str,
) -> StageRecord {
    let mut canonical = stage.clone();
    canonical.stage_id = canonicalize_job_scoped_value(&canonical.stage_id, actual_job_id, canonical_job_id);
    canonical.input = canonicalize_job_scoped_map(&canonical.input, actual_job_id, canonical_job_id);
    canonical.output = canonicalize_job_scoped_map(&canonical.output, actual_job_id, canonical_job_id);
    canonical.artifact_refs = canonicalize_job_scoped_map(&canonical.artifact_refs, actual_job_id, canonical_job_id);
    canonical.lineage_refs = canonicalize_job_scoped_map(&canonical.lineage_refs, actual_job_id, canonical_job_id);
    canonical.handoff_ref = canonicalize_job_scoped_value(&canonical.handoff_ref, actual_job_id, canonical_job_id);
    if let Some(details_ref) = canonical.error_details_ref.as_mut() {
        *details_ref = canonicalize_job_scoped_value(details_ref, actual_job_id, canonical_job_id);
    }
    canonical.replay_token = hash_bytes_hex(&stage_digest_bytes(&canonical));
    canonical
}

fn workflow_handoff_token(job_id: &str, stage: DagStageKind, phase: &str, material: &BTreeMap<String, String>) -> String {
    let mut normalized = serde_json::Map::new();
    normalized.insert("job_id".to_string(), serde_json::Value::String(job_id.to_string()));
    normalized.insert("stage_key".to_string(), serde_json::Value::String(stage.key().to_string()));
    normalized.insert("stage_index".to_string(), serde_json::Value::from(stage.index()));
    normalized.insert("phase".to_string(), serde_json::Value::String(phase.to_string()));
    for (key, value) in material {
        normalized.insert(key.clone(), serde_json::Value::String(value.clone()));
    }
    hash_bytes_hex(&serde_json::to_vec(&normalized).unwrap_or_default())
}

fn workload_contract_to_json_value(workload: &WorkloadContract) -> serde_json::Value {
    let kind = match workload.kind {
        1 => "QuantumJob",
        2 => "HybridWorkflow",
        3 => "DistributedJob",
        4 => "BenchmarkJob",
        5 => "PipelineJob",
        6 => "ReplayJob",
        _ => "QuantumJob",
    };

    let artifact_lineage = workload.artifact_lineage.as_ref().map(|artifact| {
        serde_json::json!({
            "execution_ref": artifact.execution_ref.clone(),
            "parent_ref": artifact.parent_ref.clone(),
            "policy_snapshot_ref": artifact.policy_snapshot_ref.clone(),
            "root_ref": artifact.root_ref.clone(),
        })
    }).unwrap_or_else(|| serde_json::json!({}));

    let observability = workload.observability.as_ref().map(|observability| {
        serde_json::json!({
            "emit_metrics": observability.emit_metrics,
            "trace_id": observability.trace_id.clone(),
            "trace_ref": observability.trace_ref.clone(),
            "traceparent": observability.traceparent.clone(),
        })
    }).unwrap_or_else(|| serde_json::json!({}));

    let security = workload.security.as_ref().map(|security| {
        serde_json::json!({
            "fail_closed": security.fail_closed,
            "policy_snapshot_ref": security.policy_snapshot_ref.clone(),
            "project_id": security.project_id.clone(),
            "service_identity": security.service_identity.clone(),
            "tenant_id": security.tenant_id.clone(),
        })
    }).unwrap_or_else(|| serde_json::json!({}));

    let mut value = serde_json::json!({
        "artifact_lineage": artifact_lineage,
        "backend_target": workload.backend_target.clone(),
        "execution_profile": workload.execution_profile.clone(),
        "kind": kind,
        "observability": observability,
        "replayable": workload.replayable,
        "security": security,
    });

    if let Some(topology) = workload.topology.as_ref() {
        if let Some(obj) = value.as_object_mut() {
            obj.insert(
                "topology".to_string(),
                serde_json::json!({
                    "cluster_id": topology.cluster_id.clone(),
                    "partition_count": topology.partition_count,
                    "partition_ids": topology.partition_ids.clone(),
                    "preferred_workers": topology.preferred_workers.clone(),
                }),
            );
        }
    }

    value
}

fn canonical_worker_name(index: usize) -> String {
    let mut n = index;
    let mut suffix = String::new();
    loop {
        let ch = (b'a' + (n % 26) as u8) as char;
        suffix.insert(0, ch);
        if n < 26 {
            break;
        }
        n = n / 26 - 1;
    }
    format!("worker-{suffix}")
}

fn synthesize_distributed_topology(
    metadata_kvs: &BTreeMap<String, String>,
    compiler_options: &BTreeMap<String, String>,
) -> Option<serde_json::Value> {
    let partition_count = metadata_kvs
        .get("distributed.partition_count")
        .or_else(|| metadata_kvs.get("partition_count"))
        .or_else(|| compiler_options.get("distributed.partition_count"))
        .and_then(|raw| raw.trim().parse::<usize>().ok())
        .filter(|value| *value >= 1)?;

    let cluster_id = metadata_kvs
        .get("distributed.cluster_id")
        .or_else(|| metadata_kvs.get("cluster_id"))
        .or_else(|| metadata_kvs.get("distributed.target"))
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "cluster:auto".to_string());

    let partition_ids = (0..partition_count)
        .map(|index| format!("partition-{index}"))
        .collect::<Vec<String>>();
    let preferred_workers = (0..partition_count)
        .map(canonical_worker_name)
        .collect::<Vec<String>>();

    Some(serde_json::json!({
        "cluster_id": cluster_id,
        "partition_count": partition_count,
        "partition_ids": partition_ids,
        "preferred_workers": preferred_workers,
    }))
}

fn merge_distributed_workload_topology(
    mut workload: serde_json::Value,
    request_workload: Option<&WorkloadContract>,
    metadata_kvs: &BTreeMap<String, String>,
    compiler_options: &BTreeMap<String, String>,
) -> serde_json::Value {
    let needs_topology = workload
        .as_object()
        .map(|obj| obj.get("topology").is_none())
        .unwrap_or(false);
    if !needs_topology {
        return workload;
    }

    let topology = request_workload
        .and_then(|value| value.topology.as_ref())
        .map(|topology| serde_json::json!({
            "cluster_id": topology.cluster_id.clone(),
            "partition_count": topology.partition_count,
            "partition_ids": topology.partition_ids.clone(),
            "preferred_workers": topology.preferred_workers.clone(),
        }))
        .or_else(|| synthesize_distributed_topology(metadata_kvs, compiler_options));

    let Some(topology) = topology else {
        return workload;
    };

    if let Some(obj) = workload.as_object_mut() {
        obj.insert("topology".to_string(), topology);
    }
    workload
}

fn workload_from_jobspec_yaml(metadata_kvs: &BTreeMap<String, String>) -> Result<Option<serde_json::Value>, Status> {
    let yaml_raw = match metadata_kvs.get("jobspec_yaml") {
        Some(raw) if !raw.trim().is_empty() => raw,
        _ => return Ok(None),
    };

    let jobspec: serde_yaml::Value = serde_yaml::from_str(yaml_raw)
        .map_err(|_| Status::invalid_argument("jobspec_yaml metadata must be valid YAML"))?;
    let workload = jobspec
        .get("spec")
        .and_then(|spec| spec.get("workload"))
        .cloned();

    Ok(workload.and_then(|value| serde_json::to_value(value).ok()))
}

fn distributed_workload_metadata(
    metadata_kvs: &BTreeMap<String, String>,
    compiler_options: &BTreeMap<String, String>,
    request_workload: Option<&WorkloadContract>,
) -> Result<BTreeMap<String, String>, Status> {
    let workload = match metadata_kvs.get("jobspec_workload") {
        Some(raw) if !raw.trim().is_empty() => serde_json::from_str(raw)
            .map_err(|_| Status::invalid_argument("jobspec_workload metadata must be valid JSON"))?,
        _ => match request_workload {
            Some(workload) => workload_contract_to_json_value(workload),
            None => match workload_from_jobspec_yaml(metadata_kvs)? {
                Some(value) => value,
                None => return Ok(BTreeMap::new()),
            },
        },
    };

    let workload = if workload.get("kind").and_then(|value| value.as_str()) == Some("DistributedJob") {
        merge_distributed_workload_topology(workload, request_workload, metadata_kvs, compiler_options)
    } else {
        workload
    };

    if workload.get("kind").and_then(|value| value.as_str()) != Some("DistributedJob") {
        return Ok(BTreeMap::new());
    }

    let topology = workload
        .get("topology")
        .and_then(|value| value.as_object())
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology is required for DistributedJob"))?;

    let cluster_id = topology
        .get("cluster_id")
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology.cluster_id is required"))?;

    let partition_count = topology
        .get("partition_count")
        .and_then(|value| value.as_i64())
        .filter(|value| *value > 0)
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology.partition_count must be >= 1"))? as usize;

    let partition_ids = topology
        .get("partition_ids")
        .and_then(|value| value.as_array())
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology.partition_ids must be an array"))?
        .iter()
        .map(|value| value.as_str().map(str::trim).filter(|s| !s.is_empty()).map(str::to_string))
        .collect::<Option<Vec<String>>>()
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology.partition_ids must contain non-empty strings"))?;

    let preferred_workers = topology
        .get("preferred_workers")
        .and_then(|value| value.as_array())
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology.preferred_workers must be an array"))?
        .iter()
        .map(|value| value.as_str().map(str::trim).filter(|s| !s.is_empty()).map(str::to_string))
        .collect::<Option<Vec<String>>>()
        .ok_or_else(|| Status::invalid_argument("spec.workload.topology.preferred_workers must contain non-empty strings"))?;

    if partition_ids.len() != partition_count {
        return Err(Status::invalid_argument("spec.workload.topology.partition_ids must contain partition_count entries"));
    }
    if preferred_workers.len() != partition_ids.len() {
        return Err(Status::invalid_argument("spec.workload.topology.preferred_workers must contain one worker per partition"));
    }
    let mut unique_partition_ids = partition_ids.clone();
    unique_partition_ids.sort();
    unique_partition_ids.dedup();
    if unique_partition_ids.len() != partition_ids.len() {
        return Err(Status::invalid_argument("spec.workload.topology.partition_ids must be unique"));
    }

    let canonical_topology = serde_json::json!({
        "cluster_id": cluster_id,
        "partition_count": partition_count,
        "partition_ids": partition_ids,
        "preferred_workers": preferred_workers,
    });
    let topology_json = serde_json::to_string(&canonical_topology).unwrap_or_default();
    let topology_digest = hash_bytes_hex(topology_json.as_bytes());
    let replay_token = hash_bytes_hex(
        format!("distributed:{cluster_id}:{topology_digest}").as_bytes(),
    );

    Ok(BTreeMap::from([
        ("distributed.cluster_id".to_string(), cluster_id.to_string()),
        ("distributed.partition_count".to_string(), partition_count.to_string()),
        ("distributed.partition_ids".to_string(), serde_json::to_string(&partition_ids).unwrap_or_default()),
        ("distributed.preferred_workers".to_string(), serde_json::to_string(&preferred_workers).unwrap_or_default()),
        ("distributed.topology_digest_sha256".to_string(), topology_digest),
        ("distributed.replay_token".to_string(), replay_token),
        ("distributed.topology_json".to_string(), topology_json),
    ]))
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
    workflow_events: Vec<WorkflowBoundaryRecord>,
    workflow_id: String,
    workflow_root_lineage_ref: String,
    workflow_completion_ref: Option<String>,
    workflow_failure_ref: Option<String>,
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
    reservation_token: Option<String>,
    reservation_lease_ms: u64,
    reservation_released_reason: Option<String>,
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

    fn stable_summary_map(&self) -> BTreeMap<String, String> {
        let mut summary = self.submission.summary_map();
        summary.remove("deadline_at_unix_ms");
        summary.insert(
            "job_id".to_string(),
            canonical_job_id_for_submission(&self.submission),
        );
        summary
    }

    fn snapshot_bytes(&self) -> Vec<u8> {
        // Keep the digest focused on stable logical state so equivalent runs
        // do not diverge because of transient orchestration bookkeeping.
        // Snapshot digest is used as a stability fingerprint for identical logical jobs.
        // Exclude wall-clock fields and derived replay tokens so equivalent runs hash the same.
        let actual_job_id = self.job_id.clone();
        let canonical_job_id = canonical_job_id_for_submission(&self.submission);
        let mut stage_records: Vec<&StageRecord> = self.stage_records.iter().collect();
        stage_records.sort_by(|a, b| {
            a.order
                .cmp(&b.order)
                .then_with(|| a.stage_id.cmp(&b.stage_id))
        });
        let stage_json: Vec<serde_json::Value> = stage_records
            .iter()
            .map(|stage| {
                let canonical_stage = canonicalize_stage_record(stage, &actual_job_id, &canonical_job_id);
                serde_json::json!({
                    "stage_id": canonicalize_job_scoped_value(&stage.stage_id, &actual_job_id, &canonical_job_id),
                    "stage_key": canonical_stage.stage_key,
                    "order": canonical_stage.order,
                    "state_before": canonical_stage.state_before as i32,
                    "state_after": canonical_stage.state_after as i32,
                    "status": match canonical_stage.status {
                        StageStatus::Running => "running",
                        StageStatus::Succeeded => "succeeded",
                        StageStatus::Failed => "failed",
                    },
                    "input": canonicalize_job_scoped_map(&stage.input, &actual_job_id, &canonical_job_id)
                        .into_iter()
                        .filter(|(key, _)| key != "deadline_at_unix_ms")
                        .collect::<BTreeMap<_, _>>(),
                    "output": canonicalize_job_scoped_map(&stage.output, &actual_job_id, &canonical_job_id),
                    "artifact_refs": canonicalize_job_scoped_map(&stage.artifact_refs, &actual_job_id, &canonical_job_id),
                    "lineage_refs": canonicalize_job_scoped_map(&stage.lineage_refs, &actual_job_id, &canonical_job_id),
                    "handoff_ref": canonicalize_job_scoped_value(&stage.handoff_ref, &actual_job_id, &canonical_job_id),
                    "error_code": stage.error_code,
                    "error_summary": stage.error_summary,
                    "error_details_ref": stage.error_details_ref.as_ref().map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
                    "input_refs": canonical_stage.pipeline_input_refs(),
                    "output_refs": canonical_stage.pipeline_output_refs(),
                    "depends_on": canonical_stage
                        .artifact_refs
                        .get("upstream_output_ref")
                        .cloned()
                        .map(|value| vec![value])
                        .unwrap_or_default(),
                    "failure_semantics": stage.pipeline_failure_semantics(),
                })
            })
            .collect();

        let mut pipeline_stage_json: Vec<serde_json::Value> = Vec::with_capacity(self.stage_records.len());
        let mut previous_output_ref: Option<String> = None;
        for stage in stage_records.iter() {
            let canonical_stage = canonicalize_stage_record(stage, &actual_job_id, &canonical_job_id);
            let depends_on = previous_output_ref.clone().into_iter().collect::<Vec<_>>();
            previous_output_ref = canonical_stage
                .artifact_refs
                .get("workflow_output_ref")
                .cloned()
                .or_else(|| canonical_stage.output.get("workflow_output_ref").cloned());
            pipeline_stage_json.push(serde_json::json!({
                "stage_id": canonicalize_job_scoped_value(&stage.stage_id, &actual_job_id, &canonical_job_id),
                "stage_key": canonical_stage.stage_key,
                "order": canonical_stage.order,
                "state_before": canonical_stage.state_before as i32,
                "state_after": canonical_stage.state_after as i32,
                "status": match canonical_stage.status {
                    StageStatus::Running => "running",
                    StageStatus::Succeeded => "succeeded",
                    StageStatus::Failed => "failed",
                },
                "input_refs": canonical_stage.pipeline_input_refs(),
                "output_refs": canonical_stage.pipeline_output_refs(),
                "handoff_ref": canonicalize_job_scoped_value(&stage.handoff_ref, &actual_job_id, &canonical_job_id),
                "depends_on": depends_on,
                "artifact_refs": canonicalize_job_scoped_map(&stage.artifact_refs, &actual_job_id, &canonical_job_id),
                "lineage_refs": canonicalize_job_scoped_map(&stage.lineage_refs, &actual_job_id, &canonical_job_id),
                "replay_token": canonical_stage.replay_token,
                "failure_semantics": stage.pipeline_failure_semantics(),
            }));
        }

        let pipeline_json = serde_json::json!({
            "kind": "PipelineJob",
            "job_id": canonical_job_id.clone(),
            "workflow_id": self.workflow_id.clone(),
            "root_lineage_ref": self.workflow_root_lineage_ref.clone(),
            "replay_cursor": self
                .stage_records
                .iter()
                .rev()
                .find(|stage| matches!(stage.status, StageStatus::Succeeded))
                .map(|stage| canonicalize_job_scoped_value(&stage.stage_id, &actual_job_id, &canonical_job_id))
                .unwrap_or_default(),
            "stages": pipeline_stage_json,
            "final_completion_ref": self.workflow_completion_ref.as_ref().map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
            "final_failure_ref": self.workflow_failure_ref.as_ref().map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
        });

        let HybridWorkflowGraph {
            workflow_id,
            job_id,
            root_lineage_ref,
            stages,
            boundaries,
            final_completion_ref,
            final_failure_ref,
        } = self.workflow_graph();
        let workflow_json = serde_json::json!({
            "workflow_id": workflow_id,
            "job_id": job_id,
            "root_lineage_ref": root_lineage_ref,
            "stages": stages
                .into_iter()
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
                        "input_ref": stage.input_ref,
                        "output_ref": stage.output_ref,
                        "handoff_ref": stage.handoff_ref,
                        "artifact_refs": stage.artifact_refs,
                        "lineage_refs": stage.lineage_refs,
                        "replay_token": stage.replay_token,
                    })
                })
                .collect::<Vec<_>>(),
            "boundaries": boundaries
                .into_iter()
                .map(|boundary| {
                    serde_json::json!({
                        "boundary_id": boundary.boundary_id,
                        "workflow_id": boundary.workflow_id,
                        "job_id": boundary.job_id,
                        "kind": boundary.kind.key(),
                        "stage_id": boundary.stage_id,
                        "stage_key": boundary.stage_key,
                        "order": boundary.order,
                        "state_before": boundary.state_before.map(|state| state as i32),
                        "state_after": boundary.state_after.map(|state| state as i32),
                        "input_ref": boundary.input_ref,
                        "output_ref": boundary.output_ref,
                        "artifact_ref": boundary.artifact_ref,
                        "lineage_ref": boundary.lineage_ref,
                        "replay_token": boundary.replay_token,
                    })
                })
                .collect::<Vec<_>>(),
            "final_completion_ref": final_completion_ref,
            "final_failure_ref": final_failure_ref,
        });

        serde_json::to_vec(&serde_json::json!({
            "job_id": canonical_job_id.clone(),
            "submission": self.stable_summary_map(),
            "state": self.state as i32,
            "stage_records": stage_json,
            "pipeline": pipeline_json,
            "workflow": workflow_json,
            "counts": self.counts,
            "metadata": canonicalize_job_scoped_map(&self.metadata, &actual_job_id, &canonical_job_id),
            "qfs_result_ref": self.qfs_result_ref.as_ref().map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
            "error_code": self.error_code,
            "error_summary": self.error_summary,
            "error_details_ref": self.error_details_ref.as_ref().map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
        }))
        .unwrap_or_default()
    }

    fn schedule_stage(&self) -> Option<&StageRecord> {
        self.stage_records
            .iter()
            .find(|stage| stage.stage_key == "schedule" && matches!(stage.status, StageStatus::Succeeded))
    }
}

impl JobRuntimeRecord {
    fn record_workflow_boundary(
        &mut self,
        stage: DagStageKind,
        kind: WorkflowBoundaryKind,
        input_ref: String,
        output_ref: String,
        artifact_ref: String,
        lineage_ref: String,
        state_before: Option<TaskState>,
        state_after: Option<TaskState>,
    ) {
        let boundary_id = workflow_boundary_ref(&self.job_id, stage, kind);
        let mut material = BTreeMap::from([
            ("boundary_id".to_string(), boundary_id.clone()),
            ("workflow_id".to_string(), self.workflow_id.clone()),
            ("job_id".to_string(), self.job_id.clone()),
            ("kind".to_string(), kind.key().to_string()),
            ("stage_id".to_string(), stage_id(&self.job_id, stage)),
            ("stage_key".to_string(), stage.key().to_string()),
            ("input_ref".to_string(), input_ref.clone()),
            ("output_ref".to_string(), output_ref.clone()),
            ("artifact_ref".to_string(), artifact_ref.clone()),
            ("lineage_ref".to_string(), lineage_ref.clone()),
        ]);
        let replay_token = workflow_handoff_token(&self.job_id, stage, kind.key(), &material);
        self.workflow_events.push(WorkflowBoundaryRecord {
            boundary_id,
            workflow_id: self.workflow_id.clone(),
            job_id: self.job_id.clone(),
            kind,
            stage_id: Some(stage_id(&self.job_id, stage)),
            stage_key: Some(stage.key().to_string()),
            order: Some(stage.index()),
            state_before,
            state_after,
            input_ref,
            output_ref,
            artifact_ref,
            lineage_ref,
            replay_token,
            timestamp: ts_now(),
        });
    }

fn workflow_graph(&self) -> HybridWorkflowGraph {
        let actual_job_id = self.job_id.clone();
        let canonical_job_id = canonical_job_id_for_submission(&self.submission);
        let canonical_workflow_id = self.workflow_id.clone();

        let mut stage_records: Vec<&StageRecord> = self.stage_records.iter().collect();
        stage_records.sort_by(|a, b| {
            a.order
                .cmp(&b.order)
                .then_with(|| a.stage_id.cmp(&b.stage_id))
        });
        let mut workflow_events: Vec<&WorkflowBoundaryRecord> = self.workflow_events.iter().collect();
        workflow_events.sort_by(|a, b| {
            a.order
                .unwrap_or_default()
                .cmp(&b.order.unwrap_or_default())
                .then_with(|| {
                    a.stage_key
                        .as_deref()
                        .unwrap_or_default()
                        .cmp(b.stage_key.as_deref().unwrap_or_default())
                })
                .then_with(|| a.kind.key().cmp(b.kind.key()))
                .then_with(|| a.boundary_id.cmp(&b.boundary_id))
        });

        let stages = stage_records
            .iter()
            .map(|stage| {
                let canonical_stage = canonicalize_stage_record(stage, &actual_job_id, &canonical_job_id);
                let mut artifact_refs = canonical_stage.artifact_refs.clone();
                artifact_refs
                    .entry("workflow_handoff_ref".to_string())
                    .or_insert_with(|| canonical_stage.handoff_ref.clone());
                HybridWorkflowStageNode {
                    stage_id: canonical_stage.stage_id,
                    stage_key: canonical_stage.stage_key,
                    order: canonical_stage.order,
                    state_before: canonical_stage.state_before,
                    state_after: canonical_stage.state_after,
                    status: canonical_stage.status,
                    input_ref: canonical_stage
                        .artifact_refs
                        .get("workflow_input_ref")
                        .cloned()
                        .unwrap_or_default(),
                    output_ref: canonical_stage
                        .artifact_refs
                        .get("workflow_output_ref")
                        .cloned()
                        .unwrap_or_default(),
                    handoff_ref: canonical_stage.handoff_ref,
                    artifact_refs,
                    lineage_refs: canonical_stage.lineage_refs,
                    replay_token: canonical_stage.replay_token,
                }
            })
            .collect::<Vec<_>>();

        let boundaries = workflow_events
            .iter()
            .map(|boundary| WorkflowBoundaryRecord {
                boundary_id: canonicalize_job_scoped_value(&boundary.boundary_id, &actual_job_id, &canonical_job_id),
                workflow_id: canonical_workflow_id.clone(),
                job_id: canonical_job_id.clone(),
                kind: boundary.kind,
                stage_id: boundary
                    .stage_id
                    .as_ref()
                    .map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
                stage_key: boundary.stage_key.clone(),
                order: boundary.order,
                state_before: boundary.state_before,
                state_after: boundary.state_after,
                input_ref: canonicalize_job_scoped_value(&boundary.input_ref, &actual_job_id, &canonical_job_id),
                output_ref: canonicalize_job_scoped_value(&boundary.output_ref, &actual_job_id, &canonical_job_id),
                artifact_ref: canonicalize_job_scoped_value(&boundary.artifact_ref, &actual_job_id, &canonical_job_id),
                lineage_ref: canonicalize_job_scoped_value(&boundary.lineage_ref, &actual_job_id, &canonical_job_id),
                replay_token: {
                    let stage_kind = boundary
                        .stage_key
                        .as_deref()
                        .and_then(parse_stage_kind)
                        .unwrap_or(DagStageKind::ValidateEnqueue);
                    let canonical_material = BTreeMap::from([
                        (
                            "boundary_id".to_string(),
                            canonicalize_job_scoped_value(&boundary.boundary_id, &actual_job_id, &canonical_job_id),
                        ),
                        ("workflow_id".to_string(), canonical_workflow_id.clone()),
                        ("job_id".to_string(), canonical_job_id.clone()),
                        ("kind".to_string(), boundary.kind.key().to_string()),
                        (
                            "stage_id".to_string(),
                            boundary
                                .stage_id
                                .as_ref()
                                .map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id))
                                .unwrap_or_default(),
                        ),
                        (
                            "stage_key".to_string(),
                            boundary.stage_key.clone().unwrap_or_default(),
                        ),
                        (
                            "input_ref".to_string(),
                            canonicalize_job_scoped_value(&boundary.input_ref, &actual_job_id, &canonical_job_id),
                        ),
                        (
                            "output_ref".to_string(),
                            canonicalize_job_scoped_value(&boundary.output_ref, &actual_job_id, &canonical_job_id),
                        ),
                        (
                            "artifact_ref".to_string(),
                            canonicalize_job_scoped_value(&boundary.artifact_ref, &actual_job_id, &canonical_job_id),
                        ),
                        (
                            "lineage_ref".to_string(),
                            canonicalize_job_scoped_value(&boundary.lineage_ref, &actual_job_id, &canonical_job_id),
                        ),
                    ]);
                    workflow_handoff_token(&canonical_job_id, stage_kind, boundary.kind.key(), &canonical_material)
                },
                timestamp: timestamp_from_ms(0),
            })
            .collect::<Vec<_>>();
        let mut stages = stages;
        stages.sort_by(|a, b| {
            a.order
                .cmp(&b.order)
                .then_with(|| a.stage_id.cmp(&b.stage_id))
        });
        let mut boundaries = boundaries;
        boundaries.sort_by(|a, b| {
            a.order
                .unwrap_or_default()
                .cmp(&b.order.unwrap_or_default())
                .then_with(|| {
                    a.stage_key
                        .as_deref()
                        .unwrap_or_default()
                        .cmp(b.stage_key.as_deref().unwrap_or_default())
                })
                .then_with(|| a.kind.key().cmp(b.kind.key()))
                .then_with(|| a.boundary_id.cmp(&b.boundary_id))
        });
        HybridWorkflowGraph {
            workflow_id: canonical_workflow_id,
            job_id: canonical_job_id.clone(),
            root_lineage_ref: workflow_root_lineage_ref(&canonical_job_id),
            stages,
            boundaries,
            final_completion_ref: self
                .workflow_completion_ref
                .as_ref()
                .map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
            final_failure_ref: self
                .workflow_failure_ref
                .as_ref()
                .map(|value| canonicalize_job_scoped_value(value, &actual_job_id, &canonical_job_id)),
        }
    }
}

impl StageRecord {
    fn pipeline_input_refs(&self) -> Vec<String> {
        let mut refs = Vec::new();
        for key in [
            "workflow_input_ref",
            "upstream_output_ref",
            "workflow_lineage_ref",
            "workflow_root_lineage_ref",
        ] {
            if let Some(value) = self.artifact_refs.get(key) {
                if !value.is_empty() && !refs.contains(value) {
                    refs.push(value.clone());
                }
            }
        }
        refs
    }

    fn pipeline_output_refs(&self) -> Vec<String> {
        let mut refs = Vec::new();
        for key in [
            "workflow_output_ref",
            "workflow_handoff_ref",
            "workflow_failure_ref",
            "workflow_completion_ref",
        ] {
            if let Some(value) = self.artifact_refs.get(key).or_else(|| self.output.get(key)) {
                if !value.is_empty() && !refs.contains(value) {
                    refs.push(value.clone());
                }
            }
        }
        refs
    }

    fn pipeline_failure_semantics(&self) -> serde_json::Value {
        serde_json::json!({
            "retains_outputs": true,
            "invalidates_downstream_handoffs": matches!(self.status, StageStatus::Failed),
            "resume_boundary": if matches!(self.status, StageStatus::Failed) {
                "failed-stage"
            } else {
                "last-successful-stage"
            },
            "terminal_state": match self.status {
                StageStatus::Running => "running",
                StageStatus::Succeeded => "succeeded",
                StageStatus::Failed => "failed",
            },
        })
    }
}

fn bounded_dispatch_rationale_attributes(
    job: &JobRuntimeRecord,
    schedule_stage: &StageRecord,
    selected_backend: &str,
    selected_queue: &str,
) -> BTreeMap<String, String> {
    let decision_input_digest = schedule_stage
        .input
        .get("fingerprint")
        .cloned()
        .unwrap_or_else(|| job.snapshot_digest());
    let actual_job_id = job.job_id.as_str();
    let canonical_job_id = canonical_job_id_for_submission(&job.submission);
    let mut attrs = BTreeMap::from([
        ("job_id".to_string(), canonical_job_id.clone()),
        ("stage_count".to_string(), job.stage_records.len().to_string()),
        (
            "schedule_stage_id".to_string(),
            canonicalize_job_scoped_value(&schedule_stage.stage_id, actual_job_id, &canonical_job_id),
        ),
        (
            "schedule_stage_state".to_string(),
            format!("{:?}", schedule_stage.state_after),
        ),
        (
            "scheduler_decision_version".to_string(),
            schedule_stage
                .output
                .get("scheduler_decision_version")
                .cloned()
                .unwrap_or_else(|| SCHEDULER_DECISION_VERSION.to_string()),
        ),
        (
            "policy_bundle_id".to_string(),
            schedule_stage
                .output
                .get("policy_bundle_id")
                .cloned()
                .unwrap_or_else(|| SCHEDULING_POLICY_BUNDLE_ID.to_string()),
        ),
        (
            "policy_bundle_version".to_string(),
            schedule_stage
                .output
                .get("policy_bundle_version")
                .cloned()
                .unwrap_or_else(|| SCHEDULING_POLICY_BUNDLE_VERSION.to_string()),
        ),
        ("selected_backend".to_string(), selected_backend.to_string()),
        ("selected_queue".to_string(), selected_queue.to_string()),
        (
            "resource_plan_ref".to_string(),
            canonicalize_job_scoped_value(
                &schedule_stage
                    .output
                    .get("resource_plan_ref")
                    .cloned()
                    .unwrap_or_default(),
                actual_job_id,
                &canonical_job_id,
            ),
        ),
        ("decision_input_digest".to_string(), decision_input_digest),
        ("snapshot_digest".to_string(), job.snapshot_digest()),
    ]);
    for key in [
        "distributed.cluster_id",
        "distributed.partition_count",
        "distributed.partition_ids",
        "distributed.preferred_workers",
        "distributed.topology_digest_sha256",
        "distributed.replay_token",
        "distributed.topology_json",
    ] {
        if let Some(value) = job.metadata.get(key) {
            attrs.insert(key.to_string(), value.clone());
        }
    }
    attrs
}

impl JobRuntimeRecord {
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
        let canonical_job_id = canonical_job_id_for_submission(&submission);
        let workflow_id = format!("workflow-{}", submission.fingerprint);
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
            workflow_events: vec![WorkflowBoundaryRecord {
                boundary_id: workflow_boundary_ref(
                    &submission.job_id,
                    DagStageKind::ValidateEnqueue,
                    WorkflowBoundaryKind::WorkflowStarted,
                ),
                workflow_id: workflow_id.clone(),
                job_id: submission.job_id.clone(),
                kind: WorkflowBoundaryKind::WorkflowStarted,
                stage_id: None,
                stage_key: None,
                order: None,
                state_before: None,
                state_after: Some(TaskState::Pending),
                input_ref: workflow_stage_input_ref(&submission.job_id, DagStageKind::ValidateEnqueue),
                output_ref: String::new(),
                artifact_ref: workflow_root_lineage_ref(&canonical_job_id),
                lineage_ref: workflow_root_lineage_ref(&canonical_job_id),
                replay_token: hash_bytes_hex(
                    format!(
                        "workflow-start:{}:{}",
                        canonical_job_id,
                        workflow_root_lineage_ref(&canonical_job_id)
                    )
                    .as_bytes(),
                ),
                timestamp: ts_now(),
            }],
            workflow_id,
            workflow_root_lineage_ref: workflow_root_lineage_ref(&canonical_job_id),
            workflow_completion_ref: None,
            workflow_failure_ref: None,
            counts: BTreeMap::new(),
            metadata: submission.workload_metadata.clone(),
            qfs_result_ref: None,
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            cancel_requested: false,
            cancel_reason: None,
            cancellation_fanout_ref: None,
            reservation_state: Some("held".to_string()),
            reservation_token: Some(reservation_token_for(&submission)),
            reservation_lease_ms: reservation_lease_ms_for(&submission),
            reservation_released_reason: None,
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

    fn reservation_active(&self, job_id: &str) -> Result<bool, Status> {
        let jobs = self.jobs.read();
        let job = jobs.get(job_id).ok_or_else(|| Status::not_found("job not found"))?;
        Ok(job.reservation_state.as_deref() == Some("held") && !job.is_terminal())
    }

    fn reservation_lease_expired(&self, job_id: &str) -> Result<bool, Status> {
        let jobs = self.jobs.read();
        let job = jobs.get(job_id).ok_or_else(|| Status::not_found("job not found"))?;
        Ok(Self::reservation_lease_expired_record(job))
    }

    fn reservation_lease_expired_record(job: &JobRuntimeRecord) -> bool {
        if job.reservation_state.as_deref() != Some("held") {
            return false;
        }
        let lease_ms = job.reservation_lease_ms.max(1);
        let age_ms = timestamp_to_ms(&ts_now()) - timestamp_to_ms(&job.updated_at);
        age_ms >= lease_ms as i128
    }

    fn sweep_stale_reservations(&self) -> Vec<String> {
        let mut released = Vec::new();
        let mut jobs = self.jobs.write();
        for (job_id, job) in jobs.iter_mut() {
            if job.reservation_state.as_deref() == Some("held") && !job.is_terminal() {
                let lease_ms = job.reservation_lease_ms.max(1);
                let age_ms = timestamp_to_ms(&ts_now()) - timestamp_to_ms(&job.updated_at);
                if age_ms >= lease_ms as i128 {
                    job.reservation_state = Some("released".to_string());
                    job.reservation_released_reason = Some("lease_expired".to_string());
                    job.updated_at = ts_now();
                    released.push(job_id.clone());
                }
            }
        }
        released
    }

    fn acquire_live_reservation(&self, job_id: &str) -> Result<JobRuntimeRecord, Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        if job.reservation_state.as_deref() == Some("held") && !job.is_terminal() {
            if Self::reservation_lease_expired_record(job) {
                job.reservation_state = Some("released".to_string());
                job.reservation_released_reason = Some("lease_expired".to_string());
            } else {
                return Err(Status::failed_precondition("reservation already active"));
            }
        }
        job.reservation_state = Some("held".to_string());
        job.reservation_released_reason = None;
        job.updated_at = ts_now();
        Ok(job.clone())
    }

    fn request_error_terminalization(
        &self,
        job_id: &str,
        error_code: &str,
        error_summary: &str,
        error_details_ref: &str,
    ) -> Result<JobRuntimeRecord, Status> {
        let mut jobs = self.jobs.write();
        let job = jobs
            .get_mut(job_id)
            .ok_or_else(|| Status::not_found("job not found"))?;
        if job.is_terminal() {
            return Ok(job.clone());
        }

        let stage = job.current_stage.unwrap_or(DagStageKind::ValidateEnqueue);
        let stage_id = stage_id(job_id, stage);
        let state_before = job.state;
        let input_ref = workflow_stage_input_ref(job_id, stage);
        let handoff_ref = workflow_stage_handoff_ref(job_id, stage);
        let lineage_ref = workflow_stage_lineage_ref(job_id, stage);
        let failure_ref = workflow_stage_failure_ref(job_id, stage);
        let workflow_failure_ref = workflow_failure_ref(job_id);

        if let Some(record) = job.stage_records.iter_mut().find(|record| record.stage_id == stage_id) {
            record.status = StageStatus::Failed;
            record.state_after = TaskState::Error;
            record.error_code = Some(error_code.to_string());
            record.error_summary = Some(error_summary.to_string());
            record.error_details_ref = Some(error_details_ref.to_string());
            record
                .artifact_refs
                .insert("workflow_failure_ref".to_string(), failure_ref.clone());
            record
                .artifact_refs
                .insert("workflow_output_ref".to_string(), failure_ref.clone());
            record
                .lineage_refs
                .insert("workflow_lineage_ref".to_string(), lineage_ref.clone());
            record.completed_at = Some(ts_now());
            record.replay_token = hash_bytes_hex(&stage_digest_bytes(record));
        } else {
            job.stage_records.push(StageRecord {
                stage_id: stage_id.clone(),
                stage_key: stage.key().to_string(),
                order: stage.index(),
                state_before,
                state_after: TaskState::Error,
                status: StageStatus::Failed,
                started_at: ts_now(),
                completed_at: Some(ts_now()),
                input: BTreeMap::from([
                    ("job_id".to_string(), job_id.to_string()),
                    ("error_code".to_string(), error_code.to_string()),
                    ("error_summary".to_string(), error_summary.to_string()),
                    ("workflow_stage_input_ref".to_string(), input_ref.clone()),
                    ("workflow_stage_handoff_ref".to_string(), handoff_ref.clone()),
                    ("workflow_stage_lineage_ref".to_string(), lineage_ref.clone()),
                    ("workflow_root_lineage_ref".to_string(), job.workflow_root_lineage_ref.clone()),
                ]),
                output: BTreeMap::from([
                    ("workflow_failure_ref".to_string(), failure_ref.clone()),
                    ("workflow_output_ref".to_string(), failure_ref.clone()),
                ]),
                artifact_refs: BTreeMap::from([
                    ("workflow_input_ref".to_string(), input_ref.clone()),
                    ("workflow_output_ref".to_string(), failure_ref.clone()),
                    ("workflow_handoff_ref".to_string(), handoff_ref.clone()),
                    ("workflow_failure_ref".to_string(), failure_ref.clone()),
                    ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
                    (
                        "workflow_root_lineage_ref".to_string(),
                        job.workflow_root_lineage_ref.clone(),
                    ),
                ]),
                lineage_refs: BTreeMap::from([
                    ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
                    (
                        "workflow_root_lineage_ref".to_string(),
                        job.workflow_root_lineage_ref.clone(),
                    ),
                ]),
                handoff_ref: handoff_ref.clone(),
                error_code: Some(error_code.to_string()),
                error_summary: Some(error_summary.to_string()),
                error_details_ref: Some(error_details_ref.to_string()),
                replay_token: String::new(),
            });
        }

        job.state = TaskState::Error;
        job.reservation_state = Some("released".to_string());
        job.updated_at = ts_now();
        job.completed_at = Some(ts_now());
        job.error_code = Some(error_code.to_string());
        job.error_summary = Some(error_summary.to_string());
        job.error_details_ref = Some(error_details_ref.to_string());
        job.workflow_failure_ref = Some(workflow_failure_ref.clone());
        job.record_workflow_boundary(
            stage,
            WorkflowBoundaryKind::StageFailed,
            input_ref,
            failure_ref.clone(),
            failure_ref.clone(),
            lineage_ref,
            Some(state_before),
            Some(TaskState::Error),
        );
        job.record_workflow_boundary(
            stage,
            WorkflowBoundaryKind::WorkflowCompleted,
            workflow_stage_input_ref(job_id, stage),
            workflow_failure_ref.clone(),
            workflow_failure_ref.clone(),
            workflow_stage_lineage_ref(job_id, stage),
            Some(state_before),
            Some(TaskState::Error),
        );
        Ok(job.clone())
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

        let root_lineage_ref = input
            .get("workflow_root_lineage_ref")
            .cloned()
            .unwrap_or_else(|| workflow_root_lineage_ref(job_id));
        let input_ref = input
            .get("workflow_stage_input_ref")
            .cloned()
            .unwrap_or_else(|| workflow_stage_input_ref(job_id, stage));
        let handoff_ref = input
            .get("workflow_stage_handoff_ref")
            .cloned()
            .unwrap_or_else(|| workflow_stage_handoff_ref(job_id, stage));
        let lineage_ref = input
            .get("workflow_stage_lineage_ref")
            .cloned()
            .unwrap_or_else(|| workflow_stage_lineage_ref(job_id, stage));

        let missing_fields: Vec<&str> = required_handoff_fields(stage)
            .iter()
            .copied()
            .filter(|field| !input.contains_key(*field))
            .collect();
        if !missing_fields.is_empty() {
            let error_code = "WORKFLOW_HANDOFF_CORRUPTION";
            let error_summary = format!(
                "{} stage missing required handoff refs: {}",
                stage.key(),
                missing_fields.join(", ")
            );
            let failure_ref = workflow_stage_failure_ref(job_id, stage);
            let workflow_failure_ref = workflow_failure_ref(job_id);

            job.current_stage = Some(stage);
            job.updated_at = ts_now();
            job.completed_at = Some(ts_now());
            job.state = TaskState::Error;
            job.error_code = Some(error_code.to_string());
            job.error_summary = Some(error_summary.clone());
            job.error_details_ref = Some(failure_ref.clone());
            job.reservation_state = Some("released".to_string());
            job.workflow_failure_ref = Some(workflow_failure_ref.clone());
            job.stage_records.push(StageRecord {
                stage_id: stage_id.clone(),
                stage_key: stage.key().to_string(),
                order: stage.index(),
                state_before,
                state_after: TaskState::Error,
                status: StageStatus::Failed,
                started_at: ts_now(),
                completed_at: Some(ts_now()),
                input: input.clone(),
                output: BTreeMap::from([
                    ("workflow_failure_ref".to_string(), failure_ref.clone()),
                    ("workflow_output_ref".to_string(), failure_ref.clone()),
                ]),
                artifact_refs: BTreeMap::from([
                    ("workflow_input_ref".to_string(), input_ref.clone()),
                    ("workflow_output_ref".to_string(), failure_ref.clone()),
                    ("workflow_handoff_ref".to_string(), handoff_ref.clone()),
                    ("workflow_failure_ref".to_string(), failure_ref.clone()),
                    ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
                    ("workflow_root_lineage_ref".to_string(), root_lineage_ref.clone()),
                    ("upstream_output_ref".to_string(), input_ref.clone()),
                ]),
                lineage_refs: BTreeMap::from([
                    ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
                    ("workflow_root_lineage_ref".to_string(), root_lineage_ref.clone()),
                ]),
                handoff_ref: handoff_ref.clone(),
                error_code: Some(error_code.to_string()),
                error_summary: Some(error_summary.clone()),
                error_details_ref: Some(failure_ref.clone()),
                replay_token: String::new(),
            });
            job.record_workflow_boundary(
                stage,
                WorkflowBoundaryKind::StageFailed,
                input_ref.clone(),
                failure_ref.clone(),
                failure_ref.clone(),
                lineage_ref.clone(),
                Some(state_before),
                Some(TaskState::Error),
            );
            job.record_workflow_boundary(
                stage,
                WorkflowBoundaryKind::WorkflowCompleted,
                input_ref,
                workflow_failure_ref.clone(),
                workflow_failure_ref,
                lineage_ref,
                Some(state_before),
                Some(TaskState::Error),
            );
            return Err(Status::failed_precondition(error_summary));
        }

        let previous_output_ref = job
            .stage_records
            .iter()
            .rev()
            .find_map(|record| record.artifact_refs.get("workflow_output_ref").cloned());

        job.current_stage = Some(stage);
        job.updated_at = ts_now();
        let mut artifact_refs = BTreeMap::from([
            ("workflow_input_ref".to_string(), input_ref.clone()),
            ("workflow_handoff_ref".to_string(), handoff_ref.clone()),
            ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
            ("workflow_root_lineage_ref".to_string(), root_lineage_ref.clone()),
        ]);
        if let Some(previous_output_ref) = previous_output_ref {
            artifact_refs.insert("upstream_output_ref".to_string(), previous_output_ref);
        }

        let mut lineage_refs = BTreeMap::from([
            ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
            ("workflow_root_lineage_ref".to_string(), root_lineage_ref.clone()),
        ]);
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
            artifact_refs,
            lineage_refs,
            handoff_ref: handoff_ref.clone(),
            error_code: None,
            error_summary: None,
            error_details_ref: None,
            replay_token: String::new(),
        });
        job.record_workflow_boundary(
            stage,
            WorkflowBoundaryKind::StageEntered,
            input_ref,
            String::new(),
            handoff_ref,
            lineage_ref,
            Some(state_before),
            Some(state_before),
        );
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
        let (stage_kind, input_ref, handoff_ref, lineage_ref, state_before, output_ref, completion_ref) = {
            let stage = job
                .stage_records
                .iter_mut()
                .find(|record| record.stage_id == stage_id)
                .ok_or_else(|| Status::failed_precondition("stage record not found"))?;
            let stage_kind = parse_stage_kind(&stage.stage_key).unwrap_or(DagStageKind::ValidateEnqueue);
            let input_ref = stage
                .artifact_refs
                .get("workflow_input_ref")
                .cloned()
                .unwrap_or_else(|| workflow_stage_input_ref(job_id, stage_kind));
            let handoff_ref = stage.handoff_ref.clone();
            let lineage_ref = stage
                .lineage_refs
                .get("workflow_lineage_ref")
                .cloned()
                .unwrap_or_else(|| workflow_stage_lineage_ref(job_id, stage_kind));
            let output_ref = workflow_output_ref_for_stage_output(job_id, stage_kind);
            let mut output = output;
            output.insert("workflow_output_ref".to_string(), output_ref.clone());
            output.insert("workflow_handoff_ref".to_string(), handoff_ref.clone());
            output.insert("workflow_lineage_ref".to_string(), lineage_ref.clone());
            output.insert(
                "workflow_root_lineage_ref".to_string(),
                stage
                    .lineage_refs
                    .get("workflow_root_lineage_ref")
                    .cloned()
                    .unwrap_or_else(|| workflow_root_lineage_ref(job_id)),
            );
            let completion_ref = if matches!(state_after, TaskState::Done) {
                let completion_ref = workflow_completion_ref(job_id);
                output.insert("workflow_completion_ref".to_string(), completion_ref.clone());
                Some(completion_ref)
            } else {
                None
            };

            stage.status = StageStatus::Succeeded;
            stage.state_after = state_after;
            stage.output = output;
            stage
                .artifact_refs
                .insert("workflow_input_ref".to_string(), input_ref.clone());
            stage
                .artifact_refs
                .insert("workflow_output_ref".to_string(), output_ref.clone());
            stage
                .artifact_refs
                .insert("workflow_handoff_ref".to_string(), handoff_ref.clone());
            stage
                .artifact_refs
                .insert("workflow_lineage_ref".to_string(), lineage_ref.clone());
            stage
                .artifact_refs
                .entry("workflow_root_lineage_ref".to_string())
                .or_insert_with(|| {
                    stage
                        .lineage_refs
                        .get("workflow_root_lineage_ref")
                        .cloned()
                        .unwrap_or_else(|| workflow_root_lineage_ref(job_id))
                });
            if let Some(ref completion_ref) = completion_ref {
                stage
                    .artifact_refs
                    .insert("workflow_completion_ref".to_string(), completion_ref.clone());
            }
            stage
                .lineage_refs
                .insert("workflow_lineage_ref".to_string(), lineage_ref.clone());
            stage
                .lineage_refs
                .insert(
                    "workflow_root_lineage_ref".to_string(),
                    stage
                        .lineage_refs
                        .get("workflow_root_lineage_ref")
                        .cloned()
                        .unwrap_or_else(|| workflow_root_lineage_ref(job_id)),
                );
            stage.completed_at = Some(ts_now());
            stage.replay_token = hash_bytes_hex(&stage_digest_bytes(stage));
            (stage_kind, input_ref, handoff_ref, lineage_ref, stage.state_before, output_ref, completion_ref)
        };

        job.record_workflow_boundary(
            stage_kind,
            WorkflowBoundaryKind::StageCompleted,
            input_ref,
            output_ref.clone(),
            handoff_ref,
            lineage_ref.clone(),
            Some(state_before),
            Some(state_after),
        );
        if let Some(completion_ref) = completion_ref {
            job.workflow_completion_ref = Some(completion_ref.clone());
            job.record_workflow_boundary(
                stage_kind,
                WorkflowBoundaryKind::WorkflowCompleted,
                workflow_stage_input_ref(job_id, stage_kind),
                completion_ref.clone(),
                completion_ref,
                workflow_stage_lineage_ref(job_id, stage_kind),
                Some(state_before),
                Some(state_after),
            );
        }

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
        let (stage_kind, input_ref, handoff_ref, lineage_ref, failure_ref) = {
            let stage = job
                .stage_records
                .iter_mut()
                .find(|record| record.stage_id == stage_id)
                .ok_or_else(|| Status::failed_precondition("stage record not found"))?;
            let stage_kind = parse_stage_kind(&stage.stage_key).unwrap_or(DagStageKind::ValidateEnqueue);
            let input_ref = stage
                .artifact_refs
                .get("workflow_input_ref")
                .cloned()
                .unwrap_or_else(|| workflow_stage_input_ref(job_id, stage_kind));
            let handoff_ref = stage.handoff_ref.clone();
            let lineage_ref = stage
                .lineage_refs
                .get("workflow_lineage_ref")
                .cloned()
                .unwrap_or_else(|| workflow_stage_lineage_ref(job_id, stage_kind));
            let failure_ref = workflow_stage_failure_ref(job_id, stage_kind);
            stage.status = StageStatus::Failed;
            stage.state_after = terminal_state;
            stage.error_code = Some(error_code.to_string());
            stage.error_summary = Some(error_summary.to_string());
            stage.error_details_ref = Some(error_details_ref.to_string());
            stage
                .artifact_refs
                .insert("workflow_failure_ref".to_string(), failure_ref.clone());
            stage
                .artifact_refs
                .insert("workflow_output_ref".to_string(), failure_ref.clone());
            stage
                .artifact_refs
                .insert("workflow_handoff_ref".to_string(), handoff_ref.clone());
            stage
                .artifact_refs
                .insert("workflow_lineage_ref".to_string(), lineage_ref.clone());
            stage.completed_at = Some(ts_now());
            stage.replay_token = hash_bytes_hex(&stage_digest_bytes(stage));
            (stage_kind, input_ref, handoff_ref, lineage_ref, failure_ref)
        };

        job.workflow_failure_ref = Some(workflow_failure_ref(job_id));
        job.record_workflow_boundary(
            stage_kind,
            WorkflowBoundaryKind::StageFailed,
            input_ref,
            failure_ref.clone(),
            failure_ref.clone(),
            lineage_ref,
            Some(TaskState::Running),
            Some(terminal_state),
        );
        job.record_workflow_boundary(
            stage_kind,
            WorkflowBoundaryKind::WorkflowCompleted,
            workflow_stage_input_ref(job_id, stage_kind),
            workflow_failure_ref(job_id),
            workflow_failure_ref(job_id),
            workflow_stage_lineage_ref(job_id, stage_kind),
            Some(TaskState::Running),
            Some(terminal_state),
        );

        job.state = terminal_state;
        job.updated_at = ts_now();
        job.completed_at = Some(ts_now());
        job.error_code = Some(error_code.to_string());
        job.error_summary = Some(error_summary.to_string());
        job.error_details_ref = Some(error_details_ref.to_string());
        job.reservation_state = Some("released".to_string());
        let _ = handoff_ref;
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
        job.metadata.extend(metadata);
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
        job.reservation_released_reason = Some("cancel_requested".to_string());
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
        let stage = job.current_stage.unwrap_or(DagStageKind::ValidateEnqueue);
        let stage_id = stage_id(job_id, stage);
        let state_before = job.state;
        let input_ref = workflow_stage_input_ref(job_id, stage);
        let lineage_ref = workflow_stage_lineage_ref(job_id, stage);
        let failure_ref = workflow_stage_failure_ref(job_id, stage);
        let workflow_failure_ref = workflow_failure_ref(job_id);

        job.state = TaskState::Timeout;
        job.cancel_requested = true;
        job.cancel_reason = Some("deadline_exceeded".to_string());
        job.cancellation_fanout_ref = Some(format!("qfs://jobs/{job_id}/control/deadline.json"));
        job.reservation_state = Some("released".to_string());
        job.error_code = Some("DEADLINE_EXCEEDED".to_string());
        job.error_summary = Some("deadline exceeded while orchestrating the job".to_string());
        job.error_details_ref = Some(format!("qfs://jobs/{job_id}/errors/deadline.json"));
        job.workflow_failure_ref = Some(workflow_failure_ref.clone());
        job.completed_at = Some(ts_now());
        job.updated_at = ts_now();
        
        if let Some(record) = job.stage_records.iter_mut().find(|record| record.stage_id == stage_id) {
            record.status = StageStatus::Failed;
            record.state_after = TaskState::Timeout;
            record.error_code = Some("DEADLINE_EXCEEDED".to_string());
            record.error_summary = Some("deadline exceeded while orchestrating the job".to_string());
            record.error_details_ref = Some(format!("qfs://jobs/{job_id}/errors/deadline.json"));
            record
                .artifact_refs
                .insert("workflow_failure_ref".to_string(), failure_ref.clone());
            record
                .artifact_refs
                .insert("workflow_output_ref".to_string(), failure_ref.clone());
            record.completed_at = Some(ts_now());
            record.replay_token = hash_bytes_hex(&stage_digest_bytes(record));
        } else {
            job.stage_records.push(StageRecord {
                stage_id: stage_id.clone(),
                stage_key: stage.key().to_string(),
                order: stage.index(),
                state_before,
                state_after: TaskState::Timeout,
                status: StageStatus::Failed,
                started_at: ts_now(),
                completed_at: Some(ts_now()),
                input: BTreeMap::from([
                    ("job_id".to_string(), job_id.to_string()),
                    ("reason".to_string(), "deadline_exceeded".to_string()),
                    ("workflow_stage_input_ref".to_string(), input_ref.clone()),
                    ("workflow_stage_lineage_ref".to_string(), lineage_ref.clone()),
                    ("workflow_root_lineage_ref".to_string(), job.workflow_root_lineage_ref.clone()),
                ]),
                output: BTreeMap::from([
                    ("workflow_failure_ref".to_string(), failure_ref.clone()),
                    ("workflow_output_ref".to_string(), failure_ref.clone()),
                ]),
                artifact_refs: BTreeMap::from([
                    ("workflow_input_ref".to_string(), input_ref.clone()),
                    ("workflow_output_ref".to_string(), failure_ref.clone()),
                    ("workflow_handoff_ref".to_string(), workflow_stage_handoff_ref(job_id, stage)),
                    ("workflow_failure_ref".to_string(), failure_ref.clone()),
                    ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
                    (
                        "workflow_root_lineage_ref".to_string(),
                        job.workflow_root_lineage_ref.clone(),
                    ),
                    ("upstream_output_ref".to_string(), input_ref.clone()),
                ]),
                lineage_refs: BTreeMap::from([
                    ("workflow_lineage_ref".to_string(), lineage_ref.clone()),
                    (
                        "workflow_root_lineage_ref".to_string(),
                        job.workflow_root_lineage_ref.clone(),
                    ),
                    ("upstream_output_ref".to_string(), input_ref.clone()),
                ]),
                handoff_ref: workflow_stage_handoff_ref(job_id, stage),
                error_code: Some("DEADLINE_EXCEEDED".to_string()),
                error_summary: Some("deadline exceeded while orchestrating the job".to_string()),
                error_details_ref: Some(format!("qfs://jobs/{job_id}/errors/deadline.json")),
                replay_token: String::new(),
            });
        }

        job.record_workflow_boundary(
            stage,
            WorkflowBoundaryKind::StageFailed,
            input_ref,
            failure_ref.clone(),
            failure_ref.clone(),
            lineage_ref,
            Some(state_before),
            Some(TaskState::Timeout),
        );
        job.record_workflow_boundary(
            stage,
            WorkflowBoundaryKind::WorkflowCompleted,
            workflow_stage_input_ref(job_id, stage),
            workflow_failure_ref.clone(),
            workflow_failure_ref,
            workflow_stage_lineage_ref(job_id, stage),
            Some(state_before),
            Some(TaskState::Timeout),
        );
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
    metadata: BTreeMap<String, String>,
}

const RESULT_SUMMARY_PREFIX: &str = "result.summary.";

fn is_result_summary_bookkeeping_key(key: &str) -> bool {
    matches!(
        key,
        "message"
            | "counts_ref"
            | "execution_ref"
            | "selected_backend"
            | "selected_queue"
            | "qfs_result_ref"
            | "result_manifest_ref"
            | "release_evidence_bundle_ref"
            | "release_evidence_manifest_ref"
            | "release_provenance_ref"
            | "trace_context"
            | "trace_id"
            | "traceparent"
            | "timeline_ref"
            | "contract_marker"
    )
}

fn merge_result_summary_fields(
    summary: &mut BTreeMap<String, String>,
    source: &BTreeMap<String, String>,
) {
    for (key, value) in source {
        let summary_key = key.strip_prefix(RESULT_SUMMARY_PREFIX).unwrap_or(key.as_str());
        if is_result_summary_bookkeeping_key(summary_key) {
            continue;
        }
        summary.entry(summary_key.to_string()).or_insert_with(|| value.clone());
    }
}

fn merge_result_summary_json_value(
    summary: &mut BTreeMap<String, String>,
    key_prefix: &str,
    value: &serde_json::Value,
) {
    match value {
        serde_json::Value::Object(map) => {
            for (key, child) in map {
                let next_prefix = if key_prefix.is_empty() && key == "summary" {
                    String::new()
                } else if key_prefix.is_empty() {
                    key.clone()
                } else {
                    format!("{key_prefix}.{key}")
                };
                merge_result_summary_json_value(summary, &next_prefix, child);
            }
        }
        serde_json::Value::Array(_) => {
            if !key_prefix.is_empty() {
                summary
                    .entry(key_prefix.to_string())
                    .or_insert_with(|| serde_json::to_string(value).unwrap_or_default());
            }
        }
        serde_json::Value::String(text) => {
            if !key_prefix.is_empty() {
                summary.entry(key_prefix.to_string()).or_insert_with(|| text.clone());
            }
        }
        serde_json::Value::Number(number) => {
            if !key_prefix.is_empty() {
                summary.entry(key_prefix.to_string()).or_insert_with(|| number.to_string());
            }
        }
        serde_json::Value::Bool(flag) => {
            if !key_prefix.is_empty() {
                summary.entry(key_prefix.to_string()).or_insert_with(|| flag.to_string());
            }
        }
        serde_json::Value::Null => {}
    }
}

fn merge_result_summary_artifact(
    qfs: &CircuitFsLocal,
    summary: &mut BTreeMap<String, String>,
    artifact_ref: &str,
) {
    if artifact_ref.is_empty() {
        return;
    }

    let bytes = match qfs.read_bytes(artifact_ref) {
        Ok(bytes) => bytes,
        Err(err) => {
            tracing::debug!(artifact_ref = %artifact_ref, error = %err, "workflow output artifact unavailable");
            return;
        }
    };

    let payload: serde_json::Value = match serde_json::from_slice(&bytes) {
        Ok(payload) => payload,
        Err(err) => {
            tracing::debug!(artifact_ref = %artifact_ref, error = %err, "workflow output artifact is not valid json");
            return;
        }
    };

    merge_result_summary_json_value(summary, "", &payload);
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
    optimizer_gateway: Arc<dyn OptimizerGateway>,
    compiler_endpoint: Option<String>,
    driver_manager_endpoint: Option<String>,
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
        let qfs_root = std::env::var("EIGEN_QFS_LOCAL_ROOT")
            .or_else(|_| std::env::var("EIGEN_QFS_ROOT"))
            .unwrap_or_else(|_| "/tmp/eigen/qfs".to_string());
        let hold_stage = std::env::var("EIGEN_KERNEL_TEST_HOLD_STAGE").ok().and_then(|raw| parse_stage_kind(&raw));
        let hold_for = std::env::var("EIGEN_KERNEL_TEST_HOLD_MS")
            .ok()
            .and_then(|raw| raw.parse::<u64>().ok())
            .map(Duration::from_millis)
            .unwrap_or_default();

        let optimizer_gateway: Arc<dyn OptimizerGateway> =
            match (
                std::env::var("EIGEN_OPTIMIZER_SERVICE_URL").ok(),
                std::env::var("EIGEN_OPTIMIZER_SERVICE_ADDR").ok(),
            ) {
                (Some(_), _) | (_, Some(_)) => Arc::new(GrpcOptimizerGateway::from_env()),
                _ => Arc::new(FixtureOptimizerGateway::default()),
            };

        Self {
            qfs: CircuitFsLocal::new(qfs_root),
            failure_stage: None,
            hold_stage,
            hold_for,
            execute_script: Arc::new(Mutex::new(VecDeque::new())),
            optimizer_gateway,
            compiler_endpoint: std::env::var("EIGEN_COMPILER_ENDPOINT").ok(),
            driver_manager_endpoint: std::env::var("DRIVER_MANAGER_ENDPOINT").ok(),
        }
    }

    fn new(qfs_root: impl AsRef<str>, failure_stage: Option<DagStageKind>) -> Self {
        Self {
            qfs: CircuitFsLocal::new(qfs_root.as_ref()),
            failure_stage,
            hold_stage: None,
            hold_for: Duration::from_millis(0),
            execute_script: Arc::new(Mutex::new(VecDeque::new())),
            optimizer_gateway: Arc::new(FixtureOptimizerGateway::default()),
            compiler_endpoint: None,
            driver_manager_endpoint: None,
        }
    }

    fn with_hold(
        qfs_root: impl AsRef<str>,
        failure_stage: Option<DagStageKind>,
        hold_stage: Option<DagStageKind>,
        hold_for: Duration,
    ) -> Self {
        Self {
            qfs: CircuitFsLocal::new(qfs_root.as_ref()),
            failure_stage,
            hold_stage,
            hold_for,
            execute_script: Arc::new(Mutex::new(VecDeque::new())),
            optimizer_gateway: Arc::new(FixtureOptimizerGateway::default()),
            compiler_endpoint: None,
            driver_manager_endpoint: None,
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
            optimizer_gateway: Arc::new(FixtureOptimizerGateway::default()),
            compiler_endpoint: None,
            driver_manager_endpoint: None,
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

    fn sha256_hex(&self, payload: &[u8]) -> String {
        let mut hasher = Sha256::new();
        hasher.update(payload);
        format!("{:x}", hasher.finalize())
    }

    fn qfs_ref_path(&self, artifact_ref: &str) -> PathBuf {
        let normalized = artifact_ref
            .strip_prefix("qfs://")
            .or_else(|| artifact_ref.strip_prefix("circuitfs://"))
            .unwrap_or(artifact_ref)
            .trim_start_matches('/');
        self.qfs.root_path().join(normalized)
    }

    async fn compile_via_compiler(
        &self,
        submission: &NormalizedSubmission,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        let endpoint = self
            .compiler_endpoint
            .as_ref()
            .ok_or_else(|| KernelStageError::compile("compiler endpoint is not configured", "qfs://jobs/compiler/config/error.json"))?;

        let channel = Endpoint::from_shared(endpoint.clone()).map_err(|err| {
            KernelStageError::compile(
                format!("invalid compiler endpoint: {err}"),
                "qfs://jobs/compiler/config/error.json",
            )
        })?.connect_lazy();
        let mut client = CompilationServiceClient::new(channel);

        let request = Request::new(CompileCircuitRequest {
            language: "eigen-lang".to_string(),
            source: submission.program.clone(),
            options: submission.compiler_options.iter().map(|(k, v)| (k.clone(), v.clone())).collect(),
            source_ref: format!("qfs://jobs/{}/input/program.eigen.py", submission.job_id),
            request_metadata: Some(compiler_request_metadata_for_submission(submission)),
        });

        let response = client.compile_circuit(request).await.map_err(|status| {
            KernelStageError::compile(
                format!("compiler service call failed: {}", status.message()),
                format!("status::{:?}", status.code()),
            )
        })?.into_inner();

        let circuit = response
            .circuit
            .ok_or_else(|| KernelStageError::compile("compiler service returned empty circuit", "qfs://jobs/compiler/result/empty.json"))?;
        if circuit.data.is_empty() {
            return Err(KernelStageError::compile(
                "compiler service returned empty aqo payload",
                "qfs://jobs/compiler/result/empty.json",
            ));
        }

        let compiler_version = response
            .metadata
            .get("compiler")
            .cloned()
            .unwrap_or_else(|| "eigen-compiler".to_string());
        let aqo_sha = response
            .metadata
            .get("aqo_sha256")
            .cloned()
            .unwrap_or_else(|| self.sha256_hex(&circuit.data));
        let source_ref = format!("qfs://jobs/{}/input/program.eigen.py", submission.job_id);

        let provenance = CompiledArtifactProvenance {
            producer_identity: compiler_version.clone(),
            contract_version: "1.0.0".to_string(),
            compiler_version: compiler_version.clone(),
            created_at: timestamp_to_ms(&ts_now()).to_string(),
            lineage: CompiledArtifactLineage {
                request_id: Some(submission.request_id.clone()),
                source_ref: Some(source_ref),
                source_sha256: Some(submission.program_hash.clone()),
            },
        };
        self.qfs
            .store_compiled_artifacts_v1(&submission.job_id, &circuit.data, None, None, provenance)
            .map_err(|err| KernelStageError::compile(
                format!("failed to persist compiled aqo: {err}"),
                format!("qfs://jobs/{}/compiled/metadata.json", submission.job_id),
            ))?;

        Ok(BTreeMap::from([
            ("message".to_string(), "compile stage completed".to_string()),
            (
                "compiled_artifact_ref".to_string(),
                format!("qfs://jobs/{}/compiled/circuit.aqo.json", submission.job_id),
            ),
            ("compiler_version".to_string(), compiler_version),
            ("compile_digest".to_string(), aqo_sha),
        ]))
    }

    async fn execute_via_driver_manager(
        &self,
        submission: &NormalizedSubmission,
        schedule_output: &BTreeMap<String, String>,
    ) -> Result<ExecutionOutcome, KernelStageError> {
        let endpoint = self
            .driver_manager_endpoint
            .as_ref()
            .ok_or_else(|| KernelStageError::execute("driver-manager endpoint is not configured", "qfs://jobs/driver-manager/config/error.json"))?;

        let compiled_artifact_ref = format!("qfs://jobs/{}/compiled/circuit.aqo.json", submission.job_id);
        let aqo_bytes = self.qfs.read_bytes(&compiled_artifact_ref).map_err(|err| {
            KernelStageError::execute(
                format!("compiled aqo artifact missing: {err}"),
                compiled_artifact_ref.clone(),
            )
        })?;

        let shots = submission
            .metadata_kvs
            .get("shots")
            .and_then(|raw| raw.parse::<i32>().ok())
            .filter(|v| *v > 0)
            .unwrap_or(1024);

        let channel = Endpoint::from_shared(endpoint.clone()).map_err(|err| {
            KernelStageError::execute(
                format!("invalid driver-manager endpoint: {err}"),
                "qfs://jobs/driver-manager/config/error.json",
            )
        })?.connect_lazy();
        let mut client = DriverManagerServiceClient::new(channel);
        let request = Request::new(ExecuteCircuitRequest {
            job_id: submission.job_id.clone(),
            device_id: submission.target.clone(),
            payload: Some(CircuitPayload {
                format: 1,
                data: aqo_bytes,
            }),
            shots,
            options: HashMap::from([("provider_profile".to_string(), "simulator".to_string())]),
        });

        let response = client.execute_circuit(request).await.map_err(|status| {
            KernelStageError::execute(
                format!("driver-manager execute failed: {}", status.message()),
                format!("status::{:?}", status.code()),
            )
        })?.into_inner();

        let counts: BTreeMap<String, i64> = response.counts.into_iter().collect();
        let counts_json = counts.clone();
        let metadata_json = response.metadata.clone();
        let selected_backend = schedule_output
            .get("selected_backend")
            .cloned()
            .unwrap_or_else(|| submission.target.clone());
        let counts_ref = format!("qfs://jobs/{}/results/counts.json", submission.job_id);
        let execution_ref = format!("qfs://jobs/{}/execution/execution.json", submission.job_id);
        let execution_payload = serde_json::json!({
            "job_id": submission.job_id.clone(),
            "device_id": submission.target.clone(),
            "counts": counts_json,
            "execution_time_sec": response.execution_time_sec,
            "metadata": metadata_json,
            "schedule": schedule_output,
            "compiler_artifact_ref": compiled_artifact_ref.clone(),
        });
        let counts_payload = serde_json::to_vec_pretty(&serde_json::json!({"counts": counts.clone()})).unwrap_or_default();
        let execution_payload_bytes = serde_json::to_vec_pretty(&execution_payload).unwrap_or_default();

        self.qfs.write_bytes(&counts_ref, &counts_payload).map_err(|err| {
            KernelStageError::execute(
                format!("failed to persist counts artifact: {err}"),
                counts_ref.clone(),
            )
        })?;

        self.qfs.write_bytes(&execution_ref, &execution_payload_bytes).map_err(|err| {
            KernelStageError::execute(
                format!("failed to persist execution artifact: {err}"),
                execution_ref.clone(),
            )
        })?;

        Ok(ExecutionOutcome {
            counts,
            output: BTreeMap::from([
                ("message".to_string(), "execution completed".to_string()),
                ("counts_ref".to_string(), counts_ref),
                ("execution_ref".to_string(), execution_ref),
                ("selected_backend".to_string(), selected_backend),
                (
                    "execution_time_sec".to_string(),
                    response.execution_time_sec.to_string(),
                ),
                (
                    "driver".to_string(),
                    response.metadata.get("driver").cloned().unwrap_or_else(|| "simulator".to_string()),
                ),
            ]),
            metadata: response.metadata.into_iter().collect(),
        })
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
        tracing::info!(
            event = "enqueue",
            trace_id = %submission.trace_id,
            request_id = %submission.request_id,
            job_id = %submission.job_id,
            source_service = %submission.source_service,
            stage = "validate-enqueue",
            "submission accepted into orchestration DAG"
        );
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::ValidateEnqueue, &output)?;
        Ok(output)
    }

    async fn compile(
        &self,
        submission: &NormalizedSubmission,
        _validation_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Compile).await;
        self.maybe_fail(DagStageKind::Compile)?;
        let output = if self.compiler_endpoint.is_some() {
            self.compile_via_compiler(submission).await?
        } else {
            BTreeMap::from([
                ("message".to_string(), "compile stage completed".to_string()),
                (
                    "compiled_artifact_ref".to_string(),
                    format!("qfs://jobs/{}/compiled/circuit.aqo.json", submission.job_id),
                ),
                (
                    "compiler_version".to_string(),
                    env!("CARGO_PKG_VERSION").to_string(),
                ),
                (
                    "compile_digest".to_string(),
                    format!("compile-{}", submission.program_hash),
                ),
            ])
        };
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::Compile, &output)?;
        Ok(output)
    }

    async fn optimize(
        &self,
        submission: &NormalizedSubmission,
        compile_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Optimize).await;
        self.maybe_fail(DagStageKind::Optimize)?;
        let output = self
            .optimizer_gateway
            .optimize(submission, compile_output)
            .await
            .map_err(|err| match err.grpc_code {
                Code::Unavailable => KernelStageError::unavailable(err.summary, err.details_ref),
                Code::DeadlineExceeded => KernelStageError::deadline_exceeded(err.summary, err.details_ref),
                Code::ResourceExhausted => KernelStageError::resource_exhausted(err.summary, err.details_ref),
                Code::InvalidArgument => KernelStageError::invalid_argument(err.summary, err.details_ref),
                _ => KernelStageError::optimize(err.summary, err.details_ref),
            })?;
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::Optimize, &output)?;
        Ok(output)
    }

    async fn schedule(
        &self,
        submission: &NormalizedSubmission,
        _optimize_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Schedule).await;
        self.maybe_fail(DagStageKind::Schedule)?;
        let mut output = BTreeMap::from([
            ("message".to_string(), "resource schedule selected".to_string()),
            (
                "scheduler_decision_version".to_string(),
                SCHEDULER_DECISION_VERSION.to_string(),
            ),
            (
                "policy_bundle_id".to_string(),
                SCHEDULING_POLICY_BUNDLE_ID.to_string(),
            ),
            (
                "policy_bundle_version".to_string(),
                SCHEDULING_POLICY_BUNDLE_VERSION.to_string(),
            ),
            ("selected_backend".to_string(), submission.target.clone()),
            ("selected_queue".to_string(), "scheduler:default".to_string()),
            (
                "resource_plan_ref".to_string(),
                format!("qfs://jobs/{}/schedule/plan.json", submission.job_id),
            ),
            (
                "decision_input_digest".to_string(),
                submission.fingerprint.clone(),
            ),
        ]);
        if let Some(optimize_output) = _optimize_output.get("trace_context") {
            output.insert("trace_context".to_string(), optimize_output.clone());
        }
        if let Some(optimize_output) = _optimize_output.get("model_version") {
            output.insert("optimizer_model_version".to_string(), optimize_output.clone());
        }
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::Schedule, &output)?;
        Ok(output)
    }

    async fn execute(
        &self,
        submission: &NormalizedSubmission,
        schedule_output: &BTreeMap<String, String>,
    ) -> Result<ExecutionOutcome, KernelStageError> {
        self.maybe_hold(DagStageKind::Execute).await;
        let outcome = if self.driver_manager_endpoint.is_some() {
            self.execute_via_driver_manager(submission, schedule_output).await?
        } else {
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

            ExecutionOutcome {
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
                metadata: BTreeMap::new(),
            }
            };
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::Execute, &outcome.output)?;
        Ok(outcome)
    }

    async fn persist(
        &self,
        submission: &NormalizedSubmission,
        execution_output: &ExecutionOutcome,
        stage_records: &[StageRecord],
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Persist).await;
        self.maybe_fail(DagStageKind::Persist)?;
        let compile_stage = stage_records.iter().find(|stage| stage.stage_key == "compile");
        let optimize_stage = stage_records.iter().find(|stage| stage.stage_key == "optimize");
        let selected_backend = execution_output
            .output
            .get("selected_backend")
            .cloned()
            .unwrap_or_else(|| submission.target.clone());
        let workload_kind = workload_kind_label(submission);
        let execution_time_sec = execution_output
            .output
            .get("execution_time_sec")
            .and_then(|value| value.parse::<f64>().ok())
            .unwrap_or_default();
        let total_shots: i64 = execution_output.counts.values().copied().sum();
        let nonzero_bitstrings = execution_output.counts.len() as i64;
        let dominant_bitstring = execution_output
            .counts
            .iter()
            .max_by_key(|(_, count)| *count)
            .map(|(bitstring, count)| format!("{bitstring}:{count}"))
            .unwrap_or_default();
        let stage_count = stage_records.len() as i64;
        let summary_context = submission.summary_map();
        let mut summary = BTreeMap::from([
            ("workload_kind".to_string(), workload_kind.clone()),
            ("target".to_string(), submission.target.clone()),
            ("selected_backend".to_string(), selected_backend.clone()),
            ("shots_total".to_string(), total_shots.to_string()),
            ("nonzero_bitstrings".to_string(), nonzero_bitstrings.to_string()),
            ("dominant_bitstring".to_string(), dominant_bitstring.clone()),
            ("execution_time_sec".to_string(), format!("{execution_time_sec:.6}")),
            ("stage_count".to_string(), stage_count.to_string()),
        ]);
        if let Some(optimizer) = execution_output.output.get("optimizer") {
            summary.insert("optimizer".to_string(), optimizer.clone());
        }
        if let Some(driver) = execution_output.output.get("driver") {
            summary.insert("driver".to_string(), driver.clone());
        }
        if let Some(optimize_stage) = optimize_stage {
            merge_result_summary_fields(&mut summary, &optimize_stage.output);
        }
        if let Some(workflow_output_ref) = summary.get("workflow_output_ref").cloned() {
            merge_result_summary_artifact(&self.qfs, &mut summary, &workflow_output_ref);
        }
        merge_result_summary_fields(&mut summary, &execution_output.output);
        merge_result_summary_fields(&mut summary, &execution_output.metadata);
        if let Some(objective) = summary.get("objective").cloned() {
            if objective.parse::<f64>().is_ok() {
                summary.entry("energy".to_string()).or_insert(objective);
            }
        }
        let summary_metadata: BTreeMap<String, String> = summary
            .iter()
            .map(|(key, value)| (format!("result.summary.{key}"), value.clone()))
            .collect();
        summary.extend(summary_metadata.clone());
        let measurements = scientific_measurements(
            submission,
            execution_output,
            stage_records,
            &selected_backend,
            &workload_kind,
            execution_time_sec,
        );
        let envelope = ResultEnvelope {
            artifact_version: "1.0.0".to_string(),
            schema_version: "scientific_result_bundle.v1".to_string(),
            producer_version: env!("CARGO_PKG_VERSION").to_string(),
            job_id: submission.job_id.clone(),
            workload_kind: workload_kind.clone(),
            result_ref: "results/result.json".to_string(),
            manifest_ref: "results/manifest.json".to_string(),
            created_at_epoch_ms: unix_epoch_ms_u64(),
            retention_policy: "pinned".to_string(),
            lineage: qfs::CompiledArtifactLineage {
                request_id: Some(submission.request_id.clone()),
                source_ref: Some(format!("qfs://jobs/{}/input/program.eigen.py", submission.job_id)),
                source_sha256: Some(submission.program_hash.clone()),
            },
            context: summary_context,
            summary,
            measurements,
        };
        if let Err(err) = self.qfs.ensure_job_layout(&submission.job_id) {
            tracing::warn!(job_id = %submission.job_id, error = %err, "failed to prepare QFS job layout");
        }
        if let Err(err) = self
            .qfs
            .store_results_bundle(&submission.job_id, &envelope, env!("CARGO_PKG_VERSION"))
        {
            tracing::warn!(job_id = %submission.job_id, error = %err, "failed to persist results bundle");
        }

        let compiled_artifact_ref = compile_stage
            .and_then(|stage| stage.output.get("compiled_artifact_ref"))
            .cloned()
            .unwrap_or_else(|| format!("qfs://jobs/{}/compiled/circuit.aqo.json", submission.job_id));
        let optimized_artifact_ref = optimize_stage
            .and_then(|stage| stage.output.get("optimized_artifact_ref"))
            .cloned()
            .unwrap_or_else(|| format!("qfs://jobs/{}/optimizer/optimized_aqo.json", submission.job_id));
        let compiler_version = compile_stage
            .and_then(|stage| stage.output.get("compiler_version"))
            .cloned()
            .unwrap_or_else(|| env!("CARGO_PKG_VERSION").to_string());
        let optimizer_version = optimize_stage
            .and_then(|stage| stage.output.get("optimizer_version"))
            .cloned()
            .unwrap_or_else(|| "fixture-optimizer/1".to_string());
        let optimizer_policy = optimize_stage
            .and_then(|stage| stage.output.get("optimizer_policy"))
            .cloned()
            .unwrap_or_else(|| "deterministic".to_string());

        let bundle = ReleaseEvidenceBundle {
            artifact_version: "1.0.0".to_string(),
            schema_version: "release_evidence_bundle.v1".to_string(),
            producer_version: env!("CARGO_PKG_VERSION").to_string(),
            job_id: submission.job_id.clone(),
            compiler_contract_version: "1.0.0".to_string(),
            optimizer_contract_version: "1.0.0".to_string(),
            request_id: submission.request_id.clone(),
            trace_id: submission.trace_id.clone(),
            traceparent: submission.traceparent.clone(),
            source_sha256: submission.program_hash.clone(),
            aqo_sha256: submission.fingerprint.clone(),
            optimized_aqo_sha256: Some(format!(
                "sha256:{}",
                self.sha256_hex(optimized_artifact_ref.as_bytes())
            )),
            compiled_artifact_ref: compiled_artifact_ref.clone(),
            optimized_artifact_ref: optimized_artifact_ref.clone(),
            manifest_ref: format!("qfs://jobs/{}/meta/release_evidence/manifest.json", submission.job_id),
            provenance_report_ref: format!("qfs://jobs/{}/meta/release_evidence/provenance.json", submission.job_id),
            created_at_epoch_ms: unix_epoch_ms_u64(),
        };
        let bundle_bytes = serde_json::to_vec_pretty(&bundle).unwrap_or_default();
        let provenance_report = ReleaseEvidenceProvenanceReport {
            artifact_version: "1.0.0".to_string(),
            schema_version: "release_evidence_provenance.v1".to_string(),
            job_id: submission.job_id.clone(),
            request_id: submission.request_id.clone(),
            trace_id: submission.trace_id.clone(),
            traceparent: submission.traceparent.clone(),
            compiler_stage_id: compile_stage.map(|stage| stage.stage_id.clone()).unwrap_or_default(),
            optimizer_stage_id: optimize_stage.map(|stage| stage.stage_id.clone()).unwrap_or_default(),
            compiler_run_id: compile_stage.map(|stage| stage.replay_token.clone()).unwrap_or_default(),
            optimizer_run_id: optimize_stage.map(|stage| stage.replay_token.clone()).unwrap_or_default(),
            compiler_artifact_ref: compiled_artifact_ref.clone(),
            optimized_artifact_ref: optimized_artifact_ref.clone(),
            compiler_lineage: qfs::CompiledArtifactLineage {
                request_id: Some(submission.request_id.clone()),
                source_ref: None,
                source_sha256: Some(submission.program_hash.clone()),
            },
            optimized_aqo_sha256: Some(format!("sha256:{}", self.sha256_hex(bundle_bytes.as_slice()))),
        };
        let provenance_bytes = serde_json::to_vec_pretty(&provenance_report).unwrap_or_default();
        let manifest = ReleaseEvidenceManifest {
            artifact_version: "1.0.0".to_string(),
            producer_version: env!("CARGO_PKG_VERSION").to_string(),
            schema_version: "release_evidence_manifest.v1".to_string(),
            created_at_epoch_ms: unix_epoch_ms_u64(),
            retention_policy: "pinned".to_string(),
            artifacts: vec![
                ResultArtifactDescriptor {
                    path: format!("meta/release_evidence/bundle.json"),
                    content_hash: format!("sha256:{}", self.sha256_hex(&bundle_bytes)),
                    size_bytes: bundle_bytes.len() as u64,
                },
                ResultArtifactDescriptor {
                    path: format!("meta/release_evidence/provenance.json"),
                    content_hash: format!("sha256:{}", self.sha256_hex(&provenance_bytes)),
                    size_bytes: provenance_bytes.len() as u64,
                },
            ],
        };
        let _ = self.qfs.store_release_evidence_bundle_v1(&submission.job_id, &bundle, &manifest, &provenance_report);

        let mut persist_output = BTreeMap::from([
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
                "release_evidence_bundle_ref".to_string(),
                format!("qfs://jobs/{}/meta/release_evidence/bundle.json", submission.job_id),
            ),
            (
                "release_evidence_manifest_ref".to_string(),
                format!("qfs://jobs/{}/meta/release_evidence/manifest.json", submission.job_id),
            ),
            (
                "release_provenance_ref".to_string(),
                format!("qfs://jobs/{}/meta/release_evidence/provenance.json", submission.job_id),
            ),
            (
                "artifact_version".to_string(),
                env!("CARGO_PKG_VERSION").to_string(),
            ),
            ("optimizer_policy".to_string(), optimizer_policy),
            ("compiler_version".to_string(), compiler_version),
            ("optimizer_version".to_string(), optimizer_version),
        ]);
        persist_output.extend(summary_metadata);
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::Persist, &persist_output)?;
        Ok(persist_output)
    }

    async fn record_knowledge_observability(
        &self,
        submission: &NormalizedSubmission,
        persist_output: &BTreeMap<String, String>,
        execution_output: &ExecutionOutcome,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::RecordKnowledgeObservability).await;
        self.maybe_fail(DagStageKind::RecordKnowledgeObservability)?;
        let mut payload = serde_json::Map::new();
        payload.insert("job_id".to_string(), serde_json::Value::String(submission.job_id.clone()));
        payload.insert("request_id".to_string(), serde_json::Value::String(submission.request_id.clone()));
        payload.insert("trace_id".to_string(), serde_json::Value::String(submission.trace_id.clone()));
        payload.insert(
            "traceparent".to_string(),
            serde_json::Value::String(submission.traceparent.clone()),
        );
        payload.insert(
            "timeline_ref".to_string(),
            serde_json::Value::String(format!("qfs://jobs/{}/timeline.jsonl", submission.job_id)),
        );
        payload.insert(
            "qfs_result_ref".to_string(),
            serde_json::Value::String(
                persist_output
                    .get("qfs_result_ref")
                    .cloned()
                    .unwrap_or_default(),
            ),
        );
        payload.insert(
            "counts_ref".to_string(),
            serde_json::Value::String(
                execution_output
                    .output
                    .get("counts_ref")
                    .cloned()
                    .unwrap_or_default(),
            ),
        );
        payload.insert(
            "contract_marker".to_string(),
            serde_json::Value::String(r#"eigen_orch_contract_info{version="1.0.0"} 1"#.to_string()),
        );
        for (key, value) in persist_output {
            if key.starts_with("result.summary.") {
                payload.insert(key.clone(), serde_json::Value::String(value.clone()));
            }
        }
        let payload = serde_json::Value::Object(payload);
        let metrics = serde_json::to_vec(&payload).unwrap_or_default();
        let _ = self
            .qfs
            .store_metrics_json(&submission.job_id, &metrics);
        tracing::info!(
            event = "result_reference",
            trace_id = %submission.trace_id,
            request_id = %submission.request_id,
            job_id = %submission.job_id,
            qfs_result_ref = %persist_output.get("qfs_result_ref").cloned().unwrap_or_default(),
            "result reference recorded"
        );

        let output = BTreeMap::from([
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
        ]);
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::RecordKnowledgeObservability, &output)?;
        Ok(output)
    }

    async fn finalize(
        &self,
        submission: &NormalizedSubmission,
        observability_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, KernelStageError> {
        self.maybe_hold(DagStageKind::Finalize).await;
        self.maybe_fail(DagStageKind::Finalize)?;
        let output = BTreeMap::from([
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
        ]);
        persist_stage_output_artifact(&self.qfs, &submission.job_id, DagStageKind::Finalize, &output)?;
        Ok(output)
    }
}

#[derive(Debug, Clone)]
struct OptimizerGatewayError {
    grpc_code: Code,
    summary: String,
    details_ref: String,
}

#[tonic::async_trait]
trait OptimizerGateway: Send + Sync {
    async fn optimize(
        &self,
        submission: &NormalizedSubmission,
        compile_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, OptimizerGatewayError>;
}

#[derive(Debug, Default)]
struct FixtureOptimizerGateway;

#[tonic::async_trait]
impl OptimizerGateway for FixtureOptimizerGateway {
    async fn optimize(
        &self,
        submission: &NormalizedSubmission,
        compile_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, OptimizerGatewayError> {
        let model_version = "optimizer-model-v1".to_string();
        let objective = optimizer_objective_preset(submission);
        let fallback_reason_code = "EIGEN_OPT_UNSPECIFIED".to_string();
        let fallback_reason = optimizer_fallback_reason_from_code(&fallback_reason_code);
        let selected_candidate_id = "candidate-0".to_string();
        let confidence_score = 0.92_f64;
        let optimizer_digest = compile_output
            .get("compile_digest")
            .cloned()
            .unwrap_or_else(|| submission.fingerprint.clone());

        Ok(BTreeMap::from([
            ("message".to_string(), "optimizer service completed".to_string()),
            (
                "optimized_artifact_ref".to_string(),
                format!("qfs://jobs/{}/optimizer/optimized_aqo.json", submission.job_id),
            ),
            ("optimizer_version".to_string(), model_version),
            ("optimizer_policy".to_string(), "deterministic".to_string()),
            ("optimizer_digest".to_string(), optimizer_digest),
            ("selected_candidate_id".to_string(), selected_candidate_id),
            ("fallback_used".to_string(), "false".to_string()),
            ("fallback_reason_code".to_string(), fallback_reason_code),
            ("fallback_reason".to_string(), fallback_reason),
            ("confidence_score".to_string(), confidence_score.to_string()),
            ("objective".to_string(), objective),
            (
                "score_breakdown".to_string(),
                optimizer_score_breakdown_json(0.94, 0.92, 0.96, 0.91, 0.08),
            ),
            (
                "topology_context".to_string(),
                optimizer_topology_context_json(compile_output, submission),
            ),
            ("trace_context".to_string(), optimizer_trace_context_json(submission)),
        ]))
    }

}

#[derive(Debug, Clone)]
struct GrpcOptimizerGateway {
    endpoint: String,
}

impl GrpcOptimizerGateway {
    fn from_env() -> Self {
        let endpoint = std::env::var("EIGEN_OPTIMIZER_SERVICE_URL")
            .or_else(|_| std::env::var("EIGEN_OPTIMIZER_SERVICE_ADDR"))
            .unwrap_or_else(|_| "http://127.0.0.1:50052".to_string());
        Self { endpoint }
    }

    fn build_request(
        &self,
        submission: &NormalizedSubmission,
        compile_output: &BTreeMap<String, String>,
    ) -> OptimizerServiceOptimizeCircuitRequest {
        let compile_digest = compile_output
            .get("compile_digest")
            .cloned()
            .unwrap_or_else(|| submission.program_hash.clone());
        let compiled_artifact_ref = compile_output
            .get("compiled_artifact_ref")
            .cloned()
            .unwrap_or_else(|| format!("qfs://jobs/{}/compiled/circuit.aqo.json", submission.job_id));
        let canonical_graph_json = serde_json::to_string(&serde_json::json!({
            "canonical_graph_version": "aqo-graph-v1",
            "compile_digest": compile_digest,
            "compiled_artifact_ref": compiled_artifact_ref,
        }))
        .unwrap_or_else(|_| {
            format!(
                r#"{{"canonical_graph_version":"aqo-graph-v1","compile_digest":"{}","compiled_artifact_ref":"{}"}}"#,
                compile_digest, compiled_artifact_ref
            )
        });
        
        OptimizerServiceOptimizeCircuitRequest {
            envelope: Some(OptimizerContractEnvelope {
                contract_version: submission.contract_version.clone(),
            }),
            request_id: submission.request_id.clone(),
            input_aqo: Some(CircuitPayload {
                format: 1,
                data: canonical_graph_json.as_bytes().to_vec(),
            }),
            topology: Some(TopologyContext {
                topology_ref: compiled_artifact_ref,
                topology_digest_sha256: compile_digest.clone(),
                noise_snapshot_ref: String::new(),
                backend_profile: submission.target.clone(),
            }),
            objective: Some(OptimizationObjective {
                preset: submission
                    .metadata_kvs
                    .get("optimizer.objective")
                    .cloned()
                    .unwrap_or_else(|| "balanced".to_string()),
                weights: HashMap::new(),
            }),
            deterministic_seed: stable_seed_from_submission(submission),
            candidate_budget: submission
                .metadata_kvs
                .get("optimizer.candidate_budget")
                .and_then(|s| s.parse::<u32>().ok())
                .unwrap_or(1),
            timeout_ms: submission
                .metadata_kvs
                .get("optimizer.timeout_ms")
                .and_then(|s| s.parse::<u32>().ok())
                .unwrap_or(100),
            trace_context: HashMap::from([
                ("request_id".to_string(), submission.request_id.clone()),
                ("trace_id".to_string(), submission.trace_id.clone()),
                ("traceparent".to_string(), submission.traceparent.clone()),
            ]),
            graph_encoding: Some(GraphEncodingContext {
                encoding_version: "aqo-graph-v1".to_string(),
                canonical_format: "aqo-json".to_string(),
                canonical_graph_json: canonical_graph_json.clone(),
                canonical_sha256: hash_bytes_hex(canonical_graph_json.as_bytes()),
                round_trip_stability: true,
            }),
            policy: Some(OptimizerPolicy {
                mode: "deterministic".to_string(),
                minimum_confidence: 0.8,
                max_depth: 12,
                max_swaps: 3,
                forbidden_qubits: Vec::new(),
                forbidden_edges: Vec::new(),
            }),
            ranking_semantics: Some(OptimizerRankingSemantics {
                sort_order: vec![
                    "score.total_score desc".to_string(),
                    "confidence desc".to_string(),
                    "candidate_id asc".to_string(),
                ],
                selected_candidate_is_first: true,
                tie_breakers: vec![
                    "score.total_score".to_string(),
                    "confidence".to_string(),
                    "candidate_id".to_string(),
                ],
            }),
        }
    }
}

#[tonic::async_trait]
impl OptimizerGateway for GrpcOptimizerGateway {
    async fn optimize(
        &self,
        submission: &NormalizedSubmission,
        compile_output: &BTreeMap<String, String>,
    ) -> Result<BTreeMap<String, String>, OptimizerGatewayError> {
        let endpoint = Endpoint::from_shared(self.endpoint.clone()).map_err(|err| OptimizerGatewayError {
            grpc_code: Code::InvalidArgument,
            summary: format!("invalid optimizer endpoint: {err}"),
            details_ref: "qfs://jobs/optimizer/config/error.json".to_string(),
        })?;
        let channel = endpoint.connect_lazy();
        let mut client = OptimizerServiceClient::new(channel);
        let request = Request::new(self.build_request(submission, compile_output));
        let response = client.optimize_circuit(request).await.map_err(|status| OptimizerGatewayError {
            grpc_code: status.code(),
            summary: format!("optimizer service call failed: {}", status.message()),
            details_ref: format!("status::{:?}", status.code()),
        })?.into_inner();

        let mut output = BTreeMap::new();
        output.insert("message".to_string(), "optimizer service completed".to_string());
        output.insert(
            "optimized_artifact_ref".to_string(),
            format!("qfs://jobs/{}/optimizer/optimized_aqo.json", submission.job_id),
        );
        output.insert("optimizer_version".to_string(), response.model_version.clone());
        output.insert("optimizer_policy".to_string(), "deterministic".to_string());
        output.insert("optimizer_digest".to_string(), response.optimizer_digest.clone());
        output.insert("selected_candidate_id".to_string(), response.selected_candidate_id.clone());
        output.insert("fallback_used".to_string(), response.fallback_used.to_string());
        output.insert("fallback_reason_code".to_string(), response.fallback_reason_code.clone());
        output.insert("fallback_reason".to_string(), optimizer_fallback_reason_from_code(&response.fallback_reason_code));
        output.insert("confidence_score".to_string(), response.confidence_score.to_string());
        output.insert("objective".to_string(), optimizer_objective_preset(submission));
        let selected_candidate = response.candidates.first();
        let score_breakdown = selected_candidate
            .and_then(|candidate| candidate.score.as_ref())
            .map(|score| {
                optimizer_score_breakdown_json(
                    score.total_score,
                    score.latency_score,
                    score.fidelity_score,
                    score.resource_score,
                    score.risk_score,
                )
            })
            .unwrap_or_else(|| optimizer_score_breakdown_json(0.0, 0.0, 0.0, 0.0, 0.0));
        output.insert("score_breakdown".to_string(), score_breakdown);
        output.insert("topology_context".to_string(), optimizer_topology_context_json(compile_output, submission));
        output.insert("trace_context".to_string(), optimizer_trace_context_json(submission));

        Ok(output)
    }
}

fn stable_seed_from_submission(submission: &NormalizedSubmission) -> u64 {
    fnv1a64(
        format!(
            "{}:{}:{}:{}:{}",
            submission.contract_version,
            submission.request_id,
            submission.traceparent,
            submission.program_hash,
            submission.target
        )
        .as_bytes(),
    )
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
                    if let Err(err) =
                        run_job_dag(runtime.clone(), adapters.clone(), job_id.clone(), submission_for_task).await
                    {
                        let terminalization = match err.grpc_code {
                            Code::DeadlineExceeded => runtime.request_deadline_terminalization(&job_id).map(|_| ()),
                            _ => runtime
                                .request_error_terminalization(&job_id, &err.error_code, &err.summary, &err.details_ref)
                                .map(|_| ()),
                        };
                        if let Err(status) = terminalization {
                            tracing::error!(error = %status, "kernel terminalization failed");
                        }
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
        let job = self.runtime.request_cancel(&job_id, None)?;
        tracing::info!(
            event = "cancel",
            trace_id = %job.submission.trace_id,
            request_id = %job.submission.request_id,
            job_id = %job.job_id,
            reason = "user-request",
            stage = job.stage_label(),
            "cancellation requested"
        );
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
        let deadline = tokio::time::Instant::now() + Duration::from_secs(10);
        loop {
            if let Some(job) = self.runtime.get(&job_id) {
                if job.is_terminal() {
                    break;
                }
            } else {
                return Err(Status::not_found("job not found"));
            }
            if tokio::time::Instant::now() >= deadline {
                break;
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
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

        let schedule_stage = job
            .schedule_stage()
            .ok_or_else(|| Status::failed_precondition("dispatch rationale requires a completed schedule stage"))?;

        let selected_backend = schedule_stage
            .output
            .get("selected_backend")
            .cloned()
            .ok_or_else(|| Status::failed_precondition("schedule stage missing selected_backend"))?;
        let selected_queue = schedule_stage
            .output
            .get("selected_queue")
            .cloned()
            .ok_or_else(|| Status::failed_precondition("schedule stage missing selected_queue"))?;
        let policy_bundle_id = schedule_stage
            .output
            .get("policy_bundle_id")
            .cloned()
            .unwrap_or_else(|| SCHEDULING_POLICY_BUNDLE_ID.to_string());
        let policy_bundle_version = schedule_stage
            .output
            .get("policy_bundle_version")
            .cloned()
            .unwrap_or_else(|| SCHEDULING_POLICY_BUNDLE_VERSION.to_string());
        let policy_version = format!("{policy_bundle_id}/{policy_bundle_version}");
        let mut reason_codes = BTreeSet::from([
            "schedule_stage_completed".to_string(),
            "policy_bundle_applied".to_string(),
            "backend_selected".to_string(),
            "queue_selected".to_string(),
            "trace_linked".to_string(),
        ]);
        if let Some(code) = job.error_code.clone() {
            reason_codes.insert(code);
        }

        let rationale = DispatchRationale {
            version: "1.0.0".to_string(),
            policy_version,
            reason_codes: reason_codes.into_iter().collect(),
            selected_backend: selected_backend.clone(),
            selected_queue: selected_queue.clone(),
            attributes: bounded_dispatch_rationale_attributes(
                &job,
                schedule_stage,
                &selected_backend,
                &selected_queue,
            )
            .into_iter()
            .collect(),
            timeline_ref: format!("qfs://jobs/{}/timeline.jsonl", canonical_job_id_for_submission(&job.submission)),
            logs_ref: format!("qfs://jobs/{}/logs/runtime.json", canonical_job_id_for_submission(&job.submission)),
            trace_id: job.submission.trace_id.clone(),
            trace_ref: format!("qfs://jobs/{}/trace.json", canonical_job_id_for_submission(&job.submission)),
        };
        tracing::info!(
            event = "dispatch_rationale",
            trace_id = %job.submission.trace_id,
            request_id = %job.submission.request_id,
            job_id = %job.job_id,
            stage_count = job.stage_records.len(),
            "dispatch rationale emitted"
        );

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
        metadata: BTreeMap::new(),
    };
    let mut persist_output = BTreeMap::new();
    let mut observability_output = BTreeMap::new();

    let _ = runtime.sweep_stale_reservations();
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

    let reservation_metadata = BTreeMap::from([
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

    let simulate_runtime_sec = submission
        .metadata_kvs
        .get("simulate_runtime_sec")
        .and_then(|raw| raw.parse::<f64>().ok())
        .filter(|value| *value > 0.0);
    let timeout_seconds = submission
        .metadata_kvs
        .get("timeout_seconds")
        .and_then(|raw| raw.parse::<f64>().ok())
        .filter(|value| *value > 0.0);
    let backend_error_kind = submission.metadata_kvs.get("backend_error_kind").map(String::as_str);

    if backend_error_kind == Some("unavailable") {
        let err = KernelStageError::unavailable(
            "backend unavailable",
            format!("qfs://jobs/{job_id}/errors/backend-unavailable.json"),
        );
        return Err(stage_error(execute_stage, err));
    }

    if let Some(runtime_sec) = simulate_runtime_sec {
        let started = Instant::now();
        let sleep_slice = Duration::from_millis(20);
        loop {
            if runtime.is_cancel_requested(&job_id) {
                cancel_after_stage(&runtime, &job_id, DagStageKind::Execute, "cancelled during execution")?;
                return Ok(());
            }
            if runtime.deadline_expired(&job_id) {
                terminalize_control(&runtime, &job_id, DagStageKind::Execute, "execute")?;
                return Ok(());
            }
            if let Some(timeout) = timeout_seconds {
                if started.elapsed().as_secs_f64() >= timeout {
                    let err = KernelStageError::deadline_exceeded(
                        "execution timeout exceeded",
                        format!("qfs://jobs/{job_id}/errors/deadline.json"),
                    );
                    return Err(stage_error(execute_stage, err));
                }
            }
            if started.elapsed().as_secs_f64() >= runtime_sec {
                break;
            }
            tokio::time::sleep(sleep_slice).await;
        }
    }

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

    if !persist_output.contains_key("result.summary.objective") {
        if let Some(objective) = optimize_output
            .get("objective")
            .cloned()
            .or_else(|| execution_output.metadata.get("objective").cloned())
        {
            persist_output.insert("result.summary.objective".to_string(), objective);
        }
    }

    let result_summary_metadata: BTreeMap<String, String> = persist_output
        .iter()
        .filter_map(|(key, value)| {
            key.strip_prefix(RESULT_SUMMARY_PREFIX)
                .map(|summary_key| (format!("{RESULT_SUMMARY_PREFIX}{summary_key}"), value.clone()))
        })
        .collect();
    if !result_summary_metadata.is_empty() {
        runtime
            .set_metadata(&job_id, result_summary_metadata)
            .map_err(status_to_stage_error(persist_stage, "set_result_summary_metadata"))?;
    }

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

    tracing::info!(
        event = "terminal_state",
        trace_id = %submission.trace_id,
        request_id = %submission.request_id,
        job_id = %job_id,
        final_state = "DONE",
        "job reached terminal state"
    );

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
    runtime
        .set_reservation_state(job_id, "released")
        .map_err(|status| KernelStageError::new(
            Code::Internal,
            "RUNTIME_STAGE_FAILURE",
            "reservation release after cancellation failed",
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
    let _ = (stage, stage_label);

    if is_cancel {
        cancel_after_stage(runtime, job_id, stage, "cancelled by request")
    } else {
        runtime
            .request_deadline_terminalization(job_id)
            .map_err(|status| KernelStageError::new(
                Code::Internal,
                "RUNTIME_STAGE_FAILURE",
                "deadline terminalization failed",
                format!("status::{:?}", status.code()),
            ))?;
        Ok(())
    }
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
    
    let terminalize_deadline = |runtime: &Arc<KernelRuntimeStore>| -> Result<ExecutionOutcome, KernelStageError> {
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
        Err(KernelStageError::deadline_exceeded(
            "execution retry interrupted by deadline",
            format!("qfs://jobs/{job_id}/errors/deadline.json"),
        ))
    };

    loop {
        if runtime.deadline_expired(job_id) {
            return terminalize_deadline(runtime);
        }
        attempt = attempt.saturating_add(1);
        let attempt_started = Instant::now();
        let span = tracing::info_span!(
            "execute_attempt",
            job_id = %job_id,
            trace_id = %submission.trace_id,
            request_id = %submission.request_id,
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
                if runtime.deadline_expired(job_id) {
                    return terminalize_deadline(runtime);
                }
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
                let retryable = policy.is_retryable(&err);
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
                    return terminalize_deadline(runtime);
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
                    trace_id = %submission.trace_id,
                    request_id = %submission.request_id,
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

fn timestamp_from_ms(ms: i128) -> Timestamp {
    Timestamp {
        seconds: (ms.div_euclid(1000)) as i64,
        nanos: ((ms.rem_euclid(1000)) * 1_000_000) as i32,
    }
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
        "artifact_refs": stage.artifact_refs,
        "lineage_refs": stage.lineage_refs,
        "handoff_ref": stage.handoff_ref,
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
        "input": stage
            .input
            .iter()
            .filter(|(key, _)| key.as_str() != "deadline_at_unix_ms")
            .map(|(key, value)| (key.clone(), value.clone()))
            .collect::<BTreeMap<_, _>>(),
        "output": stage.output,
        "artifact_refs": stage.artifact_refs,
        "lineage_refs": stage.lineage_refs,
        "handoff_ref": stage.handoff_ref,
        "error_code": stage.error_code,
        "error_summary": stage.error_summary,
        "error_details_ref": stage.error_details_ref,
    }))
    .unwrap_or_default()
}

fn reservation_token_for(submission: &NormalizedSubmission) -> String {
    hash_bytes_hex(
        format!("reservation:{}:{}", submission.job_id, submission.fingerprint).as_bytes(),
    )
}

fn canonical_reservation_token_for(submission: &NormalizedSubmission) -> String {
    let canonical_job_id = canonical_job_id_for_submission(submission);
    hash_bytes_hex(
        format!("reservation:{}:{}", canonical_job_id, submission.fingerprint).as_bytes(),
    )
}

fn reservation_lease_ms_for(submission: &NormalizedSubmission) -> u64 {
    parse_positive_usize(&submission.metadata_kvs, "reservation.lease_ms")
        .map(|v| v as u64)
        .unwrap_or(60_000)
}

fn compiler_deadline_seconds_for_submission(submission: &NormalizedSubmission) -> u64 {
    if let Some(seconds) = submission.deadline_seconds.filter(|seconds| *seconds > 0) {
        return seconds;
    }

    if let Some(deadline_at) = submission.deadline_at.as_ref() {
        let remaining_ms = timestamp_to_ms(deadline_at).saturating_sub(timestamp_to_ms(&ts_now()));
        if remaining_ms > 0 {
            return ((remaining_ms + 999) / 1000) as u64;
        }
    }

    ((reservation_lease_ms_for(submission) + 999) / 1000).max(1)
}

fn compiler_request_metadata_for_submission(submission: &NormalizedSubmission) -> RequestMetadata {
    let deadline_seconds = compiler_deadline_seconds_for_submission(submission);

    RequestMetadata {
        contract_version: submission.contract_version.clone(),
        request_id: submission.request_id.clone(),
        idempotency_key: submission.idempotency_key.clone(),
        traceparent: submission.traceparent.clone(),
        deadline: Some(ProtoDuration {
            seconds: deadline_seconds.min(i64::MAX as u64) as i64,
            nanos: 0,
        }),
        tenant_id: submission.tenant_id.clone(),
        project_id: submission.project_id.clone(),
        subject: submission.subject.clone(),
        role: submission.role.clone(),
        source_service: submission.source_service.clone(),
        trace_id: submission.trace_id.clone(),
        retry_policy: "retry-none".to_string(),
        security_context: "mTLS".to_string(),
        workload: Some(Default::default()),
    }
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

fn optimizer_trace_context_json(submission: &NormalizedSubmission) -> String {
    serde_json::to_string(&serde_json::json!({
        "request_id": submission.request_id.clone(),
        "trace_id": submission.trace_id.clone(),
        "traceparent": submission.traceparent.clone(),
    }))
    .unwrap_or_else(|_| "{}".to_string())
}

fn optimizer_objective_preset(submission: &NormalizedSubmission) -> String {
    submission
        .metadata_kvs
        .get("optimizer.objective")
        .cloned()
        .unwrap_or_else(|| "balanced".to_string())
}

fn optimizer_fallback_reason_from_code(code: &str) -> String {
    match code {
        "EIGEN_OPT_FEATURE_EXTRACTION_FAILED" => "feature_extraction_failed".to_string(),
        "EIGEN_OPT_MODEL_UNAVAILABLE" => "model_unavailable".to_string(),
        "EIGEN_OPT_TIMEOUT" => "timeout".to_string(),
        "EIGEN_OPT_INTERNAL" => "internal_error".to_string(),
        "EIGEN_OPT_CONFIDENCE_TOO_LOW" => "confidence_too_low".to_string(),
        "EIGEN_OPT_POLICY_REJECTED" => "policy_rejected".to_string(),
        "EIGEN_OPT_UNSUPPORTED_BACKEND" => "backend_unavailable".to_string(),
        _ => "none".to_string(),
    }
}

fn optimizer_score_breakdown_json(
    total_score: f64,
    latency_score: f64,
    fidelity_score: f64,
    resource_score: f64,
    risk_score: f64,
) -> String {
    serde_json::to_string(&serde_json::json!({
        "total_score": total_score,
        "latency_score": latency_score,
        "fidelity_score": fidelity_score,
        "resource_score": resource_score,
        "risk_score": risk_score,
    }))
    .unwrap_or_else(|_| "{}".to_string())
}

fn optimizer_topology_context_json(compile_output: &BTreeMap<String, String>, submission: &NormalizedSubmission) -> String {
    let topology_ref = compile_output
        .get("compiled_artifact_ref")
        .cloned()
        .unwrap_or_else(|| format!("qfs://jobs/{}/compiled/circuit.aqo.json", submission.job_id));
    let topology_digest = compile_output
        .get("compile_digest")
        .cloned()
        .unwrap_or_else(|| submission.program_hash.clone());
    serde_json::to_string(&serde_json::json!({
        "topology_ref": topology_ref,
        "topology_digest_sha256": topology_digest,
        "noise_snapshot_ref": "",
        "backend_profile": submission.target.clone(),
    }))
    .unwrap_or_else(|_| "{}".to_string())
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
    use std::fs;
    use std::sync::atomic::{AtomicU64, Ordering};

    static TEST_QFS_SEQ: AtomicU64 = AtomicU64::new(0);

    pub(crate) fn test_qfs_root(tag: &str) -> String {
        let seq = TEST_QFS_SEQ.fetch_add(1, Ordering::Relaxed);
        let mut root = std::env::temp_dir();
        root.push(format!(
            "eigen-kernel-test-qfs-{tag}-{}-{}-{seq}",
            std::process::id(),
            unix_epoch_ms_u64(),
        ));
        root.to_string_lossy().into_owned()
    }
    use crate::proto::RequestMetadata;
    use std::collections::{BTreeMap, BTreeSet};
    use prost_types::Duration as ProtoDuration;
    use tokio_stream::StreamExt;
    use tonic::Request;

    fn make_service(failure_stage: Option<DagStageKind>) -> (KernelGatewaySvc, Arc<KernelRuntimeStore>) {
        let runtime = Arc::new(KernelRuntimeStore::default());
        let adapters = Arc::new(FixtureAdapters::new(test_qfs_root("service"), failure_stage));
        let svc = KernelGatewaySvc::new(runtime.clone(), adapters);
        (svc, runtime)
    }

    fn make_service_with_hold(
         failure_stage: Option<DagStageKind>,
         hold_stage: Option<DagStageKind>,
         hold_for: Duration,
     ) -> (KernelGatewaySvc, Arc<KernelRuntimeStore>) {
         let runtime = Arc::new(KernelRuntimeStore::default());
         let adapters = Arc::new(FixtureAdapters::with_hold(
             test_qfs_root("hold"),
             failure_stage,
             hold_stage,
             hold_for,
         ));
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
                trace_id: "".to_string(),
                retry_policy: "".to_string(),
                security_context: "".to_string(),
                workload: Some(Default::default()),
                ..Default::default()
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

    fn make_distributed_request(name: &str) -> EnqueueJobRequest {
        let mut request = make_request(name);
        request.target = "cluster:auto".to_string();
        request.metadata_kvs.insert(
            "jobspec_workload".to_string(),
            serde_json::json!({
                "kind": "DistributedJob",
                "execution_profile": "distributed",
                "replayable": true,
                "topology": {
                    "cluster_id": "cluster:auto",
                    "partition_count": 2,
                    "partition_ids": ["partition-0", "partition-1"],
                    "preferred_workers": ["worker-a", "worker-b"],
                },
            })
            .to_string(),
        );
        request
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
                trace_id: "".to_string(),
                retry_policy: "".to_string(),
                security_context: "".to_string(),
                workload: Some(Default::default()),
                ..Default::default()
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
                    trace_id: "".to_string(),
                    retry_policy: "".to_string(),
                    security_context: "".to_string(),
                    workload: Some(Default::default()),
                    ..Default::default()
                }),
                job_id: response.job_id.clone(),
            }))
            .await
            .expect("results should succeed")
            .into_inner();
        assert_eq!(results.state, TaskState::Done as i32);
        assert!(!results.qfs_result_ref.is_empty());
        assert_eq!(job.metadata.get("result.summary.objective").map(String::as_str), Some("balanced"));
        assert!(!job.metadata.contains_key("result.summary.energy"));
    }

    #[test]
    fn result_summary_metadata_promotion_is_generic() {
        let mut summary = BTreeMap::from([("workload_kind".to_string(), "HybridWorkflow".to_string())]);
        let mut source = BTreeMap::new();
        source.insert("energy".to_string(), "-1.137270".to_string());
        source.insert("parameters".to_string(), "[0.121,-0.233,0.055,0.019]".to_string());
        source.insert("result.summary.objective".to_string(), "-1.137270".to_string());
        source.insert("message".to_string(), "ignored".to_string());
        source.insert("counts_ref".to_string(), "qfs://jobs/job-1/results/counts.json".to_string());

        merge_result_summary_fields(&mut summary, &source);

        assert_eq!(summary.get("energy").map(String::as_str), Some("-1.137270"));
        assert_eq!(summary.get("parameters").map(String::as_str), Some("[0.121,-0.233,0.055,0.019]"));
        assert_eq!(summary.get("objective").map(String::as_str), Some("-1.137270"));
        assert!(!summary.contains_key("message"));
        assert!(!summary.contains_key("counts_ref"));
    }

    #[tokio::test]
    async fn distributed_jobspec_metadata_is_projected_into_kernel_lineage() {
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_distributed_request("distributed")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let job = wait_for_terminal(runtime.clone(), &response.job_id).await;
        assert_eq!(job.state, TaskState::Done);
        assert_eq!(job.metadata.get("distributed.cluster_id").map(String::as_str), Some("cluster:auto"));
        assert_eq!(job.metadata.get("distributed.partition_count").map(String::as_str), Some("2"));
        assert_eq!(job.metadata.get("distributed.partition_ids").map(String::as_str), Some("[\"partition-0\",\"partition-1\"]"));
        assert_eq!(job.metadata.get("distributed.preferred_workers").map(String::as_str), Some("[\"worker-a\",\"worker-b\"]"));
        assert!(job.metadata.get("distributed.topology_digest_sha256").is_some());

        let validate_stage = job
            .stage_records
            .iter()
            .find(|stage| stage.stage_key == "validate-enqueue")
            .expect("validate stage should exist");
        assert_eq!(validate_stage.input.get("distributed.cluster_id").map(String::as_str), Some("cluster:auto"));
        assert_eq!(validate_stage.input.get("distributed.partition_count").map(String::as_str), Some("2"));
        assert_eq!(validate_stage.input.get("distributed.partition_ids").map(String::as_str), Some("[\"partition-0\",\"partition-1\"]"));
        assert_eq!(validate_stage.input.get("distributed.preferred_workers").map(String::as_str), Some("[\"worker-a\",\"worker-b\"]"));
        assert!(validate_stage.replay_token.len() >= 16);

        let status = svc
            .get_dispatch_rationale(Request::new(GetDispatchRationaleRequest {
                metadata: Some(RequestMetadata {
                    contract_version: "1.0.0".to_string(),
                    request_id: format!("dispatch-{}", response.job_id),
                    idempotency_key: format!("dispatch-{}", response.job_id),
                    traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                    deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                    tenant_id: "tenant-a".to_string(),
                    project_id: "project-a".to_string(),
                    subject: "alice".to_string(),
                    role: "user".to_string(),
                    source_service: "system-api".to_string(),
                    trace_id: "".to_string(),
                    retry_policy: "".to_string(),
                    security_context: "".to_string(),
                    workload: Some(Default::default()),
                    ..Default::default()
                }),
                job_id: response.job_id.clone(),
            }))
            .await
            .expect("dispatch rationale should succeed")
            .into_inner();
        let rationale = status.rationale.expect("rationale should exist");
        assert_eq!(rationale.attributes.get("distributed.cluster_id").map(String::as_str), Some("cluster:auto"));
        assert_eq!(rationale.attributes.get("distributed.partition_count").map(String::as_str), Some("2"));
    }

    #[tokio::test]
    async fn distributed_jobspec_topology_can_fall_back_to_jobspec_yaml() {
        let (svc, _) = make_service(None);

        let mut request = make_request("yaml-fallback");
        request.target = "cluster:auto".to_string();
        request.metadata_kvs.insert(
            "jobspec_yaml".to_string(),
            r#"apiVersion: eigen.os/v1
kind: QuantumJob
spec:
  target: cluster:auto
  workload:
    kind: DistributedJob
    execution_profile: distributed
    replayable: true
    topology:
      cluster_id: cluster:auto
      partition_count: 2
      partition_ids:
        - partition-0
        - partition-1
      preferred_workers:
        - worker-a
        - worker-b
"#
                .to_string(),
        );

        let response = svc
            .enqueue_job(Request::new(request))
            .await
            .expect("yaml fallback should succeed")
            .into_inner();

        assert!(response.job_id.starts_with("job-"));
    }

    #[tokio::test]
    async fn distributed_jobspec_topology_can_fall_back_to_request_workload() {
        let (svc, _) = make_service(None);

        let mut request = make_distributed_request("proto-fallback");
        request.metadata_kvs.insert(
            "jobspec_workload".to_string(),
            serde_json::json!({
                "kind": "DistributedJob",
                "execution_profile": "distributed",
                "replayable": true,
            })
            .to_string(),
        );
        request.metadata.as_mut().expect("metadata").workload = Some(WorkloadContract {
            kind: 3,
            execution_profile: "distributed".to_string(),
            replayable: true,
            topology: Some(WorkloadTopology {
                cluster_id: "cluster:auto".to_string(),
                partition_count: 2,
                partition_ids: vec!["partition-0".to_string(), "partition-1".to_string()],
                preferred_workers: vec!["worker-a".to_string(), "worker-b".to_string()],
            }),
            ..Default::default()
        });

        let response = svc
            .enqueue_job(Request::new(request))
            .await
            .expect("proto workload fallback should succeed")
            .into_inner();

        assert!(response.job_id.starts_with("job-"));
    }

    #[tokio::test]
    async fn distributed_jobspec_topology_can_fall_back_to_distributed_hints() {
        let (svc, _) = make_service(None);

        let mut request = make_request("distributed-hints");
        request.target = "cluster:auto".to_string();
        request.compiler_options.insert("distributed.partition_count".to_string(), "2".to_string());
        request.metadata_kvs.insert("cluster_id".to_string(), "cluster:auto".to_string());
        request.metadata_kvs.insert(
            "jobspec_workload".to_string(),
            serde_json::json!({
                "kind": "DistributedJob",
                "execution_profile": "distributed",
                "replayable": true,
            })
            .to_string(),
        );

        let response = svc
            .enqueue_job(Request::new(request))
            .await
            .expect("distributed hints fallback should succeed")
            .into_inner();

        assert!(response.job_id.starts_with("job-"));
    }

    #[tokio::test]
    async fn distributed_jobspec_missing_or_conflicting_topology_is_rejected() {
        let (svc, _) = make_service(None);

        let mut missing = make_request("missing-topology");
        missing.metadata_kvs.insert(
            "jobspec_workload".to_string(),
            serde_json::json!({
                "kind": "DistributedJob",
                "execution_profile": "distributed",
                "replayable": true,
            })
            .to_string(),
        );
        let err = svc.enqueue_job(Request::new(missing)).await.expect_err("missing topology should fail");
        assert_eq!(err.code(), Code::InvalidArgument);
        assert!(err.message().contains("spec.workload.topology"));

        let mut conflicting = make_request("conflicting-topology");
        conflicting.metadata_kvs.insert(
            "jobspec_workload".to_string(),
            serde_json::json!({
                "kind": "DistributedJob",
                "execution_profile": "distributed",
                "replayable": true,
                "topology": {
                    "cluster_id": "cluster:auto",
                    "partition_count": 2,
                    "partition_ids": ["partition-0"],
                    "preferred_workers": ["worker-a", "worker-b"],
                },
            })
            .to_string(),
        );
        let err = svc.enqueue_job(Request::new(conflicting)).await.expect_err("conflicting topology should fail");
        assert_eq!(err.code(), Code::InvalidArgument);
        assert!(err.message().contains("partition_ids"));
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
                    trace_id: "".to_string(),
                    retry_policy: "".to_string(),
                    security_context: "".to_string(),
                    workload: Some(Default::default()),
                    ..Default::default()
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
            test_qfs_root("retry"),
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
                trace_id: "".to_string(),
                retry_policy: "".to_string(),
                security_context: "".to_string(),
                workload: Some(Default::default()),
                ..Default::default()
            }),
            job_id: job_id.to_string(),
        }
    }

    #[tokio::test]
    async fn cancellation_while_queued_releases_reservation() {
        let (svc, runtime) = make_service_with_hold(None, Some(DagStageKind::Schedule), Duration::from_millis(80));
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
    }

    #[test]
    fn stale_reservation_is_swept_and_can_be_reacquired_with_same_token() {
        let runtime = KernelRuntimeStore::default();
        let submission = fixture_submission_with_lease_ms(1);
        let (job, _) = runtime.create_or_get_job(submission.clone()).expect("job");
        assert_eq!(job.reservation_state.as_deref(), Some("held"));

        {
            let mut jobs = runtime.jobs.write();
            let record = jobs.get_mut(&job.job_id).expect("job");
            record.updated_at = timestamp_from_ms(timestamp_to_ms(&ts_now()) - 10_000);
        }

        let released = runtime.sweep_stale_reservations();
        assert_eq!(released, vec![job.job_id.clone()]);
        let reacquired = runtime.acquire_live_reservation(&job.job_id).expect("reacquire");
        assert_eq!(reacquired.reservation_state.as_deref(), Some("held"));
        assert_eq!(reacquired.reservation_token, job.reservation_token);
    }

    #[test]
    fn duplicate_live_reservation_is_rejected_while_active() {
        let runtime = KernelRuntimeStore::default();
        let submission = fixture_submission_with_lease_ms(60_000);
        let (job, _) = runtime.create_or_get_job(submission).expect("job");

        let err = runtime.acquire_live_reservation(&job.job_id).expect_err("duplicate");
        assert_eq!(err.code(), Code::FailedPrecondition);
    }

    #[test]
    fn reservation_replay_token_is_deterministic_for_same_submission() {
        let runtime = KernelRuntimeStore::default();
        let submission = fixture_submission_with_lease_ms(60_000);
        let (job_a, _) = runtime.create_or_get_job(submission.clone()).expect("job a");
        let snapshot_a = runtime.get(&job_a.job_id).unwrap().snapshot_digest();

        let runtime2 = KernelRuntimeStore::default();
        let (job_b, _) = runtime2.create_or_get_job(submission).expect("job b");
        let snapshot_b = runtime2.get(&job_b.job_id).unwrap().snapshot_digest();

        assert_eq!(job_a.reservation_token, job_b.reservation_token);
        assert_eq!(snapshot_a, snapshot_b);
    }

    fn fixture_submission_with_lease_ms(lease_ms: u64) -> NormalizedSubmission {
        let mut metadata = BTreeMap::new();
        metadata.insert("contract_version".to_string(), "1.0.0".to_string());
        metadata.insert("request_id".to_string(), "req-live-ownership".to_string());
        metadata.insert("traceparent".to_string(), "00-11111111111111111111111111111111-2222222222222222-01".to_string());
        metadata.insert("tenant_id".to_string(), "tenant-a".to_string());
        metadata.insert("project_id".to_string(), "project-a".to_string());
        metadata.insert("reservation.lease_ms".to_string(), lease_ms.to_string());

        let mut metadata_kvs = HashMap::new();
        metadata_kvs.insert("reservation.lease_ms".to_string(), lease_ms.to_string());

        let req = EnqueueJobRequest {
            name: "reservation-test".to_string(),
            program: b"@quantum\ndef main(): pass".to_vec(),
            program_format: "eigen_lang_source".to_string(),
            target: "sim:local".to_string(),
            priority: 50,
            compiler_options: HashMap::new(),
            metadata_kvs,
            metadata: Some(RequestMetadata {
                contract_version: "1.0.0".to_string(),
                request_id: "req-live-ownership".to_string(),
                idempotency_key: "".to_string(),
                traceparent: "00-11111111111111111111111111111111-2222222222222222-01".to_string(),
                deadline: None,
                tenant_id: "tenant-a".to_string(),
                project_id: "project-a".to_string(),
                subject: "user".to_string(),
                role: "user".to_string(),
                source_service: "system-api".to_string(),
                trace_id: "".to_string(),
                retry_policy: "".to_string(),
                security_context: "".to_string(),
                workload: Some(Default::default()),
            }),
        };
        NormalizedSubmission::from_request(&req).expect("submission")
    }

    #[test]
    fn compiler_request_metadata_uses_safe_defaults_and_submission_context() {
        let submission = fixture_submission_with_lease_ms(45_000);
        let metadata = compiler_request_metadata_for_submission(&submission);

        assert_eq!(metadata.contract_version, "1.0.0");
        assert_eq!(metadata.request_id, "req-live-ownership");
        assert_eq!(metadata.idempotency_key, "req-live-ownership");
        assert_eq!(metadata.traceparent, "00-11111111111111111111111111111111-2222222222222222-01");
        assert_eq!(metadata.deadline.as_ref().map(|d| d.seconds), Some(45));
        assert_eq!(metadata.retry_policy, "retry-none");
        assert_eq!(metadata.security_context, "mTLS");
        assert_eq!(metadata.tenant_id, "tenant-a");
        assert_eq!(metadata.project_id, "project-a");
        assert!(metadata.workload.is_some());
    }

    #[test]
    fn optimizer_gateway_request_uses_bounded_defaults_and_canonical_graph_json() {
        let gateway = GrpcOptimizerGateway {
            endpoint: "http://127.0.0.1:50052".to_string(),
        };
        let submission = fixture_submission_with_lease_ms(60_000);
        let mut compile_output = BTreeMap::new();
        compile_output.insert("compile_digest".to_string(), "compile-digest-0001".to_string());
        compile_output.insert(
            "compiled_artifact_ref".to_string(),
            "qfs://jobs/job-1/compiled/circuit.aqo.json".to_string(),
        );

        let request = gateway.build_request(&submission, &compile_output);
        assert_eq!(request.candidate_budget, 1);
        assert_eq!(request.timeout_ms, 100);
        assert_eq!(request.trace_context.get("request_id"), Some(&submission.request_id));
        assert_eq!(request.trace_context.get("traceparent"), Some(&submission.traceparent));

        let graph_encoding = request.graph_encoding.expect("graph encoding");
        let graph_json: serde_json::Value = serde_json::from_str(&graph_encoding.canonical_graph_json)
            .expect("canonical graph json");
        assert_eq!(graph_json["canonical_graph_version"], "aqo-graph-v1");
        assert_eq!(graph_json["compile_digest"], "compile-digest-0001");
        assert_eq!(
            graph_json["compiled_artifact_ref"],
            "qfs://jobs/job-1/compiled/circuit.aqo.json"
        );
        assert_eq!(
            graph_encoding.canonical_sha256,
            hash_bytes_hex(graph_encoding.canonical_graph_json.as_bytes())
        );
    }

    #[tokio::test]
    async fn cancellation_while_compiling_is_deterministic() {
        let (svc, runtime) = make_service_with_hold(None, Some(DagStageKind::Compile), Duration::from_millis(80));
        let response = svc
            .enqueue_job(Request::new(make_request("compile-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Cancelled);
    }

    #[tokio::test]
    async fn cancellation_while_executing_is_deterministic() {
        let (svc, runtime) = make_service_with_hold(None, Some(DagStageKind::Execute), Duration::from_millis(80));
        let response = svc
            .enqueue_job(Request::new(make_request("execute-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Cancelled);
    }

    #[tokio::test]
    async fn cancellation_while_finalizing_keeps_canonical_terminal_state() {
        let (svc, runtime) = make_service_with_hold(None, Some(DagStageKind::Finalize), Duration::from_millis(80));
        let response = svc
            .enqueue_job(Request::new(make_request("finalize-cancel")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        tokio::time::sleep(Duration::from_millis(10)).await;
        let _ = svc.cancel_job(Request::new(make_cancel_request(&response.job_id))).await;
        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert!(matches!(job.state, TaskState::Cancelled | TaskState::Done));
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
                    trace_id: "".to_string(),
                    retry_policy: "".to_string(),
                    security_context: "".to_string(),
                    workload: Some(Default::default()),
                    ..Default::default()
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

    #[tokio::test]
    async fn dispatch_rationale_matches_completed_schedule_state() {
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("dispatch-rationale")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let job = wait_for_terminal(runtime, &response.job_id).await;
        assert_eq!(job.state, TaskState::Done);

        let rationale = svc
            .get_dispatch_rationale(Request::new(GetDispatchRationaleRequest {
                metadata: Some(RequestMetadata {
                    contract_version: "1.0.0".to_string(),
                    request_id: format!("rationale-{}", response.job_id),
                    idempotency_key: format!("rationale-{}", response.job_id),
                    traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                    deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                    tenant_id: "tenant-a".to_string(),
                    project_id: "project-a".to_string(),
                    subject: "alice".to_string(),
                    role: "user".to_string(),
                    source_service: "system-api".to_string(),
                    trace_id: "".to_string(),
                    retry_policy: "".to_string(),
                    security_context: "".to_string(),
                    workload: Some(Default::default()),
                }),
                job_id: response.job_id.clone(),
            }))
            .await
            .expect("dispatch rationale should succeed")
            .into_inner()
            .rationale
            .expect("rationale must be present");

        assert_eq!(rationale.version, "1.0.0");
        assert_eq!(rationale.policy_version, "balanced/1.0.0");
        assert_eq!(rationale.selected_backend, "sim:local");
        assert_eq!(rationale.selected_queue, "scheduler:default");
        assert_eq!(
            rationale.attributes.get("policy_bundle_id").map(String::as_str),
            Some("balanced")
        );
        assert_eq!(
            rationale.attributes.get("policy_bundle_version").map(String::as_str),
            Some("1.0.0")
        );
        assert!(rationale.attributes.contains_key("decision_input_digest"));
        assert!(rationale.attributes.contains_key("schedule_stage_id"));
    }

    #[tokio::test]
    async fn dispatch_rationale_is_stable_for_identical_inputs() {
        let (svc_a, runtime_a) = make_service(None);
        let (svc_b, runtime_b) = make_service(None);

        let response_a = svc_a
            .enqueue_job(Request::new(make_request("dispatch-rationale-stability")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let response_b = svc_b
            .enqueue_job(Request::new(make_request("dispatch-rationale-stability")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let _ = wait_for_terminal(runtime_a, &response_a.job_id).await;
        let _ = wait_for_terminal(runtime_b, &response_b.job_id).await;

        let rationale_a = svc_a
            .get_dispatch_rationale(Request::new(make_rationale_request(&response_a.job_id)))
            .await
            .expect("dispatch rationale a")
            .into_inner()
            .rationale
            .expect("rationale a");
        let rationale_b = svc_b
            .get_dispatch_rationale(Request::new(make_rationale_request(&response_b.job_id)))
            .await
            .expect("dispatch rationale b")
            .into_inner()
            .rationale
            .expect("rationale b");

        assert_eq!(rationale_a, rationale_b);
    }

    #[tokio::test]
    async fn dispatch_rationale_uses_bounded_metadata_only() {
        let (svc, runtime) = make_service(None);
        let response = svc
            .enqueue_job(Request::new(make_request("dispatch-rationale-bounded")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let _ = wait_for_terminal(runtime, &response.job_id).await;

        let rationale = svc
            .get_dispatch_rationale(Request::new(make_rationale_request(&response.job_id)))
            .await
            .expect("dispatch rationale should succeed")
            .into_inner()
            .rationale
            .expect("rationale");

        let allowed: BTreeSet<&str> = BTreeSet::from([
            "job_id",
            "stage_count",
            "schedule_stage_id",
            "schedule_stage_state",
            "scheduler_decision_version",
            "policy_bundle_id",
            "policy_bundle_version",
            "selected_backend",
            "selected_queue",
            "resource_plan_ref",
            "decision_input_digest",
            "snapshot_digest",
        ]);

        let keys: BTreeSet<&str> = rationale.attributes.keys().map(String::as_str).collect();
        assert_eq!(keys, allowed);
        assert!(!rationale.attributes.contains_key("traceparent"));
        assert!(!rationale.attributes.contains_key("subject"));
        assert!(!rationale.attributes.contains_key("request_id"));
        assert!(!rationale.attributes.contains_key("compiler_options"));
        assert!(!rationale.attributes.contains_key("metadata_kvs"));
    }


    #[tokio::test]
    async fn hybrid_workflow_graph_is_deterministic_for_identical_runs() {
        let (svc_a, runtime_a) = make_service(None);
        let (svc_b, runtime_b) = make_service(None);

        let response_a = svc_a
            .enqueue_job(Request::new(make_request("hybrid-replay")))
            .await
            .expect("enqueue should succeed")
            .into_inner();
        let response_b = svc_b
            .enqueue_job(Request::new(make_request("hybrid-replay")))
            .await
            .expect("enqueue should succeed")
            .into_inner();

        let job_a = wait_for_terminal(runtime_a, &response_a.job_id).await;
        let job_b = wait_for_terminal(runtime_b, &response_b.job_id).await;

        assert_eq!(job_a.workflow_id, job_b.workflow_id);
        assert_eq!(job_a.workflow_root_lineage_ref, job_b.workflow_root_lineage_ref);
        assert_eq!(job_a.snapshot_digest(), job_b.snapshot_digest());

        let graph_a = job_a.workflow_graph();
        let graph_b = job_b.workflow_graph();
        assert_eq!(graph_a.workflow_id, graph_b.workflow_id);
        assert_eq!(graph_a.job_id, graph_b.job_id);
        assert_eq!(graph_a.root_lineage_ref, graph_b.root_lineage_ref);
        assert_eq!(graph_a.stages, graph_b.stages);
        assert_eq!(graph_a.boundaries.len(), graph_b.boundaries.len());
        for (boundary_a, boundary_b) in graph_a.boundaries.iter().zip(graph_b.boundaries.iter()) {
            assert_eq!(boundary_a.boundary_id, boundary_b.boundary_id);
            assert_eq!(boundary_a.workflow_id, boundary_b.workflow_id);
            assert_eq!(boundary_a.job_id, boundary_b.job_id);
            assert_eq!(boundary_a.kind, boundary_b.kind);
            assert_eq!(boundary_a.stage_id, boundary_b.stage_id);
            assert_eq!(boundary_a.stage_key, boundary_b.stage_key);
            assert_eq!(boundary_a.order, boundary_b.order);
            assert_eq!(boundary_a.state_before, boundary_b.state_before);
            assert_eq!(boundary_a.state_after, boundary_b.state_after);
            assert_eq!(boundary_a.input_ref, boundary_b.input_ref);
            assert_eq!(boundary_a.output_ref, boundary_b.output_ref);
            assert_eq!(boundary_a.artifact_ref, boundary_b.artifact_ref);
            assert_eq!(boundary_a.lineage_ref, boundary_b.lineage_ref);
            assert_eq!(boundary_a.replay_token, boundary_b.replay_token);
        }
        assert!(graph_a.stages.len() >= 2);
        assert!(graph_a.final_completion_ref.as_deref().map(|value| !value.is_empty()).unwrap_or(false));
        assert!(graph_a.validate().is_ok());
    }

    #[tokio::test]
    async fn missing_handoff_refs_record_a_stage_level_failure() {
        let runtime = KernelRuntimeStore::default();
        let submission = NormalizedSubmission::from_request(&make_request("handoff-corruption"))
            .expect("submission should normalize");
        let job_id = submission.job_id.clone();
        let _ = runtime
            .create_or_get_job(submission)
            .expect("job should be created");

        let err = runtime
            .begin_stage(&job_id, DagStageKind::Compile, TaskState::Compiling, BTreeMap::new())
            .expect_err("compile should fail without required handoff refs");
        assert_eq!(err.code(), tonic::Code::FailedPrecondition);
        assert!(err.message().contains("missing required handoff refs"));

        let job = runtime.get(&job_id).expect("job should exist");
        assert_eq!(job.state, TaskState::Error);
        assert_eq!(job.error_code.as_deref(), Some("WORKFLOW_HANDOFF_CORRUPTION"));
        assert!(job.workflow_failure_ref.as_deref().map(|value| !value.is_empty()).unwrap_or(false));

        let stage = job.stage_records.last().expect("stage record should be present");
        assert_eq!(stage.stage_key, DagStageKind::Compile.key());
        assert_eq!(stage.status, StageStatus::Failed);
        assert_eq!(stage.error_code.as_deref(), Some("WORKFLOW_HANDOFF_CORRUPTION"));
        assert!(stage.output.contains_key("workflow_failure_ref"));
        assert!(stage.artifact_refs.contains_key("workflow_handoff_ref"));
        assert!(stage.artifact_refs.contains_key("workflow_lineage_ref"));

        let graph = job.workflow_graph();
        assert!(graph.final_failure_ref.as_deref().map(|value| !value.is_empty()).unwrap_or(false));
        assert!(graph.boundaries.iter().any(|boundary| matches!(boundary.kind, WorkflowBoundaryKind::StageFailed)));
        assert!(graph.validate().is_ok());
    }

    fn make_rationale_request(job_id: &str) -> GetDispatchRationaleRequest {
        GetDispatchRationaleRequest {
            metadata: Some(RequestMetadata {
                contract_version: "1.0.0".to_string(),
                request_id: format!("rationale-{job_id}"),
                idempotency_key: format!("rationale-{job_id}"),
                traceparent: "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01".to_string(),
                deadline: Some(ProtoDuration { seconds: 30, nanos: 0 }),
                tenant_id: "tenant-a".to_string(),
                project_id: "project-a".to_string(),
                subject: "alice".to_string(),
                role: "user".to_string(),
                source_service: "system-api".to_string(),
                trace_id: "".to_string(),
                retry_policy: "".to_string(),
                security_context: "".to_string(),
                workload: Some(Default::default()),
            }),
            job_id: job_id.to_string(),
        }
    }
}

fn unix_epoch_ms_u64() -> u64 {
    SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or_default()
}

fn workload_kind_label(submission: &NormalizedSubmission) -> String {
    let raw = submission
        .metadata_kvs
        .get("workload_kind")
        .cloned()
        .or_else(|| submission.metadata_kvs.get("kind").cloned())
        .or_else(|| submission.metadata_kvs.get("execution_profile").cloned())
        .unwrap_or_else(|| "HybridWorkflow".to_string());

    match raw.as_str() {
        "hybrid" | "HybridWorkflow" => "HybridWorkflow".to_string(),
        "benchmark" | "BenchmarkJob" => "BenchmarkJob".to_string(),
        "distributed" | "DistributedJob" => "DistributedJob".to_string(),
        "pipeline" | "PipelineJob" => "PipelineJob".to_string(),
        "replay" | "ReplayJob" => "ReplayJob".to_string(),
        other => other.to_string(),
    }
}

fn scientific_measurements(
    submission: &NormalizedSubmission,
    execution_output: &ExecutionOutcome,
    stage_records: &[StageRecord],
    selected_backend: &str,
    workload_kind: &str,
    execution_time_sec: f64,
) -> Vec<ScientificMeasurement> {
    let mut measurements = Vec::new();
    let trace_id = submission.trace_id.clone();
    let traceparent = submission.traceparent.clone();
    let created_at_marker = unix_epoch_ms_u64().to_string();

    measurements.push(ScientificMeasurement {
        metric_name: "execution_time_sec".to_string(),
        metric_kind: "summary".to_string(),
        metric_value: format!("{execution_time_sec:.6}"),
        metric_unit: "s".to_string(),
        stage_id: None,
        stage_key: None,
        step_index: Some(0),
        trial_index: Some(0),
        seed: submission.metadata_kvs.get("seed").and_then(|value| value.parse::<i64>().ok()),
        backend: Some(selected_backend.to_string()),
        target: Some(submission.target.clone()),
        trace_id: Some(trace_id.clone()),
        traceparent: Some(traceparent.clone()),
        artifact_ref: Some(format!("qfs://jobs/{}/execution/execution.json", submission.job_id)),
        attributes: BTreeMap::from([
            ("workload_kind".to_string(), workload_kind.to_string()),
            ("kind".to_string(), "execution_summary".to_string()),
            ("observed_at_epoch_ms".to_string(), created_at_marker.clone()),
        ]),
    });

    measurements.push(ScientificMeasurement {
        metric_name: "total_shots".to_string(),
        metric_kind: "summary".to_string(),
        metric_value: execution_output.counts.values().copied().sum::<i64>().to_string(),
        metric_unit: "shots".to_string(),
        stage_id: None,
        stage_key: None,
        step_index: Some(0),
        trial_index: Some(0),
        seed: submission.metadata_kvs.get("seed").and_then(|value| value.parse::<i64>().ok()),
        backend: Some(selected_backend.to_string()),
        target: Some(submission.target.clone()),
        trace_id: Some(trace_id.clone()),
        traceparent: Some(traceparent.clone()),
        artifact_ref: Some(format!("qfs://jobs/{}/results/counts.json", submission.job_id)),
        attributes: BTreeMap::from([
            ("workload_kind".to_string(), workload_kind.to_string()),
            ("kind".to_string(), "execution_counts".to_string()),
            ("observed_at_epoch_ms".to_string(), created_at_marker.clone()),
        ]),
    });

    for (bitstring, count) in &execution_output.counts {
        measurements.push(ScientificMeasurement {
            metric_name: "shot_count".to_string(),
            metric_kind: "measurement".to_string(),
            metric_value: count.to_string(),
            metric_unit: "shots".to_string(),
            stage_id: Some("execute".to_string()),
            stage_key: Some("execute".to_string()),
            step_index: Some(5),
            trial_index: Some(0),
            seed: submission.metadata_kvs.get("seed").and_then(|value| value.parse::<i64>().ok()),
            backend: Some(selected_backend.to_string()),
            target: Some(submission.target.clone()),
            trace_id: Some(trace_id.clone()),
            traceparent: Some(traceparent.clone()),
            artifact_ref: Some(format!("qfs://jobs/{}/results/counts.json", submission.job_id)),
            attributes: BTreeMap::from([
                ("bitstring".to_string(), bitstring.clone()),
                ("workload_kind".to_string(), workload_kind.to_string()),
                ("kind".to_string(), "bitstring_count".to_string()),
                ("observed_at_epoch_ms".to_string(), created_at_marker.clone()),
            ]),
        });
    }

    for stage in stage_records {
        if let Some(completed_at) = stage.completed_at.as_ref() {
            let duration_ms = (timestamp_to_ms(completed_at) - timestamp_to_ms(&stage.started_at)).max(0) as i64;
            measurements.push(ScientificMeasurement {
                metric_name: "stage_duration_ms".to_string(),
                metric_kind: "stage".to_string(),
                metric_value: duration_ms.to_string(),
                metric_unit: "ms".to_string(),
                stage_id: Some(stage.stage_id.clone()),
                stage_key: Some(stage.stage_key.clone()),
                step_index: Some(stage.order as i64),
                trial_index: Some(0),
                seed: submission.metadata_kvs.get("seed").and_then(|value| value.parse::<i64>().ok()),
                backend: Some(selected_backend.to_string()),
                target: Some(submission.target.clone()),
                trace_id: Some(trace_id.clone()),
                traceparent: Some(traceparent.clone()),
                artifact_ref: Some(format!("qfs://jobs/{}/timeline.jsonl", submission.job_id)),
                attributes: BTreeMap::from([
                    ("status".to_string(), match stage.status {
                        StageStatus::Running => "running".to_string(),
                        StageStatus::Succeeded => "succeeded".to_string(),
                        StageStatus::Failed => "failed".to_string(),
                    }),
                    ("workload_kind".to_string(), workload_kind.to_string()),
                    ("kind".to_string(), "stage_timing".to_string()),
                    ("observed_at_epoch_ms".to_string(), created_at_marker.clone()),
                ]),
            });
        }
    }

    measurements.sort_by(|left, right| {
        (
            left.metric_kind.as_str(),
            left.metric_name.as_str(),
            left.stage_key.as_deref().unwrap_or(""),
            left.step_index.unwrap_or_default(),
            left.metric_value.as_str(),
        )
            .cmp(&(
                right.metric_kind.as_str(),
                right.metric_name.as_str(),
                right.stage_key.as_deref().unwrap_or(""),
                right.step_index.unwrap_or_default(),
                right.metric_value.as_str(),
            ))
    });

    measurements
}

    #[test]
    fn merge_result_summary_artifact_promotes_nested_json_leafs() {
        let qfs_root = tests::test_qfs_root("summary-artifact");
        let qfs = CircuitFsLocal::new(&qfs_root);
        let artifact_ref = "qfs://jobs/job-test/workflow/stages/03-optimize-output.json";
        let payload = serde_json::json!({
            "energy": -1.2345,
            "parameters": [0.10, -0.20, 0.05, 0.02],
            "summary": {
                "objective": "balanced",
                "confidence": 0.92
            }
        });
        qfs.write_bytes(
            artifact_ref,
            &serde_json::to_vec_pretty(&payload).expect("json serialization should succeed"),
        )
        .expect("workflow artifact should be persisted");

        let mut summary = BTreeMap::new();
        merge_result_summary_artifact(&qfs, &mut summary, artifact_ref);

        assert_eq!(summary.get("energy").map(String::as_str), Some("-1.2345"));
        assert_eq!(summary.get("parameters").map(String::as_str), Some("[0.1,-0.2,0.05,0.02]"));
        assert_eq!(summary.get("objective").map(String::as_str), Some("balanced"));
        assert_eq!(summary.get("confidence").map(String::as_str), Some("0.92"));
    }

