"""Secret lifecycle state, retrieval, and audit event wiring for driver-manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import threading
from typing import Any


_AUDIT_LOG = logging.getLogger("driver_manager.secret_audit")


@dataclass(frozen=True)
class SecretRecord:
    value: Any
    state: str
    issued_at: datetime
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None


class SecretLifecycleStore:
    """In-memory lifecycle view over DRIVER_MANAGER_SECRETS_JSON with audit traces."""

    _ACTIVE_STATES = {"issued", "rotated"}

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, SecretRecord] = {}
        self._load_from_env()

    def _load_from_env(self) -> None:
        raw = os.getenv("DRIVER_MANAGER_SECRETS_JSON", "{}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("DRIVER_MANAGER_SECRETS_JSON must be valid JSON object") from exc
        if not isinstance(data, dict):
            raise ValueError("DRIVER_MANAGER_SECRETS_JSON must be valid JSON object")

        now = _utcnow()
        with self._lock:
            self._records = {}
            for ref, payload in data.items():
                rec = self._normalize_record(payload=payload, now=now)
                self._records[str(ref)] = rec

    def _normalize_record(self, payload: Any, now: datetime) -> SecretRecord:
        if isinstance(payload, dict) and "value" in payload:
            state = str(payload.get("state", "issued")).strip().lower() or "issued"
            expires_at = _parse_dt(payload.get("expires_at"))
            return SecretRecord(
                value=payload.get("value"),
                state=state,
                issued_at=_parse_dt(payload.get("issued_at")) or now,
                rotated_at=_parse_dt(payload.get("rotated_at")),
                revoked_at=_parse_dt(payload.get("revoked_at")),
                expires_at=expires_at,
            )
        return SecretRecord(value=payload, state="issued", issued_at=now)

    def get(self, secret_ref: str, *, actor: str, workload_id: str, consumer: str) -> Any:
        now = _utcnow()
        with self._lock:
            record = self._records.get(secret_ref)

        if record is None:
            self._emit("lookup_denied", secret_ref, actor, workload_id, consumer, "not_found")
            raise ValueError("missing secret")

        if record.expires_at and now >= record.expires_at:
            self._emit("expire", secret_ref, actor, workload_id, consumer, "expired")
            raise ValueError("expired secret")

        if record.state == "revoked":
            self._emit("revoke", secret_ref, actor, workload_id, consumer, "revoked")
            raise ValueError("revoked secret")

        if record.state not in self._ACTIVE_STATES:
            self._emit("lookup_denied", secret_ref, actor, workload_id, consumer, f"invalid_state:{record.state}")
            raise ValueError("inactive secret")

        action = "issue" if record.state == "issued" else "rotate"
        self._emit(action, secret_ref, actor, workload_id, consumer, "ok")
        return record.value

    def _emit(self, event: str, secret_ref: str, actor: str, workload_id: str, consumer: str, outcome: str) -> None:
        secret_ref_digest = hashlib.sha256(secret_ref.encode("utf-8")).hexdigest()[:16]
        _AUDIT_LOG.info(
            "secret_lifecycle_event",
            extra={
                "event": event,
                "secret_ref_digest": secret_ref_digest,
                "secret_ref_redacted": "<redacted>",
                "actor": actor,
                "workload_id": workload_id,
                "consumer": consumer,
                "outcome": outcome,
                "ts": _utcnow().isoformat(),
            },
        )


def _parse_dt(raw: Any) -> datetime | None:
    if raw in (None, ""):
        return None
    val = str(raw)
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"
    return datetime.fromisoformat(val).astimezone(timezone.utc)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
