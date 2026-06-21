"""Local AQO JSON simulator driver used as MVP golden backend."""

from __future__ import annotations

import cmath
import hashlib
import json
import math
import random
import time
from dataclasses import dataclass

import grpc

from .base_driver import DeviceStatusInfo, DriverCapabilities, DriverHealth

_SUPPORTED_OPS = {"RX", "RY", "RZ", "CX", "MEASURE"}
_MAX_QUBITS = 16


def _observable_terms_from_payload(payload: dict) -> dict[str, dict[str, object]]:
    annotations = payload.get("annotations")
    if not isinstance(annotations, dict):
        return {}
    observables = annotations.get("observables")
    if not isinstance(observables, dict):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for name, raw_terms in observables.items():
        if not isinstance(name, str) or not isinstance(raw_terms, dict):
            continue
        terms: dict[str, object] = {}
        for key, value in raw_terms.items():
            if not isinstance(key, str):
                break
            if isinstance(value, (int, float, str, bool)):
                terms[key.upper()] = value
            elif isinstance(value, list) and all(isinstance(item, int) for item in value):
                terms[key.upper()] = list(value)
            else:
                break
        else:
            if terms:
                normalized[name] = terms
    return normalized


def _statevector_expectation(state: list[complex], qubits: list[int], operator: str) -> float:
    operator = operator.upper()
    if not qubits or operator not in {"X", "Y", "Z"}:
        return 0.0

    total = 0j
    for basis, amplitude in enumerate(state):
        target = basis
        phase = 1 + 0j
        for qubit in qubits:
            bit = (basis >> qubit) & 1
            if operator in {"X", "Y"}:
                target ^= 1 << qubit
            if operator in {"Z", "Y"} and bit:
                phase *= -1
            if operator == "Y":
                phase *= 1j if bit == 0 else -1j
        total += amplitude.conjugate() * phase * state[target]
    return float(total.real)


class DriverExecutionError(Exception):
    """Driver-level execution error mapped to a gRPC status."""

    def __init__(self, code: grpc.StatusCode, message: str):
        super().__init__(message)
        self.code = code
        self.status_code = code
        self.message = message


@dataclass(frozen=True)
class _MeasureMap:
    qubit: int
    cbit: int


