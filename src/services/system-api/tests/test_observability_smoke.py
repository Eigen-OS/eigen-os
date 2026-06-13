from __future__ import annotations

import socket
import urllib.request

from system_api.grpc_impl import JobService
from system_api.observability import (
    _MetricsState,
    record_kb_contract_marker,
    record_kb_fallback,
    record_kb_learning_failure,
    record_kb_quarantine_event,
    record_kb_query,
    record_kb_replay_failure,
    record_public_api_contract_marker,
    start_metrics_server,
)
from system_api.proto_gen import ensure_generated

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _reset_public_contract_metrics() -> None:
    _MetricsState.public_api_contract_requests_total = {
        (version, outcome): 0
        for version in ("1.0.0", "unsupported")
        for outcome in ("accepted", "conflict", "error", "limit", "replayed")
    }


def _reset_kb_metrics() -> None:
    _MetricsState.kb_contract_info = {"1.0.0": 1}
    _MetricsState.kb_queries_total = {
        "records": 0,
        "decision_logs": 0,
        "benchmark_runs": 0,
        "runtime_decisions": 0,
        "learning_evidence": 0,
        "learning_datasets": 0,
        "learning_models": 0,
        "learning_promotions": 0,
        "learning_rollbacks": 0,
    }
    _MetricsState.kb_hits_total = dict(_MetricsState.kb_queries_total)
    _MetricsState.kb_misses_total = dict(_MetricsState.kb_queries_total)
    _MetricsState.kb_fallbacks_total = {
        "storage_unavailable": 0,
        "replay_validation_failed": 0,
        "ingest_failed": 0,
    }
    _MetricsState.kb_quarantine_total = {
        "runtime": 0,
        "benchmark": 0,
        "learning": 0,
        "dataset": 0,
        "model": 0,
        "promotion": 0,
        "rollback": 0,
    }
    _MetricsState.kb_learning_failures_total = {
        "decision_log_pressure": 0,
        "dataset_assembly": 0,
        "training": 0,
        "evaluation": 0,
        "promotion": 0,
        "rollback": 0,
        "ingest": 0,
    }
    _MetricsState.kb_replay_failures_total = 0
    _MetricsState.kb_contract_requests_total = {
        (version, outcome): 0
        for version in ("1.0.0", "unsupported")
        for outcome in ("accepted", "conflict", "error", "limit", "replayed")
    }


def test_metrics_endpoint_exposes_prometheus_payload():
    port = _free_port()
    _MetricsState.requests_total = 3
    _MetricsState.request_duration_seconds_sum = 0.75
    _MetricsState.submit_job_outcomes_total = {
        "accepted": 2,
        "replayed": 1,
        "conflict": 1,
        "limit": 1,
    }
    _MetricsState.public_api_contract_requests_total = {
        ("1.0.0", "accepted"): 2,
        ("1.0.0", "replayed"): 1,
        ("1.0.0", "conflict"): 1,
        ("1.0.0", "limit"): 1,
        ("1.0.0", "error"): 0,
        ("unsupported", "accepted"): 0,
        ("unsupported", "replayed"): 0,
        ("unsupported", "conflict"): 0,
        ("unsupported", "limit"): 0,
        ("unsupported", "error"): 0,
    }
    _reset_kb_metrics()
    record_kb_query("records", hit=True)
    record_kb_query("decision_logs", hit=False)
    record_kb_fallback("storage_unavailable")
    record_kb_quarantine_event("learning")
    record_kb_learning_failure("dataset_assembly")
    record_kb_replay_failure()
    record_kb_contract_marker("1.0.0", "accepted")
    server = start_metrics_server(port)
    try:
        body = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=2).read().decode()
    finally:
        server.shutdown()
        server.server_close()

    assert "eigen_api_requests_total 3" in body
    assert "eigen_api_request_duration_seconds 0.750000" in body
    assert 'eigen_api_submit_job_outcomes_total{outcome="accepted"} 2' in body
    assert 'eigen_api_submit_job_outcomes_total{outcome="replayed"} 1' in body
    assert 'eigen_api_submit_job_outcomes_total{outcome="conflict"} 1' in body
    assert 'eigen_api_submit_job_outcomes_total{outcome="limit"} 1' in body
    assert 'eigen_api_public_contract_requests_total{contract_version="1.0.0",outcome="accepted"} 2' in body
    assert 'eigen_public_api_contract_requests_total{contract_version="1.0.0",outcome="accepted"} 2' in body
    assert 'eigen_kb_contract_info{version="1.0.0"} 1' in body
    assert 'eigen_kb_queries_total{kind="records"} 1' in body
    assert 'eigen_kb_misses_total{kind="decision_logs"} 1' in body
    assert 'eigen_kb_fallbacks_total{reason="storage_unavailable"} 1' in body
    assert 'eigen_kb_quarantine_total{surface="learning"} 1' in body
    assert 'eigen_kb_learning_failures_total{reason="dataset_assembly"} 1' in body
    assert 'eigen_kb_replay_failures_total 1' in body
    assert 'eigen_kb_contract_requests_total{contract_version="1.0.0",outcome="accepted"} 1' in body


def test_public_contract_marker_uses_bounded_labels_and_contract_version():
    _reset_public_contract_metrics()

    record_public_api_contract_marker("1.0.0", "accepted")
    record_public_api_contract_marker("9.9.9-custom-build", "tenant-freeform-outcome")

    assert _MetricsState.public_api_contract_requests_total[("1.0.0", "accepted")] == 1
    assert _MetricsState.public_api_contract_requests_total[("unsupported", "error")] == 1
    assert {version for version, _ in _MetricsState.public_api_contract_requests_total} == {
        "1.0.0",
        "unsupported",
    }
    assert {outcome for _, outcome in _MetricsState.public_api_contract_requests_total} == {
        "accepted",
        "conflict",
        "error",
        "limit",
        "replayed",
    }


def test_submit_job_marker_and_traceparent_correlation_from_public_envelope(caplog):
    class _Context:
        def invocation_metadata(self):
            return []

        def abort(self, code, details):
            raise RuntimeError(f"{code}: {details}")

    _reset_public_contract_metrics()
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    request = job_pb.SubmitJobRequest(
        name="observability-smoke",
        target="sim:local",
        envelope=types_pb.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id="req-observability-smoke",
            traceparent=traceparent,
        ),
        eigen_lang=types_pb.EigenLangSource(source=b"fn main() {}\n", entrypoint="main"),
    )

    caplog.set_level("INFO", logger="system_api")
    response = JobService(job_pb=job_pb, types_pb=types_pb).SubmitJob(request, _Context())

    assert response.job_id
    assert _MetricsState.public_api_contract_requests_total[("1.0.0", "accepted")] == 1
    assert any(
        record.message == "rpc_start"
        and record.request_id == "req-observability-smoke"
        and record.traceparent == traceparent
        and record.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
        for record in caplog.records
    )
