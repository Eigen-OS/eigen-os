from __future__ import annotations

import json
from pathlib import Path

from unittest.mock import AsyncMock

import grpc
import pytest

from system_api.grpc_impl import JobService
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402

CONTRACT_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts" / "explain_execution_v1"


def _load_json(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_FIXTURE_ROOT / name).read_text(encoding="utf-8"))


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


def _make_service(tmp_path, monkeypatch, kernel_client) -> JobService:
    monkeypatch.setenv("SYSTEM_API_AUTH_MODE", "allow_all")
    monkeypatch.setenv("SYSTEM_API_IDEMPOTENCY_STORE_PATH", str(tmp_path / "idempotency.json"))
    monkeypatch.setenv("SYSTEM_API_IDEMPOTENCY_TTL_SECONDS", "60")
    return JobService(job_pb=job_pb, types_pb=types_pb, kernel_client=kernel_client)


def test_explain_execution_success_contract_fixture_is_stable(tmp_path, monkeypatch) -> None:
    kernel_client = AsyncMock()
    kernel_client._closed = False
    kernel_client.get_dispatch_rationale = AsyncMock(
        return_value={
            "version": "2.3.0",
            "policy_version": "policy-2026.06",
            "reason_codes": ["WEIGHTED_FAIRNESS", "DEVICE_SCORE"],
            "selected_backend": "sim:local",
            "selected_queue": "queue-a",
            "attributes": {
                "policy_branch": "main",
                "fallback_reason": "simulator",
                "artifact_version": "1.2.0",
                "decision_lineage": json.dumps(
                    [
                        {
                            "step": 1,
                            "event": "dispatch_requested",
                            "outcome": "accepted",
                            "attributes": {"cluster_id": "cluster-local"},
                        }
                    ]
                ),
                "dispatch_latency_ms": "3",
            },
            "timeline_ref": "qfs://jobs/job-thin-002/timeline.json",
            "logs_ref": "qfs://jobs/job-thin-002/logs/dispatch.log",
            "trace_id": "trace-123",
            "trace_ref": "trace-ref-123",
            "topology": {
                "contract_version": "1.1.0",
                "lineage_version": "1.1.0",
                "cluster_id": "cluster-local",
                "worker_id": "worker-local",
                "partition_id": "partition-0",
                "attempt": 1,
            },
        }
    )
    service = _make_service(tmp_path, monkeypatch, kernel_client)
    contract = _load_json("expected_contract.json")

    rationale = service.GetDispatchRationale(
        job_pb.GetDispatchRationaleRequest(job_id="job-thin-002"),
        _Context(),
    ).rationale

    assert set(contract["response_required_fields"]).issubset(set(rationale.DESCRIPTOR.fields_by_name))
    assert rationale.version == "2.3.0"
    attrs = dict(rationale.attributes)
    assert set(contract["attributes_required_keys"]).issubset(attrs.keys())
    assert attrs["artifact_version"] == "1.2.0"
    assert attrs["topology_contract_version"] == "1.1.0"

    decision_lineage = attrs.get("decision_lineage")
    assert decision_lineage
    lineage = json.loads(decision_lineage)
    assert isinstance(lineage, list)
    assert lineage
    steps = [int(item["step"]) for item in lineage]
    assert steps == sorted(steps)
    for item in lineage:
        assert {"step", "event", "outcome", "attributes"}.issubset(item.keys())
        assert item["event"]
        assert item["outcome"]
    lineage_attr_keys = {key for item in lineage for key in dict(item["attributes"]).keys()}
    assert {"cluster_id", "worker_id", "partition_id", "attempt"} & lineage_attr_keys

    for key in ("queue_delay_ms", "dispatch_latency_ms", "execution_time_ms"):
        value = attrs.get(key)
        if value not in {None, ""}:
            assert int(value) >= 0


def test_explain_execution_error_model_maps_invalid_and_missing_locally(tmp_path, monkeypatch) -> None:
    kernel_client = AsyncMock()
    kernel_client._closed = False
    kernel_client.get_dispatch_rationale = AsyncMock(side_effect=_AbortError(grpc.StatusCode.NOT_FOUND, "decision not found"))
    service = _make_service(tmp_path, monkeypatch, kernel_client)

    with pytest.raises(_AbortError) as invalid_err:
        service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(), _Context())
    assert invalid_err.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    with pytest.raises(_AbortError) as missing_err:
        service.GetDispatchRationale(
            job_pb.GetDispatchRationaleRequest(job_id="job_missing_999"),
            _Context(),
        )
    assert missing_err.value.code() == grpc.StatusCode.NOT_FOUND
