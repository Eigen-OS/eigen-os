from __future__ import annotations

from benchmark_service.reproducibility import ReproducibilityGate


def _run(request_hash: str, payload: str, fidelity: float, latency_ms: float) -> dict[str, object]:
    return {
        "snapshot": {
            "request_hash": request_hash,
            "payload": payload,
        },
        "metrics": {
            "fidelity": fidelity,
            "latency_ms": latency_ms,
        },
    }


def test_reproducibility_gate_accepts_consistent_metadata_and_bounded_variance() -> None:
    gate = ReproducibilityGate()
    runs = [
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9910, latency_ms=101.001),
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9911, latency_ms=101.002),
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9909, latency_ms=101.000),
    ]

    report = gate.evaluate(runs)

    assert report.passed is True
    assert report.metadata_consistent is True
    assert report.run_count == 3
    assert report.policy_version == "1.0.0"
    assert report.diagnostics == ()


def test_reproducibility_gate_reports_snapshot_drift_diagnostics() -> None:
    gate = ReproducibilityGate()
    runs = [
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9910, latency_ms=101.001),
        _run("hash-2", '{"a":1,"b":2}', fidelity=0.9911, latency_ms=101.002),
        _run("hash-1", '{"b":2,"a":1}', fidelity=0.9909, latency_ms=101.000),
    ]

    report = gate.evaluate(runs)

    assert report.passed is False
    assert report.metadata_consistent is False
    codes = [item.code for item in report.diagnostics]
    assert "request_hash_mismatch" in codes
    assert "payload_mismatch" in codes


def test_reproducibility_gate_blocks_metric_variance_drift_with_diagnostics() -> None:
    gate = ReproducibilityGate()
    runs = [
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9910, latency_ms=80.0),
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9911, latency_ms=120.0),
        _run("hash-1", '{"a":1,"b":2}', fidelity=0.9909, latency_ms=100.0),
    ]

    report = gate.evaluate(runs)

    assert report.passed is False
    variance_diagnostics = [item for item in report.diagnostics if item.code == "metric_variance_exceeded"]
    assert len(variance_diagnostics) == 1
    assert variance_diagnostics[0].field == "metrics.latency_ms"
    