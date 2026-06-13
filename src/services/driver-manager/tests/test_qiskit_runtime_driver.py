from __future__ import annotations

import pytest
import grpc

from driver_manager.proto_gen import ensure_generated
from driver_manager.simulator_driver import DriverExecutionError
from driver_manager.qiskit_runtime_driver import QiskitRuntimeDriver

ensure_generated()
from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


def test_initialize_from_secret_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVER_MANAGER_SECRETS_JSON", '{"ibm/runtime/token":{"value":"from-secret","state":"issued"}}')
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    driver.initialize(
        {
            "provider_config_version": "1.0",
            "runtime_isolation": "process",
            "token_secret_ref": "ibm/runtime/token",
        }
    )

    health = driver.healthcheck()
    assert health.ready is True
    assert health.details["auth_source"] == "secret_ref:ibm/runtime/token"
    assert health.details["provider_config_version"] == "1.0"
    assert health.details["runtime_isolation"] == "process"
    assert driver.get_devices()[0].device_id == "ibm:qiskit-runtime"


def test_initialize_rejects_direct_secret_material() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    with pytest.raises(ValueError, match="resolved through token_secret_ref"):
        driver.initialize(
            {
                "provider_config_version": "1.0",
                "runtime_isolation": "process",
                "token": "abc123",
                "token_secret_ref": "ibm/runtime/token",
            }
        )


def test_initialize_requires_provider_config_version() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    with pytest.raises(ValueError, match="provider config version must be 1.0"):
        driver.initialize(
            {
                "runtime_isolation": "process",
                "token_secret_ref": "ibm/runtime/token",
            }
        )


def test_initialize_rejects_insecure_runtime_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVER_MANAGER_SECRETS_JSON", '{"ibm/runtime/token":{"value":"from-secret","state":"issued"}}')
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    with pytest.raises(ValueError, match="sandbox policy violation"):
        driver.initialize(
            {
                "provider_config_version": "1.0",
                "runtime_isolation": "in_process",
                "token_secret_ref": "ibm/runtime/token",
            }
        )


def test_initialize_missing_secret_ref_message_is_redacted() -> None:
    driver = QiskitRuntimeDriver(types_pb=types_pb)

    with pytest.raises(ValueError, match="configured secret ref"):
        driver.initialize(
            {
                "provider_config_version": "1.0",
                "runtime_isolation": "process",
                "token_secret_ref": "ibm/runtime/token",
            }
        )


def test_execute_retries_resource_exhausted_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVER_MANAGER_SECRETS_JSON", '{"ibm/runtime/token":{"value":"from-secret","state":"issued"}}')
    driver = QiskitRuntimeDriver(types_pb=types_pb)
    driver.initialize(
        {
            "provider_config_version": "1.0",
            "runtime_isolation": "process",
            "token_secret_ref": "ibm/runtime/token",
            "max_retries": "2",
            "retry_backoff_sec": "0.001",
        }
    )
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


def test_execute_timeout_surface_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVER_MANAGER_SECRETS_JSON", '{"ibm/runtime/token":{"value":"from-secret","state":"issued"}}')
    driver = QiskitRuntimeDriver(types_pb=types_pb)
    driver.initialize(
        {
            "provider_config_version": "1.0",
            "runtime_isolation": "process",
            "token_secret_ref": "ibm/runtime/token",
            "max_retries": "1",
            "retry_backoff_sec": "0.001",
            "timeout_sec": "0.001",
        }
    )

    def _executor(**_kwargs):
        raise DriverExecutionError(grpc.StatusCode.UNAVAILABLE, "upstream timeout")

    driver._executor = _executor
    with pytest.raises(DriverExecutionError) as err:
        driver.execute_circuit("ibm:qiskit-runtime", b"{}", 10, {})
    assert err.value.code == grpc.StatusCode.DEADLINE_EXCEEDED
