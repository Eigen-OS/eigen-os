from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from typing import Any

RECOMMENDATION_CONTRACT_VERSION = "1.0.0"
PATTERN_MINER_CADENCE_SECONDS = 300


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class SnapshotIngestResult:
    snapshot_id: str
    config_digest: str
    idempotency_key: str
    created: bool


class PatternMinerService:
    """Deterministic in-memory Pattern Miner with idempotent snapshot ingest."""

    def __init__(self) -> None:
        self._snapshots: dict[str, dict[str, Any]] = {}

    def ingest_snapshot(self, *, snapshot_id: str, records: list[dict[str, Any]], config_digest: str) -> SnapshotIngestResult:
        normalized_records = sorted(records, key=lambda row: _canonical_json(row))
        idempotency_key = sha256(_canonical_json({
            "snapshot_id": snapshot_id,
            "config_digest": config_digest,
            "records": normalized_records,
        }).encode("utf-8")).hexdigest()
        existing = self._snapshots.get(snapshot_id)
        if existing is None:
            self._snapshots[snapshot_id] = {
                "config_digest": config_digest,
                "records": normalized_records,
                "idempotency_key": idempotency_key,
            }
            return SnapshotIngestResult(snapshot_id, config_digest, idempotency_key, True)
        if existing["idempotency_key"] != idempotency_key:
            raise ValueError("snapshot_id already ingested with different payload")
        return SnapshotIngestResult(snapshot_id, config_digest, idempotency_key, False)

    def mine_patterns(self, *, snapshot_id: str) -> dict[str, Any]:
        snapshot = self._snapshots[snapshot_id]
        records = snapshot["records"]
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for record in records:
            key = (str(record.get("circuit_id", "")), str(record.get("backend_class", "")))
            grouped.setdefault(key, []).append(record)

        patterns = []
        for (circuit_id, backend_class), members in sorted(grouped.items()):
            member_ids = sorted(str(m["record_id"]) for m in members)
            pattern_id = sha256(f"{snapshot_id}:{circuit_id}:{backend_class}".encode("utf-8")).hexdigest()[:16]
            patterns.append(
                {
                    "pattern_id": pattern_id,
                    "circuit_id": circuit_id,
                    "backend_class": backend_class,
                    "source_record_ids": member_ids,
                    "support": len(member_ids),
                }
            )

        return {
            "snapshot_id": snapshot_id,
            "config_digest": snapshot["config_digest"],
            "cadence_seconds": PATTERN_MINER_CADENCE_SECONDS,
            "patterns": patterns,
        }

    def get_recommendation(self, *, snapshot_id: str, circuit_id: str, backend_class: str, min_confidence: float = 0.0) -> dict[str, Any]:
        mined = self.mine_patterns(snapshot_id=snapshot_id)
        matching = [
            p
            for p in mined["patterns"]
            if p["circuit_id"] == circuit_id and p["backend_class"] == backend_class
        ]
        confidence = float(matching[0]["support"]) / float(max(1, len(mined["patterns"]))) if matching else 0.0
        fallback_used = confidence < min_confidence or not matching
        now = datetime.now(UTC)
        return {
            "contract": "pattern_miner.recommendation",
            "version": RECOMMENDATION_CONTRACT_VERSION,
            "snapshot_id": snapshot_id,
            "config_digest": mined["config_digest"],
            "cadence_seconds": mined["cadence_seconds"],
            "query": {"circuit_id": circuit_id, "backend_class": backend_class},
            "recommendation": {
                "selected_pattern_id": matching[0]["pattern_id"] if matching else None,
                "confidence": round(confidence, 6),
                "fallback_used": fallback_used,
                "fallback_reason": "BELOW_CONFIDENCE_THRESHOLD" if fallback_used else None,
            },
            "provenance": {
                "source_record_ids": matching[0]["source_record_ids"] if matching else [],
                "queryable_links": [f"kb://records/{rid}" for rid in (matching[0]["source_record_ids"] if matching else [])],
            },
            "timing": {
                "generated_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=PATTERN_MINER_CADENCE_SECONDS)).isoformat(),
            },
        }
