//! Resource manager scheduler core (Phase-2 baseline).
//!
//! This module implements Scheduler Core v2 with:
//! - configurable admission control with per-tenant and per-project quotas
//! - weighted fairness dispatch across tenants/projects
//! - starvation prevention guardrails
//! - observable scheduler decisions and health/metrics snapshots

#![forbid(unsafe_code)]

use std::cmp::Ordering;
use std::collections::{BTreeMap, HashMap, VecDeque};

/// SemVer version for scheduler decision DTOs/contracts.
///
/// Any breaking change to queue semantics, quota semantics,
/// dispatch reason codes, or dispatch contracts must bump MAJOR.
pub const SCHEDULER_DECISION_VERSION: &str = "2.1.0";
/// SemVer version for device score DTOs/contracts.
pub const DEVICE_SCORE_VERSION: &str = "2.1.0";
/// SemVer version for backend scoring contract artifacts (Phase-4 intelligent runtime).
pub const BACKEND_SCORING_CONTRACT_VERSION: &str = "1.0.0";
/// SemVer schema version for persisted backend scoring profiles.
pub const BACKEND_SCORING_PROFILE_SCHEMA_VERSION: &str = "1.0.0";
/// SemVer schema version for backend-selection explain API request DTO.
pub const BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION: &str = "1.0.0";
/// SemVer schema version for backend-selection explain API response envelope.
pub const BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION: &str = "1.0.0";
/// SemVer schema version for scheduling policy bundles (Phase-4 policy engine).
pub const SCHEDULING_POLICY_BUNDLE_SCHEMA_VERSION: &str = "1.0.0";
/// SemVer version for scheduling policy-resolution decision artifacts.
pub const SCHEDULING_POLICY_RESOLUTION_VERSION: &str = "1.1.0";
/// SemVer version for rebalancing/preemption safety artifacts.
pub const REBALANCING_POLICY_VERSION: &str = "2.2.0";
/// SemVer version for multi-device split/merge execution contract artifacts.
///
/// Breaking changes to partial-result envelopes or merge semantics must bump MAJOR.
pub const MULTI_DEVICE_EXECUTION_CONTRACT_VERSION: &str = "2.0.0";
/// SemVer version for Phase-5 cluster runtime control-plane artifacts.
///
/// Breaking changes to assignment semantics or lineage field meaning must bump MAJOR.
pub const CLUSTER_CONTROL_PLANE_CONTRACT_VERSION: &str = "1.0.0";
/// SemVer version for cluster assignment lineage metadata envelopes.
pub const CLUSTER_ASSIGNMENT_LINEAGE_VERSION: &str = "1.0.0";
/// SemVer version for worker-node remote execution lifecycle contract artifacts.
pub const WORKER_NODE_EXECUTION_CONTRACT_VERSION: &str = "1.0.0";
/// SemVer version for runtime artifact staging/materialization metadata.
pub const WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION: &str = "1.0.0";
/// SemVer version for provider-neutral distributed queue envelope contract.
pub const DISTRIBUTED_QUEUE_CONTRACT_VERSION: &str = "1.0.1";
/// SemVer version for queue lease lifecycle event records.
pub const QUEUE_LEASE_EVENT_VERSION: &str = "1.0.1";
/// SemVer version for queue dead-letter records.
pub const QUEUE_DEAD_LETTER_CONTRACT_VERSION: &str = "1.0.1";

/// Runtime mode for control-plane bootstrap.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClusterRuntimeMode {
    SingleNode,
    Cluster,
}

/// Worker lifecycle state in cluster control plane.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClusterWorkerState {
    Ready,
    Degraded,
    Draining,
    Offline,
}

/// Worker registration and capability handshake record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClusterWorkerRegistration {
    pub worker_id: String,
    pub state: ClusterWorkerState,
    pub capability_tags: Vec<String>,
    pub max_parallel_tasks: u32,
    pub current_load: u32,
}

/// Control-plane bootstrap input for `--cluster` mode.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClusterBootstrapInput {
    pub cluster_id: String,
    pub control_plane_node_id: String,
    pub runtime_mode: ClusterRuntimeMode,
}

/// Deterministic worker discovery output during bootstrap.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClusterBootstrapArtifact {
    pub cluster_contract_version: &'static str,
    pub cluster_id: String,
    pub control_plane_node_id: String,
    pub runtime_mode: ClusterRuntimeMode,
    pub discovered_worker_ids: Vec<String>,
}

/// Stable lineage metadata for assignment artifacts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClusterAssignmentLineage {
    pub lineage_version: &'static str,
    pub cluster_id: String,
    pub assignment_id: String,
    pub assignment_sequence: u64,
    pub assignment_epoch_ms: u64,
}

/// Deterministic assignment output consumed by queue/worker runtimes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClusterAssignmentArtifact {
    pub cluster_contract_version: &'static str,
    pub assignment_id: String,
    pub job_id: String,
    pub candidate_workers: Vec<String>,
    pub selected_worker_id: String,
    pub assignment_trace: Vec<String>,
    pub lineage: ClusterAssignmentLineage,
    pub fallback_applied: bool,
    pub fallback_reason: Option<String>,
}

/// Cluster control-plane validation and assignment errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ClusterControlPlaneError {
    EmptyClusterId,
    EmptyControlPlaneNodeId,
    EmptyJobId,
    NoWorkersRegistered,
    NoEligibleWorkers,
}

/// Runtime artifact descriptor passed to worker for materialization.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerRuntimeArtifactRef {
    pub artifact_id: String,
    pub uri: String,
    pub checksum: String,
}

/// Materialized artifact record persisted for debuggable execution replay.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerRuntimeArtifactMaterialization {
    pub artifact_contract_version: &'static str,
    pub artifact_id: String,
    pub uri: String,
    pub checksum: String,
    pub materialized_at_ms: u64,
}

/// Worker lifecycle state for a remote execution.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WorkerExecutionState {
    Running,
    Completed,
    Cancelled,
    TimedOut,
}

/// Worker start request (remote execution contract).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerExecutionStartRequest {
    pub assignment_id: String,
    pub worker_id: String,
    pub lease_id: String,
    pub idempotency_key: String,
    pub runtime_artifacts: Vec<WorkerRuntimeArtifactRef>,
}

/// Worker execution heartbeat payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerExecutionHeartbeat {
    pub execution_id: String,
    pub lease_id: String,
}

/// Worker completion payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerExecutionCompleteRequest {
    pub execution_id: String,
    pub lease_id: String,
    pub output_ref: String,
}

/// Worker cancellation payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerExecutionCancelRequest {
    pub execution_id: String,
    pub reason: String,
}

/// Execution record persisted by worker-node service.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerExecutionRecord {
    pub worker_contract_version: &'static str,
    pub execution_id: String,
    pub assignment_id: String,
    pub worker_id: String,
    pub lease_id: String,
    pub idempotency_key: String,
    pub state: WorkerExecutionState,
    pub started_at_ms: u64,
    pub last_heartbeat_ms: u64,
    pub completed_at_ms: Option<u64>,
    pub output_ref: Option<String>,
    pub cancellation_intent: Option<String>,
    pub materialized_artifacts: Vec<WorkerRuntimeArtifactMaterialization>,
}

/// Start result including idempotent replay marker.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WorkerExecutionStartResult {
    pub execution: WorkerExecutionRecord,
    pub idempotent_replay: bool,
}

/// Worker-node lifecycle API errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkerExecutionError {
    EmptyAssignmentId,
    EmptyWorkerId,
    EmptyLeaseId,
    EmptyIdempotencyKey,
    UnknownExecutionId,
    IdempotencyConflict,
    LeaseMismatch,
    NotRunning,
}

/// Queue task envelope shared across queue adapter implementations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueueTaskEnvelope {
    pub queue_contract_version: &'static str,
    pub queue_name: String,
    pub task_id: String,
    pub job_id: String,
    pub assignment_id: String,
    pub idempotency_key: String,
    pub tenant_id: String,
    pub project_id: String,
    pub attempt: u32,
    pub max_attempts: u32,
    pub visibility_timeout_seconds: u32,
    pub enqueued_at_ms: u64,
}

/// Lease acquisition record returned to workers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueueLeaseRecord {
    pub lease_event_version: &'static str,
    pub lease_id: String,
    pub queue_name: String,
    pub task_id: String,
    pub job_id: String,
    pub assignment_id: String,
    pub idempotency_key: String,
    pub worker_id: String,
    pub attempt: u32,
    pub leased_at_ms: u64,
    pub lease_expires_at_ms: u64,
}

/// Dead-letter artifact for tasks that exceed retry budget.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeadLetterRecord {
    pub dead_letter_version: &'static str,
    pub queue_name: String,
    pub task_id: String,
    pub job_id: String,
    pub assignment_id: String,
    pub idempotency_key: String,
    pub attempt: u32,
    pub max_attempts: u32,
    pub reason: String,
    pub dead_lettered_at_ms: u64,
}

/// Queue adapter metrics for observability assertions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct QueueAdapterMetrics {
    pub queue_enqueued_total: u64,
    pub queue_lease_acquired_total: u64,
    pub queue_redelivery_total: u64,
    pub queue_dead_letter_total: u64,
}

/// Queue adapter validation and runtime errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum QueueAdapterError {
    EmptyQueueName,
    EmptyTaskId,
    EmptyJobId,
    EmptyAssignmentId,
    EmptyIdempotencyKey,
    EmptyWorkerId,
    DuplicateTaskId,
    UnknownLeaseId,
    LeaseNotOwnedByWorker,
    InvalidVisibilityTimeout,
    InvalidAttempts,
}

/// Provider-neutral queue interface for pluggable delivery backends.
pub trait QueueAdapter {
    fn enqueue(&mut self, task: QueueTaskEnvelope) -> Result<(), QueueAdapterError>;
    fn lease(
        &mut self,
        queue_name: &str,
        worker_id: &str,
        now_ms: u64,
    ) -> Result<Option<QueueLeaseRecord>, QueueAdapterError>;
    fn ack(&mut self, lease_id: &str, worker_id: &str, now_ms: u64) -> Result<bool, QueueAdapterError>;
    fn requeue(
        &mut self,
        lease_id: &str,
        worker_id: &str,
        reason: &str,
        now_ms: u64,
    ) -> Result<bool, QueueAdapterError>;
    fn metrics(&self) -> QueueAdapterMetrics;
    fn dead_letters(&self) -> &[DeadLetterRecord];
}

#[derive(Debug, Clone)]
struct InFlightLease {
    task: QueueTaskEnvelope,
    lease: QueueLeaseRecord,
}

/// Deterministic in-memory queue adapter implementing v1 delivery semantics.
#[derive(Debug, Default, Clone)]
pub struct InMemoryQueueAdapter {
    sequence: u64,
    queues: BTreeMap<String, VecDeque<QueueTaskEnvelope>>,
    in_flight: HashMap<String, InFlightLease>,
    metrics: QueueAdapterMetrics,
    dead_letters: Vec<DeadLetterRecord>,
}

impl InMemoryQueueAdapter {
    pub fn new() -> Self {
        Self::default()
    }

    fn validate_task(task: &QueueTaskEnvelope) -> Result<(), QueueAdapterError> {
        if task.queue_name.trim().is_empty() {
            return Err(QueueAdapterError::EmptyQueueName);
        }
        if task.task_id.trim().is_empty() {
            return Err(QueueAdapterError::EmptyTaskId);
        }
        if task.job_id.trim().is_empty() {
            return Err(QueueAdapterError::EmptyJobId);
        }
        if task.assignment_id.trim().is_empty() {
            return Err(QueueAdapterError::EmptyAssignmentId);
        }
        if task.idempotency_key.trim().is_empty() {
            return Err(QueueAdapterError::EmptyIdempotencyKey);
        }
        if task.max_attempts == 0 || task.attempt == 0 || task.attempt > task.max_attempts {
            return Err(QueueAdapterError::InvalidAttempts);
        }
        if task.visibility_timeout_seconds == 0 {
            return Err(QueueAdapterError::InvalidVisibilityTimeout);
        }
        Ok(())
    }

    fn lease_expiry_ms(task: &QueueTaskEnvelope, leased_at_ms: u64) -> u64 {
        leased_at_ms.saturating_add(u64::from(task.visibility_timeout_seconds).saturating_mul(1_000))
    }

    fn queue_or_dead_letter(&mut self, task: QueueTaskEnvelope, reason: &str, now_ms: u64) {
        if task.attempt >= task.max_attempts {
            self.metrics.queue_dead_letter_total += 1;
            self.dead_letters.push(DeadLetterRecord {
                dead_letter_version: QUEUE_DEAD_LETTER_CONTRACT_VERSION,
                queue_name: task.queue_name.clone(),
                task_id: task.task_id,
                job_id: task.job_id,
                assignment_id: task.assignment_id,
                idempotency_key: task.idempotency_key,
                attempt: task.attempt,
                max_attempts: task.max_attempts,
                reason: reason.trim().to_string(),
                dead_lettered_at_ms: now_ms,
            });
            return;
        }

        let mut redelivery = task;
        redelivery.attempt += 1;
        self.metrics.queue_redelivery_total += 1;
        self.queues
            .entry(redelivery.queue_name.clone())
            .or_default()
            .push_back(redelivery);
    }

    fn sweep_expired_leases(&mut self, now_ms: u64) {
        let mut expired_ids: Vec<(String, u64)> = self
            .in_flight
            .iter()
            .filter_map(|(lease_id, lease)| {
                if now_ms >= lease.lease.lease_expires_at_ms {
                    Some((lease_id.clone(), lease.lease.lease_expires_at_ms))
                } else {
                    None
                }
            })
            .collect();
        expired_ids.sort_by(|(left_id, left_expiry), (right_id, right_expiry)| {
            left_expiry.cmp(right_expiry).then_with(|| left_id.cmp(right_id))
        });

        for (lease_id, _) in expired_ids {
            let lease = self
                .in_flight
                .remove(&lease_id)
                .expect("expired lease id must exist");
            self.queue_or_dead_letter(lease.task, "lease-expired", now_ms);
        }
    }
}

impl QueueAdapter for InMemoryQueueAdapter {
    fn enqueue(&mut self, task: QueueTaskEnvelope) -> Result<(), QueueAdapterError> {
        Self::validate_task(&task)?;

        let queue_name = task.queue_name.clone();
        let task_id = task.task_id.clone();
        let duplicate_in_queue = self
            .queues
            .get(&queue_name)
            .is_some_and(|q| q.iter().any(|existing| existing.task_id == task_id));
        let duplicate_in_flight = self
            .in_flight
            .values()
            .any(|lease| lease.task.task_id == task_id && lease.task.queue_name == queue_name);
        if duplicate_in_queue || duplicate_in_flight {
            return Err(QueueAdapterError::DuplicateTaskId);
        }

        self.metrics.queue_enqueued_total += 1;
        self.queues.entry(queue_name).or_default().push_back(task);
        Ok(())
    }

