//! Resource manager scheduler core (Phase-2 baseline).
//!
//! This module implements Scheduler Core v1 with:
//! - priority queues with FIFO ordering per priority bucket
//! - configurable admission control (admit/defer/reject)
//! - observable scheduler decisions and health/metrics snapshots

#![forbid(unsafe_code)]

use std::collections::{BTreeMap, VecDeque};

/// SemVer version for scheduler decision DTOs/contracts.
///
/// Any breaking change to `SchedulerDecision`/`DispatchReasonCode`
/// must bump MAJOR according to Phase-2 policy.
pub const SCHEDULER_DECISION_VERSION: &str = "1.0.0";

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
}

/// Stable reason codes for dispatch outcomes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DispatchReasonCode {
    PriorityThenFifo,
    QueueEmpty,
}

/// Job envelope tracked by scheduler queues.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScheduledJob {
    pub job_id: String,
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
}

/// Dispatch decision DTO.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchedulerDecision {
    pub version: &'static str,
    pub selected_job_id: Option<String>,
    pub selected_priority: Option<u8>,
    pub queue_depth_after: usize,
    pub reason_code: DispatchReasonCode,
}

/// Scheduler configuration for admission control.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AdmissionPolicy {
    /// Maximum number of jobs across all queues.
    pub max_total_queue_depth: usize,
    /// Maximum number of jobs in any single priority queue.
    pub max_per_priority_queue_depth: usize,
    /// Once total depth reaches this threshold, admissions are deferred.
    pub defer_at_total_queue_depth: usize,
}

impl Default for AdmissionPolicy {
    fn default() -> Self {
        Self {
            max_total_queue_depth: 1_000,
            max_per_priority_queue_depth: 100,
            defer_at_total_queue_depth: 800,
        }
    }
}

/// Lightweight scheduler loop counters.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SchedulerMetrics {
    pub admitted_total: u64,
    pub deferred_total: u64,
    pub rejected_total: u64,
    pub dispatched_total: u64,
}

/// Health/status snapshot for health endpoints.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SchedulerHealth {
    pub healthy: bool,
    pub total_queue_depth: usize,
    pub distinct_priority_buckets: usize,
    pub metrics: SchedulerMetrics,
}

/// Priority scheduler (higher priority value wins, FIFO within priority).
#[derive(Debug)]
pub struct Scheduler {
    policy: AdmissionPolicy,
    queues: BTreeMap<u8, VecDeque<ScheduledJob>>,
    total_depth: usize,
    metrics: SchedulerMetrics,
}

impl Scheduler {
    pub fn new(policy: AdmissionPolicy) -> Self {
        Self {
            policy,
            queues: BTreeMap::new(),
            total_depth: 0,
            metrics: SchedulerMetrics::default(),
        }
    }

    pub fn admission_policy(&self) -> AdmissionPolicy {
        self.policy
    }

    pub fn queue_depth(&self) -> usize {
        self.total_depth
    }

    pub fn metrics(&self) -> SchedulerMetrics {
        self.metrics.clone()
    }

    pub fn health(&self) -> SchedulerHealth {
        SchedulerHealth {
            healthy: self.total_depth <= self.policy.max_total_queue_depth,
            total_queue_depth: self.total_depth,
            distinct_priority_buckets: self.queues.len(),
            metrics: self.metrics(),
        }
    }

    /// Evaluate admission without mutating queue state.
    pub fn evaluate_admission(&self, priority: u8) -> AdmissionDecision {
        let priority_depth = self.queues.get(&priority).map_or(0, VecDeque::len);

        let (disposition, reason_code) = if self.total_depth >= self.policy.max_total_queue_depth {
            (
                AdmissionDisposition::Reject,
                AdmissionReasonCode::RejectedGlobalQueueLimit,
            )
        } else if priority_depth >= self.policy.max_per_priority_queue_depth {
            (
                AdmissionDisposition::Reject,
                AdmissionReasonCode::RejectedPriorityQueueLimit,
            )
        } else if self.total_depth >= self.policy.defer_at_total_queue_depth {
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
        }
    }

    /// Attempts to enqueue a job according to admission control policy.
    pub fn submit(&mut self, job: ScheduledJob) -> AdmissionDecision {
        let decision = self.evaluate_admission(job.priority);
        match decision.disposition {
            AdmissionDisposition::Admit => {
                self.queues.entry(job.priority).or_default().push_back(job);
                self.total_depth += 1;
                self.metrics.admitted_total += 1;
            }
            AdmissionDisposition::Defer => {
                self.metrics.deferred_total += 1;
            }
            AdmissionDisposition::Reject => {
                self.metrics.rejected_total += 1;
            }
        }
        decision
    }

