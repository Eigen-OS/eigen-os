from __future__ import annotations

import pytest

from driver_manager.proto_gen import ensure_generated
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
    