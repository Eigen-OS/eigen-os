from __future__ import annotations

from datetime import datetime, timezone

from system_api.grpc_impl import JobService
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _make_service() -> JobService:
    class _KernelClient:
        _closed = False

        async def enqueue_job(self, **_kwargs):
            return {
                "job_id": "job-abc123",
                "state": "TASK_STATE_PENDING",
                "created_at": datetime.now(timezone.utc),
            }

        async def get_job_status(self, **_kwargs):
            return {
                "job_id": "job-abc123",
                "state": "TASK_STATE_PENDING",
                "message": "accepted",
                "created_at": datetime.now(timezone.utc),
            }

    kernel_client = _KernelClient()
    return JobService(job_pb=job_pb, types_pb=types_pb, kernel_client=kernel_client)


def test_submit_job_delegates_to_kernel_client() -> None:
    service = _make_service()
    request = job_pb.SubmitJobRequest(
        name="delegation-smoke",
        target="sim:local",
        eigen_lang=types_pb.EigenLangSource(
            source=b"from eigen_lang import hybrid_program\n\n@hybrid_program()\ndef main():\n    return 0\n",
            entrypoint="main",
        ),
    )
    class _Context:
        def invocation_metadata(self):
            return []

        def abort(self, code, details):
            raise RuntimeError(f"{code}: {details}")

    response = service.SubmitJob(request, _Context())
    assert response.job_id == "job-abc123"
    assert response.status.state == types_pb.JOB_STATE_PENDING
    