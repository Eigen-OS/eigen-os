from __future__ import annotations

from datetime import datetime, timezone

import grpc

from system_api.grpc_impl import JobService
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


class _AbortError(grpc.RpcError):
    def __init__(self, code: grpc.StatusCode, details: str) -> None:
        super().__init__()
        self._code = code
        self._details = details

    def code(self) -> grpc.StatusCode:
        return self._code

    def details(self) -> str:
        return self._details


class _Context:
    def invocation_metadata(self):
        return []

    def abort(self, code, details):
        raise _AbortError(code, details)


def _make_service(tmp_path, monkeypatch) -> JobService:
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "allow_all")
    monkeypatch.setenv("SYSTEM_API_IDEMPOTENCY_STORE_PATH", str(tmp_path / "idempotency.json"))
    monkeypatch.setenv("SYSTEM_API_IDEMPOTENCY_TTL_SECONDS", "60")

    class _KernelClient:
        _closed = False


        async def enqueue_job(self, **_kwargs):
            return {
                "job_id": "job-thin-001",
                "state": "TASK_STATE_PENDING",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "topology": {
                    "contract_version": "1.1.0",
                    "lineage_version": "1.1.0",
                    "cluster_id": "cluster-local",
                    "worker_id": "worker-local",
                    "partition_id": "partition-0",
                    "attempt": 1,
                },
            }
            
        async def get_job_status(self, **_kwargs):
            return {
                "job_id": "job-thin-001",
                "state": "TASK_STATE_DONE",
                "stage": "done",
                "progress": 1.0,
                "message": "completed",
                "updated_at": datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
                "topology": {
                    "contract_version": "1.1.0",
                    "lineage_version": "1.1.0",
                    "cluster_id": "cluster-local",
                    "worker_id": "worker-local",
                    "partition_id": "partition-0",
                    "attempt": 1,
                },
            }

        async def get_job_results(self, **_kwargs):
            return {
                "job_id": "job-thin-001",
                "counts": {"00": 512, "11": 512},
                "metadata": {
                    "job_id_ref": "job/job-thin-001",
                    "simulator": "local",
                },
            }

        async def stream_job_updates(self, *, job_id: str, last_event_seq: int, public_envelope: dict, workload=None):
            for update in (
                {
                    "event_seq": 1,
                    "state": "TASK_STATE_PENDING",
                    "stage": "queued",
                    "progress": 0.0,
                    "message": "queued",
                    "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "topology": {
                        "contract_version": "1.1.0",
                        "lineage_version": "1.1.0",
                        "cluster_id": "cluster-local",
                        "worker_id": "worker-local",
                        "partition_id": "partition-0",
                        "attempt": 1,
                    },
                },
                {
                    "event_seq": 2,
                    "state": "TASK_STATE_RUNNING",
                    "stage": "running",
                    "progress": 0.5,
                    "message": "running",
                    "timestamp": datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
                    "topology": {
                        "contract_version": "1.1.0",
                        "lineage_version": "1.1.0",
                        "cluster_id": "cluster-local",
                        "worker_id": "worker-local",
                        "partition_id": "partition-0",
                        "attempt": 1,
                    },
                },
                {
                    "event_seq": 3,
                    "state": "TASK_STATE_DONE",
                    "stage": "done",
                    "progress": 1.0,
                    "message": "completed",
                    "timestamp": datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
                    "topology": {
                        "contract_version": "1.1.0",
                        "lineage_version": "1.1.0",
                        "cluster_id": "cluster-local",
                        "worker_id": "worker-local",
                        "partition_id": "partition-0",
                        "attempt": 1,
                    },
                },
            ):
                yield update

    kernel_client = _KernelClient()
    return JobService(job_pb=job_pb, types_pb=types_pb, kernel_client=kernel_client)


def test_submit_watch_status_results_thin_client(tmp_path, monkeypatch):
    """Thin-client smoke: submit -> watch -> status -> results."""

    service = _make_service(tmp_path, monkeypatch)
    context = _Context()

    submit = service.SubmitJob(
        job_pb.SubmitJobRequest(
            name="thin-client-smoke",
            target="sim:local",
            eigen_lang=types_pb.EigenLangSource(
                source=(
                    b'from eigen_lang import hybrid_program, ry, cnot\n\n'
                    b'@hybrid_program(target="sim", shots=1024)\n'
                    b'def main():\n'
                    b'    ry(0, theta=1.570796)\n'
                    b'    cnot(0, 1)\n'
                ),
                entrypoint="main",
            ),
        ),
        context,
    )

    assert submit.job_id == "job-thin-001"
    assert submit.status.state == types_pb.JOB_STATE_PENDING
    assert submit.status.topology.contract_version == "1.1.0"
    assert submit.status.topology.cluster_id == "cluster-local"

    updates = list(service.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=submit.job_id), context))
    assert len(updates) == 3
    seqs = [int(update.update.event_seq) for update in updates]
    assert seqs == [1, 2, 3]
    assert len(set(seqs)) == len(seqs)
    assert updates[-1].update.state == types_pb.JOB_STATE_DONE

    status = service.GetJobStatus(job_pb.GetJobStatusRequest(job_id=submit.job_id), context).status
    assert status.job_id == submit.job_id
    assert status.state == types_pb.JOB_STATE_DONE
    assert status.topology.contract_version == "1.1.0"
    assert status.topology.partition_id == "partition-0"
    assert status.topology.attempt == 1

    results = service.GetJobResults(job_pb.GetJobResultsRequest(job_id=submit.job_id), context)
    assert results.job_id == submit.job_id
    assert dict(results.counts) == {"00": 512, "11": 512}
    assert results.metadata["job_id_ref"] == f"job/{submit.job_id}"
    assert results.metadata["simulator"] == "local"
    