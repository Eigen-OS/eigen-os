from __future__ import annotations

import json
import socket
import time
from typing import Iterator

import grpc
import pytest

from driver_manager.grpc_server import serve
from driver_manager.proto_gen import ensure_generated

ensure_generated()

from eigen_internal.v1 import driver_manager_service_pb2 as drv_pb  # noqa: E402
from eigen_internal.v1 import driver_manager_service_pb2_grpc as drv_pb_grpc  # noqa: E402
from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


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
    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)
    yield addr
    server.stop(grace=None)


def _aqo(operations: list[dict], qubits: int = 2) -> bytes:
    return json.dumps({"version": "0.1", "qubits": qubits, "operations": operations}).encode("utf-8")


def _execute(
    stub: drv_pb_grpc.DriverManagerServiceStub,
    *,
    payload: bytes,
    shots: int = 200,
    options: dict[str, str] | None = None,
):
    return stub.ExecuteCircuit(
        drv_pb.ExecuteCircuitRequest(
            job_id="job-1",
            device_id="sim:local",
            payload=types_pb.CircuitPayload(format=_enum_value(types_pb, "CIRCUIT_FORMAT_AQO_JSON", "AQO_JSON"), data=payload),
            shots=shots,
            options=options or {},
        )
    )


def test_list_devices_returns_simulator_device(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = stub.ListDevices(drv_pb.ListDevicesRequest())

    assert len(resp.devices) == 1
    assert resp.devices[0].device_id == "sim:local"


def test_get_device_status_returns_simulator_status(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    resp = stub.GetDeviceStatus(drv_pb.DeviceStatusRequest(device_id="sim:local"))

    assert resp.device_id == "sim:local"
    assert resp.metadata["driver"] == "simulator"


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


def test_execute_circuit_simulated_unavailable(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = drv_pb_grpc.DriverManagerServiceStub(channel)

    with pytest.raises(grpc.RpcError) as err:
        _execute(stub, payload=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1), options={"simulate_error": "UNAVAILABLE"})

    assert err.value.code() == grpc.StatusCode.UNAVAILABLE


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
