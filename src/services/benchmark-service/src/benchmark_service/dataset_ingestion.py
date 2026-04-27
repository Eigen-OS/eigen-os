from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

DATASET_MANIFEST_SCHEMA_VERSION = "1.0.0"
DATASET_REGISTRY_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ValidationError:
    code: str
    field: str
    message: str


class DatasetValidationError(ValueError):
    """Raised when dataset manifest bundle validation fails."""

    def __init__(self, errors: list[ValidationError]) -> None:
        super().__init__("dataset bundle validation failed")
        self.errors = errors


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    dataset_name: str
    dataset_version: str
    manifest_version: str
    schema_version: str
    source_uri: str
    source_checksum: str
    bundle_path: str


class DatasetCatalog:
    """In-memory dataset catalog with queryable versions per dataset."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], DatasetRecord] = {}

    def register(self, record: DatasetRecord) -> DatasetRecord:
        self._records[(record.dataset_name, record.dataset_version)] = record
        return record

    def get_dataset(self, *, dataset_name: str, dataset_version: str) -> DatasetRecord:
        return self._records[(dataset_name, dataset_version)]

    def list_versions(self, *, dataset_name: str) -> list[str]:
        versions = [ver for (name, ver) in self._records if name == dataset_name]
        return sorted(versions)


class DatasetIngestionService:
    """Validates and ingests QSBench-compatible dataset bundles."""

    def __init__(self, catalog: DatasetCatalog | None = None) -> None:
        self._catalog = catalog or DatasetCatalog()

    @property
    def catalog(self) -> DatasetCatalog:
        return self._catalog

    def ingest_bundle(self, bundle_path: str | Path) -> DatasetRecord:
        root = Path(bundle_path)
        manifest_path = root / "manifest.json"
        errors: list[ValidationError] = []

        if not manifest_path.exists():
            raise DatasetValidationError(
                [ValidationError(code="manifest_missing", field="manifest.json", message="manifest.json is required")]
            )

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise DatasetValidationError(
                [
                    ValidationError(
                        code="manifest_invalid_json",
                        field="manifest.json",
                        message=f"invalid JSON: {err.msg}",
                    )
                ]
            ) from err

        self._validate_manifest(manifest=manifest, root=root, errors=errors)
        if errors:
            raise DatasetValidationError(errors)

        checksum_target = root / manifest["source_file"]
        checksum_value = self._sha256(checksum_target)
        if checksum_value != manifest["source_checksum"]:
            raise DatasetValidationError(
                [
                    ValidationError(
                        code="checksum_mismatch",
                        field="source_checksum",
                        message=(
                            f"expected {manifest['source_checksum']} but got {checksum_value} "
                            f"for {manifest['source_file']}"
                        ),
                    )
                ]
            )

        record = DatasetRecord(
            dataset_name=manifest["dataset_name"],
            dataset_version=manifest["dataset_version"],
            manifest_version=manifest["manifest_version"],
            schema_version=manifest["schema_version"],
            source_uri=manifest["source_uri"],
            source_checksum=manifest["source_checksum"],
            bundle_path=str(root.resolve()),
        )
        return self._catalog.register(record)

    def _validate_manifest(self, *, manifest: dict[str, Any], root: Path, errors: list[ValidationError]) -> None:
        required_string_fields = [
            "manifest_version",
            "schema_version",
            "dataset_name",
            "dataset_version",
            "source_uri",
            "source_checksum",
            "source_file",
        ]
        for field in required_string_fields:
            value = manifest.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    ValidationError(
                        code="field_required",
                        field=field,
                        message="field is required and must be a non-empty string",
                    )
                )

        if manifest.get("schema_version") != DATASET_MANIFEST_SCHEMA_VERSION:
            errors.append(
                ValidationError(
                    code="unsupported_schema_version",
                    field="schema_version",
                    message=(
                        f"expected {DATASET_MANIFEST_SCHEMA_VERSION}, got "
                        f"{manifest.get('schema_version')}"
                    ),
                )
            )

        source_uri = manifest.get("source_uri")
        if isinstance(source_uri, str) and "://" not in source_uri:
            errors.append(
                ValidationError(
                    code="invalid_provenance",
                    field="source_uri",
                    message="source_uri must be a URI (for example s3://, https://, file://)",
                )
            )

        source_file = manifest.get("source_file")
        if isinstance(source_file, str):
            file_path = root / source_file
            if not file_path.exists():
                errors.append(
                    ValidationError(
                        code="file_missing",
                        field="source_file",
                        message=f"file does not exist in bundle: {source_file}",
                    )
                )

        source_checksum = manifest.get("source_checksum")
        if isinstance(source_checksum, str) and len(source_checksum) != 64:
            errors.append(
                ValidationError(
                    code="invalid_checksum",
                    field="source_checksum",
                    message="source_checksum must be a 64-char sha256 hex string",
                )
            )

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(8192)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
