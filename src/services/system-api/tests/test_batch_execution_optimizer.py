from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from system_api.grpc_impl import JobService
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _make_service() -> JobService:
    kernel_client = AsyncMock()
    kernel_client._closed = False
    kernel_client.enqueue_job = AsyncMock(return_value={
        "job_id": "job-abc123",
        "state": "TASK_STATE_PENDING",
        "created_at": None,
    })
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


def test_eigen_lang_helper_keeps_cnot_alias_and_measurement() -> None:
    service = JobService.__new__(JobService)
    source = (
        b"from eigen_lang import hybrid_program, cnot\n\n"
        b"@hybrid_program()\n"
        b"def main():\n"
        b"    cnot(0, 1)\n"
    )
    
    aqo = json.loads(service._compile_eigen_lang_source(source).decode("utf-8"))
    assert any(op["op"] == "CX" for op in aqo["operations"])
    assert aqo["operations"][-1]["op"] == "MEASURE"
    