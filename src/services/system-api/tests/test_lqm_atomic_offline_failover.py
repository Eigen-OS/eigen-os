from concurrent.futures import ThreadPoolExecutor

import pytest

from system_api.lqm import DeviceState, LiveQubitManager, LqmError, LqmErrorCode


def test_atomic_race_prevention_same_qubit_one_wins() -> None:
    lqm = LiveQubitManager()

    def attempt(allocation_id: str):
        try:
            lqm.allocate(allocation_id=allocation_id, device_id="d1", qubits=[1, 2])
            return "ok"
        except LqmError as exc:
            return exc.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["a1", "a2"]))

    assert outcomes.count("ok") == 1
    assert outcomes.count(LqmErrorCode.LQM_CAPACITY_EXHAUSTED.value) == 1


def test_double_release_is_idempotent() -> None:
    lqm = LiveQubitManager()
    lqm.allocate(allocation_id="a1", device_id="d1", qubits=[1])
    first = lqm.release("a1")
    second = lqm.release("a1")
    assert first is True
    assert second is True
    assert lqm.get_owner("d1", 1) is None


def test_offline_transition_sequence_is_deterministic() -> None:
    lqm = LiveQubitManager(offline_after_failures=2, online_after_successes=2)
    assert lqm.register_probe("d1", healthy=False).value == DeviceState.DEGRADED.value
    assert lqm.register_probe("d1", healthy=False).value == DeviceState.OFFLINE.value
    assert lqm.start_reconnect("d1").value == DeviceState.RECONNECTING.value
    assert lqm.register_probe("d1", healthy=True).value == DeviceState.RECONNECTING.value
    assert lqm.register_probe("d1", healthy=True).value == DeviceState.ONLINE.value

    states = [(e["from_state"], e["to_state"]) for e in lqm.events]
    assert states == [
        ("ONLINE", "DEGRADED"),
        ("DEGRADED", "OFFLINE"),
        ("OFFLINE", "RECONNECTING"),
        ("RECONNECTING", "ONLINE"),
    ]


def test_reconnect_backoff_is_deterministic() -> None:
    lqm = LiveQubitManager(base_backoff_ms=100, max_backoff_ms=800)
    assert [lqm.reconnect_delay_ms(i) for i in range(1, 6)] == [100, 200, 400, 800, 800]


@pytest.mark.parametrize(
    ("driver_status", "expected"),
    [
        ("INVALID_ARGUMENT", LqmErrorCode.LQM_ALLOCATION_INVALID_REQUEST),
        ("FAILED_PRECONDITION", LqmErrorCode.LQM_DEVICE_OFFLINE),
        ("RESOURCE_EXHAUSTED", LqmErrorCode.LQM_CAPACITY_EXHAUSTED),
        ("UNAVAILABLE", LqmErrorCode.LQM_DRIVER_UNAVAILABLE_RETRYABLE),
        ("DEADLINE_EXCEEDED", LqmErrorCode.LQM_DRIVER_TIMEOUT_RETRYABLE),
        ("INTERNAL", LqmErrorCode.LQM_DRIVER_INTERNAL),
        ("UNKNOWN", LqmErrorCode.LQM_DRIVER_INTERNAL),
    ],
)
def test_error_mapping_conformance(driver_status: str, expected: LqmErrorCode) -> None:
    lqm = LiveQubitManager()
    assert lqm.map_driver_error(driver_status) == expected


def test_transition_event_has_required_fields_and_at_risk_marking() -> None:
    lqm = LiveQubitManager(offline_after_failures=1)
    lqm.allocate(allocation_id="a1", device_id="d1", qubits=[1])
    lqm.register_probe("d1", healthy=False, trace_id="t-1")
    event = lqm.events[-1]
    for key in ("device_id", "from_state", "to_state", "reason_code", "attempt", "trace_id", "timestamp_utc"):
        assert key in event
    assert lqm._allocations["a1"].at_risk is True
    