    /// Deterministically picks next job: highest priority first, FIFO inside bucket.
    pub fn dispatch_next(&mut self) -> SchedulerDecision {
        let maybe_priority = self.queues.keys().next_back().copied();

        if let Some(priority) = maybe_priority {
            let queue = self
                .queues
                .get_mut(&priority)
                .expect("priority key must exist while dispatching");
            let job = queue
                .pop_front()
                .expect("priority queue must have at least one job");
            if queue.is_empty() {
                self.queues.remove(&priority);
            }
            self.total_depth -= 1;
            self.metrics.dispatched_total += 1;

            SchedulerDecision {
                version: SCHEDULER_DECISION_VERSION,
                selected_job_id: Some(job.job_id),
                selected_priority: Some(priority),
                queue_depth_after: self.total_depth,
                reason_code: DispatchReasonCode::PriorityThenFifo,
            }
        } else {
            SchedulerDecision {
                version: SCHEDULER_DECISION_VERSION,
                selected_job_id: None,
                selected_priority: None,
                queue_depth_after: 0,
                reason_code: DispatchReasonCode::QueueEmpty,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn strict_policy() -> AdmissionPolicy {
        AdmissionPolicy {
            max_total_queue_depth: 3,
            max_per_priority_queue_depth: 2,
            defer_at_total_queue_depth: 2,
        }
    }

    #[test]
    fn dispatch_is_priority_then_fifo() {
        let mut scheduler = Scheduler::new(strict_policy());

        assert_eq!(
            scheduler.submit(ScheduledJob {
                job_id: "p5-first".to_string(),
                priority: 5,
            })
            .disposition,
            AdmissionDisposition::Admit
        );
        assert_eq!(
            scheduler.submit(ScheduledJob {
                job_id: "p9".to_string(),
                priority: 9,
            })
            .disposition,
            AdmissionDisposition::Admit
        );

        // Next submission is deferred due to defer threshold.
        assert_eq!(
            scheduler.submit(ScheduledJob {
                job_id: "p5-second".to_string(),
                priority: 5,
            })
            .disposition,
            AdmissionDisposition::Defer
        );

        let first = scheduler.dispatch_next();
        assert_eq!(first.selected_job_id.as_deref(), Some("p9"));
        assert_eq!(first.selected_priority, Some(9));
        assert_eq!(first.reason_code, DispatchReasonCode::PriorityThenFifo);

        let second = scheduler.dispatch_next();
        assert_eq!(second.selected_job_id.as_deref(), Some("p5-first"));

        let empty = scheduler.dispatch_next();
        assert_eq!(empty.reason_code, DispatchReasonCode::QueueEmpty);
        assert_eq!(empty.version, SCHEDULER_DECISION_VERSION);
    }

    #[test]
    fn admission_rejects_per_priority_and_global_limits() {
        let mut scheduler = Scheduler::new(AdmissionPolicy {
            max_total_queue_depth: 2,
            max_per_priority_queue_depth: 1,
            defer_at_total_queue_depth: 99,
        });

        let first = scheduler.submit(ScheduledJob {
            job_id: "a".to_string(),
            priority: 7,
        });
        assert_eq!(first.reason_code, AdmissionReasonCode::Accepted);

        let per_priority_reject = scheduler.submit(ScheduledJob {
            job_id: "b".to_string(),
            priority: 7,
        });
        assert_eq!(
            per_priority_reject.reason_code,
            AdmissionReasonCode::RejectedPriorityQueueLimit
        );

        let second_priority = scheduler.submit(ScheduledJob {
            job_id: "c".to_string(),
            priority: 6,
        });
        assert_eq!(second_priority.reason_code, AdmissionReasonCode::Accepted);

        let global_reject = scheduler.submit(ScheduledJob {
            job_id: "d".to_string(),
            priority: 1,
        });
        assert_eq!(
            global_reject.reason_code,
            AdmissionReasonCode::RejectedGlobalQueueLimit
        );
    }

    #[test]
    fn health_and_metrics_are_observable() {
        let mut scheduler = Scheduler::new(strict_policy());

        scheduler.submit(ScheduledJob {
            job_id: "a".to_string(),
            priority: 1,
        });
        scheduler.submit(ScheduledJob {
            job_id: "b".to_string(),
            priority: 2,
        });
        scheduler.submit(ScheduledJob {
            job_id: "c".to_string(),
            priority: 3,
        }); // deferred
        scheduler.dispatch_next();

        let metrics = scheduler.metrics();
        assert_eq!(metrics.admitted_total, 2);
        assert_eq!(metrics.deferred_total, 1);
        assert_eq!(metrics.rejected_total, 0);
        assert_eq!(metrics.dispatched_total, 1);

        let health = scheduler.health();
        assert!(health.healthy);
        assert_eq!(health.total_queue_depth, 1);
        assert_eq!(health.distinct_priority_buckets, 1);
        assert_eq!(health.metrics, metrics);
    }
}
