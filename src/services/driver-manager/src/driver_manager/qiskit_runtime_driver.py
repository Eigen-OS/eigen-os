"""Qiskit Runtime driver skeleton with auth resolution and health checks."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

import grpc

from .base_driver import DeviceStatusInfo, DriverCapabilities, DriverHealth
from .simulator_driver import DriverExecutionError


@dataclass(frozen=True)
class _AuthConfig:
    source: str
    token: str


class QiskitRuntimeDriver:
    """Production baseline skeleton for IBM Qiskit Runtime integration."""

    name = "qiskit-runtime"

    def __init__(self, types_pb):
        self._types_pb = types_pb
        self._initialized = False
        self._init_error = ""
        self._auth_source = ""
        self._instance = ""
        self._channel = "ibm_quantum"
        self._timeout_sec = 30.0
        self._max_retries = 2
        self._retry_backoff_sec = 0.25
        self._executor = None

    def initialize(self, config: dict[str, str]) -> None:
        self._initialized = False
        self._init_error = ""
        auth = self._resolve_auth(config)
        self._auth_source = auth.source
        self._instance = config.get("instance", "")
        self._channel = config.get("channel", "ibm_quantum")
        self._timeout_sec = _positive_float(config.get("timeout_sec"), default=30.0)
        self._max_retries = _non_negative_int(config.get("max_retries"), default=2)
        self._retry_backoff_sec = _positive_float(config.get("retry_backoff_sec"), default=0.25)
        self._initialized = True

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(
            driver_api_version="1.0",
            features={
                "execution": "qiskit_runtime",
                "auth_sources": "token,token_env,token_secret_ref",
                "channel": self._channel,
                "timeouts": "execute_timeout_sec",
                "retry_policy": "unavailable,deadline_exceeded,resource_exhausted",
            },
        )

    def healthcheck(self) -> DriverHealth:
        if self._initialized:
            return DriverHealth(
                ready=True,
                details={
                    "driver": self.name,
                    "auth_source": self._auth_source,
                    "channel": self._channel,
                    "instance": self._instance,
                },
            )
        return DriverHealth(
            ready=False,
            reason=self._init_error or "driver is not initialized",
            details={"driver": self.name},
        )

    def get_devices(self) -> list[object]:
        if not self._initialized:
            return []
        return [
            self._types_pb.DeviceInfo(
                device_id="ibm:qiskit-runtime",
                name="IBM Qiskit Runtime",
                backend_type="qpu",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities={
                    "formats": "AQO_JSON",
                    "provider": "ibm_quantum",
                    "auth_source": self._auth_source,
                },
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
                    raise DriverExecutionError(grpc.StatusCode.DEADLINE_EXCEEDED, f"IBM runtime timed out after {timeout_sec:.3f}s")
                sleep_sec = min(self._retry_backoff_sec * attempt, max(0.0, deadline - time.monotonic()))
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
        raise last_error or DriverExecutionError(grpc.StatusCode.INTERNAL, "IBM runtime execution failed")

    def _invoke_runtime(
        self,
        *,
        device_id: str,
        circuit: bytes,
        shots: int,
        options: dict[str, str],
        timeout_sec: float,
    ) -> tuple[dict[str, int], float, dict[str, str]]:
        if self._executor is None:
            raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, "Qiskit Runtime execution adapter is not configured")
        return self._executor(device_id=device_id, circuit=circuit, shots=shots, options=options, timeout_sec=timeout_sec)

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        return DeviceStatusInfo(
            device_id=device_id,
            status=self._types_pb.ONLINE if self._initialized else self._types_pb.OFFLINE,
            metadata={"driver": self.name, "ready": str(self._initialized).lower()},
        )

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        _ = (device_id, options)
        raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, "Qiskit Runtime calibration is not implemented yet")

    def _resolve_auth(self, config: dict[str, str]) -> _AuthConfig:
        direct_token = config.get("token", "").strip()
        if direct_token:
            return _AuthConfig(source="token", token=direct_token)

        token_env = config.get("token_env", "").strip()
        if token_env:
            token = os.getenv(token_env, "").strip()
            if token:
                return _AuthConfig(source=f"env:{token_env}", token=token)
            self._init_error = f"missing token in env var '{token_env}'"
            raise ValueError(self._init_error)

        token_secret_ref = config.get("token_secret_ref", "").strip()
        if token_secret_ref:
            secrets_blob = os.getenv("DRIVER_MANAGER_SECRETS_JSON", "{}")
            try:
                secrets = json.loads(secrets_blob)
            except json.JSONDecodeError as exc:
                self._init_error = "DRIVER_MANAGER_SECRETS_JSON must be valid JSON object"
                raise ValueError(self._init_error) from exc
            token = str(secrets.get(token_secret_ref, "")).strip()
            if token:
                return _AuthConfig(source=f"secret_ref:{token_secret_ref}", token=token)
            self._init_error = f"missing token for secret ref '{token_secret_ref}'"
            raise ValueError(self._init_error)

        self._init_error = "qiskit runtime auth missing: set token, token_env, or token_secret_ref"
        raise ValueError(self._init_error)

    def _ensure_ready(self) -> None:
        if not self._initialized:
            raise DriverExecutionError(grpc.StatusCode.FAILED_PRECONDITION, "Qiskit Runtime driver is not initialized")

    @staticmethod
    def _is_retryable(code: grpc.StatusCode) -> bool:
        return code in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.RESOURCE_EXHAUSTED}

    @staticmethod
    def _normalize_provider_error(err: DriverExecutionError) -> DriverExecutionError:
        msg = err.message.lower()
        if "quota" in msg or "rate limit" in msg:
            return DriverExecutionError(grpc.StatusCode.RESOURCE_EXHAUSTED, err.message)
        if "timeout" in msg:
            return DriverExecutionError(grpc.StatusCode.DEADLINE_EXCEEDED, err.message)
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
