"""In-memory driver registry for plugin lifecycle and device lookup."""

from __future__ import annotations

from dataclasses import dataclass

from .base_driver import BaseDriver, DriverCapabilities, DriverHealth


@dataclass(frozen=True)
class RegisteredDriver:
    name: str
    driver: BaseDriver
    device_ids: frozenset[str]
    capabilities: DriverCapabilities


class DriverRegistry:
    """Manage registered drivers and reverse index device_id -> driver."""

    def __init__(self) -> None:
        self._drivers: dict[str, RegisteredDriver] = {}
        self._device_to_driver: dict[str, str] = {}

    def add_driver(self, name: str, driver: BaseDriver) -> None:
        if not name:
            raise ValueError("driver name is required")
        if name in self._drivers:
            raise ValueError(f"driver already registered: {name}")
        
        capabilities = driver.capability_handshake()
        if not capabilities.driver_api_version:
            raise ValueError(f"driver {name} capability handshake missing driver_api_version")

        device_ids = []
        for device in driver.get_devices():
            device_id = getattr(device, "device_id", "")
            if not device_id:
                raise ValueError(f"driver {name} produced device with empty device_id")
            if device_id in self._device_to_driver:
                existing = self._device_to_driver[device_id]
                raise ValueError(
                    f"device_id '{device_id}' already owned by driver '{existing}'"
                )
            device_ids.append(device_id)

        for device_id in device_ids:
            self._device_to_driver[device_id] = name

        self._drivers[name] = RegisteredDriver(
            name=name,
            driver=driver,
            device_ids=frozenset(device_ids),
            capabilities=capabilities,
        )

    def remove_driver(self, name: str) -> bool:
        registered = self._drivers.pop(name, None)
        if registered is None:
            return False

        for device_id in registered.device_ids:
            self._device_to_driver.pop(device_id, None)

        return True

    def get_driver(self, name: str) -> BaseDriver | None:
        registered = self._drivers.get(name)
        return None if registered is None else registered.driver

    def get_driver_for_device(self, device_id: str) -> BaseDriver | None:
        driver_name = self._device_to_driver.get(device_id)
        if driver_name is None:
            return None
        return self._drivers[driver_name].driver

    def list_devices(self) -> list[object]:
        devices: list[object] = []
        for registered in self._drivers.values():
            devices.extend(registered.driver.get_devices())
        return devices

    def health_snapshot(self) -> dict[str, DriverHealth]:
        return {name: registered.driver.healthcheck() for name, registered in self._drivers.items()}

    def capability_snapshot(self) -> dict[str, DriverCapabilities]:
        return {name: registered.capabilities for name, registered in self._drivers.items()}
