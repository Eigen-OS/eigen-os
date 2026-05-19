from __future__ import annotations

import grpc
import pytest

from driver_manager.aws_braket_driver import AwsBraketDriver
from driver_manager.proto_gen import ensure_generated
from driver_manager.simulator_driver import DriverExecutionError

ensure_generated()
from eigen_internal.v1 import types_pb2 as types_pb  # noqa: E402


def test_initialize_from_static_keys() -> None:
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize({"access_key_id": "AKIA...", "secret_access_key": "secret"})
    assert driver.healthcheck().ready is True
    assert driver.healthcheck().details["auth_source"] == "keys"


def test_initialize_from_secret_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRIVER_MANAGER_SECRETS_JSON", '{"aws/braket/creds":{"access_key_id":"a","secret_access_key":"s"}}')
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize({"credentials_secret_ref": "aws/braket/creds"})
    assert driver.healthcheck().details["auth_source"] == "secret_ref:aws/braket/creds"


def test_requires_auth() -> None:
    driver = AwsBraketDriver(types_pb=types_pb)
    with pytest.raises(ValueError, match="auth missing"):
        driver.initialize({})


def test_retry_maps_throttling() -> None:
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize({"access_key_id": "a", "secret_access_key": "s", "max_retries": "2", "retry_backoff_sec": "0.001"})
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


def test_queue_status_degraded() -> None:
    driver = AwsBraketDriver(types_pb=types_pb)
    driver.initialize({"access_key_id": "a", "secret_access_key": "s", "queue_state": "degraded"})
    info = driver.get_device_status("aws:braket")
    assert info.status == types_pb.DEGRADED
