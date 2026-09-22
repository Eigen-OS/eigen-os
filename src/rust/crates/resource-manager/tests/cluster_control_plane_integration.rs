use resource_manager::{
    CLUSTER_ASSIGNMENT_LINEAGE_VERSION, CLUSTER_CONTROL_PLANE_CONTRACT_VERSION,
    ClusterBootstrapInput, ClusterControlPlaneError, ClusterRuntimeMode,
    ClusterWorkerRegistration, ClusterWorkerState, assign_cluster_job,
    bootstrap_cluster_control_plane,
};

#[test]
fn cluster_mode_bootstrap_discovers_workers_deterministically() {
    let workers = vec![
        ClusterWorkerRegistration {
            worker_id: "worker-c".to_string(),
            state: ClusterWorkerState::Ready,
            capability_tags: vec!["qpu".to_string()],
            max_parallel_tasks: 8,
            current_load: 4,
        },
        ClusterWorkerRegistration {
            worker_id: "worker-a".to_string(),
            state: ClusterWorkerState::Degraded,
            capability_tags: vec!["sim".to_string()],
            max_parallel_tasks: 4,
            current_load: 2,
        },
        ClusterWorkerRegistration {
            worker_id: "worker-b".to_string(),
            state: ClusterWorkerState::Offline,
            capability_tags: vec!["qpu".to_string()],
            max_parallel_tasks: 8,
            current_load: 1,
        },
    ];

    let artifact = bootstrap_cluster_control_plane(
        &ClusterBootstrapInput {
            cluster_id: "cluster-alpha".to_string(),
            control_plane_node_id: "cp-1".to_string(),
            runtime_mode: ClusterRuntimeMode::Cluster,
        },
        &workers,
    )
    .expect("bootstrap must succeed");

    assert_eq!(
        artifact.cluster_contract_version,
        CLUSTER_CONTROL_PLANE_CONTRACT_VERSION
    );
    assert_eq!(artifact.cluster_id, "cluster-alpha");
    assert_eq!(artifact.control_plane_node_id, "cp-1");
    assert_eq!(artifact.runtime_mode, ClusterRuntimeMode::Cluster);
    assert_eq!(artifact.discovered_worker_ids, vec!["worker-a", "worker-c"]);
}

#[test]
fn assignment_contains_explicit_version_and_lineage_metadata() {
    let workers = vec![
        ClusterWorkerRegistration {
            worker_id: "worker-z".to_string(),
            state: ClusterWorkerState::Ready,
            capability_tags: vec!["qpu".to_string(), "gpu".to_string()],
            max_parallel_tasks: 8,
            current_load: 3,
        },
        ClusterWorkerRegistration {
            worker_id: "worker-a".to_string(),
            state: ClusterWorkerState::Ready,
            capability_tags: vec!["qpu".to_string()],
            max_parallel_tasks: 8,
            current_load: 1,
        },
    ];

    let assignment = assign_cluster_job(
        "cluster-alpha",
        "job-42",
        7,
        1_746_200_000_000,
        &workers,
        &["qpu".to_string()],
        &[],
    )
    .expect("assignment must succeed");

    assert_eq!(
        assignment.cluster_contract_version,
        CLUSTER_CONTROL_PLANE_CONTRACT_VERSION
    );
    assert_eq!(assignment.assignment_id, "job-42-a-000007");
    assert_eq!(assignment.lineage.lineage_version, CLUSTER_ASSIGNMENT_LINEAGE_VERSION);
    assert_eq!(assignment.lineage.cluster_id, "cluster-alpha");
    assert_eq!(assignment.lineage.assignment_sequence, 7);
    assert_eq!(assignment.lineage.assignment_epoch_ms, 1_746_200_000_000);
    assert_eq!(assignment.selected_worker_id, "worker-a");
    assert_eq!(assignment.candidate_workers, vec!["worker-a", "worker-z"]);
    assert!(!assignment.fallback_applied);
}

#[test]
fn node_loss_fallback_reassigns_to_remaining_worker() {
    let workers = vec![
        ClusterWorkerRegistration {
            worker_id: "worker-a".to_string(),
            state: ClusterWorkerState::Ready,
            capability_tags: vec!["qpu".to_string()],
            max_parallel_tasks: 8,
            current_load: 1,
        },
        ClusterWorkerRegistration {
            worker_id: "worker-b".to_string(),
            state: ClusterWorkerState::Ready,
            capability_tags: vec!["cpu".to_string()],
            max_parallel_tasks: 8,
            current_load: 2,
        },
    ];

    let assignment = assign_cluster_job(
        "cluster-alpha",
        "job-43",
        8,
        1_746_200_100_000,
        &workers,
        &["qpu".to_string()],
        &["worker-a".to_string()],
    )
    .expect("node-loss fallback must succeed");

    assert_eq!(assignment.selected_worker_id, "worker-b");
    assert_eq!(assignment.candidate_workers, vec!["worker-b"]);
    assert!(assignment.fallback_applied);
    assert_eq!(
        assignment.fallback_reason,
        Some(
            "no-worker-satisfies-required-capabilities-after-node-loss-fallback-to-load-order"
                .to_string()
        )
    );
}

#[test]
fn cluster_mode_requires_registered_workers() {
    let err = bootstrap_cluster_control_plane(
        &ClusterBootstrapInput {
            cluster_id: "cluster-alpha".to_string(),
            control_plane_node_id: "cp-1".to_string(),
            runtime_mode: ClusterRuntimeMode::Cluster,
        },
        &[],
    )
    .expect_err("cluster mode without workers must fail");

    assert_eq!(err, ClusterControlPlaneError::NoWorkersRegistered);
}
