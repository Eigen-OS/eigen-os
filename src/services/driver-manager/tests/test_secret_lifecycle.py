from __future__ import annotations

import pytest

from driver_manager.secret_lifecycle import SecretLifecycleStore


def test_secret_lifecycle_issued_and_rotated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DRIVER_MANAGER_SECRETS_JSON",
        '{"a":{"value":"x","state":"issued"},"b":{"value":"y","state":"rotated"}}',
    )
    store = SecretLifecycleStore()
    assert store.get("a", actor="runtime", workload_id="job-1", consumer="qiskit") == "x"
    assert store.get("b", actor="runtime", workload_id="job-1", consumer="aws") == "y"


def test_secret_lifecycle_revoked_or_expired_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DRIVER_MANAGER_SECRETS_JSON",
        '{"rev":{"value":"x","state":"revoked"},"exp":{"value":"x","state":"issued","expires_at":"2000-01-01T00:00:00Z"}}',
    )
    store = SecretLifecycleStore()
    with pytest.raises(ValueError, match="revoked secret"):
        store.get("rev", actor="runtime", workload_id="job-1", consumer="aws")
    with pytest.raises(ValueError, match="expired secret"):
        store.get("exp", actor="runtime", workload_id="job-1", consumer="aws")
