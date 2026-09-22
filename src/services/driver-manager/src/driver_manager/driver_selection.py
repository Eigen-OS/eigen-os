"""Deterministic driver selection policy.

Explicit device ids are the default, stable routing contract.
Auto-selection is opt-in and deterministic: it can only run when
driver_selection=auto and only among healthy AQO-capable devices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AUTO_DEVICE_IDS = frozenset({"auto", "cluster:auto"})


class DriverSelectionError(ValueError):
    """A request does not contain a single unambiguous driver target."""


@dataclass(frozen=True)
class ExecutionTarget:
    device_id: str
    driver_name: str
    driver: Any
    selection: str


def resolve_execution_target(
    registry: Any,
    *,
    device_id: str,
    driver_name: str,
    selection: str,
) -> ExecutionTarget:
    """Resolve request to exactly one registered driver and device.

    explicit: route by concrete device_id, fail closed if device is missing
    auto: opt-in metric-based selection across healthy AQO-capable devices
    """
    mode = (selection or "explicit").strip().lower()
    requested_driver = (driver_name or "").strip()
    requested_device = (device_id or "").strip()

    if mode not in {"explicit", "auto"}:
        raise DriverSelectionError(
            "DRIVER_SELECTION_INVALID: driver_selection must be 'explicit' or 'auto'"
        )

    if mode == "explicit":
        if requested_device in AUTO_DEVICE_IDS:
            raise DriverSelectionError(
                "DRIVER_SELECTION_REQUIRED: explicit selection requires a concrete device_id"
            )
        driver = registry.get_driver_for_device(requested_device)
        if driver is None:
            raise DriverSelectionError(f"device not registered: {requested_device}")
        actual_name = str(getattr(driver, "name", ""))
        if requested_driver and requested_driver != actual_name:
            raise DriverSelectionError(
                f"DRIVER_SELECTION_MISMATCH: device_id '{requested_device}' is owned by "
                f"'{actual_name}', not '{requested_driver}'"
            )
        return ExecutionTarget(requested_device, actual_name, driver, "explicit")

    if requested_driver:
        raise DriverSelectionError(
            "DRIVER_SELECTION_CONFLICT: auto selection cannot include driver override"
        )

    candidates: list[tuple[tuple[int, int, int, str, str], ExecutionTarget]] = []
    for device in registry.list_devices():
        candidate_id = str(getattr(device, "device_id", ""))
        if not candidate_id or candidate_id in AUTO_DEVICE_IDS:
            continue

        capabilities = getattr(device, "capabilities", {}) or {}
        formats = str(capabilities.get("formats", ""))
        supported = {item.strip() for item in formats.split(",") if item.strip()}
        if "AQO_JSON" not in supported:
            continue

        driver = registry.get_driver_for_device(candidate_id)
        if driver is None:
            continue

        health = driver.healthcheck()
        if not health.ready:
            continue

        status = int(getattr(device, "status", 0))
        queue = max(0, int(getattr(device, "queue_depth", 0)))
        wait = max(0, int(getattr(device, "estimated_wait_sec", 0)))
        driver_name = str(getattr(driver, "name", ""))

        score = (
            0 if status == 1 else 1,
            queue,
            wait,
            driver_name,
            candidate_id,
        )
        candidates.append((score, ExecutionTarget(candidate_id, driver_name, driver, "auto")))

    if not candidates:
        raise DriverSelectionError(
            "DRIVER_SELECTION_UNAVAILABLE: auto selection found no healthy AQO-capable device"
        )

    return min(candidates, key=lambda item: item[0])[1]