    fn lease(
        &mut self,
        queue_name: &str,
        worker_id: &str,
        now_ms: u64,
    ) -> Result<Option<QueueLeaseRecord>, QueueAdapterError> {
        if queue_name.trim().is_empty() {
            return Err(QueueAdapterError::EmptyQueueName);
        }
        if worker_id.trim().is_empty() {
            return Err(QueueAdapterError::EmptyWorkerId);
        }

        self.sweep_expired_leases(now_ms);

        let queue_key = queue_name.trim().to_string();
        let (task, queue_became_empty) = {
            let queue = self.queues.entry(queue_key.clone()).or_default();
            let Some(task) = queue.pop_front() else {
                return Ok(None);
            };
            (task, queue.is_empty())
        };
        if queue_became_empty {
            self.queues.remove(&queue_key);
        }

        self.sequence += 1;
        let lease_id = format!("lease-{:08}", self.sequence);
        let lease = QueueLeaseRecord {
            lease_event_version: QUEUE_LEASE_EVENT_VERSION,
            lease_id: lease_id.clone(),
            queue_name: task.queue_name.clone(),
            task_id: task.task_id.clone(),
            job_id: task.job_id.clone(),
            assignment_id: task.assignment_id.clone(),
            idempotency_key: task.idempotency_key.clone(),
            worker_id: worker_id.trim().to_string(),
            attempt: task.attempt,
            leased_at_ms: now_ms,
            lease_expires_at_ms: Self::lease_expiry_ms(&task, now_ms),
        };

        self.in_flight.insert(
            lease_id,
            InFlightLease {
                task,
                lease: lease.clone(),
            },
        );
        self.metrics.queue_lease_acquired_total += 1;
        Ok(Some(lease))
    }

    fn ack(&mut self, lease_id: &str, worker_id: &str, now_ms: u64) -> Result<bool, QueueAdapterError> {
        if worker_id.trim().is_empty() {
            return Err(QueueAdapterError::EmptyWorkerId);
        }
        self.sweep_expired_leases(now_ms);
        let Some(lease) = self.in_flight.get(lease_id) else {
            return Ok(false);
        };
        if lease.lease.worker_id != worker_id.trim() {
            return Err(QueueAdapterError::LeaseNotOwnedByWorker);
        }
        self.in_flight.remove(lease_id);
        Ok(true)
    }

    fn requeue(
        &mut self,
        lease_id: &str,
        worker_id: &str,
        reason: &str,
        now_ms: u64,
    ) -> Result<bool, QueueAdapterError> {
        if worker_id.trim().is_empty() {
            return Err(QueueAdapterError::EmptyWorkerId);
        }
        self.sweep_expired_leases(now_ms);
        let Some(lease) = self.in_flight.remove(lease_id) else {
            return Ok(false);
        };
        if lease.lease.worker_id != worker_id.trim() {
            self.in_flight.insert(lease_id.to_string(), lease);
            return Err(QueueAdapterError::LeaseNotOwnedByWorker);
        }
        self.queue_or_dead_letter(lease.task, reason, now_ms);
        Ok(true)
    }

    fn metrics(&self) -> QueueAdapterMetrics {
        self.metrics
    }

    fn dead_letters(&self) -> &[DeadLetterRecord] {
        &self.dead_letters
    }
}

/// In-memory worker-node service implementing deterministic remote-execution lifecycle.
#[derive(Debug, Clone)]
pub struct WorkerNodeService {
    heartbeat_timeout_ms: u64,
    sequence: u64,
    executions: HashMap<String, WorkerExecutionRecord>,
    idempotency_index: HashMap<String, String>,
}

impl WorkerNodeService {
    pub fn new(heartbeat_timeout_ms: u64) -> Self {
        Self {
            heartbeat_timeout_ms: heartbeat_timeout_ms.max(1),
            sequence: 0,
            executions: HashMap::new(),
            idempotency_index: HashMap::new(),
        }
    }

    pub fn start(
        &mut self,
        request: WorkerExecutionStartRequest,
        now_ms: u64,
    ) -> Result<WorkerExecutionStartResult, WorkerExecutionError> {
        if request.assignment_id.trim().is_empty() {
            return Err(WorkerExecutionError::EmptyAssignmentId);
        }
        if request.worker_id.trim().is_empty() {
            return Err(WorkerExecutionError::EmptyWorkerId);
        }
        if request.lease_id.trim().is_empty() {
            return Err(WorkerExecutionError::EmptyLeaseId);
        }
        if request.idempotency_key.trim().is_empty() {
            return Err(WorkerExecutionError::EmptyIdempotencyKey);
        }

        if let Some(existing_execution_id) = self.idempotency_index.get(request.idempotency_key.as_str()) {
            let existing = self
                .executions
                .get(existing_execution_id)
                .expect("idempotency index must reference existing execution");
            if existing.assignment_id != request.assignment_id || existing.worker_id != request.worker_id {
                return Err(WorkerExecutionError::IdempotencyConflict);
            }
            return Ok(WorkerExecutionStartResult {
                execution: existing.clone(),
                idempotent_replay: true,
            });
        }

        self.sequence += 1;
        let execution_id = format!("{}-exec-{:06}", request.assignment_id.trim(), self.sequence);
        let mut artifacts = request.runtime_artifacts;
        artifacts.sort_by(|left, right| {
            left.uri
                .cmp(&right.uri)
                .then_with(|| left.artifact_id.cmp(&right.artifact_id))
        });
        artifacts.dedup_by(|left, right| left.artifact_id == right.artifact_id && left.uri == right.uri);
        let materialized_artifacts = artifacts
            .into_iter()
            .map(|artifact| WorkerRuntimeArtifactMaterialization {
                artifact_contract_version: WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION,
                artifact_id: artifact.artifact_id.trim().to_string(),
                uri: artifact.uri.trim().to_string(),
                checksum: artifact.checksum.trim().to_string(),
                materialized_at_ms: now_ms,
            })
            .collect();

        let execution = WorkerExecutionRecord {
            worker_contract_version: WORKER_NODE_EXECUTION_CONTRACT_VERSION,
            execution_id: execution_id.clone(),
            assignment_id: request.assignment_id.trim().to_string(),
            worker_id: request.worker_id.trim().to_string(),
            lease_id: request.lease_id.trim().to_string(),
            idempotency_key: request.idempotency_key.trim().to_string(),
            state: WorkerExecutionState::Running,
            started_at_ms: now_ms,
            last_heartbeat_ms: now_ms,
            completed_at_ms: None,
            output_ref: None,
            cancellation_intent: None,
            materialized_artifacts,
        };

        self.idempotency_index
            .insert(execution.idempotency_key.clone(), execution_id.clone());
        self.executions.insert(execution_id, execution.clone());

        Ok(WorkerExecutionStartResult {
            execution,
            idempotent_replay: false,
        })
    }

    pub fn heartbeat(
        &mut self,
        request: WorkerExecutionHeartbeat,
        now_ms: u64,
    ) -> Result<WorkerExecutionRecord, WorkerExecutionError> {
        let execution = self
            .executions
            .get_mut(request.execution_id.as_str())
            .ok_or(WorkerExecutionError::UnknownExecutionId)?;
        if execution.lease_id != request.lease_id {
            return Err(WorkerExecutionError::LeaseMismatch);
        }
        if execution.state != WorkerExecutionState::Running {
            return Err(WorkerExecutionError::NotRunning);
        }

        if now_ms.saturating_sub(execution.last_heartbeat_ms) > self.heartbeat_timeout_ms {
            execution.state = WorkerExecutionState::TimedOut;
            execution.completed_at_ms = Some(now_ms);
            return Ok(execution.clone());
        }

        execution.last_heartbeat_ms = now_ms;
        Ok(execution.clone())
    }

    pub fn complete(
        &mut self,
        request: WorkerExecutionCompleteRequest,
        now_ms: u64,
    ) -> Result<WorkerExecutionRecord, WorkerExecutionError> {
        let execution = self
            .executions
            .get_mut(request.execution_id.as_str())
            .ok_or(WorkerExecutionError::UnknownExecutionId)?;
        if execution.lease_id != request.lease_id {
            return Err(WorkerExecutionError::LeaseMismatch);
        }
        if execution.state != WorkerExecutionState::Running {
            return Err(WorkerExecutionError::NotRunning);
        }
        if execution.cancellation_intent.is_some() {
            execution.state = WorkerExecutionState::Cancelled;
            execution.completed_at_ms = Some(now_ms);
            return Ok(execution.clone());
        }

        execution.state = WorkerExecutionState::Completed;
        execution.completed_at_ms = Some(now_ms);
        execution.output_ref = Some(request.output_ref.trim().to_string());
        Ok(execution.clone())
    }

    pub fn cancel(
        &mut self,
        request: WorkerExecutionCancelRequest,
        now_ms: u64,
    ) -> Result<WorkerExecutionRecord, WorkerExecutionError> {
        let execution = self
            .executions
            .get_mut(request.execution_id.as_str())
            .ok_or(WorkerExecutionError::UnknownExecutionId)?;
        execution.cancellation_intent = Some(request.reason.trim().to_string());
        if execution.state == WorkerExecutionState::Running {
            execution.state = WorkerExecutionState::Cancelled;
            execution.completed_at_ms = Some(now_ms);
        }
        Ok(execution.clone())
    }

    pub fn execution(&self, execution_id: &str) -> Option<&WorkerExecutionRecord> {
        self.executions.get(execution_id)
    }
}

/// Bootstraps control-plane state and deterministically discovers workers.
pub fn bootstrap_cluster_control_plane(
    input: &ClusterBootstrapInput,
    workers: &[ClusterWorkerRegistration],
) -> Result<ClusterBootstrapArtifact, ClusterControlPlaneError> {
    if input.cluster_id.trim().is_empty() {
        return Err(ClusterControlPlaneError::EmptyClusterId);
    }
    if input.control_plane_node_id.trim().is_empty() {
        return Err(ClusterControlPlaneError::EmptyControlPlaneNodeId);
    }
    if input.runtime_mode == ClusterRuntimeMode::Cluster && workers.is_empty() {
        return Err(ClusterControlPlaneError::NoWorkersRegistered);
    }

    let mut discovered_worker_ids: Vec<String> = workers
        .iter()
        .filter(|worker| worker.state != ClusterWorkerState::Offline)
        .map(|worker| worker.worker_id.trim())
        .filter(|worker_id| !worker_id.is_empty())
        .map(ToOwned::to_owned)
        .collect();
    discovered_worker_ids.sort();
    discovered_worker_ids.dedup();

    Ok(ClusterBootstrapArtifact {
        cluster_contract_version: CLUSTER_CONTROL_PLANE_CONTRACT_VERSION,
        cluster_id: input.cluster_id.trim().to_string(),
        control_plane_node_id: input.control_plane_node_id.trim().to_string(),
        runtime_mode: input.runtime_mode,
        discovered_worker_ids,
    })
}

/// Deterministically assigns a job to a worker with node-loss fallback behavior.
pub fn assign_cluster_job(
    cluster_id: &str,
    job_id: &str,
    assignment_sequence: u64,
    assignment_epoch_ms: u64,
    workers: &[ClusterWorkerRegistration],
    required_capability_tags: &[String],
    lost_worker_ids: &[String],
) -> Result<ClusterAssignmentArtifact, ClusterControlPlaneError> {
    if cluster_id.trim().is_empty() {
        return Err(ClusterControlPlaneError::EmptyClusterId);
    }
    if job_id.trim().is_empty() {
        return Err(ClusterControlPlaneError::EmptyJobId);
    }
    if workers.is_empty() {
        return Err(ClusterControlPlaneError::NoWorkersRegistered);
    }

    let lost: std::collections::HashSet<&str> = lost_worker_ids
        .iter()
        .map(String::as_str)
        .filter(|worker_id| !worker_id.trim().is_empty())
        .collect();

    let required_tags: std::collections::HashSet<&str> = required_capability_tags
        .iter()
        .map(String::as_str)
        .filter(|tag| !tag.trim().is_empty())
        .collect();

    let mut eligible: Vec<&ClusterWorkerRegistration> = workers
        .iter()
        .filter(|worker| !lost.contains(worker.worker_id.as_str()))
        .filter(|worker| {
            matches!(
                worker.state,
                ClusterWorkerState::Ready | ClusterWorkerState::Degraded
            )
        })
        .collect();

    eligible.sort_by(|left, right| {
        left.current_load
            .cmp(&right.current_load)
            .then_with(|| left.worker_id.cmp(&right.worker_id))
    });

    let mut assignment_trace = vec![
        "filter-offline-draining-and-lost".to_string(),
        "sort-by-load-asc-worker-id-asc".to_string(),
    ];

    let mut fallback_applied = false;
    let mut fallback_reason = None;

    let mut primary_candidates: Vec<&ClusterWorkerRegistration> = eligible
        .iter()
        .copied()
        .filter(|worker| {
            if required_tags.is_empty() {
                return true;
            }
            let worker_tags: std::collections::HashSet<&str> =
                worker.capability_tags.iter().map(String::as_str).collect();
            required_tags.iter().all(|tag| worker_tags.contains(tag))
        })
        .collect();

    if primary_candidates.is_empty() && !eligible.is_empty() {
        fallback_applied = true;
        fallback_reason = Some(
            "no-worker-satisfies-required-capabilities-after-node-loss-fallback-to-load-order"
                .to_string(),
        );
        assignment_trace.push("fallback-any-ready-or-degraded-worker".to_string());
        primary_candidates = eligible.clone();
    }

    if primary_candidates.is_empty() {
        return Err(ClusterControlPlaneError::NoEligibleWorkers);
    }

    let selected = primary_candidates[0];
    let candidate_workers: Vec<String> = primary_candidates
        .iter()
        .map(|worker| worker.worker_id.clone())
        .collect();
    let assignment_id = format!("{}-a-{:06}", job_id.trim(), assignment_sequence);

    Ok(ClusterAssignmentArtifact {
        cluster_contract_version: CLUSTER_CONTROL_PLANE_CONTRACT_VERSION,
        assignment_id: assignment_id.clone(),
        job_id: job_id.trim().to_string(),
        candidate_workers,
        selected_worker_id: selected.worker_id.clone(),
        assignment_trace,
        lineage: ClusterAssignmentLineage {
            lineage_version: CLUSTER_ASSIGNMENT_LINEAGE_VERSION,
            cluster_id: cluster_id.trim().to_string(),
            assignment_id,
            assignment_sequence,
            assignment_epoch_ms,
        },
        fallback_applied,
        fallback_reason,
    })
}

