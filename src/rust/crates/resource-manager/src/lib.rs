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
pub const SCHEDULER_DECISION_VERSION: &str = "2.3.0";
pub const SCHEDULING_POLICY_BUNDLE_ID: &str = "balanced";
pub const SCHEDULING_POLICY_BUNDLE_VERSION: &str = "1.0.0";
/// SemVer version for device score DTOs/contracts.
pub const DEVICE_SCORE_VERSION: &str = "2.1.0";
/// SemVer version for backend scoring contract artifacts (Phase-4 intelligent runtime).
pub const BACKEND_SCORING_CONTRACT_VERSION: &str = "1.0.0";
/// SemVer schema version for persisted backend scoring profiles.
pub const BACKEND_SCORING_PROFILE_SCHEMA_VERSION: &str = "1.0.0";
/// SemVer schema version for backend-selection explain API request DTO.
pub const BACKEND_SELECTION_EXPLAIN_REQUEST_VERSION: &str = "1.1.0";
/// SemVer schema version for backend-selection explain API response envelope.
pub const BACKEND_SELECTION_EXPLAIN_RESPONSE_VERSION: &str = "1.1.0";
/// SemVer schema version for scheduling policy bundles (Phase-4 policy engine).
pub const SCHEDULING_POLICY_BUNDLE_SCHEMA_VERSION: &str = "1.0.0";
/// SemVer version for scheduling policy-resolution decision artifacts.
pub const SCHEDULING_POLICY_RESOLUTION_VERSION: &str = "1.2.0";
/// SemVer version for rebalancing/preemption safety artifacts.
pub const REBALANCING_POLICY_VERSION: &str = "2.2.0";
pub const MULTI_DEVICE_EXECUTION_CONTRACT_VERSION: &str = "3.1.0";
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
