"""PennyLane quantum driver plugin."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import grpc

from .base_driver import DeviceStatusInfo, DriverCapabilities, DriverHealth
from .simulator_driver import DriverExecutionError


def create_plugin(*, types_pb) -> "PennyLaneDriver":
    return PennyLaneDriver(types_pb=types_pb)


class PennyLaneDriver:
    name = "pennylane"

    def __init__(self, types_pb: Any):
        self._types_pb = types_pb
        self._initialized = False
        self._device_name = "default.qubit"
        self._max_wires = 16

    def initialize(self, config: dict[str, str]) -> None:
        try:
            import pennylane as qml
        except ImportError as exc:
            raise RuntimeError(
                "PennyLane plugin requires the 'pennylane' optional dependency"
            ) from exc

        self._device_name = config.get("device", "default.qubit")
        self._max_wires = int(config.get("max_wires", "16"))
        qml.device(self._device_name, wires=min(1, self._max_wires))
        self._initialized = True

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(
            driver_api_version="1.0",
            features={
                "execution": "aqo_json",
                "backend_type": "simulator",
                "provider": "pennylane",
                "device": self._device_name,
                "ops": "RX,RY,RZ,H,X,CP,CX,SWAP,MEASURE",
            },
        )

    def healthcheck(self) -> DriverHealth:
        return DriverHealth(
            ready=self._initialized,
            reason="" if self._initialized else "driver is not initialized",
            details={"driver": self.name, "device": self._device_name},
        )

    def get_devices(self) -> list[object]:
        if not self._initialized:
            return []

        return [
            self._types_pb.DeviceInfo(
                device_id="sim:pennylane",
                name=f"PennyLane ({self._device_name})",
                backend_type="simulator",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities={
                    "provider": "pennylane",
                    "device": self._device_name,
                    "formats": "AQO_JSON",
                    "ops": "RX,RY,RZ,H,X,CP,CX,SWAP,MEASURE",
                    "bitstring_order": "msb_first_by_classical_index",
                },
            )
        ]

    def execute_circuit(
        self,
        device_id: str,
        circuit: bytes,
        shots: int,
        options: dict[str, str],
    ) -> tuple[dict[str, int], float, dict[str, str]]:
        if device_id != "sim:pennylane":
            raise DriverExecutionError(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"unknown PennyLane device: {device_id}",
            )

        try:
            import pennylane as qml

            payload = json.loads(circuit.decode("utf-8"))
            wires = int(payload["qubits"])
            operations = payload["operations"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise DriverExecutionError(
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid AQO_JSON payload",
            ) from exc

        if wires < 1 or wires > self._max_wires:
            raise DriverExecutionError(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"qubits must be between 1 and {self._max_wires}",
            )

        shots = int(shots)
        seed = int(options.get("seed", "0"))
        dev = qml.device(self._device_name, wires=wires, shots=shots, seed=seed)

        @qml.qnode(dev)
        def execute():
            for index, operation in enumerate(operations):
                self._apply_operation(qml, operation, index)
            return qml.sample(wires=range(wires))

        start = time.perf_counter()
        samples = execute()
        elapsed = time.perf_counter() - start

        counts: dict[str, int] = {}
        for sample in samples:
            bitstring = "".join(str(int(bit)) for bit in reversed(sample))
            counts[bitstring] = counts.get(bitstring, 0) + 1

        return counts, elapsed, {
            "driver": self.name,
            "provider_profile": "pennylane",
            "device": self._device_name,
            "qubits": str(wires),
            "shots": str(shots),
            "bitstring_order": "msb_first_by_classical_index",
        }

    @staticmethod
    def _apply_operation(qml: Any, operation: dict[str, Any], index: int) -> None:
        op = str(operation.get("op", "")).upper()
        qubits = operation.get("q")
        params = operation.get("params") or {}

        if not isinstance(qubits, list) or not all(isinstance(q, int) for q in qubits):
            raise DriverExecutionError(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"operation[{index}].q must be a list of integers",
            )

        theta = float(params.get("theta", 0.0))
        gates = {
            "RX": lambda: qml.RX(theta, wires=qubits[0]),
            "RY": lambda: qml.RY(theta, wires=qubits[0]),
            "RZ": lambda: qml.RZ(theta, wires=qubits[0]),
            "H": lambda: qml.Hadamard(wires=qubits[0]),
            "X": lambda: qml.PauliX(wires=qubits[0]),
            "CX": lambda: qml.CNOT(wires=qubits[:2]),
            "CP": lambda: qml.ControlledPhaseShift(theta, wires=qubits[:2]),
            "SWAP": lambda: qml.SWAP(wires=qubits[:2]),
        }

        if op == "MEASURE":
            return
        if op not in gates:
            raise DriverExecutionError(
                grpc.StatusCode.UNIMPLEMENTED,
                f"Unsupported Op: {op} at operation[{index}]",
            )
        gates[op]()

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        return DeviceStatusInfo(
            device_id=device_id,
            status=self._types_pb.ONLINE if self._initialized else self._types_pb.OFFLINE,
            metadata={"driver": self.name},
        )

    def session_key(self, device_id: str, options: dict[str, str]) -> str:
        raw = json.dumps(
            {"device_id": device_id, "options": options},
            sort_keys=True,
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def refresh_session(self, session_key: str) -> None:
        return None

    def close_session(self, session_key: str) -> None:
        return None

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        return f"calibration:{self.name}:{device_id}"