/// Split planning input for a task that can run on multiple backends.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SplitTask {
    pub task_id: String,
    pub compatible_backends: Vec<String>,
}

/// Planned shard assignment artifact for multi-device execution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SplitShardPlan {
    pub version: &'static str,
    pub parent_job_id: String,
    pub shard_id: String,
    pub backend_id: String,
    pub task_ids: Vec<String>,
}

/// Split planner output that can be persisted as a manifest artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SplitPlanManifest {
    pub version: &'static str,
    pub parent_job_id: String,
    pub scheduler_decision_version: &'static str,
    pub shard_plans: Vec<SplitShardPlan>,
}

/// Split planner validation errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SplitPlanError {
    EmptyParentJobId,
    EmptyTaskSet,
    EmptyCompatibleBackends { task_id: String },
    TooManyShards { requested: usize, allowed: usize },
}

/// Standardized partial-failure envelope for shard execution.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialFailureEnvelope {
    pub version: &'static str,
    pub parent_job_id: String,
    pub shard_id: String,
    pub backend_id: String,
    pub reason_code: PartialFailureReasonCode,
    pub retryable: bool,
    pub message: String,
}

/// Stable reason codes for partial shard failures.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PartialFailureReasonCode {
    BackendUnavailable,
    ExecutionTimeout,
    ValidationFailed,
    InternalError,
}

/// Partial result payload produced by a successful shard.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartialResultEnvelope {
    pub version: &'static str,
    pub parent_job_id: String,
    pub shard_id: String,
    pub backend_id: String,
    pub payload_ref: String,
    pub payload_checksum: String,
}

/// Merge success criteria.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MergePolicy {
    /// All expected shards must produce a success result.
    AllShardsRequired,
    /// At least `min_successful_shards` successful results are required.
    Quorum { min_successful_shards: usize },
}

/// Stable merge reason codes for orchestration audit and routing explanations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MergeReasonCode {
    AllShardsMerged,
    QuorumSatisfied,
    QuorumNotReached,
    MissingExpectedShards,
    ParentJobMismatch,
    DuplicateShardEnvelope,
}

/// Result of merge consistency checks for shard outcomes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MergeDecision {
    pub version: &'static str,
    pub parent_job_id: String,
    pub reason_code: MergeReasonCode,
    pub merged_shard_ids: Vec<String>,
    pub failed_shard_ids: Vec<String>,
    pub missing_shard_ids: Vec<String>,
    pub failures: Vec<PartialFailureEnvelope>,
}

/// Plans deterministic shard splits across compatible backends.
pub fn plan_split(
    parent_job_id: &str,
    tasks: &[SplitTask],
    max_shards: usize,
) -> Result<SplitPlanManifest, SplitPlanError> {
    if parent_job_id.trim().is_empty() {
        return Err(SplitPlanError::EmptyParentJobId);
    }
    if tasks.is_empty() {
        return Err(SplitPlanError::EmptyTaskSet);
    }
    if max_shards == 0 {
        return Err(SplitPlanError::TooManyShards {
            requested: 1,
            allowed: 0,
        });
    }

    let mut assignments: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for task in tasks {
        if task.compatible_backends.is_empty() {
            return Err(SplitPlanError::EmptyCompatibleBackends {
                task_id: task.task_id.clone(),
            });
        }

        let mut normalized_backends: Vec<String> = task
            .compatible_backends
            .iter()
            .map(|backend| backend.trim())
            .filter(|backend| !backend.is_empty())
            .map(ToOwned::to_owned)
            .collect();
        normalized_backends.sort();
        normalized_backends.dedup();
        if normalized_backends.is_empty() {
            return Err(SplitPlanError::EmptyCompatibleBackends {
                task_id: task.task_id.clone(),
            });
        }

        let selected_backend = normalized_backends[0].clone();
        assignments
            .entry(selected_backend)
            .or_default()
            .push(task.task_id.clone());
    }

    if assignments.len() > max_shards {
        return Err(SplitPlanError::TooManyShards {
            requested: assignments.len(),
            allowed: max_shards,
        });
    }

    let shard_plans = assignments
        .into_iter()
        .enumerate()
        .map(|(idx, (backend_id, task_ids))| SplitShardPlan {
            version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
            parent_job_id: parent_job_id.to_string(),
            shard_id: format!("{}-shard-{:03}", parent_job_id, idx + 1),
            backend_id,
            task_ids,
        })
        .collect();

    Ok(SplitPlanManifest {
        version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
        parent_job_id: parent_job_id.to_string(),
        scheduler_decision_version: SCHEDULER_DECISION_VERSION,
        shard_plans,
    })
}

/// Validates and merges partial shard outcomes into a single merge decision.
pub fn merge_partial_results(
    parent_job_id: &str,
    expected_shard_ids: &[String],
    results: &[PartialResultEnvelope],
    failures: &[PartialFailureEnvelope],
    policy: MergePolicy,
) -> MergeDecision {
    let mut observed = std::collections::HashSet::new();
    let mut merged_shard_ids = Vec::new();
    let mut failed_shard_ids = Vec::new();
    let mut filtered_failures = Vec::new();

    for result in results {
        if result.parent_job_id != parent_job_id {
            return MergeDecision {
                version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
                parent_job_id: parent_job_id.to_string(),
                reason_code: MergeReasonCode::ParentJobMismatch,
                merged_shard_ids: Vec::new(),
                failed_shard_ids: Vec::new(),
                missing_shard_ids: expected_shard_ids.to_vec(),
                failures: Vec::new(),
            };
        }
        if !observed.insert(result.shard_id.clone()) {
            return MergeDecision {
                version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
                parent_job_id: parent_job_id.to_string(),
                reason_code: MergeReasonCode::DuplicateShardEnvelope,
                merged_shard_ids: Vec::new(),
                failed_shard_ids: Vec::new(),
                missing_shard_ids: expected_shard_ids.to_vec(),
                failures: Vec::new(),
            };
        }
        merged_shard_ids.push(result.shard_id.clone());
    }

    for failure in failures {
        if failure.parent_job_id != parent_job_id {
            return MergeDecision {
                version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
                parent_job_id: parent_job_id.to_string(),
                reason_code: MergeReasonCode::ParentJobMismatch,
                merged_shard_ids: Vec::new(),
                failed_shard_ids: Vec::new(),
                missing_shard_ids: expected_shard_ids.to_vec(),
                failures: Vec::new(),
            };
        }
        if !observed.insert(failure.shard_id.clone()) {
            return MergeDecision {
                version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
                parent_job_id: parent_job_id.to_string(),
                reason_code: MergeReasonCode::DuplicateShardEnvelope,
                merged_shard_ids: Vec::new(),
                failed_shard_ids: Vec::new(),
                missing_shard_ids: expected_shard_ids.to_vec(),
                failures: Vec::new(),
            };
        }
        failed_shard_ids.push(failure.shard_id.clone());
        filtered_failures.push(failure.clone());
    }

    let missing_shard_ids: Vec<String> = expected_shard_ids
        .iter()
        .filter(|shard_id| !observed.contains(shard_id.as_str()))
        .cloned()
        .collect();

    let reason_code = match policy {
        MergePolicy::AllShardsRequired => {
            if missing_shard_ids.is_empty() && failed_shard_ids.is_empty() {
                MergeReasonCode::AllShardsMerged
            } else {
                MergeReasonCode::MissingExpectedShards
            }
        }
        MergePolicy::Quorum {
            min_successful_shards,
        } => {
            if merged_shard_ids.len() >= min_successful_shards {
                MergeReasonCode::QuorumSatisfied
            } else {
                MergeReasonCode::QuorumNotReached
            }
        }
    };

    MergeDecision {
        version: MULTI_DEVICE_EXECUTION_CONTRACT_VERSION,
        parent_job_id: parent_job_id.to_string(),
        reason_code,
        merged_shard_ids,
        failed_shard_ids,
        missing_shard_ids,
        failures: filtered_failures,
    }
}

/// Outcome of admission control for a candidate job.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionDisposition {
    Admit,
    Defer,
    Reject,
}

/// Stable reason codes for admission outcomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionReasonCode {
    Accepted,
    DeferredHighBacklog,
    RejectedGlobalQueueLimit,
    RejectedPriorityQueueLimit,
    RejectedTenantQuota,
    RejectedProjectQuota,
}

/// Stable reason codes for dispatch outcomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DispatchReasonCode {
    WeightedFairness,
    StarvationPrevention,
    DeviceScore,
    DeviceScoreTieBreak,
    QueueEmpty,
}

/// Stable operational health statuses consumed by device scoring.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DeviceHealthStatus {
    Healthy,
    Degraded,
    Unavailable,
}

/// Runtime signals used by the device scoring engine.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeviceScoreInput {
    pub device_id: String,
    pub queue_depth: usize,
    pub recent_latency_ms: u64,
    pub calibration_age_sec: u64,
    pub health_status: DeviceHealthStatus,
}

/// Weight/policy configuration for score calculation.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DeviceScoringPolicy {
    pub queue_depth_weight: f64,
    pub latency_weight: f64,
    pub calibration_weight: f64,
    pub availability_weight: f64,
    pub max_queue_depth: usize,
    pub target_latency_ms: u64,
    pub calibration_ttl_sec: u64,
}

impl Default for DeviceScoringPolicy {
    fn default() -> Self {
        Self {
            queue_depth_weight: 0.35,
            latency_weight: 0.30,
            calibration_weight: 0.20,
            availability_weight: 0.15,
            max_queue_depth: 100,
            target_latency_ms: 2_000,
            calibration_ttl_sec: 3_600,
        }
    }
}

/// Score components for explainable dispatch records.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeviceScoreBreakdown {
    pub version: &'static str,
    pub device_id: String,
    pub total_score_millis: u64,
    pub queue_depth_score_millis: u64,
    pub latency_score_millis: u64,
    pub calibration_score_millis: u64,
    pub availability_score_millis: u64,
}

/// Device scoring decision record used by dispatch traces.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeviceDispatchRecord {
    pub version: &'static str,
    pub selected_device_id: String,
    pub reason_code: DispatchReasonCode,
    pub score_breakdown: Vec<DeviceScoreBreakdown>,
}

/// Workload descriptor features used by backend scoring v1.
#[derive(Debug, Clone, PartialEq)]
pub struct BackendWorkloadDescriptor {
    pub job_type: String,
    pub priority: u8,
    pub shots: u64,
    pub circuit_depth: u64,
    pub circuit_width: u64,
    pub estimated_runtime_ms: u64,
    pub noise_sensitivity: f64,
    pub cost_sensitivity: f64,
    pub required_features: Vec<String>,
}

/// Backend descriptor features used by backend scoring v1.
#[derive(Debug, Clone, PartialEq)]
pub struct BackendCandidateDescriptor {
    pub backend_id: String,
    pub backend_type: String,
    pub qubit_count: u32,
    pub availability: f64,
    pub queue_length: usize,
    pub historical_latency_ms: u64,
    pub historical_success_rate: f64,
    pub historical_fidelity: f64,
    pub error_rate: f64,
    pub calibration_age_sec: u64,
    pub policy_priority: i32,
    pub capability_rank: i32,
    pub supported_features: Vec<String>,
}

/// Runtime/context descriptor used by backend scoring v1.
#[derive(Debug, Clone, PartialEq)]
pub struct BackendRuntimeDescriptor {
    pub current_cluster_load: f64,
    pub retry_count: u32,
    pub warm_cache_hit: bool,
}

/// Persisted scoring profile for deterministic backend scoring.
#[derive(Debug, Clone, PartialEq)]
pub struct BackendScoringProfile {
    pub profile_id: String,
    pub profile_version: String,
    pub max_queue_length: usize,
    pub target_latency_ms: u64,
    pub calibration_ttl_sec: u64,
    pub queue_weight: f64,
    pub latency_weight: f64,
    pub success_weight: f64,
    pub fidelity_weight: f64,
    pub availability_weight: f64,
    pub calibration_weight: f64,
    pub cost_weight: f64,
}

impl Default for BackendScoringProfile {
    fn default() -> Self {
        Self {
            profile_id: "balanced".to_string(),
            profile_version: "1.0.0".to_string(),
            max_queue_length: 256,
            target_latency_ms: 2_000,
            calibration_ttl_sec: 7_200,
            queue_weight: 0.2,
            latency_weight: 0.2,
            success_weight: 0.2,
            fidelity_weight: 0.15,
            availability_weight: 0.15,
            calibration_weight: 0.05,
            cost_weight: 0.05,
        }
    }
}

/// In-memory profile store keyed by `<profile_id>@<profile_version>`.
#[derive(Debug, Clone, Default)]
pub struct BackendScoringProfileStore {
    profiles: BTreeMap<String, BackendScoringProfile>,
}

impl BackendScoringProfileStore {
    pub fn save(&mut self, profile: BackendScoringProfile) {
        let key = Self::make_key(&profile.profile_id, &profile.profile_version);
        self.profiles.insert(key, profile);
    }

    pub fn load(&self, profile_id: &str, profile_version: &str) -> Option<BackendScoringProfile> {
        let key = Self::make_key(profile_id, profile_version);
        self.profiles.get(&key).cloned()
    }

    fn make_key(profile_id: &str, profile_version: &str) -> String {
        format!("{profile_id}@{profile_version}")
    }
}

/// Stable breakdown of backend feature contributions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackendFeatureContribution {
    pub feature: &'static str,
    pub contribution_millis: u64,
}

/// Per-backend scoring result in decision artifacts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackendScoreCandidate {
    pub backend_id: String,
    pub score_millis: u64,
    pub eligible: bool,
    pub ineligibility_reason: Option<&'static str>,
    pub feature_contributions: Vec<BackendFeatureContribution>,
}

/// Versioned backend-scoring decision artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackendScoringDecisionArtifact {
    pub scoring_contract_version: &'static str,
    pub profile_schema_version: &'static str,
    pub profile_version: String,
    pub decision_id: String,
    pub candidates: Vec<BackendScoreCandidate>,
    pub selected_backend_id: Option<String>,
    pub tie_break_trace: Vec<String>,
}

/// Request DTO for `/explain/backend-selection`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExplainBackendSelectionRequest {
    pub request_version: &'static str,
    pub response_version: &'static str,
    pub decision_id: String,
    pub include_rejected_candidates: bool,
}

/// Ordered factor contribution in the explain response envelope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExplainFactorContribution {
    pub backend_id: String,
    pub factor: &'static str,
    pub contribution_millis: u64,
}

