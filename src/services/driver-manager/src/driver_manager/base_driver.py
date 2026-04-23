"""Driver plugin interface definitions for driver-manager.

References:
- rfcs/0006-qdriver-api-v0.1.md
- docs/architecture/components/driver-manager.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class DeviceStatusInfo:
    """Normalized status payload used by DriverManagerService."""

    device_id: str
    status: int
    queue_depth: int = 0
    estimated_wait_sec: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


class BaseDriver(Protocol):
    """MVP base interface for quantum drivers/plugins."""

    name: str

    def initialize(self, config: dict[str, str]) -> None:
        """Initialize driver resources."""

    def get_devices(self) -> list[object]:
        """Return `DeviceInfo` protobuf messages supported by this driver."""

    def execute_circuit(
        self,
        device_id: str,
        circuit: bytes,
        shots: int,
        options: dict[str, str],
    ) -> tuple[dict[str, int], float, dict[str, str]]:
        """Execute a circuit and return normalized counts/time/metadata."""

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        """Return status for a specific device."""

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        """Run calibration and return calibration artifact reference."""


QDriver = BaseDriver
