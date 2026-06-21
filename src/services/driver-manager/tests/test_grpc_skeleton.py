from __future__ import annotations

import json
import socket
import time
import logging
from typing import Iterator

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from driver_manager.base_driver import DeviceStatusInfo, DriverCapabilities, DriverHealth
from driver_manager.grpc_server import serve
from driver_manager.main import _JsonFormatter, render_metrics_text
from driver_manager.proto_gen import ensure_generated
from driver_manager.simulator_driver import DriverExecutionError

ensure_generated()

from eigen_internal.v1 import driver_manager_service_pb2 as drv_pb  # noqa: E402
from eigen_internal.v1 import driver_manager_service_pb2_grpc as drv_pb_grpc  # noqa: E402
from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


_SERVER: grpc.Server | None = None


def _enum_value(module, *names: str) -> int:
    for name in names:
        if hasattr(module, name):
            return int(getattr(module, name))
    raise AttributeError(f"None of enum names exist: {names}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def grpc_addr() -> Iterator[str]:
    global _SERVER
    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    _SERVER = server
    time.sleep(0.05)
    yield addr
    server.stop(grace=None)
    _SERVER = None


def _extract_error_info(err: grpc.RpcError) -> error_details_pb2.ErrorInfo:
    st = rpc_status.from_call(err)
    assert st is not None
    info = error_details_pb2.ErrorInfo()
    unpacked = [d.Unpack(info) for d in st.details]
    assert any(unpacked)
    return info


def _extract_detail(err: grpc.RpcError, detail_type):
    st = rpc_status.from_call(err)
    assert st is not None
    detail = detail_type()
    for candidate in st.details:
        if candidate.Unpack(detail):
            return detail
    return None


def _aqo(operations: list[dict], qubits: int = 2) -> bytes:
    return json.dumps({"version": "0.1", "qubits": qubits, "operations": operations}).encode("utf-8")


def _execute(
    stub: drv_pb_grpc.DriverManagerServiceStub,
    *,
    payload: bytes,
    shots: int = 200,
    options: dict[str, str] | None = None,
    metadata: list[tuple[str, str]] | None = None,
    device_id: str = "sim:local",
    job_id: str = "job-1",
):
    return stub.ExecuteCircuit(
        drv_pb.ExecuteCircuitRequest(
            job_id=job_id,
            device_id=device_id,
            payload=types_pb.CircuitPayload(
                format=_enum_value(types_pb, "CIRCUIT_FORMAT_AQO_JSON", "AQO_JSON"),
                data=payload,
            ),
            shots=shots,
            options=options or {},
        ),
        metadata=metadata or (),
    )


class _NormalizedDriver:
    name = "normalized-driver"

    def initialize(self, config: dict[str, str]) -> None:
        _ = config

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(driver_api_version="1.0", features={"execution": "normalized"})

    def healthcheck(self) -> DriverHealth:
        return DriverHealth(ready=True, details={"driver": self.name})

    def get_devices(self) -> list[object]:
        return [
            types_pb.DeviceInfo(
                device_id="norm:0",
                name="Normalized backend",
                backend_type="qpu",
                status=types_pb.ONLINE,
                queue_depth=3,
                estimated_wait_sec=9,
                capabilities={"formats": "AQO_JSON"},
            )
        ]

    def execute_circuit(self, device_id: str, circuit: bytes, shots: int, options: dict[str, str]):
        _ = (device_id, circuit, shots)
        signal = options.get("simulate_error", "").upper()
        if signal == "UNAVAILABLE":
            raise DriverExecutionError(grpc.StatusCode.UNAVAILABLE, "normalized backend unavailable")
        if signal == "RESOURCE_EXHAUSTED":
            raise DriverExecutionError(grpc.StatusCode.RESOURCE_EXHAUSTED, "normalized backend quota exhausted")
        if signal == "FAILED_PRECONDITION":
            raise DriverExecutionError(grpc.StatusCode.FAILED_PRECONDITION, "normalized backend precondition failed")
        return {"11": 1, "00": 2}, 1.23456789, {"z": "last", "a": "first", "b": 7}

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        return DeviceStatusInfo(
            device_id=device_id,
            status=types_pb.ONLINE,
            queue_depth=3,
            estimated_wait_sec=9,
            metadata={"driver": self.name},
        )

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        _ = options
        return f"calib://{self.name}/{device_id}"


def _ensure_normalized_driver_registered() -> None:
    assert _SERVER is not None
    if _SERVER.driver_registry.get_driver("normalized-driver") is None:
        _SERVER.driver_registry.add_driver(_NormalizedDriver().name, _NormalizedDriver())


def test_list_devices_returns_simulator_devices(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = stub.ListDevices(drv_pb.ListDevicesRequest())

    assert {device.device_id for device in resp.devices} == {"cluster:auto", "sim:local"}


@pytest.mark.parametrize("device_id", ["cluster:auto", "sim:local"])
def test_get_device_status_returns_simulator_status(grpc_addr: str, device_id: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = stub.GetDeviceStatus(drv_pb.DeviceStatusRequest(device_id=device_id))

    assert resp.device_id == device_id
    assert resp.metadata["driver"] == "simulator"


def test_execute_circuit_normalizes_counts_metadata_and_timing(grpc_addr: str) -> None:
    _ensure_normalized_driver_registered()

    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)
    resp = _execute(stub, payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1), device_id="norm:0")

    assert dict(resp.counts) == {"00": 2, "11": 1}
    assert dict(resp.metadata) == {"a": "first", "b": "7", "z": "last"}
    assert resp.execution_time_sec == pytest.approx(1.234568, abs=1e-9)


def test_get_device_status_validates_device_id(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.GetDeviceStatus(drv_pb.DeviceStatusRequest())

    assert err.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_execute_circuit_returns_counts_with_canonical_bit_order(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = _execute(
        stub,
        payload=_aqo(
            operations=[
                {"op": "RX", "q": [0], "params": {"theta": 3.141592653589793}},
                {"op": "MEASURE", "q": [0, 1], "c": [0, 1]},
            ],
            qubits=2,
        ),
        shots=64,
        options={"seed": "7"},
    )

    assert sum(resp.counts.values()) == 64
    assert set(resp.counts.keys()) == {"01"}
    assert resp.metadata["bitstring_order"] == "msb_first_by_classical_index"


def test_execute_circuit_rejects_unsupported_format(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        stub.ExecuteCircuit(
            drv_pb.ExecuteCircuitRequest(
                job_id="job-1",
                device_id="sim:local",
                payload=types_pb.CircuitPayload(
                    format=_enum_value(types_pb, "CIRCUIT_FORMAT_QASM3_TEXT", "QASM3_TEXT"),
                    data=b"OPENQASM 3;",
                ),
                shots=128,
            )
        )

    assert err.value.code() == grpc.StatusCode.UNIMPLEMENTED
    info = _extract_error_info(err.value)
    assert info.reason == "EIGEN_BACKEND_PROVIDER"
    assert info.metadata["retryable"] == "false"


def test_execute_circuit_simulated_unavailable(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        _execute(stub, payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1), options={"simulate_error": "UNAVAILABLE"})

    assert err.value.code() == grpc.StatusCode.UNAVAILABLE
    info = _extract_error_info(err.value)
    assert info.reason == "EIGEN_BACKEND_UNAVAILABLE"
    assert info.metadata["taxonomy"] == "network"
    assert info.metadata["remediation"]
    assert info.metadata["job_id"] == "job-1"
    assert info.metadata["retryable"] == "true"
    retry_info = _extract_detail(err.value, error_details_pb2.RetryInfo)
    assert retry_info is not None
    assert retry_info.retry_delay.seconds == 1


def test_execute_circuit_simulated_resource_exhausted(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        _execute(
            stub,
            payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1),
            options={"simulate_error": "RESOURCE_EXHAUSTED"},
        )

    assert err.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED
    info = _extract_error_info(err.value)
    assert info.reason == "EIGEN_BACKEND_QUOTA"
    assert info.metadata["taxonomy"] == "quota"
    assert info.metadata["retryable"] == "true"
    retry_info = _extract_detail(err.value, error_details_pb2.RetryInfo)
    assert retry_info is not None
    assert retry_info.retry_delay.seconds == 5


def test_observability_smoke_and_trace_continuity(grpc_addr: str, caplog: pytest.LogCaptureFixture) -> None:
    _ensure_normalized_driver_registered()
    caplog.set_level(logging.INFO, logger="driver_manager")

    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    metadata = [("traceparent", "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01")]
    resp = _execute(
        stub,
        payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1),
        device_id="norm:0",
        job_id="job-trace",
        metadata=metadata,
    )
    assert dict(resp.counts)
    assert any(getattr(record, "trace_id", None) == "0123456789abcdef0123456789abcdef" for record in caplog.records)
    assert any(getattr(record, "job_id", None) == "job-trace" for record in caplog.records)
    assert any(getattr(record, "method", None) == "DriverManagerService.ExecuteCircuit" for record in caplog.records)


def test_bounded_label_regression_gate() -> None:
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="driver_manager",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="rpc_start",
        args=(),
        exc_info=None,
    )
    record.trace_id = "0123456789abcdef0123456789abcdef"
    record.job_id = "job-1"
    record.traceparent = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    record.method = "DriverManagerService.ExecuteCircuit"
    record.unbounded = "should_not_escape"
    payload = json.loads(formatter.format(record))
    assert "unbounded" not in payload
    assert payload["service"] == "driver-manager"
    assert payload["trace_id"] == "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    ("simulate_error", "expected_code", "expected_reason", "retryable", "precondition"),
    [
        ("UNAVAILABLE", grpc.StatusCode.UNAVAILABLE, "EIGEN_BACKEND_UNAVAILABLE", True, False),
        ("RESOURCE_EXHAUSTED", grpc.StatusCode.RESOURCE_EXHAUSTED, "EIGEN_BACKEND_QUOTA", True, False),
        ("FAILED_PRECONDITION", grpc.StatusCode.FAILED_PRECONDITION, "EIGEN_BACKEND_PRECONDITION", False, True),
    ],
)
def test_execute_circuit_error_mapping_matrix(
    grpc_addr: str,
    simulate_error: str,
    expected_code: grpc.StatusCode,
    expected_reason: str,
    retryable: bool,
    precondition: bool,
) -> None:
    _ensure_normalized_driver_registered()

    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        _execute(
            stub,
            payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1),
            device_id="norm:0",
            options={"simulate_error": simulate_error},
            job_id="job-error",
        )

    assert err.value.code() == expected_code
    info = _extract_error_info(err.value)
    assert info.reason == expected_reason
    assert info.metadata["retryable"] == str(retryable).lower()
    assert info.metadata["precondition"] == str(precondition).lower()
    if retryable:
        retry_info = _extract_detail(err.value, error_details_pb2.RetryInfo)
        assert retry_info is not None
        assert retry_info.retry_delay.seconds > 0
    if precondition:
        precondition_detail = _extract_detail(err.value, error_details_pb2.PreconditionFailure)
        assert precondition_detail is not None
        assert precondition_detail.violations[0].type == "STATE"