/// Confidence metadata in `/explain/backend-selection` responses.
#[derive(Debug, Clone, PartialEq)]
pub struct ExplainConfidenceMetadata {
    pub score_margin_millis: u64,
    pub selected_score_millis: u64,
    pub runner_up_score_millis: u64,
    pub confidence: f64,
}

/// Stable response envelope for `/explain/backend-selection`.
#[derive(Debug, Clone, PartialEq)]
pub struct ExplainBackendSelectionResponse {
    pub explain_contract_version: &'static str,
    pub request_version: &'static str,
    pub response_version: &'static str,
    pub scoring_contract_version: &'static str,
    pub profile_schema_version: &'static str,
    pub profile_version: String,
    pub decision_id: String,
    pub selected_backend_id: Option<String>,
    pub tie_break_trace: Vec<String>,
    pub candidate_scores: Vec<BackendScoreCandidate>,
    pub factor_contributions: Vec<ExplainFactorContribution>,
    pub confidence: ExplainConfidenceMetadata,
}

/// Named policy operating mode for scheduling policy bundle resolution.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PolicyMode {
    Latency,
    Throughput,
    Cost,
    Balanced,
}

/// Deterministic priority ladder used by policy resolution.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PolicyPriorityMap {
    pub hard_constraints: u16,
    pub correctness: u16,
    pub user_intent: u16,
    pub operational_optimization: u16,
    pub learning_hints: u16,
}

impl Default for PolicyPriorityMap {
    fn default() -> Self {
        Self {
            hard_constraints: 100,
            correctness: 90,
            user_intent: 70,
            operational_optimization: 50,
            learning_hints: 30,
        }
    }
}

/// User-intent weights for deterministic policy ranking.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct UserIntentWeights {
    pub fidelity: f64,
    pub latency: f64,
    pub cost: f64,
    pub throughput: f64,
    pub determinism: f64,
    pub debuggability: f64,
}

impl Default for UserIntentWeights {
    fn default() -> Self {
        Self {
            fidelity: 1.0,
            latency: 0.8,
            cost: 0.7,
            throughput: 0.6,
            determinism: 0.9,
            debuggability: 0.85,
        }
    }
}

/// Versioned scheduling policy bundle schema.
#[derive(Debug, Clone, PartialEq)]
pub struct PolicyBundle {
    pub policy_bundle_id: String,
    pub policy_bundle_version: String,
    pub policy_mode: PolicyMode,
    pub policy_priority_map: PolicyPriorityMap,
    pub user_intent_weights: UserIntentWeights,
}

impl Default for PolicyBundle {
    fn default() -> Self {
        Self {
            policy_bundle_id: "balanced".to_string(),
            policy_bundle_version: "1.0.0".to_string(),
            policy_mode: PolicyMode::Balanced,
            policy_priority_map: PolicyPriorityMap::default(),
            user_intent_weights: UserIntentWeights::default(),
        }
    }
}

/// Policy bundle validation errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PolicyBundleValidationError {
    EmptyBundleId,
    InvalidBundleVersion,
    InvalidPriorityOrder,
    InvalidWeight { field: &'static str },
}

/// Execution candidate signals consumed by policy resolution.
#[derive(Debug, Clone, PartialEq)]
pub struct PolicyCandidate {
    pub candidate_id: String,
    pub hard_constraint_satisfied: bool,
    pub correctness_score: f64,
    pub fidelity_score: f64,
    pub latency_ms: u64,
    pub cost_units: u64,
    pub throughput_qps: u64,
    pub deterministic: bool,
    pub debuggability_score: f64,
    pub learning_hint_score: f64,
}

/// Failure code for policy-resolution errors.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PolicyResolutionErrorCode {
    PolicyBundleInvalid,
    PolicyModeUnsupported,
    PolicyResolutionFailed,
    ModelDecisionInvalid,
}

/// Stable reason-code mapping for deterministic/model-assisted transition outcomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PolicyTransitionReasonCode {
    DeterministicSelection,
    ModelSelectionAccepted,
    FallbackMissingModelOutput,
    FallbackInvalidModelOutput,
    FallbackMissingPolicyBundle,
    FallbackInvalidPolicyBundle,
    FallbackNoViableCandidate,
}

/// Versioned policy-resolution artifact for scheduling/explainability.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyResolutionArtifact {
    pub version: &'static str,
    pub policy_bundle_schema_version: &'static str,
    pub policy_bundle_id: String,
    pub policy_bundle_version: String,
    pub policy_mode: PolicyMode,
    pub selected_candidate_id: Option<String>,
    pub resolution_trace: Vec<String>,
    pub fallback_applied: bool,
    pub fallback_reason: Option<String>,
    pub transition_reason_code: PolicyTransitionReasonCode,
    pub deterministic_seed: u64,
    pub error_code: Option<PolicyResolutionErrorCode>,
}

/// Validate policy bundle schema and values.
pub fn validate_policy_bundle(bundle: &PolicyBundle) -> Result<(), PolicyBundleValidationError> {
    if bundle.policy_bundle_id.trim().is_empty() {
        return Err(PolicyBundleValidationError::EmptyBundleId);
    }
    if !is_semver_like(&bundle.policy_bundle_version) {
        return Err(PolicyBundleValidationError::InvalidBundleVersion);
    }
    if !(bundle.policy_priority_map.hard_constraints > bundle.policy_priority_map.correctness
        && bundle.policy_priority_map.correctness > bundle.policy_priority_map.user_intent
        && bundle.policy_priority_map.user_intent
            > bundle.policy_priority_map.operational_optimization
        && bundle.policy_priority_map.operational_optimization
            > bundle.policy_priority_map.learning_hints)
    {
        return Err(PolicyBundleValidationError::InvalidPriorityOrder);
    }

    for (field, value) in [
        ("fidelity", bundle.user_intent_weights.fidelity),
        ("latency", bundle.user_intent_weights.latency),
        ("cost", bundle.user_intent_weights.cost),
        ("throughput", bundle.user_intent_weights.throughput),
        ("determinism", bundle.user_intent_weights.determinism),
        ("debuggability", bundle.user_intent_weights.debuggability),
    ] {
        if !value.is_finite() || value < 0.0 {
            return Err(PolicyBundleValidationError::InvalidWeight { field });
        }
    }

    Ok(())
}

/// Deterministically resolves policy bundle against scheduling candidates.
///
/// Safe fallback behavior:
/// - missing bundle -> `balanced@1.0.0`
/// - invalid bundle -> `balanced@1.0.0` + `POLICY_BUNDLE_INVALID`
/// - no viable candidate -> deterministic empty selection + `POLICY_RESOLUTION_FAILED`
pub fn resolve_policy_bundle(
    bundle: Option<&PolicyBundle>,
    candidates: &[PolicyCandidate],
) -> PolicyResolutionArtifact {
    resolve_policy_bundle_with_model(bundle, candidates, None, 0)
}

/// Deterministic + model-assisted transition resolver with hardened fallback behavior.
pub fn resolve_policy_bundle_with_model(
    bundle: Option<&PolicyBundle>,
    candidates: &[PolicyCandidate],
    model_selected_candidate_id: Option<&str>,
    deterministic_seed: u64,
) -> PolicyResolutionArtifact {
    let mut trace = vec![
        "validate-policy-schema".to_string(),
        "apply-profile-defaults".to_string(),
        "apply-overrides-canonical-order".to_string(),
        "resolve-conflicts-fixed-precedence".to_string(),
    ];

    let (resolved_bundle, fallback_applied, fallback_reason, error_code, mut transition_reason_code) = match bundle {
        Some(candidate_bundle) => match validate_policy_bundle(candidate_bundle) {
            Ok(()) => (candidate_bundle.clone(), false, None, None, PolicyTransitionReasonCode::DeterministicSelection),
            Err(_) => (
                PolicyBundle::default(),
                true,
                Some("invalid_policy_bundle".to_string()),
                PolicyTransitionReasonCode::FallbackInvalidPolicyBundle,
            ),
        },
        None => (
            PolicyBundle::default(),
            true,
            Some("missing_policy_bundle".to_string()),
            None,
            PolicyTransitionReasonCode::FallbackMissingPolicyBundle,
        ),
    };

    let mut ranked: Vec<&PolicyCandidate> = candidates
        .iter()
        .filter(|candidate| candidate.hard_constraint_satisfied)
        .collect();
    ranked.sort_by(|left, right| compare_policy_candidates(left, right, &resolved_bundle));

    if ranked.is_empty() {
        trace.push("emit-fallback-no-viable-candidate".to_string());
        return PolicyResolutionArtifact {
            version: SCHEDULING_POLICY_RESOLUTION_VERSION,
            policy_bundle_schema_version: SCHEDULING_POLICY_BUNDLE_SCHEMA_VERSION,
            policy_bundle_id: resolved_bundle.policy_bundle_id,
            policy_bundle_version: resolved_bundle.policy_bundle_version,
            policy_mode: resolved_bundle.policy_mode,
            selected_candidate_id: None,
            resolution_trace: trace,
            fallback_applied: true,
            fallback_reason: Some("no_viable_candidate".to_string()),
            transition_reason_code: PolicyTransitionReasonCode::FallbackNoViableCandidate,
            deterministic_seed,
            error_code: Some(PolicyResolutionErrorCode::PolicyResolutionFailed),
        };
    }

    let deterministic_selected = ranked
        .first()
        .map(|candidate| candidate.candidate_id.clone());
    let selected_candidate_id = match model_selected_candidate_id {
        Some(model_id) if ranked.iter().any(|c| c.candidate_id == model_id) => {
            transition_reason_code = PolicyTransitionReasonCode::ModelSelectionAccepted;
            trace.push("model-selection-accepted".to_string());
            Some(model_id.to_string())
        }
        Some(_) => {
            transition_reason_code = PolicyTransitionReasonCode::FallbackInvalidModelOutput;
            trace.push("fallback-invalid-model-selection".to_string());
            deterministic_selected
        }
        None => {
            if !fallback_applied {
                transition_reason_code = PolicyTransitionReasonCode::FallbackMissingModelOutput;
                trace.push("fallback-missing-model-selection".to_string());
            }
            deterministic_selected
        }
    };
    trace.push("selection-complete".to_string());

    PolicyResolutionArtifact {
        version: SCHEDULING_POLICY_RESOLUTION_VERSION,
        policy_bundle_schema_version: SCHEDULING_POLICY_BUNDLE_SCHEMA_VERSION,
        policy_bundle_id: resolved_bundle.policy_bundle_id,
        policy_bundle_version: resolved_bundle.policy_bundle_version,
        policy_mode: resolved_bundle.policy_mode,
        selected_candidate_id,
        resolution_trace: trace,
        fallback_applied,
        fallback_reason,
        transition_reason_code,
        deterministic_seed,
        error_code,
    }
}

/// Job envelope tracked by scheduler queues.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScheduledJob {
    pub job_id: String,
    pub tenant_id: String,
    pub project_id: String,
    pub priority: u8,
}

/// Admission decision DTO (observable and auditable).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmissionDecision {
    pub version: &'static str,
    pub disposition: AdmissionDisposition,
    pub reason_code: AdmissionReasonCode,
    pub total_queue_depth: usize,
    pub priority_queue_depth: usize,
    pub tenant_queue_depth: usize,
    pub project_queue_depth: usize,
}

/// Dispatch decision DTO.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchedulerDecision {
    pub version: &'static str,
    pub selected_job_id: Option<String>,
    pub selected_tenant_id: Option<String>,
    pub selected_project_id: Option<String>,
    pub selected_priority: Option<u8>,
    pub queue_depth_after: usize,
    pub reason_code: DispatchReasonCode,
    pub device_dispatch: Option<DeviceDispatchRecord>,
}

/// Scheduler configuration for admission control.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AdmissionPolicy {
    /// Maximum number of jobs across all queues.
    pub max_total_queue_depth: usize,
    /// Maximum number of jobs in any single priority queue.
    pub max_per_priority_queue_depth: usize,
    /// Maximum number of queued jobs per tenant.
    pub max_per_tenant_queue_depth: usize,
    /// Maximum number of queued jobs per project.
    pub max_per_project_queue_depth: usize,
    /// Once total depth reaches this threshold, admissions are deferred.
    pub defer_at_total_queue_depth: usize,
}

impl Default for AdmissionPolicy {
    fn default() -> Self {
        Self {
            max_total_queue_depth: 1_000,
            max_per_priority_queue_depth: 100,
            max_per_tenant_queue_depth: 200,
            max_per_project_queue_depth: 100,
            defer_at_total_queue_depth: 800,
        }
    }
}

/// Weighted fairness + starvation policy.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FairnessPolicy {
    /// Relative tenant weight used in expected-share computation.
    pub default_tenant_weight: u32,
    /// Relative project weight used in expected-share computation.
    pub default_project_weight: u32,
    /// Dispatch-round age that triggers starvation override.
    pub starvation_round_threshold: u64,
}

impl Default for FairnessPolicy {
    fn default() -> Self {
        Self {
            default_tenant_weight: 1,
            default_project_weight: 1,
            starvation_round_threshold: 10,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
struct FairnessKey {
    tenant_id: String,
    project_id: String,
}

impl FairnessKey {
    fn from_job(job: &ScheduledJob) -> Self {
        Self {
            tenant_id: job.tenant_id.clone(),
            project_id: job.project_id.clone(),
        }
    }
}

#[derive(Debug, Clone)]
struct QueueState {
    per_priority: BTreeMap<u8, VecDeque<ScheduledJob>>,
}

impl QueueState {
    fn new() -> Self {
        Self {
            per_priority: BTreeMap::new(),
        }
    }

    fn is_empty(&self) -> bool {
        self.per_priority.is_empty()
    }

    fn depth(&self) -> usize {
        self.per_priority.values().map(VecDeque::len).sum()
    }

    fn push(&mut self, job: ScheduledJob) {
        self.per_priority
            .entry(job.priority)
            .or_default()
            .push_back(job);
    }

    fn push_front(&mut self, job: ScheduledJob) {
        self.per_priority
            .entry(job.priority)
            .or_default()
            .push_front(job);
    }

    fn pop_next(&mut self) -> Option<ScheduledJob> {
        let priority = self.per_priority.keys().next_back().copied()?;
        let queue = self
            .per_priority
            .get_mut(&priority)
            .expect("priority bucket must exist");
        let job = queue.pop_front();
        if queue.is_empty() {
            self.per_priority.remove(&priority);
        }
        job
    }
}

/// Lightweight scheduler loop counters.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SchedulerMetrics {
    pub admitted_total: u64,
    pub deferred_total: u64,
    pub rejected_total: u64,
    pub quota_denied_tenant_total: u64,
    pub quota_denied_project_total: u64,
    pub dispatched_total: u64,
    pub starvation_prevention_total: u64,
    /// Accumulated non-negative fairness lag (milli-jobs).
    pub fairness_lag_millis_total: u64,
    /// Maximum observed non-negative fairness lag (milli-jobs).
    pub fairness_lag_millis_max: u64,
    pub rebalance_trigger_total: u64,
    pub preemption_attempted_total: u64,
    pub preempted_total: u64,
    pub requeued_total: u64,
    pub requeue_idempotent_hits_total: u64,
}

/// Health/status snapshot for health endpoints.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchedulerHealth {
    pub healthy: bool,
    pub total_queue_depth: usize,
    pub fairness_entities: usize,
    pub metrics: SchedulerMetrics,
}

/// Device load sample used for rebalance trigger evaluation.
#[derive(Debug, Clone, PartialEq)]
pub struct DeviceLoad {
    pub device_id: String,
    /// Ratio in the `[0.0, 1.0]` interval.
    pub load_ratio: f64,
}

/// Rebalancing trigger policy.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RebalancingPolicy {
    pub high_watermark: f64,
    pub low_watermark: f64,
    pub min_imbalance_gap: f64,
    pub max_preemptions_per_rebalance: usize,
}

