from __future__ import annotations

from pathlib import Path

from benchmark_service.dataset_ingestion import (
    DATASET_MANIFEST_SCHEMA_VERSION,
    DatasetIngestionService,
    DatasetValidationError,
)

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "datasets"


def test_ingestion_registers_valid_bundle_and_exposes_queryable_versions() -> None:
    service = DatasetIngestionService()

    record = service.ingest_bundle(FIXTURES_ROOT / "positive_qsbench_bundle")

    assert record.schema_version == DATASET_MANIFEST_SCHEMA_VERSION
    assert record.dataset_name == "qsbench-core"
    assert service.catalog.list_versions(dataset_name="qsbench-core") == ["2026.04.27"]


def test_ingestion_rejects_invalid_manifest_with_structured_errors() -> None:
    service = DatasetIngestionService()

    try:
        service.ingest_bundle(FIXTURES_ROOT / "negative_missing_required")
    except DatasetValidationError as err:
        codes = {item.code for item in err.errors}
        fields = {item.field for item in err.errors}
        assert "field_required" in codes
        assert "invalid_provenance" in codes
        assert "invalid_checksum" in codes
        assert "file_missing" in codes
        assert "dataset_name" in fields
    else:
        raise AssertionError("invalid dataset bundle must be rejected")


def test_ingestion_rejects_checksum_mismatch() -> None:
    service = DatasetIngestionService()

    try:
        service.ingest_bundle(FIXTURES_ROOT / "negative_checksum_mismatch")
    except DatasetValidationError as err:
        assert len(err.errors) == 1
        assert err.errors[0].code == "checksum_mismatch"
        assert err.errors[0].field == "source_checksum"
    else:
        raise AssertionError("checksum mismatch must be rejected")
