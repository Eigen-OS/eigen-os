from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from neuro_symbolic_service import main as entrypoint  # noqa: E402
from neuro_symbolic_service.observability import (  # noqa: E402
    record_suggestion_outcome,
    render_metrics_text,
)


class _FakeServer:
    def __init__(self) -> None:
        self.waited = False
        self.stopped = False
        self.grace = None

    def wait_for_termination(self) -> None:
        self.waited = True

    def stop(self, grace: int = 0) -> None:
        self.stopped = True
        self.grace = grace


@pytest.mark.parametrize("outcome", ["accepted", "rejected", "transformed"])
def test_suggestion_outcomes_are_exported(outcome: str) -> None:
    record_suggestion_outcome(outcome)
    metrics = render_metrics_text()
    assert f'eigen_neuro_suggestion_outcomes_total{{outcome="{outcome}"}} 1' in metrics


def test_main_starts_grpc_server(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_server = _FakeServer()
    metrics_ports: list[int] = []

    monkeypatch.setattr(entrypoint, "start_metrics_server", lambda port: metrics_ports.append(port))
    monkeypatch.setattr(entrypoint, "serve", lambda: fake_server)

    exit_code = entrypoint.main([])

    assert exit_code == 0
    assert metrics_ports == [50082]
    assert fake_server.waited is True
    assert fake_server.stopped is False
