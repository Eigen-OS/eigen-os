from types import SimpleNamespace
import pytest
from driver_manager.driver_selection import DriverSelectionError, resolve_execution_target


class _Driver:
    def __init__(self, name: str, ready: bool = True):
        self.name = name
        self._ready = ready

    def healthcheck(self):
        return SimpleNamespace(ready=self._ready)


def _registry(devices, owners):
    class _R:
        def list_devices(self):
            return devices

        def get_driver_for_device(self, device_id):
            return owners.get(device_id)

    return _R()


def test_explicit_device_is_unambiguous():
    driver = _Driver("qiskit-runtime")
    registry = _registry([], {"ibm:1": driver})
    target = resolve_execution_target(
        registry,
        device_id="ibm:1",
        driver_name="qiskit-runtime",
        selection="explicit",
    )
    assert (target.device_id, target.driver_name, target.selection) == (
        "ibm:1",
        "qiskit-runtime",
        "explicit",
    )


def test_explicit_auto_device_is_rejected():
    with pytest.raises(DriverSelectionError, match="concrete device_id"):
        resolve_execution_target(
            _registry([], {}),
            device_id="auto",
            driver_name="",
            selection="explicit",
        )


def test_auto_uses_metrics_and_deterministic_tie_breaker():
    first = _Driver("a-driver")
    second = _Driver("b-driver")
    devices = [
        SimpleNamespace(
            device_id="b:1",
            status=1,
            queue_depth=0,
            estimated_wait_sec=1,
            capabilities={"formats": "AQO_JSON"},
        ),
        SimpleNamespace(
            device_id="a:1",
            status=1,
            queue_depth=0,
            estimated_wait_sec=1,
            capabilities={"formats": "AQO_JSON"},
        ),
    ]
    target = resolve_execution_target(
        _registry(devices, {"a:1": first, "b:1": second}),
        device_id="auto",
        driver_name="",
        selection="auto",
    )
    assert target.device_id == "a:1"


def test_auto_does_not_accept_driver_override():
    with pytest.raises(DriverSelectionError, match="cannot include driver"):
        resolve_execution_target(
            _registry([], {}),
            device_id="auto",
            driver_name="simulator",
            selection="auto",
        )
