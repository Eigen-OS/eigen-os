from __future__ import annotations

import pytest
import grpc

from driver_manager.proto_gen import ensure_generated
from driver_manager.simulator_driver import DriverExecutionError
from driver_manager.qiskit_runtime_driver import QiskitRuntimeDriver

ensure_generated()
from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


def test_initialize_from_direct_token() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    driver.initialize({"token": "abc123"})

    health = driver.healthcheck()
    assert health.ready is True
    assert health.details["auth_source"] == "token"
    assert driver.get_devices()[0].device_id == "ibm:qiskit-runtime"


def test_initialize_from_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IBM_RUNTIME_TOKEN", "from-env")
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    driver.initialize({"token_env": "IBM_RUNTIME_TOKEN"})

    assert driver.healthcheck().details["auth_source"] == "env:IBM_RUNTIME_TOKEN"


def test_initialize_from_secret_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVER_MANAGER_SECRETS_JSON", '{"ibm/runtime/token":"from-secret"}')
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    driver.initialize({"token_secret_ref": "ibm/runtime/token"})

    assert driver.healthcheck().details["auth_source"] == "secret_ref:ibm/runtime/token"


def test_initialize_requires_auth() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    with pytest.raises(ValueError, match="auth missing"):
        driver.initialize({})

    health = driver.healthcheck()
    assert health.ready is False
    assert "auth missing" in health.reason


def test_missing_env_token_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IBM_RUNTIME_TOKEN", raising=False)
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    with pytest.raises(ValueError, match="missing token in env var"):
        driver.initialize({"token_env": "IBM_RUNTIME_TOKEN"})

    assert driver.healthcheck().ready is False

def test_execute_retries_resource_exhausted_then_succeeds() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)
    driver.initialize({"token": "abc", "max_retries": "2", "retry_backoff_sec": "0.001"})
    calls = {"n": 0}

    def _executor(**_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise DriverExecutionError(grpc.StatusCode.RESOURCE_EXHAUSTED, "quota exceeded")
        return {"0": 10}, 0.2, {"provider_profile": "ibm"}

    driver._executor = _executor
    counts, _, metadata = driver.execute_circuit("ibm:qiskit-runtime", b"{}", 10, {})
    assert counts == {"0": 10}
    assert metadata["provider_profile"] == "ibm"
    assert calls["n"] == 3


def test_execute_timeout_surface_deadline() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)
    driver.initialize({"token": "abc", "max_retries": "1", "retry_backoff_sec": "0.001", "timeout_sec": "0.001"})

    def _executor(**_kwargs):
        raise DriverExecutionError(grpc.StatusCode.UNAVAILABLE, "upstream timeout")

    driver._executor = _executor
    with pytest.raises(DriverExecutionError) as err:
        driver.execute_circuit("ibm:qiskit-runtime", b"{}", 10, {})
    assert err.value.code == grpc.StatusCode.DEADLINE_EXCEEDED
