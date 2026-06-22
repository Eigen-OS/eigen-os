from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from typing import Any

RECOMMENDATION_CONTRACT_VERSION = "1.0.0"
PATTERN_CONTRACT_VERSION = "1.0.0"
PATTERN_MINER_CADENCE_SECONDS = 300
PATTERN_MINER_MAX_CANDIDATES = 8

_PATTERN_QUERY_MODES = {"structural", "vector", "hybrid"}
_PATTERN_COMPATIBILITY_FIELDS = (
    "schema_version",
    "compiler_version",
    "aqo_version",
    "optimizer_version",
    "policy_mode",
    "policy_digest",
)
_PATTERN_INCOMPATIBILITY_REASON_MAP = {
    "schema_version": "SCHEMA_MISMATCH",
    "compiler_version": "COMPILER_MISMATCH",
    "aqo_version": "AQO_MISMATCH",
    "optimizer_version": "OPTIMIZER_MISMATCH",
    "policy_mode": "POLICY_MISMATCH",
    "policy_digest": "POLICY_MISMATCH",
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalized_text(value: Any) -> str:
    return str(value).strip()


def _clamp_budget(value: Any) -> int:
    try:
        requested = int(value)
    except Exception:
        requested = 1
    return max(1, min(requested, PATTERN_MINER_MAX_CANDIDATES))


def _sha256_hex(payload: Any) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _pattern_source_provenance(
    *,
    snapshot_id: str,
    config_digest: str,
    source_record_ids: list[str],
) -> dict[str, Any]:
    return {
        "kind": "knowledge_base_snapshot",
        "snapshot_id": snapshot_id,
        "config_digest": config_digest,
        "source_record_ids": source_record_ids,
        "source_record_count": len(source_record_ids),
    }


def _pattern_version_provenance(
    *,
    compatibility_signature: str,
) -> dict[str, Any]:
    return {
        "contract_version": PATTERN_CONTRACT_VERSION,
        "pattern_miner_version": PATTERN_CONTRACT_VERSION,
        "compatibility_signature": compatibility_signature,
    }


def _pattern_compilation_context(
    *,
    snapshot_id: str,
    circuit_id: str,
    backend_class: str,
    compatibility_window: dict[str, str],
    query_signature: str = "",
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    query_payload = query or {}
    return {
        "snapshot_id": snapshot_id,
        "circuit_id": circuit_id,
        "backend_class": backend_class,
        "compatibility_window": compatibility_window,
        "query_signature": query_signature,
        "query_mode": _normalized_text(query_payload.get("query_mode", "")) or "structural",
       "candidate_budget": int(query_payload.get("candidate_budget", PATTERN_MINER_MAX_CANDIDATES) or PATTERN_MINER_MAX_CANDIDATES),
        "deterministic": bool(query_payload.get("deterministic", True)),
        "semantic_hash": _normalized_text(query_payload.get("semantic_hash", "")),
        "aqo_hash": _normalized_text(query_payload.get("aqo_hash", "")),
        "schema_version": _normalized_text(query_payload.get("schema_version", "")),
        "compiler_version": _normalized_text(query_payload.get("compiler_version", "")),
        "aqo_version": _normalized_text(query_payload.get("aqo_version", "")),
        "optimizer_version": _normalized_text(query_payload.get("optimizer_version", "")),
        "policy_mode": _normalized_text(query_payload.get("policy_mode", "")) or "deterministic",
        "policy_digest": _normalized_text(query_payload.get("policy_digest", "")),
    }


def _pattern_validation_status(
    *,
    state: str,
    compatible: bool,
    canonical_eligible: bool,
    selected: bool,
    rank: int,
    incompatibility_reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "state": state,
        "compatible": compatible,
        "canonical_eligible": canonical_eligible,
        "selected": selected,
        "rank": rank,
        "incompatibility_reasons": list(incompatibility_reasons),
    }


def _pattern_provenance(
    *,
    snapshot_id: str,
    config_digest: str,
    source_record_ids: list[str],
    compatibility_signature: str,
    snapshot_state: str,
    circuit_id: str,
    backend_class: str,
    compatibility_window: dict[str, str],
    query_signature: str = "",
    query: dict[str, Any] | None = None,
    validation_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": _pattern_source_provenance(
            snapshot_id=snapshot_id,
            config_digest=config_digest,
            source_record_ids=source_record_ids,
        ),
        "version": _pattern_version_provenance(compatibility_signature=compatibility_signature),
        "compilation_context": _pattern_compilation_context(
            snapshot_id=snapshot_id,
            circuit_id=circuit_id,
            backend_class=backend_class,
            compatibility_window=compatibility_window,
            query_signature=query_signature,
            query=query,
        ),
        "validation_status": _pattern_validation_status(
            state=snapshot_state,
            compatible=True if validation_status is None else bool(validation_status.get("compatible", True)),
            canonical_eligible=True if validation_status is None else bool(validation_status.get("canonical_eligible", True)),
            selected=False if validation_status is None else bool(validation_status.get("selected", False)),
            rank=0 if validation_status is None else int(validation_status.get("rank", 0) or 0),
            incompatibility_reasons=() if validation_status is None else tuple(validation_status.get("incompatibility_reasons", []) or []),
        ),
    }


def _digest_to_unit_interval(digest: str, *, start: int = 0, end: int = 16) -> float:
    raw = int(digest[start:end], 16)
    return raw / float(0xFFFFFFFFFFFFFFFF)


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

    def ingest_snapshot(
        self,
        *,
        snapshot_id: str,
        records: list[dict[str, Any]],
        config_digest: str,
        tenant_id: str = "",
        project_id: str = "",
    ) -> SnapshotIngestResult:
        normalized_tenant_id, normalized_project_id, normalized_records = self._normalize_snapshot_records(
            records,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        idempotency_key = sha256(
            _canonical_json(
                {
                    "snapshot_id": snapshot_id,
                    "config_digest": config_digest,
                    "tenant_id": normalized_tenant_id,
                    "project_id": normalized_project_id,
                    "records": normalized_records,
                }
            ).encode("utf-8")
        ).hexdigest()
        existing = self._snapshots.get(snapshot_id)
        snapshot_payload = {
            "config_digest": config_digest,
            "tenant_id": normalized_tenant_id,
            "project_id": normalized_project_id,
            "records": normalized_records,
            "idempotency_key": idempotency_key,
        }
        if existing is None:
            self._snapshots[snapshot_id] = snapshot_payload
            return SnapshotIngestResult(snapshot_id, config_digest, idempotency_key, True)
        if existing["idempotency_key"] != idempotency_key:
            raise ValueError("snapshot_id already ingested with different payload")
        return SnapshotIngestResult(snapshot_id, config_digest, idempotency_key, False)

    def mine_patterns(self, *, snapshot_id: str, tenant_id: str, project_id: str) -> dict[str, Any]:
        snapshot = self._snapshots[snapshot_id]
        patterns = self._pattern_catalog(snapshot_id=snapshot_id)
        return {
            "snapshot_id": snapshot_id,
            "config_digest": snapshot["config_digest"],
            "cadence_seconds": PATTERN_MINER_CADENCE_SECONDS,
            "patterns": patterns,
        }

    def get_pattern(
        self,
        *,
        snapshot_id: str,
        tenant_id: str,
        project_id: str,
        circuit_id: str,
        backend_class: str,
        semantic_hash: str,
        aqo_hash: str,
        schema_version: str,
        compiler_version: str,
        aqo_version: str,
        optimizer_version: str,
        policy_mode: str = "deterministic",
        policy_digest: str = "",
        seed: int = 0,
        query_mode: str = "structural",
        candidate_budget: int = PATTERN_MINER_MAX_CANDIDATES,
        deterministic: bool = True,
    ) -> dict[str, Any]:
        snapshot = self._snapshots[snapshot_id]
        self._require_snapshot_scope(snapshot, tenant_id=tenant_id, project_id=project_id)
        query = self._normalize_pattern_query(
            {
                "snapshot_id": snapshot_id,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "circuit_id": circuit_id,
                "backend_class": backend_class,
                "semantic_hash": semantic_hash,
                "aqo_hash": aqo_hash,
                "schema_version": schema_version,
                "compiler_version": compiler_version,
                "aqo_version": aqo_version,
                "optimizer_version": optimizer_version,
                "policy_mode": policy_mode,
                "policy_digest": policy_digest,
                "seed": seed,
                "query_mode": query_mode,
                "candidate_budget": candidate_budget,
                "deterministic": deterministic,
            }
        )
        catalog = self._pattern_catalog(snapshot_id=snapshot_id)
        scoped = [pattern for pattern in catalog if pattern["circuit_id"] == query["circuit_id"] and pattern["backend_class"] == query["backend_class"]]
        query_window = self._query_compatibility_window(query)
        query_signature = _sha256_hex(query_window)
        max_support = max((pattern["support"] for pattern in scoped), default=1)

        scored_candidates = [
            self._decorate_pattern_candidate(
                pattern=pattern,
                query=query,
                query_signature=query_signature,
                max_support=max_support,
            )
            for pattern in scoped
        ]

        compatible_candidates = [item for item in scored_candidates if item["compatible"]]
        canonical_candidate = self._choose_canonical_pattern(compatible_candidates)
        canonical_pattern_id = canonical_candidate["pattern_id"] if canonical_candidate else ""

        ordered_candidates = self._order_pattern_candidates(
            scored_candidates,
            canonical_pattern_id=canonical_pattern_id,
        )
        selected_candidates = ordered_candidates[: query["candidate_budget"]]
        if canonical_candidate and canonical_pattern_id not in {item["pattern_id"] for item in selected_candidates}:
            selected_candidates = [canonical_candidate] + selected_candidates[: query["candidate_budget"] - 1]

        selected_candidates = selected_candidates[: query["candidate_budget"]]
        for rank, candidate in enumerate(selected_candidates, start=1):
            candidate["rank"] = rank
            candidate["selected"] = candidate["pattern_id"] == canonical_pattern_id if canonical_candidate else False
            validation_status = dict(candidate["provenance"]["validation_status"])
            validation_status["selected"] = candidate["selected"]
            validation_status["rank"] = rank
            validation_status["state"] = "selected" if candidate["selected"] else validation_status["state"]
            candidate["provenance"] = {**candidate["provenance"], "validation_status": validation_status}

        canonical_pattern = None
        if canonical_candidate is not None:
            canonical_pattern = dict(canonical_candidate)
            canonical_pattern["pattern_kind"] = "canonical"
            canonical_pattern["selected"] = True
            canonical_pattern["canonical_template_ref"] = f"kb://patterns/{canonical_pattern['pattern_id']}"
            canonical_pattern["explanation_ref"] = f"kb://patterns/{canonical_pattern['pattern_id']}/explanation"
            canonical_pattern["rank"] = 1
            canonical_validation_status = dict(canonical_pattern["provenance"]["validation_status"])
            canonical_validation_status["state"] = "canonical"
            canonical_validation_status["selected"] = True
            canonical_validation_status["rank"] = 1
            canonical_pattern["provenance"] = {**canonical_pattern["provenance"], "validation_status": canonical_validation_status}

        incompatible_reasons = self._collect_incompatibility_reasons(scored_candidates)
        fallback_used = canonical_pattern is None
        diagnostics = {
            "fallback_used": fallback_used,
            "fallback_reason": "NO_CANONICAL_PATTERN" if fallback_used else None,
            "compatibility_signature": query_signature,
            "canonical_selection_rule": [
                "exact compatibility window",
                "support desc",
                "pattern_family asc",
                "pattern_id asc",
            ],
            "compatible_candidate_count": len(compatible_candidates),
            "incompatible_candidate_count": len(scored_candidates) - len(compatible_candidates),
            "incompatibility_reason_codes": incompatible_reasons,
        }

        explanation_pattern = {
            "explanation_id": _sha256_hex(
                {
                    "snapshot_id": snapshot_id,
                    "query_signature": query_signature,
                    "canonical_pattern_id": canonical_pattern_id,
                    "candidate_pattern_ids": [item["pattern_id"] for item in selected_candidates],
                    "reason_codes": incompatible_reasons,
                }
            ),
            "pattern_kind": "explanation",
            "snapshot_id": snapshot_id,
            "query_signature": query_signature,
            "canonical_pattern_id": canonical_pattern_id,
            "candidate_pattern_ids": [item["pattern_id"] for item in selected_candidates],
            "reason_codes": incompatible_reasons,
            "summary": (
                "Exact compatibility window matched a canonical template."
                if canonical_candidate is not None
                else "No canonical template matched the requested compatibility window."
            ),
            "provenance": _pattern_provenance(
                snapshot_id=snapshot_id,
                config_digest=snapshot["config_digest"],
                source_record_ids=sorted({rid for candidate in selected_candidates for rid in candidate["source_record_ids"]}),
                compatibility_signature=query_signature,
                snapshot_state="explanation",
                circuit_id=circuit_id,
                backend_class=backend_class,
                compatibility_window=query_window,
                query_signature=query_signature,
                query=query,
                validation_status={
                    "compatible": canonical_candidate is not None,
                    "canonical_eligible": canonical_candidate is not None,
                    "selected": False,
                    "rank": 0,
                    "incompatibility_reasons": incompatible_reasons,
                },
            ),
        }

        return {
            "contract": "pattern_miner.pattern",
            "version": PATTERN_CONTRACT_VERSION,
            "tenant_id": query["tenant_id"],
            "project_id": query["project_id"],
            "snapshot_id": snapshot_id,
            "config_digest": snapshot["config_digest"],
            "candidate_budget": query["candidate_budget"],
            "canonical_pattern_id": canonical_pattern_id,
            "selected_candidate_id": canonical_pattern_id,
            "cadence_seconds": PATTERN_MINER_CADENCE_SECONDS,
            "query": query,
            "canonical_pattern": canonical_pattern,
            "candidate_patterns": selected_candidates,
            "explanation_pattern": explanation_pattern,
            "diagnostics": diagnostics,
        }

    def get_recommendation(
        self,
        *,
        snapshot_id: str,
        tenant_id: str,
        project_id: str,
        circuit_id: str,
        backend_class: str,
        min_confidence: float = 0.0,
    ) -> dict[str, Any]:
        mined = self.mine_patterns(snapshot_id=snapshot_id, tenant_id=tenant_id, project_id=project_id)
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
            "tenant_id": tenant_id,
            "project_id": project_id,
            "snapshot_id": snapshot_id,
            "config_digest": mined["config_digest"],
            "cadence_seconds": mined["cadence_seconds"],
            "query": {"tenant_id": tenant_id, "project_id": project_id, "circuit_id": circuit_id, "backend_class": backend_class},
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

    GetPattern = get_pattern

    def _normalize_snapshot_records(
        self,
        records: list[dict[str, Any]],
        *,
        tenant_id: str,
        project_id: str,
    ) -> tuple[str, str, list[dict[str, Any]]]:
        normalized_tenant_id = _normalized_text(tenant_id)
        normalized_project_id = _normalized_text(project_id)

        record_tenants = sorted(
            {
                _normalized_text(record.get("tenant_id"))
                for record in records
                if _normalized_text(record.get("tenant_id"))
            }
        )
        record_projects = sorted(
            {
                _normalized_text(record.get("project_id"))
                for record in records
                if _normalized_text(record.get("project_id"))
            }
        )

        if not normalized_tenant_id:
            normalized_tenant_id = record_tenants[0] if len(record_tenants) == 1 else "tenant-default"
        if not normalized_project_id:
            normalized_project_id = record_projects[0] if len(record_projects) == 1 else "project-default"

        if len(record_tenants) > 1:
            raise ValueError("snapshot records must share a single tenant_id")
        if len(record_projects) > 1:
            raise ValueError("snapshot records must share a single project_id")
        if record_tenants and record_tenants[0] != normalized_tenant_id:
            raise ValueError("snapshot tenant_id does not match record tenant_id")
        if record_projects and record_projects[0] != normalized_project_id:
            raise ValueError("snapshot project_id does not match record project_id")

        normalized_records: list[dict[str, Any]] = []
        for record in sorted(records, key=lambda row: _canonical_json(row)):
            normalized_record = dict(record)
            record_tenant_id = _normalized_text(normalized_record.get("tenant_id")) or normalized_tenant_id
            record_project_id = _normalized_text(normalized_record.get("project_id")) or normalized_project_id
            if record_tenant_id != normalized_tenant_id or record_project_id != normalized_project_id:
                raise ValueError("snapshot records must share a single tenant/project scope")
            normalized_record["tenant_id"] = normalized_tenant_id
            normalized_record["project_id"] = normalized_project_id
            normalized_records.append(normalized_record)

        return normalized_tenant_id, normalized_project_id, normalized_records

    def _require_snapshot_scope(self, snapshot: dict[str, Any], *, tenant_id: str, project_id: str) -> None:
        if snapshot["tenant_id"] != _normalized_text(tenant_id) or snapshot["project_id"] != _normalized_text(project_id):
            raise PermissionError("snapshot scope mismatch")

    def _pattern_catalog(self, *, snapshot_id: str) -> list[dict[str, Any]]:
        snapshot = self._snapshots[snapshot_id]
        grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
        for record in [
            record
            for record in snapshot["records"]
            if _normalized_text(record.get("tenant_id")) == snapshot["tenant_id"]
            and _normalized_text(record.get("project_id")) == snapshot["project_id"]
        ]:
            circuit_id = _normalized_text(record.get("circuit_id"))
            backend_class = _normalized_text(record.get("backend_class"))
            pattern_family = _normalized_text(record.get("pattern_family") or f"{circuit_id}:{backend_class}") or f"{circuit_id}:{backend_class}"
            compatibility_window = self._record_compatibility_window(record)
            compatibility_signature = _sha256_hex(compatibility_window)
            grouped.setdefault((circuit_id, backend_class, pattern_family, compatibility_signature), []).append(record)

        patterns: list[dict[str, Any]] = []
        for (circuit_id, backend_class, pattern_family, compatibility_signature), members in sorted(grouped.items()):
            ordered_members = sorted(members, key=_canonical_json)
            source_record_ids = sorted(
                {
                    _normalized_text(member.get("record_id"))
                    for member in ordered_members
                    if _normalized_text(member.get("record_id"))
                }
            )
            representative = ordered_members[0] if ordered_members else {}
            compatibility_window = self._record_compatibility_window(representative)
            pattern_id = sha256(
                _canonical_json(
                    {
                        "snapshot_id": snapshot_id,
                        "circuit_id": circuit_id,
                        "backend_class": backend_class,
                        "pattern_family": pattern_family,
                        "compatibility_signature": compatibility_signature,
                        "source_record_ids": source_record_ids,
                    }
                ).encode("utf-8")
            ).hexdigest()[:16]
            patterns.append(
                {
                    "candidate_id": f"candidate-{pattern_id}",
                    "pattern_id": pattern_id,
                    "pattern_family": pattern_family,
                    "pattern_kind": "candidate",
                    "circuit_id": circuit_id,
                    "backend_class": backend_class,
                    "source_record_ids": source_record_ids,
                    "support": len(source_record_ids),
                    "compatibility_window": compatibility_window,
                    "compatibility_signature": compatibility_signature,
                    "canonical_eligible": True,
                    "selected": False,
                    "rank": 0,
                    "score_breakdown": {
                        "structural_score": 0.0,
                        "vector_score": 0.0,
                        "hybrid_score": 0.0,
                    },
                    "score_total": 0.0,
                    "confidence": 0.0,
                    "canonical_template_ref": f"kb://patterns/{pattern_id}",
                    "explanation_ref": f"kb://patterns/{pattern_id}/explanation",
                    "metadata": {
                        "snapshot_id": snapshot_id,
                        "config_digest": snapshot["config_digest"],
                        "source_record_count": len(source_record_ids),
                    },
                    "provenance": _pattern_provenance(
                        snapshot_id=snapshot_id,
                        config_digest=snapshot["config_digest"],
                        source_record_ids=source_record_ids,
                        compatibility_signature=compatibility_signature,
                        snapshot_state="catalogued",
                        circuit_id=circuit_id,
                        backend_class=backend_class,
                        compatibility_window=compatibility_window,
                    ),
                }
            )

        return patterns

    def _record_compatibility_window(self, record: dict[str, Any]) -> dict[str, str]:
        return {field: _normalized_text(record.get(field, "")) for field in _PATTERN_COMPATIBILITY_FIELDS}

    def _query_compatibility_window(self, query: dict[str, Any]) -> dict[str, str]:
        return {field: _normalized_text(query.get(field, "")) for field in _PATTERN_COMPATIBILITY_FIELDS}

    def _normalize_pattern_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        required_fields = (
            "tenant_id",
            "project_id",
            "snapshot_id",
            "circuit_id",
            "backend_class",
            "semantic_hash",
            "aqo_hash",
            "schema_version",
            "compiler_version",
            "aqo_version",
            "optimizer_version",
        )
        missing = [field for field in required_fields if not _normalized_text(payload.get(field, ""))]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")

        query_mode = _normalized_text(payload.get("query_mode", "structural")).lower() or "structural"
        if query_mode not in _PATTERN_QUERY_MODES:
            query_mode = "structural"

        return {
            "tenant_id": _normalized_text(payload.get("tenant_id")),
            "project_id": _normalized_text(payload.get("project_id")),
            "snapshot_id": _normalized_text(payload.get("snapshot_id")),
            "circuit_id": _normalized_text(payload.get("circuit_id")),
            "backend_class": _normalized_text(payload.get("backend_class")),
            "semantic_hash": _normalized_text(payload.get("semantic_hash")),
            "aqo_hash": _normalized_text(payload.get("aqo_hash")),
            "schema_version": _normalized_text(payload.get("schema_version")),
            "compiler_version": _normalized_text(payload.get("compiler_version")),
            "aqo_version": _normalized_text(payload.get("aqo_version")),
            "optimizer_version": _normalized_text(payload.get("optimizer_version")),
            "policy_mode": _normalized_text(payload.get("policy_mode", "deterministic")) or "deterministic",
            "policy_digest": _normalized_text(payload.get("policy_digest")),
            "seed": int(payload.get("seed", 0) or 0),
            "deterministic": bool(payload.get("deterministic", True)),
            "query_mode": query_mode,
            "candidate_budget": _clamp_budget(payload.get("candidate_budget", PATTERN_MINER_MAX_CANDIDATES)),
        }

    def _decorate_pattern_candidate(
        self,
        *,
        pattern: dict[str, Any],
        query: dict[str, Any],
        query_signature: str,
        max_support: int,
    ) -> dict[str, Any]:
        compatibility_checks = self._compatibility_checks(pattern["compatibility_window"], query)
        compatible = not compatibility_checks["incompatibility_reasons"]
        compatibility_ratio = compatibility_checks["compatibility_ratio"]
        support_ratio = pattern["support"] / float(max_support or 1)
        structural_score = round((support_ratio * 0.6) + (compatibility_ratio * 0.4), 6)

        vector_digest = _sha256_hex(
            {
                "pattern_id": pattern["pattern_id"],
                "pattern_family": pattern["pattern_family"],
                "query_signature": query_signature,
                "semantic_hash": query["semantic_hash"],
                "aqo_hash": query["aqo_hash"],
                "seed": query["seed"],
            }
        )
        vector_score = round(_digest_to_unit_interval(vector_digest), 6)
        hybrid_score = round((structural_score * 0.6) + (vector_score * 0.4), 6)

        if query["query_mode"] == "vector":
            selected_score = vector_score
        elif query["query_mode"] == "hybrid":
            selected_score = hybrid_score
        else:
            selected_score = structural_score

        confidence = round(min(1.0, (support_ratio * 0.5) + (compatibility_ratio * 0.5)), 6)

        candidate = dict(pattern)
        candidate.update(
            {
                "compatible": compatible,
                "incompatibility_reasons": compatibility_checks["incompatibility_reasons"],
                "canonical_eligible": compatible,
                "score_breakdown": {
                    "structural_score": structural_score,
                    "vector_score": vector_score,
                    "hybrid_score": hybrid_score,
                },
                "score_total": selected_score,
                "confidence": confidence,
                "metadata": {
                    **pattern["metadata"],
                    "query_mode": query["query_mode"],
                    "query_signature": query_signature,
                    "compatibility_ratio": compatibility_ratio,
                    "support_ratio": round(support_ratio, 6),
                },
                "provenance": _pattern_provenance(
                    snapshot_id=pattern["provenance"]["source"]["snapshot_id"],
                    config_digest=pattern["provenance"]["source"]["config_digest"],
                    source_record_ids=list(pattern["source_record_ids"]),
                    compatibility_signature=pattern["compatibility_signature"],
                    snapshot_state="compatible" if compatible else "incompatible",
                    circuit_id=pattern["circuit_id"],
                    backend_class=pattern["backend_class"],
                    compatibility_window=pattern["compatibility_window"],
                    query_signature=query_signature,
                    query=query,
                    validation_status={
                        "compatible": compatible,
                        "canonical_eligible": compatible,
                        "selected": False,
                        "rank": 0,
                        "incompatibility_reasons": compatibility_checks["incompatibility_reasons"],
                    },
                ),
            }
        )
        return candidate

    def _compatibility_checks(self, compatibility_window: dict[str, str], query: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        matched_fields = 0
        for field in _PATTERN_COMPATIBILITY_FIELDS:
            expected = compatibility_window.get(field, "")
            actual = _normalized_text(query.get(field, ""))
            if expected and expected == actual:
                matched_fields += 1
                continue
            if expected or actual:
                reason_code = _PATTERN_INCOMPATIBILITY_REASON_MAP[field]
                if reason_code not in reasons:
                    reasons.append(reason_code)
        compatibility_ratio = matched_fields / float(len(_PATTERN_COMPATIBILITY_FIELDS))
        return {
            "compatible": not reasons,
            "incompatibility_reasons": reasons,
            "compatibility_ratio": round(compatibility_ratio, 6),
        }

    def _choose_canonical_pattern(self, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda item: (
                -item["support"],
                item["pattern_family"],
                item["pattern_id"],
            ),
        )[0]

    def _order_pattern_candidates(self, candidates: list[dict[str, Any]], *, canonical_pattern_id: str) -> list[dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda item: (
                0 if canonical_pattern_id and item["pattern_id"] == canonical_pattern_id else 1,
                -item["score_total"],
                -item["confidence"],
                item["candidate_id"],
            ),
        )

    def _collect_incompatibility_reasons(self, candidates: list[dict[str, Any]]) -> list[str]:
        reasons: list[str] = []
        for candidate in candidates:
            for reason in candidate["incompatibility_reasons"]:
                if reason not in reasons:
                    reasons.append(reason)
        return reasons
