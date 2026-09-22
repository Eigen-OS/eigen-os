use resource_manager::{
    WORKER_NODE_EXECUTION_CONTRACT_VERSION, WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION,
    WorkerExecutionCancelRequest, WorkerExecutionCompleteRequest, WorkerExecutionHeartbeat,
    WorkerExecutionStartRequest, WorkerExecutionState, WorkerNodeService,
    WorkerRuntimeArtifactRef,
};

#[test]
fn duplicate_delivery_with_same_idempotency_key_is_safe() {
    let mut service = WorkerNodeService::new(30_000);
    let request = WorkerExecutionStartRequest {
        assignment_id: "assignment-01".to_string(),
        worker_id: "worker-a".to_string(),
        lease_id: "lease-1".to_string(),
        idempotency_key: "idem-001".to_string(),
        runtime_artifacts: vec![WorkerRuntimeArtifactRef {
            artifact_id: "artifact-a".to_string(),
            uri: "s3://bucket/a.tar.zst".to_string(),
            checksum: "sha256:a".to_string(),
        }],
    };

    let first = service.start(request.clone(), 1_746_300_000_000).expect("first start must succeed");
    let second = service.start(request, 1_746_300_000_100).expect("idempotent replay must succeed");

    assert!(!first.idempotent_replay);
    assert!(second.idempotent_replay);
    assert_eq!(first.execution.execution_id, second.execution.execution_id);
    assert_eq!(first.execution.worker_contract_version, WORKER_NODE_EXECUTION_CONTRACT_VERSION);
    assert_eq!(
        first.execution.materialized_artifacts[0].artifact_contract_version,
        WORKER_RUNTIME_ARTIFACT_CONTRACT_VERSION
    );
}

#[test]
fn heartbeat_timeout_is_deterministic() {
    let mut service = WorkerNodeService::new(100);
    let started = service
        .start(
            WorkerExecutionStartRequest {
                assignment_id: "assignment-02".to_string(),
                worker_id: "worker-a".to_string(),
                lease_id: "lease-2".to_string(),
                idempotency_key: "idem-002".to_string(),
                runtime_artifacts: vec![],
            },
            1_746_300_001_000,
        )
        .expect("start must succeed");

    let alive = service
        .heartbeat(
            WorkerExecutionHeartbeat {
                execution_id: started.execution.execution_id.clone(),
                lease_id: "lease-2".to_string(),
            },
            1_746_300_001_090,
        )
        .expect("within timeout stays running");
    assert_eq!(alive.state, WorkerExecutionState::Running);

    let timed_out = service
        .heartbeat(
            WorkerExecutionHeartbeat {
                execution_id: started.execution.execution_id,
                lease_id: "lease-2".to_string(),
            },
            1_746_300_001_300,
        )
        .expect("timeout transition should be persisted deterministically");
    assert_eq!(timed_out.state, WorkerExecutionState::TimedOut);
}

#[test]
fn cancellation_intent_and_terminal_state_are_durable() {
    let mut service = WorkerNodeService::new(30_000);
    let started = service
        .start(
            WorkerExecutionStartRequest {
                assignment_id: "assignment-03".to_string(),
                worker_id: "worker-b".to_string(),
                lease_id: "lease-3".to_string(),
                idempotency_key: "idem-003".to_string(),
                runtime_artifacts: vec![],
            },
            1_746_300_002_000,
        )
        .expect("start must succeed");

    let cancelled = service
        .cancel(
            WorkerExecutionCancelRequest {
                execution_id: started.execution.execution_id.clone(),
                reason: "operator-request".to_string(),
            },
            1_746_300_002_100,
        )
        .expect("cancel must succeed");
    assert_eq!(cancelled.state, WorkerExecutionState::Cancelled);
    assert_eq!(cancelled.cancellation_intent, Some("operator-request".to_string()));

    let completed = service
        .complete(
            WorkerExecutionCompleteRequest {
                execution_id: started.execution.execution_id.clone(),
                lease_id: "lease-3".to_string(),
                output_ref: "qfs://result-1".to_string(),
            },
            1_746_300_002_200,
        )
        .expect_err("terminal cancelled execution must reject completion");
    assert_eq!(format!("{:?}", completed), "NotRunning");

    let stored = service.execution(&started.execution.execution_id).expect("execution persisted");
    assert_eq!(stored.state, WorkerExecutionState::Cancelled);
    assert_eq!(stored.cancellation_intent, Some("operator-request".to_string()));
}