impl Default for RebalancingPolicy {
    fn default() -> Self {
        Self {
            high_watermark: 0.85,
            low_watermark: 0.40,
            min_imbalance_gap: 0.30,
            max_preemptions_per_rebalance: 2,
        }
    }
}

/// Guardrails for safe preemption.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PreemptionPolicy {
    pub min_dispatch_rounds_before_preempt: u64,
    pub max_preemptions_per_job: u32,
}

impl Default for PreemptionPolicy {
    fn default() -> Self {
        Self {
            min_dispatch_rounds_before_preempt: 1,
            max_preemptions_per_job: 3,
        }
    }
}

/// Stable reason codes for preemption outcomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreemptionReasonCode {
    RebalanceOverloadedDevice,
    DuplicateRequeueRequest,
    GuardrailMinRuntime,
    GuardrailPreemptionCap,
    ActiveDispatchNotFound,
}

/// Rebalance plan artifact with explicit version marker.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RebalancePlan {
    pub version: &'static str,
    pub source_device_id: String,
    pub target_device_id: String,
    pub candidate_job_ids: Vec<String>,
}

/// Preemption + requeue decision artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PreemptionDecision {
    pub version: &'static str,
    pub job_id: String,
    pub disposition: AdmissionDisposition,
    pub reason_code: PreemptionReasonCode,
    pub queue_depth_after: usize,
    pub idempotent: bool,
}

#[derive(Debug, Clone)]
struct ActiveDispatch {
    job: ScheduledJob,
    assigned_round: u64,
    assigned_device_id: Option<String>,
}

/// Priority scheduler with fairness-aware entity selection.
#[derive(Debug)]
pub struct Scheduler {
    admission_policy: AdmissionPolicy,
    fairness_policy: FairnessPolicy,
    queues: HashMap<FairnessKey, QueueState>,
    total_depth: usize,
    per_priority_depth: HashMap<u8, usize>,
    per_tenant_depth: HashMap<String, usize>,
    per_project_depth: HashMap<String, usize>,
    dispatch_count: u64,
    dispatch_by_entity: HashMap<FairnessKey, u64>,
    last_dispatch_round: HashMap<FairnessKey, u64>,
    preemption_policy: PreemptionPolicy,
    active_dispatches: HashMap<String, ActiveDispatch>,
    preemptions_by_job: HashMap<String, u32>,
    applied_requeue_tokens: HashMap<String, String>,
    metrics: SchedulerMetrics,
}

impl Scheduler {
    pub fn new(admission_policy: AdmissionPolicy, fairness_policy: FairnessPolicy) -> Self {
        Self {
            admission_policy,
            fairness_policy,
            queues: HashMap::new(),
            total_depth: 0,
            per_priority_depth: HashMap::new(),
            per_tenant_depth: HashMap::new(),
            per_project_depth: HashMap::new(),
            dispatch_count: 0,
            dispatch_by_entity: HashMap::new(),
            last_dispatch_round: HashMap::new(),
            preemption_policy: PreemptionPolicy::default(),
            active_dispatches: HashMap::new(),
            preemptions_by_job: HashMap::new(),
            applied_requeue_tokens: HashMap::new(),
            metrics: SchedulerMetrics::default(),
        }
    }

    pub fn with_preemption_policy(mut self, preemption_policy: PreemptionPolicy) -> Self {
        self.preemption_policy = preemption_policy;
        self
    }

    pub fn admission_policy(&self) -> AdmissionPolicy {
        self.admission_policy
    }

    pub fn fairness_policy(&self) -> FairnessPolicy {
        self.fairness_policy.clone()
    }

    pub fn queue_depth(&self) -> usize {
        self.total_depth
    }

    pub fn metrics(&self) -> SchedulerMetrics {
        self.metrics.clone()
    }

    pub fn active_dispatches(&self) -> usize {
        self.active_dispatches.len()
    }

    /// Scores candidate devices and returns a deterministic dispatch record.
    pub fn score_devices(
        &self,
        candidates: &[DeviceScoreInput],
        policy: DeviceScoringPolicy,
    ) -> Option<DeviceDispatchRecord> {
        if candidates.is_empty() {
            return None;
        }

        let mut breakdown: Vec<DeviceScoreBreakdown> = candidates
            .iter()
            .map(|candidate| score_candidate(candidate, policy))
            .collect();
        breakdown.sort_by(|a, b| {
            b.total_score_millis
                .cmp(&a.total_score_millis)
                .then_with(|| a.device_id.cmp(&b.device_id))
        });

        let top_score = breakdown[0].total_score_millis;
        let tied_for_top = breakdown
            .iter()
            .filter(|item| item.total_score_millis == top_score)
            .count()
            > 1;
        let reason_code = if tied_for_top {
            DispatchReasonCode::DeviceScoreTieBreak
        } else {
            DispatchReasonCode::DeviceScore
        };

        Some(DeviceDispatchRecord {
            version: DEVICE_SCORE_VERSION,
            selected_device_id: breakdown[0].device_id.clone(),
            reason_code,
            score_breakdown: breakdown,
        })
    }

    pub fn health(&self) -> SchedulerHealth {
        SchedulerHealth {
            healthy: self.total_depth <= self.admission_policy.max_total_queue_depth,
            total_queue_depth: self.total_depth,
            fairness_entities: self.queues.len(),
            metrics: self.metrics(),
        }
    }

    /// Evaluate admission without mutating queue state.
    pub fn evaluate_admission(
        &self,
        tenant_id: &str,
        project_id: &str,
        priority: u8,
    ) -> AdmissionDecision {
        let priority_depth = *self.per_priority_depth.get(&priority).unwrap_or(&0);
        let tenant_depth = *self.per_tenant_depth.get(tenant_id).unwrap_or(&0);
        let project_depth = *self.per_project_depth.get(project_id).unwrap_or(&0);

        let (disposition, reason_code) =
            if self.total_depth >= self.admission_policy.max_total_queue_depth {
                (
                    AdmissionDisposition::Reject,
                    AdmissionReasonCode::RejectedGlobalQueueLimit,
                )
            } else if priority_depth >= self.admission_policy.max_per_priority_queue_depth {
                (
                    AdmissionDisposition::Reject,
                    AdmissionReasonCode::RejectedPriorityQueueLimit,
                )
            } else if tenant_depth >= self.admission_policy.max_per_tenant_queue_depth {
                (
                    AdmissionDisposition::Reject,
                    AdmissionReasonCode::RejectedTenantQuota,
                )
            } else if project_depth >= self.admission_policy.max_per_project_queue_depth {
                (
                    AdmissionDisposition::Reject,
                    AdmissionReasonCode::RejectedProjectQuota,
                )
            } else if self.total_depth >= self.admission_policy.defer_at_total_queue_depth {
                (
                    AdmissionDisposition::Defer,
                    AdmissionReasonCode::DeferredHighBacklog,
                )
            } else {
                (AdmissionDisposition::Admit, AdmissionReasonCode::Accepted)
            };

        AdmissionDecision {
            version: SCHEDULER_DECISION_VERSION,
            disposition,
            reason_code,
            total_queue_depth: self.total_depth,
            priority_queue_depth: priority_depth,
            tenant_queue_depth: tenant_depth,
            project_queue_depth: project_depth,
        }
    }

    /// Attempts to enqueue a job according to admission control policy.
    pub fn submit(&mut self, job: ScheduledJob) -> AdmissionDecision {
        let decision = self.evaluate_admission(&job.tenant_id, &job.project_id, job.priority);
        match decision.disposition {
            AdmissionDisposition::Admit => {
                let key = FairnessKey::from_job(&job);
                self.queues
                    .entry(key)
                    .or_insert_with(QueueState::new)
                    .push(job.clone());
                self.total_depth += 1;
                *self.per_priority_depth.entry(job.priority).or_insert(0) += 1;
                *self.per_tenant_depth.entry(job.tenant_id).or_insert(0) += 1;
                *self.per_project_depth.entry(job.project_id).or_insert(0) += 1;
                self.metrics.admitted_total += 1;
            }
            AdmissionDisposition::Defer => {
                self.metrics.deferred_total += 1;
            }
            AdmissionDisposition::Reject => {
                self.metrics.rejected_total += 1;
                match decision.reason_code {
                    AdmissionReasonCode::RejectedTenantQuota => {
                        self.metrics.quota_denied_tenant_total += 1;
                    }
                    AdmissionReasonCode::RejectedProjectQuota => {
                        self.metrics.quota_denied_project_total += 1;
                    }
                    _ => {}
                }
            }
        }
        decision
    }

    /// Fairness-based dispatch with starvation prevention.
    pub fn dispatch_next(&mut self) -> SchedulerDecision {
        if self.total_depth == 0 {
            return SchedulerDecision {
                version: SCHEDULER_DECISION_VERSION,
                selected_job_id: None,
                selected_tenant_id: None,
                selected_project_id: None,
                selected_priority: None,
                queue_depth_after: 0,
                reason_code: DispatchReasonCode::QueueEmpty,
                device_dispatch: None,
            };
        }

        let current_round = self.dispatch_count + 1;
        let candidate = self.pick_dispatch_entity(current_round);

        let (key, reason_code) = candidate.expect("queue depth > 0 must have dispatch candidate");

        let queue = self
            .queues
            .get_mut(&key)
            .expect("selected fairness queue must exist");
        let job = queue.pop_next().expect("selected queue must be non-empty");

        if queue.is_empty() {
            self.queues.remove(&key);
        }

        self.total_depth -= 1;
        self.dispatch_count += 1;
        *self.dispatch_by_entity.entry(key.clone()).or_insert(0) += 1;
        self.last_dispatch_round
            .insert(key.clone(), self.dispatch_count);
        Self::decrement_counter(&mut self.per_priority_depth, job.priority);
        Self::decrement_counter(&mut self.per_tenant_depth, job.tenant_id.clone());
        Self::decrement_counter(&mut self.per_project_depth, job.project_id.clone());

        self.metrics.dispatched_total += 1;
        if reason_code == DispatchReasonCode::StarvationPrevention {
            self.metrics.starvation_prevention_total += 1;
        }

        let fairness_lag = self.compute_entity_fairness_lag_millis(&key, self.dispatch_count);
        self.metrics.fairness_lag_millis_total += fairness_lag;
        self.metrics.fairness_lag_millis_max =
            self.metrics.fairness_lag_millis_max.max(fairness_lag);
        self.active_dispatches.insert(
            job.job_id.clone(),
            ActiveDispatch {
                job: job.clone(),
                assigned_round: self.dispatch_count,
                assigned_device_id: None,
            },
        );

        SchedulerDecision {
            version: SCHEDULER_DECISION_VERSION,
            selected_job_id: Some(job.job_id),
            selected_tenant_id: Some(job.tenant_id),
            selected_project_id: Some(job.project_id),
            selected_priority: Some(job.priority),
            queue_depth_after: self.total_depth,
            reason_code,
            device_dispatch: None,
        }
    }

    /// Dispatches the next job and appends device scoring details to the record.
    pub fn dispatch_next_with_device_scores(
        &mut self,
        candidates: &[DeviceScoreInput],
        policy: DeviceScoringPolicy,
    ) -> SchedulerDecision {
        let mut decision = self.dispatch_next();
        decision.device_dispatch = self.score_devices(candidates, policy);
        if let Some(device_dispatch) = decision.device_dispatch.as_ref() {
            decision.reason_code = device_dispatch.reason_code;
            if let Some(job_id) = decision.selected_job_id.as_ref() {
                if let Some(active) = self.active_dispatches.get_mut(job_id) {
                    active.assigned_device_id = Some(device_dispatch.selected_device_id.clone());
                }
            }
        }
        decision
    }

    /// Marks an active job as terminal and removes it from in-flight tracking.
    pub fn complete_job(&mut self, job_id: &str) -> bool {
        self.active_dispatches.remove(job_id).is_some()
    }

    /// Evaluates load samples and returns a deterministic rebalance plan when thresholds are crossed.
    pub fn evaluate_rebalance(
        &self,
        device_loads: &[DeviceLoad],
        policy: RebalancingPolicy,
    ) -> Option<RebalancePlan> {
        if device_loads.len() < 2 {
            return None;
        }

        let mut sorted = device_loads.to_vec();
        sorted.sort_by(|a, b| {
            b.load_ratio
                .total_cmp(&a.load_ratio)
                .then_with(|| a.device_id.cmp(&b.device_id))
        });
        let source = sorted.first()?;
        let target = sorted.last()?;
        if source.load_ratio < policy.high_watermark
            || target.load_ratio > policy.low_watermark
            || (source.load_ratio - target.load_ratio) < policy.min_imbalance_gap
        {
            return None;
        }

        let mut candidate_job_ids: Vec<String> = self
            .active_dispatches
            .iter()
            .filter_map(|(job_id, active)| {
                (active.assigned_device_id.as_deref() == Some(source.device_id.as_str()))
                    .then_some(job_id.clone())
            })
            .collect();
        candidate_job_ids.sort();
        candidate_job_ids.truncate(policy.max_preemptions_per_rebalance);
        if candidate_job_ids.is_empty() {
            return None;
        }

        Some(RebalancePlan {
            version: REBALANCING_POLICY_VERSION,
            source_device_id: source.device_id.clone(),
            target_device_id: target.device_id.clone(),
            candidate_job_ids,
        })
    }

