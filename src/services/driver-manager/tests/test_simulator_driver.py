from __future__ import annotations

import json
import math

import grpc
import pytest

from driver_manager.proto_gen import ensure_generated
from driver_manager.simulator_driver import DriverExecutionError, SimulatorDriver

ensure_generated()

from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


def _driver() -> SimulatorDriver:
    drv = SimulatorDriver(types_pb=types_pb)
    drv.initialize(config={})
    return drv


def _aqo(operations: list[dict], qubits: int = 2, parameters: dict[str, object] | None = None) -> bytes:
    payload: dict[str, object] = {"version": "0.1", "qubits": qubits, "operations": operations}
    if parameters is not None:
        payload["parameters"] = parameters
    return json.dumps(payload).encode("utf-8")


def test_circuit_ground_state_counts() -> None:
    drv = _driver()

    counts, _, meta = drv.execute_circuit(
        device_id="sim:golden",
        circuit=_aqo([{"op": "MEASURE", "q": [0, 1], "c": [0, 1]}]),
        shots=32,
        options={"seed": "1"},
    )

    assert counts == {"00": 32}
    assert meta["bitstring_order"] == "msb_first_by_classical_index"


def test_circuit_rx_pi_then_measure() -> None:
    drv = _driver()

    counts, _, _ = drv.execute_circuit(
        device_id="sim:golden",
        circuit=_aqo(
            [
                {"op": "RX", "q": [0], "params": {"theta": math.pi}},
                {"op": "MEASURE", "q": [0, 1], "c": [0, 1]},
            ]
        ),
        shots=32,
        options={"seed": "2"},
    )

    assert counts == {"01": 32}


def test_circuit_symbolic_theta_resolves_from_top_level_parameters() -> None:
    drv = _driver()

    counts, _, _ = drv.execute_circuit(
        device_id="sim:golden",
        circuit=_aqo(
            [
                {"op": "RY", "q": [0], "params": {"theta": "theta"}},
                {"op": "MEASURE", "q": [0, 1], "c": [0, 1]},
            ],
            parameters={"theta": math.pi},
        ),
        shots=32,
        options={"seed": "4"},
    )

    assert counts == {"01": 32}


def test_circuit_ry_pi_cx_rz_then_measure() -> None:
    drv = _driver()

    counts, _, _ = drv.execute_circuit(
        device_id="sim:golden",
        circuit=_aqo(
            [
                {"op": "RY", "q": [0], "params": {"theta": math.pi}},
                {"op": "CX", "q": [0, 1]},
                {"op": "RZ", "q": [1], "params": {"theta": 0.25}},
                {"op": "MEASURE", "q": [0, 1], "c": [0, 1]},
            ]
        ),
        shots=32,
        options={"seed": "3"},
    )

    assert counts == {"11": 32}


def test_simulated_errors() -> None:
    drv = _driver()
    payload = _aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1)

    with pytest.raises(DriverExecutionError) as unavailable:
        drv.execute_circuit("sim:golden", payload, 10, {"simulate_error": "UNAVAILABLE"})
    assert unavailable.value.code == grpc.StatusCode.UNAVAILABLE

    with pytest.raises(DriverExecutionError) as exhausted:
        drv.execute_circuit("sim:golden", payload, 10, {"simulate_error": "RESOURCE_EXHAUSTED"})
    assert exhausted.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED


def test_aqo_version_is_required() -> None:
    drv = _driver()
    payload = json.dumps({"qubits": 1, "operations": [{"op": "MEASURE", "q": [0], "c": [0]}]}).encode("utf-8")

    with pytest.raises(DriverExecutionError) as invalid:
        drv.execute_circuit("sim:golden", payload, 10, {})

    assert invalid.value.code == grpc.StatusCode.INVALID_ARGUMENT
    assert invalid.value.message == "aqo.version is required"
    