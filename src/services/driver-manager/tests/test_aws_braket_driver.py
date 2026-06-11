from __future__ import annotations

import grpc
import pytest

from driver_manager.aws_braket_driver import AwsBraketDriver
from driver_manager.proto_gen import ensure_generated
from driver_manager.simulator_driver import DriverExecutionError

ensure_generated()
from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


def test_initialize_from_secret_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DRIVER_MANAGER_SECRETS_JSON",
        '{"aws/braket/creds":{"value":{"access_key_id":"a","secret_access_key":"s"},"state":"issued"}}',
    )
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize(
        {
            "provider_config_version": "1.0",
            "runtime_isolation": "process",
            "credentials_secret_ref": "aws/braket/creds",
        }
    )
    assert driver.healthcheck().ready is True
    assert driver.healthcheck().details["auth_source"] == "secret_ref:aws/braket/creds"
    assert driver.healthcheck().details["provider_config_version"] == "1.0"


def test_initialize_requires_provider_config_version() -> None:
    driver = AwsBraketDriver(types_pb=types_pb)
    with pytest.raises(ValueError, match="provider config version must be 1.0"):
        driver.initialize(
            {
                "runtime_isolation": "process",
                "credentials_secret_ref": "aws/braket/creds",
            }
        )


def test_retry_maps_throttling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DRIVER_MANAGER_SECRETS_JSON",
        '{"aws/braket/creds":{"value":{"access_key_id":"a","secret_access_key":"s"},"state":"issued"}}',
    )
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize(
        {
            "provider_config_version": "1.0",
            "runtime_isolation": "process",
            "credentials_secret_ref": "aws/braket/creds",
            "max_retries": "2",
            "retry_backoff_sec": "0.001",
        }
    )
    calls = {"n": 0}

    def _executor(**_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise DriverExecutionError(grpc.StatusCode.UNAVAILABLE, "ThrottlingException: rate exceeded")
        return {"0": 7}, 0.1, {"provider_profile": "aws"}

    driver._executor = _executor
    counts, _, metadata = driver.execute_circuit("aws:braket", b"{}", 7, {})
    assert counts == {"0": 7}
    assert metadata["provider_profile"] == "aws"


def test_queue_status_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DRIVER_MANAGER_SECRETS_JSON",
        '{"aws/braket/creds":{"value":{"access_key_id":"a","secret_access_key":"s"},"state":"issued"}}',
    )
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize(
        {
            "provider_config_version": "1.0",
            "runtime_isolation": "process",
            "credentials_secret_ref": "aws/braket/creds",
            "queue_state": "degraded",
        }
    )
    info = driver.get_device_status("aws:braket")
    assert info.status == getattr(types_pb, "DEGRADED", types_pb.ONLINE)