    /// Helper that increments rebalance metrics and returns a plan if trigger conditions are met.
    pub fn plan_rebalance(
        &mut self,
        device_loads: &[DeviceLoad],
        policy: RebalancingPolicy,
    ) -> Option<RebalancePlan> {
        let plan = self.evaluate_rebalance(device_loads, policy)?;
        self.metrics.rebalance_trigger_total += 1;
        Some(plan)
    }

    /// Applies rebalance-triggered preemption with idempotent requeue semantics.
    pub fn preempt_for_rebalance(
        &mut self,
        job_id: &str,
        requeue_token: &str,
    ) -> PreemptionDecision {
        self.metrics.preemption_attempted_total += 1;

        if let Some(existing_job_id) = self.applied_requeue_tokens.get(requeue_token) {
            self.metrics.requeue_idempotent_hits_total += 1;
            return PreemptionDecision {
                version: REBALANCING_POLICY_VERSION,
                job_id: existing_job_id.clone(),
                disposition: AdmissionDisposition::Admit,
                reason_code: PreemptionReasonCode::DuplicateRequeueRequest,
                queue_depth_after: self.total_depth,
                idempotent: true,
            };
        }

        let Some(active) = self.active_dispatches.get(job_id).cloned() else {
            return PreemptionDecision {
                version: REBALANCING_POLICY_VERSION,
                job_id: job_id.to_string(),
                disposition: AdmissionDisposition::Reject,
                reason_code: PreemptionReasonCode::ActiveDispatchNotFound,
                queue_depth_after: self.total_depth,
                idempotent: false,
            };
        };

        if self.dispatch_count.saturating_sub(active.assigned_round)
            < self.preemption_policy.min_dispatch_rounds_before_preempt
        {
            return PreemptionDecision {
                version: REBALANCING_POLICY_VERSION,
                job_id: job_id.to_string(),
                disposition: AdmissionDisposition::Defer,
                reason_code: PreemptionReasonCode::GuardrailMinRuntime,
                queue_depth_after: self.total_depth,
                idempotent: false,
            };
        }

        let preemption_count = *self.preemptions_by_job.get(job_id).unwrap_or(&0);
        if preemption_count >= self.preemption_policy.max_preemptions_per_job {
            return PreemptionDecision {
                version: REBALANCING_POLICY_VERSION,
                job_id: job_id.to_string(),
                disposition: AdmissionDisposition::Reject,
                reason_code: PreemptionReasonCode::GuardrailPreemptionCap,
                queue_depth_after: self.total_depth,
                idempotent: false,
            };
        }

        self.active_dispatches.remove(job_id);
        self.applied_requeue_tokens
            .insert(requeue_token.to_string(), job_id.to_string());
        *self
            .preemptions_by_job
            .entry(job_id.to_string())
            .or_insert(0) += 1;
        self.metrics.preempted_total += 1;
        self.metrics.requeued_total += 1;

        let key = FairnessKey::from_job(&active.job);
        self.queues
            .entry(key)
            .or_insert_with(QueueState::new)
            .push_front(active.job.clone());
        self.total_depth += 1;
        *self
            .per_priority_depth
            .entry(active.job.priority)
            .or_insert(0) += 1;
        *self
            .per_tenant_depth
            .entry(active.job.tenant_id.clone())
            .or_insert(0) += 1;
        *self
            .per_project_depth
            .entry(active.job.project_id.clone())
            .or_insert(0) += 1;

        PreemptionDecision {
            version: REBALANCING_POLICY_VERSION,
            job_id: job_id.to_string(),
            disposition: AdmissionDisposition::Admit,
            reason_code: PreemptionReasonCode::RebalanceOverloadedDevice,
            queue_depth_after: self.total_depth,
            idempotent: false,
        }
    }

    fn pick_dispatch_entity(
        &self,
        current_round: u64,
    ) -> Option<(FairnessKey, DispatchReasonCode)> {
        // Starvation override first.
        let starvation_choice = self
            .queues
            .iter()
            .filter_map(|(key, queue)| {
                if queue.is_empty() {
                    return None;
                }
                let rounds_since_dispatch = self.rounds_since_dispatch(key, current_round);
                (rounds_since_dispatch >= self.fairness_policy.starvation_round_threshold)
                    .then_some((key.clone(), rounds_since_dispatch))
            })
            .max_by(|(ka, ra), (kb, rb)| ra.cmp(rb).then_with(|| compare_keys(ka, kb)));

        if let Some((key, _)) = starvation_choice {
            return Some((key, DispatchReasonCode::StarvationPrevention));
        }

        self.queues
            .iter()
            .filter(|(_, queue)| !queue.is_empty())
            .map(|(key, _)| {
                let lag = self.compute_entity_fairness_lag_millis(key, current_round);
                let depth = self.queues.get(key).map_or(0, QueueState::depth);
                (key.clone(), lag, depth)
            })
            .max_by(|(ka, laga, deptha), (kb, lagb, depthb)| {
                laga.cmp(lagb)
                    .then_with(|| deptha.cmp(depthb))
                    .then_with(|| compare_keys(ka, kb))
            })
            .map(|(key, _, _)| (key, DispatchReasonCode::WeightedFairness))
    }

    fn rounds_since_dispatch(&self, key: &FairnessKey, current_round: u64) -> u64 {
        match self.last_dispatch_round.get(key) {
            Some(round) => current_round.saturating_sub(*round),
            None => current_round,
        }
    }

    fn compute_entity_fairness_lag_millis(&self, key: &FairnessKey, round: u64) -> u64 {
        let total_weight = self.total_active_weight();
        if total_weight == 0 {
            return 0;
        }

        let entity_weight = self.weight_for_key(key) as u128;
        let expected_times_weight = round as u128 * entity_weight;
        let expected_millis = (expected_times_weight * 1_000) / total_weight as u128;

        let actual = *self.dispatch_by_entity.get(key).unwrap_or(&0) as u128;
        let actual_millis = actual * 1_000;

        expected_millis.saturating_sub(actual_millis) as u64
    }

    fn total_active_weight(&self) -> u64 {
        self.queues
            .iter()
            .filter(|(_, queue)| !queue.is_empty())
            .map(|(key, _)| self.weight_for_key(key))
            .sum()
    }

    fn weight_for_key(&self, _key: &FairnessKey) -> u64 {
        self.fairness_policy.default_tenant_weight as u64
            * self.fairness_policy.default_project_weight as u64
    }

    fn decrement_counter<K: std::cmp::Eq + std::hash::Hash + Clone>(
        map: &mut HashMap<K, usize>,
        key: K,
    ) {
        if let Some(value) = map.get_mut(&key) {
            *value = value.saturating_sub(1);
            if *value == 0 {
                map.remove(&key);
            }
        }
    }
}

fn score_candidate(
    candidate: &DeviceScoreInput,
    policy: DeviceScoringPolicy,
) -> DeviceScoreBreakdown {
    let queue_depth_max = policy.max_queue_depth.max(1) as f64;
    let latency_target = policy.target_latency_ms.max(1) as f64;
    let calibration_ttl = policy.calibration_ttl_sec.max(1) as f64;

    let queue_depth_score = bounded_ratio(1.0 - (candidate.queue_depth as f64 / queue_depth_max));
    let latency_score = bounded_ratio(1.0 - (candidate.recent_latency_ms as f64 / latency_target));
    let calibration_score =
        bounded_ratio(1.0 - (candidate.calibration_age_sec as f64 / calibration_ttl));
    let availability_score = match candidate.health_status {
        DeviceHealthStatus::Healthy => 1.0,
        DeviceHealthStatus::Degraded => 0.5,
        DeviceHealthStatus::Unavailable => 0.0,
    };

    let queue_depth_score_millis = weighted_millis(queue_depth_score, policy.queue_depth_weight);
    let latency_score_millis = weighted_millis(latency_score, policy.latency_weight);
    let calibration_score_millis = weighted_millis(calibration_score, policy.calibration_weight);
    let availability_score_millis = weighted_millis(availability_score, policy.availability_weight);
    let total_score_millis = queue_depth_score_millis
        + latency_score_millis
        + calibration_score_millis
        + availability_score_millis;

    DeviceScoreBreakdown {
        version: DEVICE_SCORE_VERSION,
        device_id: candidate.device_id.clone(),
        total_score_millis,
        queue_depth_score_millis,
        latency_score_millis,
        calibration_score_millis,
        availability_score_millis,
    }
}

/// Scores backend candidates using the Phase-4 deterministic scoring contract.
pub fn score_backend_candidates(
    decision_id: &str,
    workload: &BackendWorkloadDescriptor,
    runtime: &BackendRuntimeDescriptor,
    candidates: &[BackendCandidateDescriptor],
    profile: &BackendScoringProfile,
) -> BackendScoringDecisionArtifact {
    let mut candidate_scores: Vec<BackendScoreCandidate> = candidates
        .iter()
        .map(|candidate| {
            let missing_feature = workload
                .required_features
                .iter()
                .find(|required| !candidate.supported_features.contains(*required))
                .cloned();
            let unavailable = candidate.availability <= 0.0;
            let ineligibility_reason = if unavailable {
                Some("backend_unavailable")
            } else if missing_feature.is_some() {
                Some("missing_required_feature")
            } else {
                None
            };

            let queue_signal = bounded_ratio(
                1.0 - (candidate.queue_length as f64 / profile.max_queue_length.max(1) as f64),
            );
            let latency_signal = bounded_ratio(
                1.0 - (candidate.historical_latency_ms as f64
                    / profile.target_latency_ms.max(1) as f64),
            );
            let success_signal = bounded_ratio(candidate.historical_success_rate);
            let fidelity_signal = bounded_ratio(candidate.historical_fidelity);
            let availability_signal = bounded_ratio(candidate.availability);
            let calibration_signal = bounded_ratio(
                1.0 - (candidate.calibration_age_sec as f64
                    / profile.calibration_ttl_sec.max(1) as f64),
            );
            let cost_signal = bounded_ratio(
                1.0 - ((workload.cost_sensitivity * candidate.queue_length as f64)
                    / profile.max_queue_length.max(1) as f64),
            );
            let retry_penalty = (runtime.retry_count.min(3) as u64) * 5;
            let warm_cache_bonus = if runtime.warm_cache_hit { 10 } else { 0 };

            let mut contributions = vec![
                BackendFeatureContribution {
                    feature: "queue_length",
                    contribution_millis: weighted_millis(queue_signal, profile.queue_weight),
                },
                BackendFeatureContribution {
                    feature: "historical_latency",
                    contribution_millis: weighted_millis(latency_signal, profile.latency_weight),
                },
                BackendFeatureContribution {
                    feature: "historical_success_rate",
                    contribution_millis: weighted_millis(success_signal, profile.success_weight),
                },
                BackendFeatureContribution {
                    feature: "historical_fidelity",
                    contribution_millis: weighted_millis(fidelity_signal, profile.fidelity_weight),
                },
                BackendFeatureContribution {
                    feature: "availability",
                    contribution_millis: weighted_millis(
                        availability_signal,
                        profile.availability_weight,
                    ),
                },
                BackendFeatureContribution {
                    feature: "calibration_age",
                    contribution_millis: weighted_millis(
                        calibration_signal,
                        profile.calibration_weight,
                    ),
                },
                BackendFeatureContribution {
                    feature: "cost_sensitivity",
                    contribution_millis: weighted_millis(cost_signal, profile.cost_weight),
                },
                BackendFeatureContribution {
                    feature: "runtime_retry_penalty",
                    contribution_millis: retry_penalty,
                },
                BackendFeatureContribution {
                    feature: "runtime_warm_cache_bonus",
                    contribution_millis: warm_cache_bonus,
                },
            ];

            let mut score_millis = contributions
                .iter()
                .map(|item| item.contribution_millis)
                .sum::<u64>();
            if unavailable || missing_feature.is_some() {
                score_millis = 0;
                contributions.push(BackendFeatureContribution {
                    feature: "ineligibility_zero_out",
                    contribution_millis: 0,
                });
            }

            BackendScoreCandidate {
                backend_id: candidate.backend_id.clone(),
                score_millis,
                eligible: ineligibility_reason.is_none(),
                ineligibility_reason,
                feature_contributions: contributions,
            }
        })
        .collect();

    let candidate_priority: BTreeMap<&str, (i32, i32)> = candidates
        .iter()
        .map(|candidate| {
            (
                candidate.backend_id.as_str(),
                (candidate.policy_priority, candidate.capability_rank),
            )
        })
        .collect();
    candidate_scores.sort_by(|left, right| {
        let (left_policy, left_rank) = candidate_priority
            .get(left.backend_id.as_str())
            .copied()
            .unwrap_or((i32::MAX, i32::MAX));
        let (right_policy, right_rank) = candidate_priority
            .get(right.backend_id.as_str())
            .copied()
            .unwrap_or((i32::MAX, i32::MAX));
        right
            .score_millis
            .cmp(&left.score_millis)
            .then_with(|| left_policy.cmp(&right_policy))
            .then_with(|| left_rank.cmp(&right_rank))
            .then_with(|| left.backend_id.cmp(&right.backend_id))
    });

    let top = candidate_scores
        .iter()
        .find(|candidate| candidate.eligible && candidate.score_millis > 0);
    let tie_break_trace = if let Some(top_candidate) = top {
        let tied: Vec<&BackendScoreCandidate> = candidate_scores
            .iter()
            .filter(|candidate| {
                candidate.eligible && candidate.score_millis == top_candidate.score_millis
            })
            .collect();
        if tied.len() <= 1 {
            vec!["score-desc".to_string()]
        } else {
            vec![
                "score-desc".to_string(),
                "policy-priority-asc".to_string(),
                "capability-rank-asc".to_string(),
                "backend-id-lex-asc".to_string(),
            ]
        }
    } else {
        vec!["no-eligible-backend".to_string()]
    };

    BackendScoringDecisionArtifact {
        scoring_contract_version: BACKEND_SCORING_CONTRACT_VERSION,
        profile_schema_version: BACKEND_SCORING_PROFILE_SCHEMA_VERSION,
        profile_version: profile.profile_version.clone(),
        decision_id: decision_id.to_string(),
        selected_backend_id: top.map(|candidate| candidate.backend_id.clone()),
        candidates: candidate_scores,
        tie_break_trace,
    }
}

