from __future__ import annotations

import socket
import urllib.request

from system_api.observability import _MetricsState, start_metrics_server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


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