@pytest.mark.parametrize(
    ("operations", "qubits", "shots", "seed"),
    [
        ([{"op": "MEASURE", "q": [0], "c": [0]}], 1, 32, "1"),
        (
            [
                {"op": "RY", "q": [0], "params": {"theta": 1.5707963267948966}},
                {"op": "MEASURE", "q": [0], "c": [0]},
            ],
            1,
            64,
            "13",
        ),
        (
            [
                {"op": "RX", "q": [0], "params": {"theta": 3.141592653589793}},
                {"op": "CX", "q": [0, 1]},
                {"op": "MEASURE", "q": [0, 1], "c": [0, 1]},
            ],
            2,
            64,
            "21",
        ),
    ],
)
def test_execute_circuit_is_deterministic_for_contract_fixtures(
    grpc_addr: str,
    operations: list[dict],
    qubits: int,
    shots: int,
    seed: str,
) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)
    payload = _aqo(operations=operations, qubits=qubits)

    first = _execute(stub, payload=payload, shots=shots, options={"seed": seed})
    second = _execute(stub, payload=payload, shots=shots, options={"seed": seed})

    assert dict(first.counts) == dict(second.counts)
    assert first.metadata["qubits"] == str(qubits)
    assert first.metadata["shots"] == str(shots)


def test_execute_circuit_reports_unsupported_op_exhaustively(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        _execute(stub, payload=_aqo([{"op": "H", "q": [0]}], qubits=1))

    assert err.value.code() == grpc.StatusCode.UNIMPLEMENTED
    assert "Unsupported Op: H at operation[0]" in err.value.details()


def test_execute_circuit_reports_simulator_out_of_memory(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        _execute(stub, payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=17))

    assert err.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED
    assert "Simulator Out of Memory" in err.value.details()
