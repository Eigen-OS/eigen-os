from __future__ import annotations

import json
from pathlib import Path

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

CONTRACT_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "explain_execution_v1"


def _load_json(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _submit_job(stub: job_pb_grpc.JobServiceStub) -> str:
    req = job_pb.SubmitJobRequest(
        name="explain-contract",
        target="sim:local",
        metadata={"simulate_runtime_sec": "0.7"},
        eigen_lang=types_pb.EigenLangSource(source=b"def main():\n return 'ok'\n", entrypoint="main"),
    )
    return stub.SubmitJob(req).job_id


def _extract_error_info(err: grpc.RpcError) -> error_details_pb2.ErrorInfo:
    st = rpc_status.from_call(err)
    assert st is not None
    info = error_details_pb2.ErrorInfo()
    assert st.details
    unpacked = st.details[0].Unpack(info)
    assert unpacked
    return info


def test_explain_execution_success_contract_fixture_is_stable(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    contract = _load_json("expected_contract.json")

    job_id = _submit_job(stub)
    rationale = stub.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=job_id)).rationale

    assert set(contract["response_required_fields"]).issubset(set(rationale.DESCRIPTOR.fields_by_name))
    assert rationale.version == "2.1.0"
    attrs = dict(rationale.attributes)
    assert set(contract["attributes_required_keys"]).issubset(attrs.keys())
    assert attrs["artifact_version"] == "1.1.0"

    lineage = json.loads(attrs["decision_lineage"])
    assert len(lineage) >= int(contract["lineage_min_length"])
    steps = [int(item["step"]) for item in lineage]
    assert steps == sorted(steps)
    for item in lineage:
        assert set(contract["lineage_required_fields"]).issubset(item.keys())
        assert item["event"]
        assert item["outcome"]

    assert int(attrs["queue_delay_ms"]) >= 0
    assert int(attrs["dispatch_latency_ms"]) >= 0
    assert int(attrs["execution_time_ms"]) >= 0


def test_explain_execution_error_model_maps_invalid_and_missing(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = job_pb_grpc.JobServiceStub(channel)
    contract = _load_json("expected_contract.json")

    with pytest.raises(grpc.RpcError) as invalid_err:
        stub.GetDispatchRationale(job_pb.GetDispatchRationaleRequest())
    assert invalid_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    invalid_info = _extract_error_info(invalid_err.value)
    assert invalid_info.reason == contract["error_expected_invalid_reason"]

    with pytest.raises(grpc.RpcError) as missing_err:
        stub.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id="job_missing_999"))
    assert missing_err.value.code() == grpc.StatusCode.NOT_FOUND
    missing_info = _extract_error_info(missing_err.value)
    assert missing_info.reason == contract["error_expected_missing_reason"]
