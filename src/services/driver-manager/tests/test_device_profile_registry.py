from __future__ import annotations

from dataclasses import asdict
from types import SimpleNamespace

import pytest

from driver_manager.base_driver import DeviceStatusInfo, DriverCapabilities, DriverHealth
from driver_manager.registry import DeviceProfileSnapshot, DriverRegistry


def _device(device_id: str, *, backend_type: str, capabilities: dict[str, str], name: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        device_id=device_id,
        backend_type=backend_type,
        capabilities=capabilities,
        name=name or device_id,
    )


class _FakeDriver:
    def __init__(
        self,
        *,
        name: str,
        driver_api_version: str,
        devices: list[SimpleNamespace],
    ) -> None:
        self.name = name
        self._driver_api_version = driver_api_version
        self._devices = devices

    def initialize(self, config: dict[str, str]) -> None:
        _ = config

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(
            driver_api_version=self._driver_api_version,
            features={"execution": "aqo_json", "backend_type": self._devices[0].backend_type},
        )

    def healthcheck(self) -> DriverHealth:
        return DriverHealth(ready=True, details={"driver": self.name})

    def get_devices(self) -> list[object]:
        return list(self._devices)

    def execute_circuit(self, device_id: str, circuit: bytes, shots: int, options: dict[str, str]):
        _ = (device_id, circuit, shots, options)
        return {}, 0.0, {}

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        return DeviceStatusInfo(device_id=device_id, status=1, metadata={"driver": self.name})

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        _ = options
        return f"calib://{self.name}/{device_id}"


def test_device_profile_fixture_round_trip() -> None:
    registry = DriverRegistry()
    registry.add_driver(
        "simulator",
        _FakeDriver(
            name="simulator",
            driver_api_version="1.0",
            devices=[
                _device(
                    "sim:local",
                    backend_type="simulator",
                    capabilities={"provider": "simulator", "backend_type": "simulator", "topology": "none"},
                )
            ],
        ),
    )

    snapshot = registry.device_profile_snapshot()
    assert len(snapshot) == 1

    profile = snapshot[0]
    payload = asdict(profile)
    assert payload["profile_name"] == "simulator"
    assert payload["profile_version"] == "1.0"
    assert payload["device_id"] == "sim:local"
    assert payload["driver_name"] == "simulator"
    assert payload["capability_descriptors"]["provider"] == "simulator"
    assert registry.get_device_profile("sim:local") == profile


def test_unknown_profile_and_unknown_device_rejection() -> None:
    registry = DriverRegistry()
    registry.add_driver(
        "qiskit-runtime",
        _FakeDriver(
            name="qiskit-runtime",
            driver_api_version="1.0",
            devices=[
                _device(
                    "ibm:qiskit-runtime",
                    backend_type="qpu",
                    capabilities={"provider": "ibm_quantum", "backend_type": "qpu"},
                )
            ],
        ),
    )

    with pytest.raises(ValueError, match="unknown device_id: missing-device"):
        registry.resolve_device_profile("missing-device")

    with pytest.raises(ValueError, match="unsupported device profile 'unsupported-profile'"):
        registry.resolve_device_profile("ibm:qiskit-runtime", requested_profile="unsupported-profile")


def test_deterministic_capability_snapshot_ordering() -> None:
    registry = DriverRegistry()
    registry.add_driver(
        "zeta",
        _FakeDriver(
            name="zeta",
            driver_api_version="1.0",
            devices=[
                _device("z-device", backend_type="qpu", capabilities={"provider": "zeta", "backend_type": "qpu"})
            ],
        ),
    )
    registry.add_driver(
        "alpha",
        _FakeDriver(
            name="alpha",
            driver_api_version="1.0",
            devices=[
                _device("a-device", backend_type="qpu", capabilities={"provider": "alpha", "backend_type": "qpu"})
            ],
        ),
    )

    assert list(registry.capability_snapshot().keys()) == ["alpha", "zeta"]
    assert [device.device_id for device in registry.list_devices()] == ["a-device", "z-device"]


def test_profile_negotiation_falls_back_to_simulator() -> None:
    registry = DriverRegistry()
    registry.add_driver(
        "qiskit-runtime",
        _FakeDriver(
            name="qiskit-runtime",
            driver_api_version="1.0",
            devices=[
                _device(
                    "ibm:qiskit-runtime",
                    backend_type="qpu",
                    capabilities={"provider": "ibm_quantum", "backend_type": "qpu"},
                )
            ],
        ),
    )
    registry.add_driver(
        "simulator",
        _FakeDriver(
            name="simulator",
            driver_api_version="1.0",
            devices=[
                _device(
                    "sim:local",
                    backend_type="simulator",
                    capabilities={"provider": "simulator", "backend_type": "simulator"},
                )
            ],
        ),
    )

    resolved = registry.negotiate_device_profile("ibm:qiskit-runtime", requested_profile="unsupported-profile")
    assert resolved.profile_name == "simulator"
    assert resolved.device_id == "sim:local"
