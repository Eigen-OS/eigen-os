from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest


from system_api.jobspec_parser import (
    JobSpecValidationError,
    canonical_jobspec_digest,
    canonical_jobspec_json,
    normalize_jobspec,
    parse_jobspec_to_submit_request,
)


FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "jobspec"
WORKLOAD_KIND_VALUES = {
    "QuantumJob": 1,
    "HybridWorkflow": 2,
    "DistributedJob": 3,
    "BenchmarkJob": 4,
    "PipelineJob": 5,
    "ReplayJob": 6,
}


def _positive_cases() -> list[Path]:
    return sorted((FIXTURES_ROOT / "positive").iterdir())


def test_jobspec_positive_fixtures_are_mapped_deterministically() -> None:
    for case_dir in _positive_cases():
        req = parse_jobspec_to_submit_request(case_dir / "job.yaml")
        normalized = normalize_jobspec(case_dir / "job.yaml")

        assert req.name == normalized["metadata"]["name"]
        assert req.target == normalized["spec"]["target"]
        assert req.priority == normalized["spec"]["priority"]
        assert dict(req.compiler_options) == normalized["spec"]["compiler_options"]
        assert list(req.dependencies) == normalized["spec"]["dependencies"]
        assert req.eigen_lang.entrypoint == normalized["spec"]["program"]["entrypoint"]
        assert req.eigen_lang.sha256 == sha256(bytes(req.eigen_lang.source)).hexdigest()
        assert req.workload.kind == WORKLOAD_KIND_VALUES[normalized["spec"]["workload"]["kind"]]
        assert req.workload.execution_profile == normalized["spec"]["workload"]["execution_profile"]
        assert req.workload.replayable == normalized["spec"]["workload"]["replayable"]
        assert json.loads(req.metadata["jobspec_workload"]) == normalized["spec"]["workload"]
        assert req.metadata["jobspec_version"] == "1.0.0"
        assert req.metadata["jobspec_digest"] == normalized["digest"]
        assert req.metadata["source_sha256"] == req.eigen_lang.sha256
        assert req.metadata["jobspec_yaml"]


def test_jobspec_1_0_canonical_json_and_digest_are_byte_stable() -> None:
    case_path = FIXTURES_ROOT / "positive" / "v1_full" / "job.yaml"

    first_json = canonical_jobspec_json(case_path)
    second_json = canonical_jobspec_json(case_path)
    payload = json.loads(first_json)

    assert first_json == second_json
    assert payload["apiVersion"] == "eigen.os/v1"
    assert payload["version"] == "1.0.0"
    assert payload["digest"] == canonical_jobspec_digest(case_path)
    assert len(payload["digest"]) == 64
    assert payload["package"]["canonical_digest"] == payload["digest"]
    assert payload["scheduling"] == {"queue": "interactive"}
    assert payload["security"] == {"network": "disabled"}
    assert payload["observability"] == {"trace": "required"}


def test_jobspec_legacy_v0_1_migration_report_is_documented_in_normalized_payload() -> None:
    case_path = FIXTURES_ROOT / "positive" / "v01_migration" / "job.yaml"

    normalized = normalize_jobspec(case_path)

    assert normalized["apiVersion"] == "eigen.os/v1"
    assert normalized["compatibility"] == {
        "input_apiVersion": "eigen.os/v0.1",
        "migration": "v0.1-inline-and-program_path",
    }


def test_jobspec_future_compatible_sections_are_preserved_in_internal_metadata() -> None:
    case_path = FIXTURES_ROOT / "positive" / "v1_future_compatible" / "job.yaml"

    req = parse_jobspec_to_submit_request(case_path)

    assert json.loads(req.metadata["jobspec_observability"])["future_hint"] == "accepted-by-normalizer"


def test_jobspec_negative_missing_target_is_rejected() -> None:
    case_path = FIXTURES_ROOT / "negative" / "missing_target" / "job.yaml"

    with pytest.raises(JobSpecValidationError) as exc:
        parse_jobspec_to_submit_request(case_path)

    fields = {v.field for v in exc.value.violations}
    assert "spec.target" in fields


def test_jobspec_negative_unsupported_workload_kind_is_rejected() -> None:
    case_path = FIXTURES_ROOT / "negative" / "unsupported_workload_kind" / "job.yaml"

    with pytest.raises(JobSpecValidationError) as exc:
        parse_jobspec_to_submit_request(case_path)

    fields = {v.field for v in exc.value.violations}
    assert "spec.workload.kind" in fields


def test_submit_normalize_internal_workload_context() -> None:
    case_path = FIXTURES_ROOT / "positive" / "workload_family_hybrid" / "job.yaml"
    normalized = normalize_jobspec(case_path)
    req = parse_jobspec_to_submit_request(case_path)
 
    assert req.workload.kind == WORKLOAD_KIND_VALUES["HybridWorkflow"]
    assert req.workload.execution_profile == "hybrid"
    assert req.workload.execution_profile == normalized["spec"]["workload"]["execution_profile"]

    assert req.workload.replayable is True

    assert json.loads(req.metadata["jobspec_workload"]) == normalized["spec"]["workload"]


def test_missing_workload_context_defaults_to_quantumjob() -> None:
    case_path = FIXTURES_ROOT / "positive" / "v1_minimal" / "job.yaml"

    normalized = normalize_jobspec(case_path)
    req = parse_jobspec_to_submit_request(case_path)

    assert normalized["spec"]["workload"]["kind"] == "QuantumJob"
    assert normalized["spec"]["workload"]["execution_profile"] == "quantum"
    assert normalized["spec"]["workload"]["replayable"] is False
    assert normalized["spec"]["workload"]["backend_target"] == "sim:local"
    assert req.workload.kind == WORKLOAD_KIND_VALUES["QuantumJob"]
    assert req.workload.execution_profile == "quantum"
    assert json.loads(req.metadata["jobspec_workload"]) == normalized["spec"]["workload"]


def test_distributed_job_workload_is_preserved_opaquely() -> None:
    case_path = FIXTURES_ROOT / "positive" / "workload_family_distributed" / "job.yaml"

    normalized = normalize_jobspec(case_path)
    req = parse_jobspec_to_submit_request(case_path)

    assert normalized["spec"]["workload"]["kind"] == "DistributedJob"
    assert normalized["spec"]["workload"]["topology"] == {
        "cluster_id": "cluster:auto",
        "partition_count": 2,
        "partition_ids": ["partition-0", "partition-1"],
        "preferred_workers": ["worker-a", "worker-b"],
    }
    assert "jobspec_topology" not in req.metadata
    assert json.loads(req.metadata["jobspec_workload"]) == normalized["spec"]["workload"]
        