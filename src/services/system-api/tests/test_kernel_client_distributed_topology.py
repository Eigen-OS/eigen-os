from __future__ import annotations

import asyncio
from types import SimpleNamespace

from system_api.kernel_client import KernelGatewayClient
from system_api.proto_gen import ensure_generated

ensure_generated()
from eigen.internal.v1 import kernel_gateway_pb2 as kernel_pb  # noqa: E402


def test_enqueue_job_injects_jobspec_workload_into_kernel_metadata() -> None:
    client = KernelGatewayClient()
    captured: dict[str, object] = {}

    class _Stub:
        def EnqueueJob(self, request, timeout=None):
            captured["request"] = request
            return SimpleNamespace(
                job_id="job-distributed-001",
                state=kernel_pb.TaskState.TASK_STATE_PENDING,
                created_at=None,
            )

    client._stub = _Stub()
    client._closed = False
    client.connect = lambda: None  # type: ignore[method-assign]

    workload = {
        "kind": "DistributedJob",
        "execution_profile": "distributed",
        "replayable": True,
        "backend_target": "cluster:auto",
        "topology": {
            "cluster_id": "cluster:auto",
            "partition_count": 2,
            "partition_ids": ["partition-0", "partition-1"],
            "preferred_workers": ["worker-a", "worker-b"],
        },
    }

    result = asyncio.run(
        client.enqueue_job(
            name="distributed-network-partition-demo",
            program=b"from eigen_lang import hybrid_program\n\n@hybrid_program()\ndef main():\n    return 1\n",
            program_format="eigen_lang_source",
            target="cluster:auto",
            priority=80,
            compiler_options={},
            metadata_kvs={},
            public_envelope={"request_id": "req-1", "traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01"},
            workload=workload,
        )
    )

    request = captured["request"]
    assert request is not None
    assert "jobspec_workload" in request.metadata_kvs
    assert "topology" in request.metadata_kvs["jobspec_workload"]
    assert request.metadata.workload is not None
    assert request.metadata.workload.topology.cluster_id == "cluster:auto"
    assert request.metadata.workload.topology.partition_count == 2
    assert list(request.metadata.workload.topology.partition_ids) == ["partition-0", "partition-1"]
    assert list(request.metadata.workload.topology.preferred_workers) == ["worker-a", "worker-b"]
    assert result["job_id"] == "job-distributed-001"


def test_enqueue_job_injects_jobspec_workload_from_proto_workload() -> None:
    client = KernelGatewayClient()
    captured: dict[str, object] = {}

    class _Stub:
        def EnqueueJob(self, request, timeout=None):
            captured["request"] = request
            return SimpleNamespace(
                job_id="job-distributed-002",
                state=kernel_pb.TaskState.TASK_STATE_PENDING,
                created_at=None,
            )

    client._stub = _Stub()
    client._closed = False
    client.connect = lambda: None  # type: ignore[method-assign]

    workload = kernel_pb.WorkloadContract(
        kind=kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_DISTRIBUTED_JOB,
        execution_profile="distributed",
        replayable=True,
        backend_target="cluster:auto",
        topology=kernel_pb.WorkloadTopology(
            cluster_id="cluster:auto",
            partition_count=2,
            partition_ids=["partition-0", "partition-1"],
            preferred_workers=["worker-a", "worker-b"],
        ),
    )

    result = asyncio.run(
        client.enqueue_job(
            name="distributed-network-partition-demo",
            program=b"from eigen_lang import hybrid_program\n\n@hybrid_program()\ndef main():\n    return 1\n",
            program_format="eigen_lang_source",
            target="cluster:auto",
            priority=80,
            compiler_options={},
            metadata_kvs={},
            public_envelope={"request_id": "req-2", "traceparent": "00-1234567890abcdef1234567890abcdef-1234567890abcdef-01"},
            workload=workload,
        )
    )

    request = captured["request"]
    assert request is not None
    assert "jobspec_workload" in request.metadata_kvs
    assert "topology" in request.metadata_kvs["jobspec_workload"]
    assert request.metadata.workload is not None
    assert request.metadata.workload.topology.cluster_id == "cluster:auto"
    assert request.metadata.workload.topology.partition_count == 2
    assert list(request.metadata.workload.topology.partition_ids) == ["partition-0", "partition-1"]
    assert list(request.metadata.workload.topology.preferred_workers) == ["worker-a", "worker-b"]
    assert result["job_id"] == "job-distributed-002"
