from __future__ import annotations

import json

import grpc
import pytest

from driver_manager.simulator_driver import DriverExecutionError, SimulatorDriver


class _FakeDevice:
    def __init__(self, device_id: str) -> None:
        self.device_id = device_id


@pytest.fixture()
def simulator_driver() -> SimulatorDriver:
    from eigen_internal.v1 import types_pb2 as types_pb

    drv = SimulatorDriver(types_pb=types_pb)
    drv.initialize(config={})
    return drv


def _aqo(ops: list[dict], qubits: int = 2) -> bytes:
    return json.dumps({"version": "1.0.0", "qubits": qubits, "operations": ops}).encode("utf-8")


@pytest.mark.parametrize(
    ("profile", "enabled", "expected"),
    [
        ("simulator", True, "pass"),
        ("ibm", False, "unsupported"),
        ("aws", False, "unsupported"),
    ],
)
def test_qdriver_v1_profile_matrix_fail_closed(
    simulator_driver: SimulatorDriver,
    profile: str,
    enabled: bool,
    expected: str,
) -> None:
    if not enabled:
        with pytest.raises(DriverExecutionError) as err:
            simulator_driver.execute_circuit(
                device_id="sim:local",
                circuit=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1),
                shots=8,
                options={"provider_profile": profile},
            )
        assert err.value.status_code == grpc.StatusCode.UNIMPLEMENTED
        assert f"Unsupported provider_profile: {profile}" == err.value.message
        return

    counts, _, metadata = simulator_driver.execute_circuit(
        device_id="sim:local",
        circuit=_aqo([{"op": "MEASURE", "q": [0], "c": [0]}], qubits=1),
        shots=8,
        options={"provider_profile": profile, "seed": "11"},
    )
    assert sum(counts.values()) == 8
    assert metadata["provider_profile"] == "simulator"
    assert expected == "pass"
    
def test_session_reuse_across_compatible_execution(
    simulator_driver,
):
    first = simulator_driver.session_key(
        "sim:local",
        {"seed": "1"},
    )

    second = simulator_driver.session_key(
        "sim:local",
        {"seed": "1"},
    )

    assert first == second


def test_calibration_artifact_reference_stability(
    simulator_driver,
):
    first = simulator_driver.calibrate_device(
        "sim:local",
        {},
    )

    second = simulator_driver.calibrate_device(
        "sim:local",
        {},
    )

    assert first == second
