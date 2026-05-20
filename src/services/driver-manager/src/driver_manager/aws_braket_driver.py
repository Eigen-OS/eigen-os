"""AWS Braket driver skeleton with pinned adapter profile and queue-aware retries."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import grpc

from .base_driver import DeviceStatusInfo, DriverCapabilities, DriverHealth
from .simulator_driver import DriverExecutionError
from .secret_lifecycle import SecretLifecycleStore


@dataclass(frozen=True)
class _AwsAuthConfig:
    source: str
    access_key_id: str
    secret_access_key: str


class AwsBraketDriver:
    """Production baseline skeleton for AWS Braket integration."""

    name = "aws-braket"
    _ADAPTER_VERSION = "braket-adapter/1.0.0"

    def __init__(self, types_pb):
        self._types_pb = types_pb
        self._initialized = False
        self._init_error = ""
        self._auth_source = ""
        self._region = "us-east-1"
        self._timeout_sec = 30.0
        self._max_retries = 2
        self._retry_backoff_sec = 0.25
        self._queue_state = "ready"
        self._executor = None

    def initialize(self, config: dict[str, str]) -> None:
        self._initialized = False
        self._init_error = ""
        auth = self._resolve_auth(config)
        self._auth_source = auth.source
        self._region = config.get("region", "us-east-1")
        self._timeout_sec = _positive_float(config.get("timeout_sec"), default=30.0)
        self._max_retries = _non_negative_int(config.get("max_retries"), default=2)
        self._retry_backoff_sec = _positive_float(config.get("retry_backoff_sec"), default=0.25)
        self._queue_state = config.get("queue_state", "ready").strip().lower() or "ready"
        self._initialized = True

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(
            driver_api_version="1.0",
            features={
                "execution": "aws_braket",
                "adapter_version": self._ADAPTER_VERSION,
                "auth_sources": "keys,env,secret_ref",
                "timeouts": "execute_timeout_sec",
                "retry_policy": "unavailable,deadline_exceeded,resource_exhausted",
                "queue_states": "ready,queued,degraded",
            },
        )

    def healthcheck(self) -> DriverHealth:
        if self._initialized:
            return DriverHealth(
                ready=True,
                details={"driver": self.name, "auth_source": self._auth_source, "region": self._region, "queue_state": self._queue_state},
            )
        return DriverHealth(ready=False, reason=self._init_error or "driver is not initialized", details={"driver": self.name})

    def get_devices(self) -> list[object]:
        if not self._initialized:
            return []
        return [
            self._types_pb.DeviceInfo(
                device_id="aws:braket",
                name="AWS Braket",
                backend_type="qpu",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities={"formats": "AQO_JSON", "provider": "aws_braket", "region": self._region, "adapter_version": self._ADAPTER_VERSION},
            )
        ]

    def execute_circuit(self, device_id: str, circuit: bytes, shots: int, options: dict[str, str]) -> tuple[dict[str, int], float, dict[str, str]]:
        self._ensure_ready()
        timeout_sec = _positive_float(options.get("timeout_sec"), default=self._timeout_sec)
        deadline = time.monotonic() + timeout_sec
        attempts = self._max_retries + 1
        last_error: DriverExecutionError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._invoke_runtime(device_id=device_id, circuit=circuit, shots=shots, options=options, timeout_sec=timeout_sec)
            except DriverExecutionError as err:
                last_error = self._normalize_provider_error(err)
                if not self._is_retryable(last_error.code) or attempt >= attempts:
                    raise last_error
                if time.monotonic() >= deadline:
                    raise DriverExecutionError(grpc.StatusCode.DEADLINE_EXCEEDED, f"AWS Braket timed out after {timeout_sec:.3f}s")
                sleep_sec = min(self._retry_backoff_sec * attempt, max(0.0, deadline - time.monotonic()))
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
        raise last_error or DriverExecutionError(grpc.StatusCode.INTERNAL, "AWS Braket execution failed")

    def _invoke_runtime(self, *, device_id: str, circuit: bytes, shots: int, options: dict[str, str], timeout_sec: float) -> tuple[dict[str, int], float, dict[str, str]]:
        if self._executor is None:
            raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, "AWS Braket execution adapter is not configured")
        return self._executor(device_id=device_id, circuit=circuit, shots=shots, options=options, timeout_sec=timeout_sec)

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        queue_depth = 5 if self._queue_state == "queued" else 0
        est_wait = 60 if self._queue_state == "queued" else 0
        status = self._types_pb.ONLINE if self._initialized else self._types_pb.OFFLINE
        if self._queue_state == "degraded":
            status = self._types_pb.DEGRADED
        return DeviceStatusInfo(device_id=device_id, status=status, queue_depth=queue_depth, estimated_wait_sec=est_wait, metadata={"driver": self.name, "queue_state": self._queue_state})

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        _ = (device_id, options)
        raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, "AWS Braket calibration is not implemented yet")

    def _resolve_auth(self, config: dict[str, str]) -> _AwsAuthConfig:
        access_key_id = config.get("access_key_id", "").strip()
        secret_access_key = config.get("secret_access_key", "").strip()
        if access_key_id and secret_access_key:
            return _AwsAuthConfig("keys", access_key_id, secret_access_key)

        key_env = config.get("credentials_env", "").strip()
        if key_env:
            raw = os.getenv(key_env, "").strip()
            if raw:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    self._init_error = f"invalid JSON in env var '{key_env}'"
                    raise ValueError(self._init_error) from exc
                access_key_id = str(data.get("access_key_id", "")).strip()
                secret_access_key = str(data.get("secret_access_key", "")).strip()
                if access_key_id and secret_access_key:
                    return _AwsAuthConfig(f"env:{key_env}", access_key_id, secret_access_key)
            self._init_error = f"missing AWS credentials in env var '{key_env}'"
            raise ValueError(self._init_error)

        secret_ref = config.get("credentials_secret_ref", "").strip()
        if secret_ref:
            secrets = SecretLifecycleStore()
            raw = secrets.get(secret_ref, actor=self.name, workload_id=config.get("workload_id", "driver-init"), consumer=self.name)
            if isinstance(raw, dict):
                access_key_id = str(raw.get("access_key_id", "")).strip()
                secret_access_key = str(raw.get("secret_access_key", "")).strip()
                if access_key_id and secret_access_key:
                    return _AwsAuthConfig(f"secret_ref:{secret_ref}", access_key_id, secret_access_key)
            self._init_error = f"missing AWS credentials for secret ref '{secret_ref}'"
            raise ValueError(self._init_error)

        self._init_error = "aws braket auth missing: set access_key_id/secret_access_key, credentials_env, or credentials_secret_ref"
        raise ValueError(self._init_error)

    def _ensure_ready(self) -> None:
        if not self._initialized:
            raise DriverExecutionError(grpc.StatusCode.FAILED_PRECONDITION, "AWS Braket driver is not initialized")

    @staticmethod
    def _is_retryable(code: grpc.StatusCode) -> bool:
        return code in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.RESOURCE_EXHAUSTED}

    @staticmethod
    def _normalize_provider_error(err: DriverExecutionError) -> DriverExecutionError:
        msg = err.message.lower()
        if "throttl" in msg or "rate exceeded" in msg:
            return DriverExecutionError(grpc.StatusCode.RESOURCE_EXHAUSTED, err.message)
        if "queue" in msg and "full" in msg:
            return DriverExecutionError(grpc.StatusCode.RESOURCE_EXHAUSTED, err.message)
        if "timeout" in msg:
            return DriverExecutionError(grpc.StatusCode.DEADLINE_EXCEEDED, err.message)
        if "access denied" in msg or "unauthorized" in msg:
            return DriverExecutionError(grpc.StatusCode.PERMISSION_DENIED, err.message)
        return err


def _positive_float(raw: str | None, *, default: float) -> float:
    if raw is None or str(raw).strip() == "":
        return default
    value = float(raw)
    if value <= 0:
        raise ValueError("value must be > 0")
    return value


def _non_negative_int(raw: str | None, *, default: int) -> int:
    if raw is None or str(raw).strip() == "":
        return default
    value = int(raw)
    if value < 0:
        raise ValueError("value must be >= 0")
    return value
