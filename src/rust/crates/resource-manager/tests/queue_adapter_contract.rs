use resource_manager::{
    DISTRIBUTED_QUEUE_CONTRACT_VERSION, InMemoryQueueAdapter, QUEUE_DEAD_LETTER_CONTRACT_VERSION,
    QUEUE_LEASE_EVENT_VERSION, QueueAdapter, QueueTaskEnvelope,
};

#[derive(Default)]
struct ExternalQueueAdapterStub {
    inner: InMemoryQueueAdapter,
}

impl QueueAdapter for ExternalQueueAdapterStub {
    fn enqueue(&mut self, task: QueueTaskEnvelope) -> Result<(), resource_manager::QueueAdapterError> {
        self.inner.enqueue(task)
    }

    fn lease(
        &mut self,
        queue_name: &str,
        worker_id: &str,
        now_ms: u64,
    ) -> Result<Option<resource_manager::QueueLeaseRecord>, resource_manager::QueueAdapterError> {
        self.inner.lease(queue_name, worker_id, now_ms)
    }

    fn ack(
        &mut self,
        lease_id: &str,
        worker_id: &str,
        now_ms: u64,
    ) -> Result<bool, resource_manager::QueueAdapterError> {
        self.inner.ack(lease_id, worker_id, now_ms)
    }

    fn requeue(
        &mut self,
        lease_id: &str,
        worker_id: &str,
        reason: &str,
        now_ms: u64,
    ) -> Result<bool, resource_manager::QueueAdapterError> {
        self.inner.requeue(lease_id, worker_id, reason, now_ms)
    }

    fn metrics(&self) -> resource_manager::QueueAdapterMetrics {
        self.inner.metrics()
    }

    fn dead_letters(&self) -> &[resource_manager::DeadLetterRecord] {
        self.inner.dead_letters()
    }
}

fn task(task_id: &str, max_attempts: u32) -> QueueTaskEnvelope {
    QueueTaskEnvelope {
        queue_contract_version: DISTRIBUTED_QUEUE_CONTRACT_VERSION,
        queue_name: "priority-50".to_string(),
        task_id: task_id.to_string(),
        job_id: format!("job-{task_id}"),
        assignment_id: format!("assignment-{task_id}"),
        idempotency_key: format!("idem-{task_id}"),
        tenant_id: "tenant-a".to_string(),
        project_id: "project-a".to_string(),
        attempt: 1,
        max_attempts,
        visibility_timeout_seconds: 10,
        enqueued_at_ms: 1000,
    }
}

fn run_contract_suite(name: &str, mut adapter: impl QueueAdapter) {
    let queue = "priority-50";

    adapter
        .enqueue(task(&format!("{name}-a"), 3))
        .expect("enqueue must succeed");
    adapter
        .enqueue(task(&format!("{name}-b"), 1))
        .expect("enqueue must succeed");

    let lease_a = adapter
        .lease(queue, "worker-1", 2_000)
        .expect("lease must succeed")
        .expect("first task must be leaseable");
    assert_eq!(lease_a.lease_event_version, QUEUE_LEASE_EVENT_VERSION);
    assert_eq!(lease_a.attempt, 1);

    // Deterministic expiration should redeliver task-a with incremented attempt.
    let lease_b = adapter
        .lease(queue, "worker-2", 13_000)
        .expect("lease must succeed")
        .expect("next task must be leaseable");
    assert_eq!(lease_b.task_id, format!("{name}-b"));

    // Explicit requeue for task-b should push it to dead-letter immediately (max_attempts=1).
    let requeued = adapter
        .requeue(&lease_b.lease_id, "worker-2", "execution-failed", 13_100)
        .expect("requeue call must succeed");
    assert!(requeued);

    let redelivery = adapter
        .lease(queue, "worker-3", 13_200)
        .expect("lease must succeed")
        .expect("redelivered task must be leaseable");
    assert_eq!(redelivery.task_id, format!("{name}-a"));
    assert_eq!(redelivery.attempt, 2);

    let acked = adapter
        .ack(&redelivery.lease_id, "worker-3", 13_250)
        .expect("ack must succeed");
    assert!(acked);

    assert!(adapter
        .lease(queue, "worker-3", 13_300)
        .expect("empty lease request must succeed")
        .is_none());

    let metrics = adapter.metrics();
    assert_eq!(metrics.queue_enqueued_total, 2);
    assert_eq!(metrics.queue_lease_acquired_total, 3);
    assert_eq!(metrics.queue_redelivery_total, 1);
    assert_eq!(metrics.queue_dead_letter_total, 1);

    let dead_letters = adapter.dead_letters();
    assert_eq!(dead_letters.len(), 1);
    assert_eq!(dead_letters[0].dead_letter_version, QUEUE_DEAD_LETTER_CONTRACT_VERSION);
    assert_eq!(dead_letters[0].task_id, format!("{name}-b"));
    assert_eq!(dead_letters[0].reason, "execution-failed");
}

#[test]
fn in_memory_adapter_satisfies_queue_contract_suite() {
    run_contract_suite("mem", InMemoryQueueAdapter::new());
}

#[test]
fn external_adapter_stub_satisfies_queue_contract_suite() {
    run_contract_suite("ext", ExternalQueueAdapterStub::default());
}