class SimulatorDriver:
    """Simple statevector simulator for AQO JSON payloads."""

    name = "simulator"

    def __init__(self, types_pb):
        self._types_pb = types_pb
        self._sessions: dict[str, str] = {}

    def initialize(self, config: dict[str, str]) -> None:
        _ = config

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(
            driver_api_version="1.0",
            features={
                "execution": "aqo_json",
                "backend_type": "simulator",
            },
        )

    def healthcheck(self) -> DriverHealth:
        return DriverHealth(ready=True, details={"driver": self.name})

    def get_devices(self) -> list[object]:
        simulator_capabilities = {
            "formats": "AQO_JSON",
            "ops": "RX,RY,RZ,CX,MEASURE",
            "bitstring_order": "msb_first_by_classical_index",
        }
        return [
            self._types_pb.DeviceInfo(
                device_id="cluster:auto",
                name="Auto-dispatched distributed simulator",
                backend_type="simulator",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities=dict(simulator_capabilities),
            ),
            self._types_pb.DeviceInfo(
                device_id="sim:local",
                name="Local AQO simulator",
                backend_type="simulator",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities=dict(simulator_capabilities),
            ),
            self._types_pb.DeviceInfo(
                device_id="runtime:deterministic",
                name="Deterministic replay runtime",
                backend_type="simulator",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities=dict(simulator_capabilities),
            ),
        ]

    def execute_circuit(
        self,
        device_id: str,
        circuit: bytes,
        shots: int,
        options: dict[str, str],
    ) -> tuple[dict[str, int], float, dict[str, str]]:
        _ = device_id
        start = time.perf_counter()

        self._validate_provider_profile(options)
        self._simulate_error(options)
        payload = self._parse_payload(circuit)
        qubits = self._parse_qubits(payload)
        operations = payload.get("operations")
        if not isinstance(operations, list):
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "aqo.operations must be a list")

        state = [0j] * (1 << qubits)
        state[0] = 1 + 0j
        measure_map = self._run_operations(state=state, qubits=qubits, payload=payload, operations=operations, options=options)
        counts = self._sample_counts(state=state, qubits=qubits, shots=shots, measure_map=measure_map, options=options)

        elapsed = time.perf_counter() - start
        metadata = {
            "provider_profile": options.get("provider_profile", "simulator"),
            "driver": self.name,
            "aqo_version": str(payload.get("version", "")),
            "qubits": str(qubits),
            "shots": str(shots),
            "bitstring_order": "msb_first_by_classical_index",
        }

        observable_bindings = _observable_terms_from_payload(payload)
        annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
        expectation_info = annotations.get("expectation") if isinstance(annotations, dict) else None
        if isinstance(expectation_info, dict):
            observable_terms = expectation_info.get("observable_terms")
            if not isinstance(observable_terms, dict):
                observable_name = expectation_info.get("observable_name")
                if isinstance(observable_name, str):
                    observable_terms = observable_bindings.get(observable_name)
            if isinstance(observable_terms, dict):
                energy = 0.0
                for operator_name, qubit_spec in observable_terms.items():
                    if isinstance(qubit_spec, int):
                        qubit_indices = [qubit_spec]
                    elif isinstance(qubit_spec, list) and all(isinstance(item, int) for item in qubit_spec):
                        qubit_indices = list(qubit_spec)
                    else:
                        continue
                    energy += _statevector_expectation(state, qubit_indices, operator_name)
                metadata["energy"] = f"{energy:.6f}"

        return counts, elapsed, metadata

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        return DeviceStatusInfo(
            device_id=device_id,
            status=self._types_pb.ONLINE,
            queue_depth=0,
            estimated_wait_sec=0,
            metadata={"driver": self.name},
        )

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        _ = (options,)
        return f"calib://simulator/{device_id}"

    def session_key(self, device_id: str, options: dict[str, str]) -> str:
        normalized_options = {
            str(key): str(value)
            for key, value in sorted(options.items(), key=lambda item: str(item[0]))
        }
        payload = json.dumps(
            {"device_id": str(device_id), "options": normalized_options},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        key = f"session://simulator/{hashlib.sha256(payload).hexdigest()[:24]}"
        self._sessions.setdefault(key, "created")
        return key

    def refresh_session(self, session_key: str) -> None:
        if session_key not in self._sessions:
            raise DriverExecutionError(grpc.StatusCode.FAILED_PRECONDITION, f"unknown session: {session_key}")
        self._sessions[session_key] = "active"

    def close_session(self, session_key: str) -> None:
        if session_key in self._sessions:
            self._sessions[session_key] = "closed"

    def _validate_provider_profile(self, options: dict[str, str]) -> None:
        profile = options.get("provider_profile", "simulator").strip().lower()
        if profile != "simulator":
            raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, f"Unsupported provider_profile: {profile}")

    def _simulate_error(self, options: dict[str, str]) -> None:
        signal = options.get("simulate_error", "").upper()
        if signal == "UNAVAILABLE":
            raise DriverExecutionError(grpc.StatusCode.UNAVAILABLE, "simulated backend unavailable")
        if signal == "RESOURCE_EXHAUSTED":
            raise DriverExecutionError(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                "simulated backend resource exhausted",
            )

    def _parse_payload(self, circuit: bytes) -> dict:
        if not circuit:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "payload.data is required")

        try:
            payload = json.loads(circuit.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "payload.data must be utf-8") from exc
        except json.JSONDecodeError as exc:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"invalid AQO JSON: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "aqo payload must be an object")
        
        version = payload.get("version")
        if not isinstance(version, str) or not version.strip():
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "aqo.version is required")

        operations = payload.get("operations")
        if not isinstance(operations, list):
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "aqo.operations must be a list")
        self._validate_supported_ops(operations)
        return payload

    def _parse_qubits(self, payload: dict) -> int:
        qubits = payload.get("qubits")
        if not isinstance(qubits, int) or qubits <= 0:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "aqo.qubits must be a positive int")
        if qubits > _MAX_QUBITS:
            raise DriverExecutionError(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                f"Simulator Out of Memory: requested {qubits} qubits exceeds limit {_MAX_QUBITS}",
            )
        return qubits

    def _validate_supported_ops(self, operations: list[dict]) -> None:
        for idx, raw_op in enumerate(operations):
            if not isinstance(raw_op, dict):
                raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] must be object")
            op = str(raw_op.get("op", "")).upper()
            if op not in _SUPPORTED_OPS:
                raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, f"Unsupported Op: {op} at operation[{idx}]")

    def _run_operations(
        self,
        state: list[complex],
        qubits: int,
        payload: dict,
        operations: list[dict],
        options: dict[str, str],
    ) -> list[_MeasureMap]:
        measures: list[_MeasureMap] = []
        for idx, raw_op in enumerate(operations):
            if not isinstance(raw_op, dict):
                raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] must be object")

            op = str(raw_op.get("op", "")).upper()
            if op not in _SUPPORTED_OPS:
                raise DriverExecutionError(grpc.StatusCode.UNIMPLEMENTED, f"Unsupported Op: {op} at operation[{idx}]")

            q = raw_op.get("q")
            if not isinstance(q, list) or not all(isinstance(v, int) for v in q):
                raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}].q must be int[]")
            for qidx in q:
                if qidx < 0 or qidx >= qubits:
                    raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] qubit out of range")

            if op in {"RX", "RY", "RZ"}:
                if len(q) != 1:
                    raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"{op} requires exactly one qubit")
                theta = self._get_theta(raw_op, payload=payload, options=options, idx=idx)
                self._apply_single_qubit_rotation(state, qubits, q[0], op, theta)
            elif op == "CX":
                if len(q) != 2:
                    raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "CX requires exactly two qubits")
                self._apply_cx(state, qubits, q[0], q[1])
            elif op == "MEASURE":
                c = raw_op.get("c")
                if not isinstance(c, list) or len(c) != len(q) or not all(isinstance(v, int) for v in c):
                    raise DriverExecutionError(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "MEASURE requires c[] with same length as q[]",
                    )
                if len(set(c)) != len(c):
                    raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "MEASURE c[] must be unique")
                for qidx, cidx in zip(q, c, strict=True):
                    if cidx < 0:
                        raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "classical index must be >= 0")
                    measures.append(_MeasureMap(qubit=qidx, cbit=cidx))

        if not measures:
            measures = [_MeasureMap(qubit=i, cbit=i) for i in range(qubits)]
        return measures

    def _get_theta(self, raw_op: dict, payload: dict, options: dict[str, str], idx: int) -> float:
        params = raw_op.get("params")
        if not isinstance(params, dict) or "theta" not in params:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] missing theta")

        return self._resolve_theta_value(params["theta"], payload=payload, options=options, idx=idx)

    def _resolve_theta_value(
        self,
        value: object,
        *,
        payload: dict,
        options: dict[str, str],
        idx: int,
        seen: set[str] | None = None,
    ) -> float:
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] theta must be numeric")

            try:
                return float(text)
            except ValueError:
                pass

            seen = set() if seen is None else set(seen)
            if text in seen:
                raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] theta binding is circular: {text}")
            seen.add(text)

            parameters = payload.get("parameters")
            if isinstance(parameters, dict) and text in parameters:
                return self._resolve_theta_value(parameters[text], payload=payload, options=options, idx=idx, seen=seen)

            if text in options:
                return self._resolve_theta_value(options[text], payload=payload, options=options, idx=idx, seen=seen)

            for option_key in (f"param.{text}", f"param:{text}", f"parameters.{text}", f"parameters:{text}"):
                if option_key in options:
                    return self._resolve_theta_value(options[option_key], payload=payload, options=options, idx=idx, seen=seen)

            raise DriverExecutionError(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"operation[{idx}] theta must be numeric (unresolved symbol: {text})",
            )
        raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"operation[{idx}] theta must be numeric")

    def _sample_counts(
        self,
        state: list[complex],
        qubits: int,
        shots: int,
        measure_map: list[_MeasureMap],
        options: dict[str, str],
    ) -> dict[str, int]:
        if shots <= 0:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "shots must be > 0")

        cwidth = max((m.cbit for m in measure_map), default=-1) + 1
        cwidth = max(cwidth, 1)

        probabilities = [abs(a) ** 2 for a in state]
        total = sum(probabilities)
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            probabilities = [p / total for p in probabilities]

        rnd = random.Random(int(options.get("seed", "0")))
        counts: dict[str, int] = {}
        for _ in range(shots):
            basis_state = rnd.choices(range(1 << qubits), weights=probabilities, k=1)[0]
            classical = [0] * cwidth
            for mapping in measure_map:
                classical[mapping.cbit] = (basis_state >> mapping.qubit) & 1
            bitstring = "".join(str(classical[i]) for i in range(cwidth - 1, -1, -1))
            counts[bitstring] = counts.get(bitstring, 0) + 1

        return counts

    def _apply_single_qubit_rotation(
        self,
        state: list[complex],
        qubits: int,
        target: int,
        op: str,
        theta: float,
    ) -> None:
        _ = qubits
        c = math.cos(theta / 2)
        s = math.sin(theta / 2)
        if op == "RX":
            matrix = ((c, -1j * s), (-1j * s, c))
        elif op == "RY":
            matrix = ((c, -s), (s, c))
        elif op == "RZ":
            matrix = ((cmath.exp(-1j * theta / 2), 0j), (0j, cmath.exp(1j * theta / 2)))
        else:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, f"unsupported rotation: {op}")

        step = 1 << target
        span = step << 1
        for base in range(0, len(state), span):
            for offset in range(step):
                i0 = base + offset
                i1 = i0 + step
                a0 = state[i0]
                a1 = state[i1]
                state[i0] = matrix[0][0] * a0 + matrix[0][1] * a1
                state[i1] = matrix[1][0] * a0 + matrix[1][1] * a1

    def _apply_cx(self, state: list[complex], qubits: int, control: int, target: int) -> None:
        _ = qubits
        if control == target:
            raise DriverExecutionError(grpc.StatusCode.INVALID_ARGUMENT, "CX control and target must differ")

        control_mask = 1 << control
        target_mask = 1 << target
        for idx in range(len(state)):
            if (idx & control_mask) and not (idx & target_mask):
                swap_idx = idx | target_mask
                state[idx], state[swap_idx] = state[swap_idx], state[idx]
                