/// Builds a stable `/explain/backend-selection` envelope from a scoring artifact.
pub fn explain_backend_selection(
    request: &ExplainBackendSelectionRequest,
    decision: &BackendScoringDecisionArtifact,
) -> ExplainBackendSelectionResponse {
    let mut eligible_scores: Vec<u64> = decision
        .candidates
        .iter()
        .filter(|candidate| candidate.eligible)
        .map(|candidate| candidate.score_millis)
        .collect();
    eligible_scores.sort_by(|left, right| right.cmp(left));

    let selected_score_millis = eligible_scores.first().copied().unwrap_or(0);
    let runner_up_score_millis = eligible_scores.get(1).copied().unwrap_or(0);
    let score_margin_millis = selected_score_millis.saturating_sub(runner_up_score_millis);
    let confidence = if selected_score_millis == 0 {
        0.0
    } else {
        score_margin_millis as f64 / selected_score_millis as f64
    };

    let mut candidate_scores = decision.candidates.clone();
    if !request.include_rejected_candidates {
        candidate_scores.retain(|candidate| candidate.eligible);
    }

    let mut factor_contributions: Vec<ExplainFactorContribution> = candidate_scores
        .iter()
        .flat_map(|candidate| {
            candidate
                .feature_contributions
                .iter()
                .map(|feature| ExplainFactorContribution {
                    backend_id: candidate.backend_id.clone(),
                    factor: feature.feature,
                    contribution_millis: feature.contribution_millis,
                })
                .collect::<Vec<_>>()
        })
        .collect();
    factor_contributions.sort_by(|left, right| {
        left.backend_id
            .cmp(&right.backend_id)
            .then_with(|| left.factor.cmp(right.factor))
    });

    ExplainBackendSelectionResponse {
        explain_contract_version: BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION,
        request_version: request.request_version,
        response_version: request.response_version,
        scoring_contract_version: decision.scoring_contract_version,
        profile_schema_version: decision.profile_schema_version,
        profile_version: decision.profile_version.clone(),
        decision_id: decision.decision_id.clone(),
        selected_backend_id: decision.selected_backend_id.clone(),
        tie_break_trace: decision.tie_break_trace.clone(),
        candidate_scores,
        factor_contributions,
        confidence: ExplainConfidenceMetadata {
            score_margin_millis,
            selected_score_millis,
            runner_up_score_millis,
            confidence,
        },
    }
}

fn weighted_millis(signal: f64, weight: f64) -> u64 {
    let bounded_weight = bounded_ratio(weight);
    (bounded_ratio(signal) * bounded_weight * 1_000.0).round() as u64
}

fn is_semver_like(version: &str) -> bool {
    let parts: Vec<&str> = version.split('.').collect();
    parts.len() == 3
        && parts
            .iter()
            .all(|part| !part.is_empty() && part.chars().all(|ch| ch.is_ascii_digit()))
}

fn compare_policy_candidates(
    left: &PolicyCandidate,
    right: &PolicyCandidate,
    bundle: &PolicyBundle,
) -> Ordering {
    let left_correctness = bounded_ratio(left.correctness_score);
    let right_correctness = bounded_ratio(right.correctness_score);
    let left_user = policy_user_intent_score(left, bundle);
    let right_user = policy_user_intent_score(right, bundle);
    let left_ops = policy_operational_score(left, bundle.policy_mode);
    let right_ops = policy_operational_score(right, bundle.policy_mode);
    let left_hint = bounded_ratio(left.learning_hint_score);
    let right_hint = bounded_ratio(right.learning_hint_score);

    right_correctness
        .partial_cmp(&left_correctness)
        .unwrap_or(Ordering::Equal)
        .then_with(|| {
            right_user
                .partial_cmp(&left_user)
                .unwrap_or(Ordering::Equal)
        })
        .then_with(|| right_ops.partial_cmp(&left_ops).unwrap_or(Ordering::Equal))
        .then_with(|| {
            right_hint
                .partial_cmp(&left_hint)
                .unwrap_or(Ordering::Equal)
        })
        .then_with(|| left.candidate_id.cmp(&right.candidate_id))
}

fn policy_user_intent_score(candidate: &PolicyCandidate, bundle: &PolicyBundle) -> f64 {
    let latency_signal = bounded_ratio(1.0 - (candidate.latency_ms as f64 / 10_000.0));
    let cost_signal = bounded_ratio(1.0 - (candidate.cost_units as f64 / 10_000.0));
    let throughput_signal = bounded_ratio(candidate.throughput_qps as f64 / 10_000.0);
    let determinism_signal = if candidate.deterministic { 1.0 } else { 0.0 };

    bounded_ratio(candidate.fidelity_score) * bundle.user_intent_weights.fidelity
        + latency_signal * bundle.user_intent_weights.latency
        + cost_signal * bundle.user_intent_weights.cost
        + throughput_signal * bundle.user_intent_weights.throughput
        + determinism_signal * bundle.user_intent_weights.determinism
        + bounded_ratio(candidate.debuggability_score) * bundle.user_intent_weights.debuggability
}

fn policy_operational_score(candidate: &PolicyCandidate, mode: PolicyMode) -> f64 {
    let latency_signal = bounded_ratio(1.0 - (candidate.latency_ms as f64 / 10_000.0));
    let cost_signal = bounded_ratio(1.0 - (candidate.cost_units as f64 / 10_000.0));
    let throughput_signal = bounded_ratio(candidate.throughput_qps as f64 / 10_000.0);

    match mode {
        PolicyMode::Latency => {
            latency_signal * 0.65 + throughput_signal * 0.25 + cost_signal * 0.10
        }
        PolicyMode::Throughput => {
            throughput_signal * 0.70 + latency_signal * 0.20 + cost_signal * 0.10
        }
        PolicyMode::Cost => cost_signal * 0.70 + latency_signal * 0.20 + throughput_signal * 0.10,
        PolicyMode::Balanced => {
            latency_signal * 0.34 + throughput_signal * 0.33 + cost_signal * 0.33
        }
    }
}

fn bounded_ratio(value: f64) -> f64 {
    value.clamp(0.0, 1.0)
}

