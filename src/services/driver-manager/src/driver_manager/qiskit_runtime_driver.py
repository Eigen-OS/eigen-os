"""Qiskit Runtime driver skeleton with auth resolution and health checks."""

from __future__ import annotations

import json
import os
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

    def initialize(self, config: dict[str, str]) -> None:
        self._initialized = False
        self._init_error = ""
        auth = self._resolve_auth(config)
        self._auth_source = auth.source
        self._instance = config.get("instance", "")
        self._channel = config.get("channel", "ibm_quantum")
        self._initialized = True

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(
            driver_api_version="1.0",
            features={
                "execution": "qiskit_runtime",
                "auth_sources": "token,token_env,token_secret_ref",
                "channel": self._channel,
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
        _ = (device_id, circuit, shots, options)
        raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, "Qiskit Runtime execution is not implemented yet")

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
