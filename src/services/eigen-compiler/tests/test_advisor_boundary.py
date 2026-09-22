from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from eigen_compiler import advisor_boundary  # noqa: E402


@pytest.mark.parametrize("outcome", ["accepted", "rejected", "transformed"])
def test_suggestion_outcomes_are_exported(outcome: str) -> None:
    advisor_boundary.record_suggestion_outcome(outcome)
    metrics = advisor_boundary.render_metrics_text()
    assert f'eigen_compiler_suggestion_outcomes_total{{outcome="{outcome}"}} 1' in metrics


def test_advisor_boundary_records_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[str] = []

    class _FakeResponse:
        request_id = "req-1"
        tenant_id = "tenant-1"
        project_id = "project-1"
        policy_snapshot_version = "1.0.0"
        model_version = "dpda-model-v1"
        decision = 1

    def fake_record_suggestion_outcome(outcome: str) -> None:
        recorded.append(outcome)

    monkeypatch.setattr(advisor_boundary, "record_suggestion_outcome", fake_record_suggestion_outcome)
    monkeypatch.setattr(
        advisor_boundary._BaseNeuroSymbolicService,
        "ScoreCompilationPlan",
        lambda self, request, context: _FakeResponse(),
    )

    response = advisor_boundary.NeuroSymbolicService(nsc_pb=object()).ScoreCompilationPlan(object(), object())

    assert response.decision == 1
    assert recorded == ["accepted"]
