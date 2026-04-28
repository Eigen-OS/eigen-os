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
/// SemVer version for rebalancing/preemption safety artifacts.
pub const REBALANCING_POLICY_VERSION: &str = "2.2.0";
/// SemVer version for multi-device split/merge execution contract artifacts.
///
/// Breaking changes to partial-result envelopes or merge semantics must bump MAJOR.
pub const MULTI_DEVICE_EXECUTION_CONTRACT_VERSION: &str = "2.0.0";

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

fn weighted_millis(signal: f64, weight: f64) -> u64 {
    let bounded_weight = bounded_ratio(weight);
    (bounded_ratio(signal) * bounded_weight * 1_000.0).round() as u64
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
