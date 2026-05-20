from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Dict, List, Optional, Tuple


class DeviceState(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    RECONNECTING = "RECONNECTING"


class AllocationState(str, Enum):
    PENDING = "PENDING"
    RESERVED = "RESERVED"
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    FAILED = "FAILED"


class LqmErrorCode(str, Enum):
    LQM_ALLOCATION_INVALID_REQUEST = "LQM_ALLOCATION_INVALID_REQUEST"
    LQM_DEVICE_OFFLINE = "LQM_DEVICE_OFFLINE"
    LQM_CAPACITY_EXHAUSTED = "LQM_CAPACITY_EXHAUSTED"
    LQM_DRIVER_UNAVAILABLE_RETRYABLE = "LQM_DRIVER_UNAVAILABLE_RETRYABLE"
    LQM_DRIVER_TIMEOUT_RETRYABLE = "LQM_DRIVER_TIMEOUT_RETRYABLE"
    LQM_DRIVER_INTERNAL = "LQM_DRIVER_INTERNAL"


QDRIVER_TO_LQM_ERRORS = {
    "INVALID_ARGUMENT": LqmErrorCode.LQM_ALLOCATION_INVALID_REQUEST,
    "FAILED_PRECONDITION": LqmErrorCode.LQM_DEVICE_OFFLINE,
    "RESOURCE_EXHAUSTED": LqmErrorCode.LQM_CAPACITY_EXHAUSTED,
    "UNAVAILABLE": LqmErrorCode.LQM_DRIVER_UNAVAILABLE_RETRYABLE,
    "DEADLINE_EXCEEDED": LqmErrorCode.LQM_DRIVER_TIMEOUT_RETRYABLE,
}


@dataclass(frozen=True)
class DeviceTransitionEvent:
    device_id: str
    from_state: str
    to_state: str
    reason_code: str
    attempt: int
    trace_id: str
    timestamp_utc: str


@dataclass
class AllocationRecord:
    allocation_id: str
    device_id: str
    qubits: Tuple[int, ...]
    state: AllocationState
    at_risk: bool = False


class LqmError(RuntimeError):
    def __init__(self, code: LqmErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class LiveQubitManager:
    def __init__(
        self,
        offline_after_failures: int = 3,
        online_after_successes: int = 2,
        base_backoff_ms: int = 100,
        max_backoff_ms: int = 5_000,
    ) -> None:
        self.offline_after_failures = offline_after_failures
        self.online_after_successes = online_after_successes
        self.base_backoff_ms = base_backoff_ms
        self.max_backoff_ms = max_backoff_ms
        self._lock = Lock()
        self._owner_map: Dict[Tuple[str, int], str] = {}
        self._allocations: Dict[str, AllocationRecord] = {}
        self._device_state: Dict[str, DeviceState] = {}
        self._probe_failures: Dict[str, int] = {}
        self._probe_successes: Dict[str, int] = {}
        self._reconnect_attempts: Dict[str, int] = {}
        self.events: List[dict] = []

    def map_driver_error(self, status: str) -> LqmErrorCode:
        return QDRIVER_TO_LQM_ERRORS.get(status, LqmErrorCode.LQM_DRIVER_INTERNAL)

    def _emit_transition(self, device_id: str, old: DeviceState, new: DeviceState, reason: str, trace_id: str) -> None:
        attempt = self._reconnect_attempts.get(device_id, 0)
        self.events.append(
            DeviceTransitionEvent(
                device_id=device_id,
                from_state=old.value,
                to_state=new.value,
                reason_code=reason,
                attempt=attempt,
                trace_id=trace_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            ).__dict__
        )

    def _set_state(self, device_id: str, new: DeviceState, reason: str, trace_id: str) -> None:
        old = self._device_state.get(device_id, DeviceState.ONLINE)
        if old != new:
            self._device_state[device_id] = new
            self._emit_transition(device_id, old, new, reason, trace_id)

    def register_probe(self, device_id: str, healthy: bool, trace_id: str = "probe") -> DeviceState:
        with self._lock:
            state = self._device_state.get(device_id, DeviceState.ONLINE)
            if healthy:
                self._probe_successes[device_id] = self._probe_successes.get(device_id, 0) + 1
                self._probe_failures[device_id] = 0
                if state == DeviceState.RECONNECTING and self._probe_successes[device_id] >= self.online_after_successes:
                    self._set_state(device_id, DeviceState.ONLINE, "HEALTHCHECK_RESTORED", trace_id)
            else:
                self._probe_failures[device_id] = self._probe_failures.get(device_id, 0) + 1
                self._probe_successes[device_id] = 0
                if state == DeviceState.ONLINE:
                    self._set_state(device_id, DeviceState.DEGRADED, "PROBE_FAILURE", trace_id)
                if self._probe_failures[device_id] >= self.offline_after_failures:
                    self._set_state(device_id, DeviceState.OFFLINE, "OFFLINE_THRESHOLD_REACHED", trace_id)
                    for allocation in self._allocations.values():
                        if allocation.device_id == device_id and allocation.state == AllocationState.ACTIVE:
                            allocation.at_risk = True
            return self._device_state.get(device_id, DeviceState.ONLINE)

    def start_reconnect(self, device_id: str, trace_id: str = "reconnect") -> DeviceState:
        with self._lock:
            self._reconnect_attempts[device_id] = self._reconnect_attempts.get(device_id, 0) + 1
            self._set_state(device_id, DeviceState.RECONNECTING, "RECONNECT_SCHEDULED", trace_id)
            return self._device_state.get(device_id, DeviceState.RECONNECTING)

    def fail_reconnect(self, device_id: str, trace_id: str = "reconnect") -> DeviceState:
        with self._lock:
            self._set_state(device_id, DeviceState.OFFLINE, "RECONNECT_FAILED", trace_id)
            return self._device_state.get(device_id, DeviceState.OFFLINE)

    def reconnect_delay_ms(self, attempt: int) -> int:
        return min(self.max_backoff_ms, self.base_backoff_ms * (2 ** (attempt - 1)))

    def allocate(self, allocation_id: str, device_id: str, qubits: List[int], driver_ack: bool = True) -> AllocationRecord:
        with self._lock:
            state = self._device_state.get(device_id, DeviceState.ONLINE)
            if state in (DeviceState.OFFLINE, DeviceState.RECONNECTING):
                raise LqmError(LqmErrorCode.LQM_DEVICE_OFFLINE, f"Device {device_id} is {state.value}")
            record = AllocationRecord(allocation_id=allocation_id, device_id=device_id, qubits=tuple(qubits), state=AllocationState.PENDING)
            for q in qubits:
                key = (device_id, q)
                if key in self._owner_map:
                    record.state = AllocationState.FAILED
                    self._allocations[allocation_id] = record
                    raise LqmError(LqmErrorCode.LQM_CAPACITY_EXHAUSTED, f"Qubit already reserved: {key}")
            for q in qubits:
                self._owner_map[(device_id, q)] = allocation_id
            record.state = AllocationState.RESERVED
            if not driver_ack:
                for q in qubits:
                    self._owner_map.pop((device_id, q), None)
                record.state = AllocationState.FAILED
                self._allocations[allocation_id] = record
                raise LqmError(LqmErrorCode.LQM_DRIVER_INTERNAL, "Driver reservation failed")
            record.state = AllocationState.ACTIVE
            self._allocations[allocation_id] = record
            return record

    def release(self, allocation_id: str) -> bool:
        with self._lock:
            rec = self._allocations.get(allocation_id)
            if rec is None:
                return False
            if rec.state == AllocationState.RELEASED:
                return True
            for q in rec.qubits:
                owner = self._owner_map.get((rec.device_id, q))
                if owner == allocation_id:
                    self._owner_map.pop((rec.device_id, q), None)
            rec.state = AllocationState.RELEASED
            return True

    def get_owner(self, device_id: str, qubit_id: int) -> Optional[str]:
        with self._lock:
            return self._owner_map.get((device_id, qubit_id))
