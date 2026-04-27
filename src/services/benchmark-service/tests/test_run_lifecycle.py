from benchmark_service.run_lifecycle import (
    RUN_CONTRACT_VERSION,
    BenchmarkRunService,
    RunState,
    RunTransitionError,
)


def test_run_state_machine_allows_happy_path_and_blocks_reverse_transition() -> None:
    service = BenchmarkRunService()
    run = service.start_run(idempotency_key="job-1", config={"dataset": "d1", "seed": 7})

    service.transition(run_id=run.run_id, new_state=RunState.PREPARING)
    service.transition(run_id=run.run_id, new_state=RunState.RUNNING)
    terminal = service.transition(run_id=run.run_id, new_state=RunState.SUCCEEDED)

    assert terminal.state == RunState.SUCCEEDED
    assert terminal.state_contract_version == RUN_CONTRACT_VERSION

    try:
        service.transition(run_id=run.run_id, new_state=RunState.RUNNING)
    except RunTransitionError as err:
        assert "forbidden" in str(err)
    else:
        raise AssertionError("expected transition error")


def test_start_run_is_idempotent_for_duplicate_request_key() -> None:
    service = BenchmarkRunService()
    first = service.start_run(idempotency_key="dup-key", config={"dataset": "same", "seed": 11})
    second = service.start_run(idempotency_key="dup-key", config={"dataset": "same", "seed": 11})

    assert first.run_id == second.run_id
    assert first.snapshot.request_hash == second.snapshot.request_hash
    assert first.snapshot.contract_version == RUN_CONTRACT_VERSION


def test_retry_is_idempotent_and_requires_terminal_source() -> None:
    service = BenchmarkRunService()
    run = service.start_run(idempotency_key="retryable", config={"dataset": "d2"})

    try:
        service.retry_run(run_id=run.run_id, retry_key="retry-1")
    except RunTransitionError as err:
        assert "allowed only" in str(err)
    else:
        raise AssertionError("retry should fail for non-terminal state")

    service.transition(run_id=run.run_id, new_state=RunState.PREPARING)
    service.transition(run_id=run.run_id, new_state=RunState.FAILED)

    retry_1 = service.retry_run(run_id=run.run_id, retry_key="retry-1")
    retry_2 = service.retry_run(run_id=run.run_id, retry_key="retry-1")

    assert retry_1.run_id == retry_2.run_id
    assert retry_1.parent_run_id == run.run_id


def test_snapshot_is_immutable_and_deterministic() -> None:
    service = BenchmarkRunService()
    run_a = service.start_run(idempotency_key="snapshot-a", config={"b": 2, "a": 1})
    run_b = service.start_run(idempotency_key="snapshot-b", config={"a": 1, "b": 2})

    assert run_a.snapshot.payload == '{"a":1,"b":2}'
    assert run_a.snapshot.request_hash == run_b.snapshot.request_hash

    try:
        run_a.snapshot.payload = "mutated"
    except Exception as err:  # dataclass frozen mutation guard
        assert err is not None
    else:
        raise AssertionError("snapshot must be immutable")
