from __future__ import annotations

import grpc

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _submit_stub_job(stub: job_pb_grpc.JobServiceStub) -> str:
    req = job_pb.SubmitJobRequest(
        name="stream-semantics-test",
        target="sim:local",
        eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}", entrypoint="main"),
    )
    resp = stub.SubmitJob(req)
    return resp.job_id


def test_stream_job_updates_seq_and_resume(grpc_addr: str):
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)

    job_id = _submit_stub_job(stub)

    full_stream = list(stub.StreamJobUpdates(job_pb.StreamJobUpdatesRequest(job_id=job_id)))
    updates = [item.update for item in full_stream]

    seqs = [u.event_seq for u in updates]
    assert seqs == sorted(seqs)
    assert seqs and seqs[0] == 1
    assert updates[-1].state in {
        types_pb.JOB_STATE_DONE,
        types_pb.JOB_STATE_ERROR,
        types_pb.JOB_STATE_CANCELLED,
        types_pb.JOB_STATE_TIMEOUT,
    }

    resumed_stream = list(
        stub.StreamJobUpdates(
            job_pb.StreamJobUpdatesRequest(job_id=job_id, last_event_seq=1)
        )
    )
    resumed_updates = [item.update for item in resumed_stream]

    resumed_seqs = [u.event_seq for u in resumed_updates]
    assert resumed_seqs == sorted(resumed_seqs)
    assert resumed_updates[-1].state in {
        types_pb.JOB_STATE_DONE,
        types_pb.JOB_STATE_ERROR,
        types_pb.JOB_STATE_CANCELLED,
        types_pb.JOB_STATE_TIMEOUT,
    }
