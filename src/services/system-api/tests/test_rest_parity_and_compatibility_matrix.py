from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA = Path(__file__).resolve().parents[4] / "contracts" / "product-1.0" / "public-rest.openapi.json"
FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "contracts"
    / "system_api_rest_v1"
    / "parity_matrix_v1_0_0.json"
)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_rest_schema_bundle_contains_canonical_error_and_observability_contracts() -> None:
    schema = _load_json(SCHEMA)

    assert schema["openapi"] == "3.1.0"
    assert schema["info"]["version"] == "1.0.0"
    assert schema["x-product-release-target"] == "1.0.0"
    assert schema["x-schema-bundle-contract"] == "contracts/product-1.0/public-rest.openapi.json"

    paths = schema["paths"]
    assert "/v1/benchmarks/run" in paths
    assert "/v1/explain/backend-selection" in paths

    benchmark = paths["/v1/benchmarks/run"]["post"]
    explain = paths["/v1/explain/backend-selection"]["post"]

    assert benchmark["x-canonical-error-map"]["FAILED_PRECONDITION"] == 409
    assert benchmark["x-canonical-error-reasons"]["FAILED_PRECONDITION"] == "EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT"
    assert benchmark["x-observability-contract-marker"]["metric_family"] == "eigen_public_api_contract_requests_total"
    assert benchmark["x-deterministic-request-hashing"]["algorithm"] == "sha256"

    benchmark_request = schema["components"]["schemas"]["BenchmarkRunRequest"]
    assert benchmark_request["required"] == ["idempotency_key", "config"]
    assert benchmark_request["properties"]["config"]["minProperties"] == 1
    assert benchmark_request["properties"]["config"]["required"] == ["dataset", "backend", "seed"]

    error_envelope = schema["components"]["schemas"]["CanonicalErrorEnvelope"]
    assert "x-canonical-detail-shapes" in error_envelope
    assert "google.rpc.BadRequest" in error_envelope["x-canonical-detail-shapes"]

    assert explain["x-canonical-error-map"]["NOT_FOUND"] == 404
    assert explain["x-canonical-error-reasons"]["NOT_FOUND"] == "EIGEN_PUBLIC_BACKEND_SELECTION_NOT_FOUND"
    assert explain["security"] == [{"bearerAuth": []}]


def test_rest_parity_matrix_fixture_records_schema_bundle_and_parity_contracts() -> None:
    matrix = _load_json(FIXTURE)
    assert matrix["artifact_version"] == "1.0.0"

    release_artifacts = matrix["release_artifacts"]
    assert release_artifacts["schema_bundle"] == "contracts/product-1.0/public-rest.openapi.json"
    assert release_artifacts["public_parity_matrix"] == "docs/development/wave-4/product-1.0-wave-4-public-parity-matrix.md"

    rest = matrix["rest_parity"]
    assert rest["paths"] == ["submit", "watch", "results", "cancel"]
    assert rest["required_terminal_states"] == ["DONE", "ERROR", "CANCELLED", "TIMEOUT"]
    assert rest["watch_monotonic_event_seq"] is True
    assert rest["schema_contract"] == "contracts/product-1.0/public-rest.openapi.json"
    assert rest["error_parity"]["FAILED_PRECONDITION"] == "EIGEN_PUBLIC_IDEMPOTENCY_CONFLICT"
    assert rest["observability_marker"] == "eigen_public_api_contract_requests_total"
    assert rest["trace_headers"] == ["traceparent", "x-request-id"]
    assert rest["idempotency_parity"]["hash_algorithm"] == "sha256"

    providers = matrix["providers"]
    assert len(providers) == 1
    assert providers[0]["provider"] == "sim:local"
    assert providers[0]["status"] == "ga"


def test_rest_schema_error_envelope_stays_canonical_and_fails_closed() -> None:
    schema = _load_json(SCHEMA)
    error = schema["components"]["responses"]["InvalidArgument"]["content"]["application/json"]["schema"]
    assert error == {"$ref": "#/components/schemas/CanonicalErrorEnvelope"}
    responses = schema["paths"]["/v1/benchmarks/run"]["post"]["responses"]
    assert responses["400"]["$ref"] == "#/components/responses/InvalidArgument"
    assert responses["401"]["$ref"] == "#/components/responses/Unauthenticated"
    assert responses["403"]["$ref"] == "#/components/responses/PermissionDenied"
    assert responses["409"]["$ref"] == "#/components/responses/IdempotencyConflict"
    assert responses["429"]["$ref"] == "#/components/responses/ResourceExhausted"
    assert responses["500"]["$ref"] == "#/components/responses/Internal"
    assert responses["503"]["$ref"] == "#/components/responses/Unavailable"
    