fn compare_keys(a: &FairnessKey, b: &FairnessKey) -> Ordering {
    a.tenant_id
        .cmp(&b.tenant_id)
        .then_with(|| a.project_id.cmp(&b.project_id))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    fn strict_policy() -> AdmissionPolicy {
        AdmissionPolicy {
            max_total_queue_depth: 10,
            max_per_priority_queue_depth: 10,
            max_per_tenant_queue_depth: 3,
            max_per_project_queue_depth: 10,
            defer_at_total_queue_depth: 9,
        }
    }

    fn fairness_policy() -> FairnessPolicy {
        FairnessPolicy {
            default_tenant_weight: 1,
            default_project_weight: 1,
            starvation_round_threshold: 3,
        }
    }

    #[test]
    fn quota_rejections_are_reported_in_metrics() {
        let mut scheduler = Scheduler::new(
            AdmissionPolicy {
                max_total_queue_depth: 100,
                max_per_priority_queue_depth: 100,
                max_per_tenant_queue_depth: 1,
                max_per_project_queue_depth: 1,
                defer_at_total_queue_depth: 99,
            },
            fairness_policy(),
        );

        let first = scheduler.submit(ScheduledJob {
            job_id: "j1".to_string(),
            tenant_id: "t1".to_string(),
            project_id: "p1".to_string(),
            priority: 5,
        });
        assert_eq!(first.reason_code, AdmissionReasonCode::Accepted);

        let tenant_denied = scheduler.submit(ScheduledJob {
            job_id: "j2".to_string(),
            tenant_id: "t1".to_string(),
            project_id: "p2".to_string(),
            priority: 5,
        });
        assert_eq!(
            tenant_denied.reason_code,
            AdmissionReasonCode::RejectedTenantQuota
        );

        let project_denied = scheduler.submit(ScheduledJob {
            job_id: "j3".to_string(),
            tenant_id: "t2".to_string(),
            project_id: "p1".to_string(),
            priority: 5,
        });
        assert_eq!(
            project_denied.reason_code,
            AdmissionReasonCode::RejectedProjectQuota
        );

        let metrics = scheduler.metrics();
        assert_eq!(metrics.quota_denied_tenant_total, 1);
        assert_eq!(metrics.quota_denied_project_total, 1);
    }

    #[test]
    fn dispatch_uses_weighted_fairness_and_publishes_lag_metrics() {
        let mut scheduler = Scheduler::new(strict_policy(), fairness_policy());

        for idx in 0..3 {
            scheduler.submit(ScheduledJob {
                job_id: format!("a-{idx}"),
                tenant_id: "tenant-a".to_string(),
                project_id: "proj-a".to_string(),
                priority: 9,
            });
            scheduler.submit(ScheduledJob {
                job_id: format!("b-{idx}"),
                tenant_id: "tenant-b".to_string(),
                project_id: "proj-b".to_string(),
                priority: 1,
            });
        }

        let mut seen_a = 0;
        let mut seen_b = 0;

        for _ in 0..6 {
            let decision = scheduler.dispatch_next();
            assert_eq!(decision.version, SCHEDULER_DECISION_VERSION);
            assert_eq!(decision.reason_code, DispatchReasonCode::WeightedFairness);
            match decision.selected_tenant_id.as_deref() {
                Some("tenant-a") => seen_a += 1,
                Some("tenant-b") => seen_b += 1,
                other => panic!("unexpected tenant in dispatch: {other:?}"),
            }
        }

        assert_eq!(seen_a, 3);
        assert_eq!(seen_b, 3);

        let metrics = scheduler.metrics();
        assert!(metrics.fairness_lag_millis_total > 0);
        assert!(metrics.fairness_lag_millis_max > 0);
    }

    #[test]
    fn starvation_prevention_forces_dispatch_after_threshold() {
        let mut scheduler = Scheduler::new(
            strict_policy(),
            FairnessPolicy {
                default_tenant_weight: 1,
                default_project_weight: 1,
                starvation_round_threshold: 2,
            },
        );

        scheduler.submit(ScheduledJob {
            job_id: "cold-0".to_string(),
            tenant_id: "cold-tenant".to_string(),
            project_id: "cold-project".to_string(),
            priority: 1,
        });
        
        for idx in 0..3 {
            scheduler.submit(ScheduledJob {
                job_id: format!("hot-{idx}"),
                tenant_id: "hot-tenant".to_string(),
                project_id: "hot-project".to_string(),
                priority: 9,
            });
        }

        // First dispatch can pick hot tenant due higher lag tie-break on depth.
        let _ = scheduler.dispatch_next();
        // Second dispatch must invoke starvation prevention for cold tenant.
        let second = scheduler.dispatch_next();
        assert_eq!(second.reason_code, DispatchReasonCode::StarvationPrevention);
        assert_eq!(second.selected_tenant_id.as_deref(), Some("cold-tenant"));

        let metrics = scheduler.metrics();
        assert_eq!(metrics.starvation_prevention_total, 1);
    }

    #[test]
    fn empty_queue_returns_versioned_empty_decision() {
        let mut scheduler = Scheduler::new(strict_policy(), fairness_policy());
        let empty = scheduler.dispatch_next();
        assert_eq!(empty.version, SCHEDULER_DECISION_VERSION);
        assert_eq!(empty.reason_code, DispatchReasonCode::QueueEmpty);
        assert!(empty.selected_job_id.is_none());
        assert!(empty.device_dispatch.is_none());
    }

    #[test]
    fn device_score_is_loaded_from_fixtures() {
        let scheduler = Scheduler::new(strict_policy(), fairness_policy());
        let fixture = include_str!("../tests/fixtures/device_score_fixtures.csv");
        let mut candidates = Vec::new();

        for line in fixture.lines().skip(1) {
            if line.trim().is_empty() {
                continue;
            }
            let columns: Vec<&str> = line.split(',').collect();
            assert_eq!(columns.len(), 5);
            candidates.push(DeviceScoreInput {
                device_id: columns[0].to_string(),
                queue_depth: usize::from_str(columns[1]).expect("queue_depth must be usize"),
                recent_latency_ms: u64::from_str(columns[2]).expect("latency must be u64"),
                calibration_age_sec: u64::from_str(columns[3])
                    .expect("calibration_age_sec must be u64"),
                health_status: match columns[4] {
                    "healthy" => DeviceHealthStatus::Healthy,
                    "degraded" => DeviceHealthStatus::Degraded,
                    "unavailable" => DeviceHealthStatus::Unavailable,
                    other => panic!("unknown health status: {other}"),
                },
            });
        }

        let record = scheduler
            .score_devices(&candidates, DeviceScoringPolicy::default())
            .expect("fixture must contain candidates");
        assert_eq!(record.version, DEVICE_SCORE_VERSION);
        assert_eq!(record.selected_device_id, "ionq-qpu-1");
        assert_eq!(record.reason_code, DispatchReasonCode::DeviceScore);
        assert_eq!(record.score_breakdown.len(), 3);
        assert!(
            record.score_breakdown[0].total_score_millis
                > record.score_breakdown[1].total_score_millis
        );
    }

    #[test]
    fn tie_breaker_is_deterministic_by_device_id() {
        let scheduler = Scheduler::new(strict_policy(), fairness_policy());
        let candidates = vec![
            DeviceScoreInput {
                device_id: "device-b".to_string(),
                queue_depth: 10,
                recent_latency_ms: 1000,
                calibration_age_sec: 200,
                health_status: DeviceHealthStatus::Healthy,
            },
            DeviceScoreInput {
                device_id: "device-a".to_string(),
                queue_depth: 10,
                recent_latency_ms: 1000,
                calibration_age_sec: 200,
                health_status: DeviceHealthStatus::Healthy,
            },
        ];

        let record = scheduler
            .score_devices(&candidates, DeviceScoringPolicy::default())
            .expect("candidates must produce score");
        assert_eq!(record.reason_code, DispatchReasonCode::DeviceScoreTieBreak);
        assert_eq!(record.selected_device_id, "device-a");
    }

    fn backend_workload() -> BackendWorkloadDescriptor {
        BackendWorkloadDescriptor {
            job_type: "sampling".to_string(),
            priority: 5,
            shots: 8_000,
            circuit_depth: 120,
            circuit_width: 20,
            estimated_runtime_ms: 900,
            noise_sensitivity: 0.8,
            cost_sensitivity: 0.3,
            required_features: vec!["dynamic-circuits".to_string()],
        }
    }

    fn backend_runtime() -> BackendRuntimeDescriptor {
        BackendRuntimeDescriptor {
            current_cluster_load: 0.4,
            retry_count: 1,
            warm_cache_hit: true,
        }
    }

    fn policy_candidates_fixture() -> Vec<PolicyCandidate> {
        vec![
            PolicyCandidate {
                candidate_id: "cand-fast".to_string(),
                hard_constraint_satisfied: true,
                correctness_score: 0.94,
                fidelity_score: 0.90,
                latency_ms: 700,
                cost_units: 300,
                throughput_qps: 500,
                deterministic: true,
                debuggability_score: 0.8,
                learning_hint_score: 0.2,
            },
            PolicyCandidate {
                candidate_id: "cand-cheap".to_string(),
                hard_constraint_satisfied: true,
                correctness_score: 0.94,
                fidelity_score: 0.89,
                latency_ms: 950,
                cost_units: 120,
                throughput_qps: 450,
                deterministic: true,
                debuggability_score: 0.85,
                learning_hint_score: 0.9,
            },
            PolicyCandidate {
                candidate_id: "cand-blocked".to_string(),
                hard_constraint_satisfied: false,
                correctness_score: 1.0,
                fidelity_score: 1.0,
                latency_ms: 10,
                cost_units: 10,
                throughput_qps: 1_000,
                deterministic: true,
                debuggability_score: 1.0,
                learning_hint_score: 1.0,
            },
        ]
    }

    #[test]
    fn policy_bundle_validation_enforces_semver_priority_and_weights() {
        let mut invalid = PolicyBundle::default();
        invalid.policy_bundle_version = "v1".to_string();
        assert_eq!(
            validate_policy_bundle(&invalid),
            Err(PolicyBundleValidationError::InvalidBundleVersion)
        );

        invalid.policy_bundle_version = "1.0.0".to_string();
        invalid.policy_priority_map.correctness = 101;
        assert_eq!(
            validate_policy_bundle(&invalid),
            Err(PolicyBundleValidationError::InvalidPriorityOrder)
        );

        invalid.policy_priority_map = PolicyPriorityMap::default();
        invalid.user_intent_weights.cost = f64::NAN;
        assert_eq!(
            validate_policy_bundle(&invalid),
            Err(PolicyBundleValidationError::InvalidWeight { field: "cost" })
        );
    }

    #[test]
    fn policy_resolution_is_deterministic_and_reproducible() {
        let bundle = PolicyBundle {
            policy_bundle_id: "latency".to_string(),
            policy_bundle_version: "1.0.0".to_string(),
            policy_mode: PolicyMode::Latency,
            policy_priority_map: PolicyPriorityMap::default(),
            user_intent_weights: UserIntentWeights {
                fidelity: 0.8,
                latency: 1.4,
                cost: 0.2,
                throughput: 0.8,
                determinism: 0.9,
                debuggability: 0.85,
            },
        };
        let candidates = policy_candidates_fixture();

        let first = resolve_policy_bundle(Some(&bundle), &candidates);
        let second = resolve_policy_bundle(Some(&bundle), &candidates);
        assert_eq!(first, second);
        assert_eq!(first.selected_candidate_id.as_deref(), Some("cand-fast"));
        assert!(!first.fallback_applied);
        assert_eq!(first.version, SCHEDULING_POLICY_RESOLUTION_VERSION);
        assert_eq!(
            first.policy_bundle_schema_version,
            SCHEDULING_POLICY_BUNDLE_SCHEMA_VERSION
        );
    }

    #[test]
    fn policy_resolution_falls_back_for_missing_or_invalid_bundle() {
        let candidates = policy_candidates_fixture();
        let missing = resolve_policy_bundle(None, &candidates);
        assert!(missing.fallback_applied);
        assert_eq!(
            missing.fallback_reason.as_deref(),
            Some("missing_policy_bundle")
        );
        assert_eq!(missing.policy_bundle_id, "balanced");
        assert_eq!(missing.policy_bundle_version, "1.0.0");

        let mut invalid = PolicyBundle::default();
        invalid.policy_bundle_version = "invalid".to_string();
        let invalid_result = resolve_policy_bundle(Some(&invalid), &candidates);
        assert!(invalid_result.fallback_applied);
        assert_eq!(
            invalid_result.error_code,
            Some(PolicyResolutionErrorCode::PolicyBundleInvalid)
        );
        assert_eq!(
            invalid_result.fallback_reason.as_deref(),
            Some("invalid_policy_bundle")
        );
    }

    #[test]
    fn policy_resolution_returns_safe_empty_selection_when_no_viable_candidate() {
        let no_viable = vec![PolicyCandidate {
            candidate_id: "blocked".to_string(),
            hard_constraint_satisfied: false,
            correctness_score: 0.99,
            fidelity_score: 0.99,
            latency_ms: 100,
            cost_units: 100,
            throughput_qps: 100,
            deterministic: true,
            debuggability_score: 0.5,
            learning_hint_score: 0.5,
        }];

        let decision = resolve_policy_bundle(Some(&PolicyBundle::default()), &no_viable);
        assert!(decision.selected_candidate_id.is_none());
        assert!(decision.fallback_applied);
        assert_eq!(
            decision.fallback_reason.as_deref(),
            Some("no_viable_candidate")
        );
        assert_eq!(
            decision.error_code,
            Some(PolicyResolutionErrorCode::PolicyResolutionFailed)
        );
    }

    #[test]
    fn backend_scoring_is_deterministic_for_identical_input() {
        let workload = backend_workload();
        let runtime = backend_runtime();
        let profile = BackendScoringProfile::default();
        let candidates = vec![
            BackendCandidateDescriptor {
                backend_id: "backend-z".to_string(),
                backend_type: "qpu".to_string(),
                qubit_count: 32,
                availability: 0.9,
                queue_length: 40,
                historical_latency_ms: 1_500,
                historical_success_rate: 0.97,
                historical_fidelity: 0.95,
                error_rate: 0.03,
                calibration_age_sec: 500,
                policy_priority: 2,
                capability_rank: 2,
                supported_features: vec!["dynamic-circuits".to_string()],
            },
            BackendCandidateDescriptor {
                backend_id: "backend-a".to_string(),
                backend_type: "qpu".to_string(),
                qubit_count: 24,
                availability: 0.95,
                queue_length: 20,
                historical_latency_ms: 1_000,
                historical_success_rate: 0.98,
                historical_fidelity: 0.97,
                error_rate: 0.02,
                calibration_age_sec: 350,
                policy_priority: 1,
                capability_rank: 1,
                supported_features: vec!["dynamic-circuits".to_string()],
            },
        ];

        let first =
            score_backend_candidates("decision-001", &workload, &runtime, &candidates, &profile);
        let second =
            score_backend_candidates("decision-001", &workload, &runtime, &candidates, &profile);
        assert_eq!(first, second);
    }

    #[test]
    fn backend_scoring_tie_break_policy_is_explicit_and_stable() {
        let workload = backend_workload();
        let runtime = backend_runtime();
        let profile = BackendScoringProfile::default();
        let candidates = vec![
            BackendCandidateDescriptor {
                backend_id: "backend-b".to_string(),
                backend_type: "qpu".to_string(),
                qubit_count: 20,
                availability: 1.0,
                queue_length: 0,
                historical_latency_ms: 0,
                historical_success_rate: 1.0,
                historical_fidelity: 1.0,
                error_rate: 0.0,
                calibration_age_sec: 0,
                policy_priority: 2,
                capability_rank: 3,
                supported_features: vec!["dynamic-circuits".to_string()],
            },
            BackendCandidateDescriptor {
                backend_id: "backend-a".to_string(),
                backend_type: "qpu".to_string(),
                qubit_count: 20,
                availability: 1.0,
                queue_length: 0,
                historical_latency_ms: 0,
                historical_success_rate: 1.0,
                historical_fidelity: 1.0,
                error_rate: 0.0,
                calibration_age_sec: 0,
                policy_priority: 1,
                capability_rank: 1,
                supported_features: vec!["dynamic-circuits".to_string()],
            },
        ];

        let decision =
            score_backend_candidates("decision-002", &workload, &runtime, &candidates, &profile);
        assert_eq!(decision.selected_backend_id.as_deref(), Some("backend-a"));
        assert_eq!(
            decision.tie_break_trace,
            vec![
                "score-desc".to_string(),
                "policy-priority-asc".to_string(),
                "capability-rank-asc".to_string(),
                "backend-id-lex-asc".to_string(),
            ]
        );
    }

    #[test]
    fn backend_scoring_output_has_contract_and_profile_versions() {
        let workload = backend_workload();
        let runtime = backend_runtime();
        let profile = BackendScoringProfile::default();
        let candidates = vec![BackendCandidateDescriptor {
            backend_id: "backend-a".to_string(),
            backend_type: "qpu".to_string(),
            qubit_count: 24,
            availability: 0.9,
            queue_length: 10,
            historical_latency_ms: 1_100,
            historical_success_rate: 0.98,
            historical_fidelity: 0.96,
            error_rate: 0.01,
            calibration_age_sec: 100,
            policy_priority: 1,
            capability_rank: 1,
            supported_features: vec!["dynamic-circuits".to_string()],
        }];

        let decision =
            score_backend_candidates("decision-003", &workload, &runtime, &candidates, &profile);
        assert_eq!(
            decision.scoring_contract_version,
            BACKEND_SCORING_CONTRACT_VERSION
        );
        assert_eq!(
            decision.profile_schema_version,
            BACKEND_SCORING_PROFILE_SCHEMA_VERSION
        );
        assert_eq!(decision.profile_version, "1.0.0");
    }

    #[test]
    fn backend_scoring_profile_store_persists_versioned_profiles() {
        let mut store = BackendScoringProfileStore::default();
        let mut profile = BackendScoringProfile::default();
        profile.profile_version = "1.1.0".to_string();
        profile.queue_weight = 0.25;
        store.save(profile.clone());

        let loaded = store
            .load("balanced", "1.1.0")
            .expect("profile must load by id + version");
        assert_eq!(loaded, profile);
        assert!(store.load("balanced", "9.9.9").is_none());
    }

    #[test]
    fn rebalance_trigger_and_preemption_requeue_are_safe_and_idempotent() {
        let mut scheduler = Scheduler::new(strict_policy(), fairness_policy())
            .with_preemption_policy(PreemptionPolicy {
                min_dispatch_rounds_before_preempt: 0,
                max_preemptions_per_job: 2,
            });
        scheduler.submit(ScheduledJob {
            job_id: "job-1".to_string(),
            tenant_id: "tenant-a".to_string(),
            project_id: "proj-a".to_string(),
            priority: 9,
        });

        let dispatch = scheduler.dispatch_next_with_device_scores(
            &[
                DeviceScoreInput {
                    device_id: "device-hot".to_string(),
                    queue_depth: 0,
                    recent_latency_ms: 100,
                    calibration_age_sec: 10,
                    health_status: DeviceHealthStatus::Healthy,
                },
                DeviceScoreInput {
                    device_id: "device-cold".to_string(),
                    queue_depth: 90,
                    recent_latency_ms: 2_000,
                    calibration_age_sec: 3_000,
                    health_status: DeviceHealthStatus::Degraded,
                },
            ],
            DeviceScoringPolicy::default(),
        );
        assert_eq!(dispatch.selected_job_id.as_deref(), Some("job-1"));
        assert_eq!(scheduler.queue_depth(), 0);
        assert_eq!(scheduler.active_dispatches(), 1);

        let plan = scheduler
            .plan_rebalance(
                &[
                    DeviceLoad {
                        device_id: "device-hot".to_string(),
                        load_ratio: 0.92,
                    },
                    DeviceLoad {
                        device_id: "device-cold".to_string(),
                        load_ratio: 0.15,
                    },
                ],
                RebalancingPolicy::default(),
            )
            .expect("rebalance must be triggered");
        assert_eq!(plan.version, REBALANCING_POLICY_VERSION);
        assert_eq!(plan.candidate_job_ids, vec!["job-1".to_string()]);

        let first = scheduler.preempt_for_rebalance("job-1", "rq-1");
        assert_eq!(
            first.reason_code,
            PreemptionReasonCode::RebalanceOverloadedDevice
        );
        assert_eq!(first.disposition, AdmissionDisposition::Admit);
        assert!(!first.idempotent);
        assert_eq!(scheduler.queue_depth(), 1);
        assert_eq!(scheduler.active_dispatches(), 0);

        let duplicate = scheduler.preempt_for_rebalance("job-1", "rq-1");
        assert_eq!(
            duplicate.reason_code,
            PreemptionReasonCode::DuplicateRequeueRequest
        );
        assert!(duplicate.idempotent);
        assert_eq!(scheduler.queue_depth(), 1);

        let next = scheduler.dispatch_next();
        assert_eq!(next.selected_job_id.as_deref(), Some("job-1"));
    }

    #[test]
    fn preemption_guardrails_block_thrashing() {
        let mut scheduler = Scheduler::new(strict_policy(), fairness_policy())
            .with_preemption_policy(PreemptionPolicy {
                min_dispatch_rounds_before_preempt: 2,
                max_preemptions_per_job: 1,
            });
        scheduler.submit(ScheduledJob {
            job_id: "job-guard".to_string(),
            tenant_id: "tenant-a".to_string(),
            project_id: "proj-a".to_string(),
            priority: 5,
        });
        let _ = scheduler.dispatch_next();

        let early = scheduler.preempt_for_rebalance("job-guard", "rq-early");
        assert_eq!(early.reason_code, PreemptionReasonCode::GuardrailMinRuntime);
        assert_eq!(early.disposition, AdmissionDisposition::Defer);

        scheduler.submit(ScheduledJob {
            job_id: "filler-1".to_string(),
            tenant_id: "tenant-b".to_string(),
            project_id: "proj-b".to_string(),
            priority: 5,
        });
        scheduler.submit(ScheduledJob {
            job_id: "filler-2".to_string(),
            tenant_id: "tenant-c".to_string(),
            project_id: "proj-c".to_string(),
            priority: 5,
        });
        let _ = scheduler.dispatch_next();
        let _ = scheduler.dispatch_next();

        let accepted = scheduler.preempt_for_rebalance("job-guard", "rq-ok");
        assert_eq!(
            accepted.reason_code,
            PreemptionReasonCode::RebalanceOverloadedDevice
        );
        let _ = scheduler.dispatch_next();
        scheduler.submit(ScheduledJob {
            job_id: "filler-3".to_string(),
            tenant_id: "tenant-d".to_string(),
            project_id: "proj-d".to_string(),
            priority: 5,
        });
        scheduler.submit(ScheduledJob {
            job_id: "filler-4".to_string(),
            tenant_id: "tenant-e".to_string(),
            project_id: "proj-e".to_string(),
            priority: 5,
        });
        let _ = scheduler.dispatch_next();
        let _ = scheduler.dispatch_next();
        let capped = scheduler.preempt_for_rebalance("job-guard", "rq-cap");
        assert_eq!(
            capped.reason_code,
            PreemptionReasonCode::GuardrailPreemptionCap
        );
        assert_eq!(capped.disposition, AdmissionDisposition::Reject);

        let metrics = scheduler.metrics();
        assert_eq!(metrics.preempted_total, 1);
        assert_eq!(metrics.requeued_total, 1);
        assert_eq!(metrics.preemption_attempted_total, 3);
        assert_eq!(metrics.requeue_idempotent_hits_total, 0);
    }
}
