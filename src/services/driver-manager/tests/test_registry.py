from __future__ import annotations

from dataclasses import dataclass

import pytest

from driver_manager.registry import DriverRegistry


@dataclass(frozen=True)
class _Device:
    device_id: str


class _Driver:
    def __init__(self, devices: list[str]):
        self._devices = devices

    def get_devices(self) -> list[_Device]:
        return [_Device(device_id=d) for d in self._devices]


def test_add_and_lookup_by_device_id() -> None:
    registry = DriverRegistry()
    driver = _Driver(devices=["sim:1", "sim:2"])

    registry.add_driver("sim", driver)

    assert registry.get_driver("sim") is driver
    assert registry.get_driver_for_device("sim:1") is driver
    assert registry.get_driver_for_device("unknown") is None


def test_remove_driver_clears_device_lookup() -> None:
    registry = DriverRegistry()
    driver = _Driver(devices=["sim:1"])
    registry.add_driver("sim", driver)

    assert registry.remove_driver("sim") is True
    assert registry.remove_driver("sim") is False
    assert registry.get_driver_for_device("sim:1") is None


def test_duplicate_device_id_rejected() -> None:
    registry = DriverRegistry()
    registry.add_driver("d1", _Driver(devices=["sim:shared"]))

    with pytest.raises(ValueError, match="already owned"):
        registry.add_driver("d2", _Driver(devices=["sim:shared"]))
