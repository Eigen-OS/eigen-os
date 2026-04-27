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
}

/// Health/status snapshot for health endpoints.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchedulerHealth {
    pub healthy: bool,
    pub total_queue_depth: usize,
    pub fairness_entities: usize,
    pub metrics: SchedulerMetrics,
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
            metrics: SchedulerMetrics::default(),
        }
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
        }
        decision
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
}
