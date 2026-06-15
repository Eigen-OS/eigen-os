"""Versioned Knowledge Base wrapper for append-only record storage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .errors import abort_with_error_info
from .knowledge_base import (
    KnowledgeBaseService as _BaseKnowledgeBaseService,
    KnowledgeBaseUnavailable,
    _StoredRecord,
    _anonymize_mapping,
    _stable_hash,
    _stable_json,
    _ts_to_dt,
)


@dataclass(slots=True)
class _RevisionEntry:
    revision_id: str
    record_id: str
    revision_kind: str
    ingest_kind: str
    fingerprint: str
    source: str
    replay_bundle_ref: str
    tenant_id: str
    project_id: str
    created_at: str
    updated_at: str
    sequence: int
    active: bool


class KnowledgeBaseService(_BaseKnowledgeBaseService):
    """Append-only revisioned KB service layered over the existing deterministic KB."""

    def __init__(self, kb_pb, types_pb, *, storage_mode: str | None = None, retention_seconds: int | None = None) -> None:
        super().__init__(kb_pb, types_pb, storage_mode=storage_mode, retention_seconds=retention_seconds)
        self._record_history: dict[str, list[_RevisionEntry]] = {}
        self._record_last_ingest_kind: dict[str, str] = {}
        self._record_last_ingest_at: dict[str, str] = {}

    def describe_record_history(self, record_id: str) -> dict[str, Any]:
        history = list(self._record_history.get(record_id, []))
        active = history[-1] if history else None
        return {
            "record_id": record_id,
            "revision_count": len(history),
            "active_revision_id": active.revision_id if active else "",
            "active_version_label": self._active_version_label(active.sequence) if active else "",
            "last_ingest_kind": self._record_last_ingest_kind.get(record_id, ""),
            "last_ingest_at": self._record_last_ingest_at.get(record_id, ""),
            "history": [self._revision_as_dict(item) for item in history],
        }

    def QueryRecords(self, request, context: grpc.ServicerContext):  # noqa: N802
        self._require_read(context, operation="query_records")
        envelope = self._normalize_envelope(request.envelope, context)
        page_size = self._page_size(request.page_size)
        with self._lock:
            self._gc_locked()
            filtered = [
                self._clone_record(entry.record)
                for entry in self._records.values()
                if self._record_visible_to_tenant(entry, envelope["tenant_id"], envelope["project_id"], context)
                and self._record_matches_filter(entry.record, request.filter)
            ]
            filtered.sort(key=lambda item: (self._ts_signature(item.created_at), item.record_id))
            offset, query_sig = self._decode_cursor(request.page_token, envelope, self._filter_signature(request.filter), kind="records", context=context)
            next_offset = offset + page_size
            window = filtered[offset:next_offset]
            next_token = self._encode_cursor(envelope=envelope, filter_payload=self._filter_signature(request.filter), kind="records", offset=next_offset, query_sig=query_sig, more=next_offset < len(filtered))
        return self._kb_pb.QueryRecordsResponse(records=window, next_page_token=next_token)

    def _record_fingerprint(self, record: Any, *, replay_bundle_ref: str, source: str = "") -> str:
        payload = {
            "record_id": getattr(record, "record_id", ""),
            "job_id": getattr(record, "job_id", ""),
            "circuit_id": getattr(record, "circuit_id", ""),
            "artifact_ref": getattr(record, "artifact_ref", ""),
            "dataset_ref": getattr(record, "dataset_ref", ""),
            "backend_profile": getattr(record, "backend_profile", ""),
            "optimizer_version": getattr(record, "optimizer_version", ""),
            "qubit_count": int(getattr(record, "qubit_count", 0) or 0),
            "entanglement_score": float(getattr(record, "entanglement_score", 0.0) or 0.0),
            "noise_profile_id": getattr(record, "noise_profile_id", ""),
            "backend_class": getattr(record, "backend_class", ""),
            "provenance": {
                "compiler_ref": getattr(getattr(record, "provenance", None), "compiler_ref", ""),
                "optimizer_ref": getattr(getattr(record, "provenance", None), "optimizer_ref", ""),
                "runtime_ref": getattr(getattr(record, "provenance", None), "runtime_ref", ""),
                "checkpoint_ref": getattr(getattr(record, "provenance", None), "checkpoint_ref", ""),
            },
            "lineage": {
                "model_version": getattr(getattr(record, "lineage", None), "model_version", ""),
                "training_set_hash": getattr(getattr(record, "lineage", None), "training_set_hash", ""),
                "evaluation_bundle_hash": getattr(getattr(record, "lineage", None), "evaluation_bundle_hash", ""),
                "promotion_policy_version": getattr(getattr(record, "lineage", None), "promotion_policy_version", ""),
                "promotion_outcome": getattr(getattr(record, "lineage", None), "promotion_outcome", ""),
            },
            "attributes": {k: str(v) for k, v in sorted(dict(getattr(record, "attributes", {})).items())},
            "replay_bundle_ref": replay_bundle_ref,
            "source": source,
        }
        return _stable_hash(payload)

    def _upsert_record(
        self,
        record: Any,
        envelope: dict[str, Any],
        allow_overwrite: bool,
        anonymize_attributes: bool,
        source: str,
        replay_bundle_ref: str,
        context: grpc.ServicerContext | None,
        capability_scope: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        record_id = str(record.record_id)
        now = datetime.now(timezone.utc)
        existing = self._records.get(record_id)
        incoming_created_at = _ts_to_dt(getattr(record, "created_at", None)) if getattr(record, "created_at", None) else now
        fingerprint = self._record_fingerprint(record, replay_bundle_ref=replay_bundle_ref, source=source)

        if existing and existing.fingerprint == fingerprint:
            self._record_last_ingest_kind[record_id] = "idempotent_replay"
            self._record_last_ingest_at[record_id] = now.isoformat()
            ts = Timestamp()
            ts.FromDatetime(existing.updated_at)
            return {"record_id": record_id, "created": False, "updated_at": ts}

        if existing and not allow_overwrite:
            if context:
                abort_with_error_info(
                    context,
                    grpc_code=grpc.StatusCode.ALREADY_EXISTS,
                    message=f"Record {record_id} already exists",
                    reason="KB_RECORD_ALREADY_EXISTS",
                    domain="eigen.api.v1",
                )
                return {}
            raise ValueError(f"Record {record_id} already exists and overwrite is disabled.")

        record_created_at = existing.created_at if existing else incoming_created_at
        record.created_at.FromDatetime(record_created_at)

        attrs = dict(record.attributes)
        if anonymize_attributes:
            attrs = _anonymize_mapping(attrs, salt=self._anon_salt, epoch=self._anon_epoch)
        attrs["request_hash"] = fingerprint
        attrs["replay_bundle_ref"] = replay_bundle_ref
        record.attributes.clear()
        record.attributes.update({k: str(v) for k, v in attrs.items()})

        self._sequence += 1
        revision_sequence = self._sequence
        revision_kind = "create" if existing is None else "new_revision"
        ingest_kind = "create" if existing is None else "overwrite_authorized"
        revision_id = self._revision_id(record_id=record_id, fingerprint=fingerprint, sequence=revision_sequence, source=source, replay_bundle_ref=replay_bundle_ref)
        revision = _RevisionEntry(
            revision_id=revision_id,
            record_id=record_id,
            revision_kind=revision_kind,
            ingest_kind=ingest_kind,
            fingerprint=fingerprint,
            source=source,
            replay_bundle_ref=replay_bundle_ref,
            tenant_id=envelope["tenant_id"],
            project_id=envelope["project_id"],
            created_at=incoming_created_at.isoformat(),
            updated_at=now.isoformat(),
            sequence=revision_sequence,
            active=True,
        )

        history = self._record_history.get(record_id, [])
        for item in history:
            item.active = False
        history.append(revision)
        self._record_history[record_id] = history
        self._record_last_ingest_kind[record_id] = ingest_kind
        self._record_last_ingest_at[record_id] = now.isoformat()

        stored = _StoredRecord(
            record=self._clone_record(record),
            tenant_id=envelope["tenant_id"],
            project_id=envelope["project_id"],
            capability_scope=tuple(capability_scope or ()),
            created_at=record_created_at,
            updated_at=now,
            fingerprint=fingerprint,
            sequence=revision_sequence,
        )
        self._records[record_id] = stored

        ts = Timestamp()
        ts.FromDatetime(now)
        return {"record_id": record_id, "created": existing is None, "updated_at": ts}

    def _clone_record(self, record: Any):
        clone = super()._clone_record(record)
        history = self._record_history.get(clone.record_id, [])
        if history:
            self._decorate_record(
                clone,
                history[-1],
                len(history),
                self._record_last_ingest_kind.get(clone.record_id, history[-1].ingest_kind),
                self._record_last_ingest_at.get(clone.record_id, history[-1].updated_at),
            )
        return clone

    def _gc_locked(self) -> None:
        super()._gc_locked()
        valid_ids = set(self._records.keys())
        self._record_history = {record_id: history for record_id, history in self._record_history.items() if record_id in valid_ids}
        self._record_last_ingest_kind = {record_id: kind for record_id, kind in self._record_last_ingest_kind.items() if record_id in valid_ids}
        self._record_last_ingest_at = {record_id: when for record_id, when in self._record_last_ingest_at.items() if record_id in valid_ids}

    def _revision_id(self, *, record_id: str, fingerprint: str, sequence: int, source: str, replay_bundle_ref: str) -> str:
        payload = {
            "record_id": record_id,
            "fingerprint": fingerprint,
            "sequence": sequence,
            "source": source,
            "replay_bundle_ref": replay_bundle_ref,
        }
        return f"rev_{hashlib.sha256(_stable_json(payload).encode('utf-8')).hexdigest()[:24]}"

    def _active_version_label(self, sequence: int) -> str:
        return f"v{sequence:08d}"

    def _decorate_record(self, record: Any, active: _RevisionEntry, revision_count: int, last_ingest_kind: str, last_ingest_at: str) -> None:
        attrs = dict(getattr(record, "attributes", {}))
        attrs.update(
            {
                "kb_revision_id": active.revision_id,
                "kb_active_revision_id": active.revision_id,
                "kb_revision_kind": active.revision_kind,
                "kb_last_ingest_kind": last_ingest_kind,
                "kb_revision_state": "active",
                "kb_revision_count": str(revision_count),
                "kb_revision_sequence": str(active.sequence),
                "kb_active_version_label": self._active_version_label(active.sequence),
                "kb_revision_history_ref": f"kb://records/{active.record_id}/revisions",
                "kb_revision_fingerprint": active.fingerprint,
                "kb_revision_source": active.source,
                "kb_revision_replay_bundle_ref": active.replay_bundle_ref,
                "kb_revision_last_ingest_at": last_ingest_at,
            }
        )
        record.attributes.clear()
        record.attributes.update({k: str(v) for k, v in attrs.items()})

    def _revision_as_dict(self, item: _RevisionEntry) -> dict[str, Any]:
        return {
            "revision_id": item.revision_id,
            "record_id": item.record_id,
            "revision_kind": item.revision_kind,
            "ingest_kind": item.ingest_kind,
            "fingerprint": item.fingerprint,
            "source": item.source,
            "replay_bundle_ref": item.replay_bundle_ref,
            "tenant_id": item.tenant_id,
            "project_id": item.project_id,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "sequence": item.sequence,
            "active": item.active,
        }
