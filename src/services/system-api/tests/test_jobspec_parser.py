from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from eigen.api.v1 import job_service_pb2 as job_pb

from system_api.jobspec_parser import (
    JobSpecValidationError,
    canonical_jobspec_digest,
    canonical_jobspec_json,
    normalize_jobspec,
    parse_jobspec_to_submit_request,
)


FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "jobspec"


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
        assert req.workload.kind == job_pb.WorkloadFamilyKind.Value(
            {
                "QuantumJob": "WORKLOAD_FAMILY_KIND_QUANTUM_JOB",
                "HybridWorkflow": "WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW",
                "DistributedJob": "WORKLOAD_FAMILY_KIND_DISTRIBUTED_JOB",
                "BenchmarkJob": "WORKLOAD_FAMILY_KIND_BENCHMARK_JOB",
                "PipelineJob": "WORKLOAD_FAMILY_KIND_PIPELINE_JOB",
                "ReplayJob": "WORKLOAD_FAMILY_KIND_REPLAY_JOB",
            }[normalized["spec"]["workload"]["kind"]]
        )
        assert req.workload.execution_profile == normalized["spec"]["workload"]["execution_profile"]
        assert req.workload.replayable == normalized["spec"]["workload"]["replayable"]
        assert req.workload.backend_target == normalized["spec"]["workload"]["backend_target"]
        assert req.metadata["jobspec_version"] == "1.0.0"
        assert req.metadata["jobspec_digest"] == normalized["digest"]
        assert req.metadata["source_sha256"] == req.eigen_lang.sha256
        assert json.loads(req.metadata["jobspec_workload"]) == normalized["spec"]["workload"]
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


def test_jobspec_workload_family_fixtures_cover_all_supported_roles() -> None:
    cases = [
        ("workload_family_hybrid", "HybridWorkflow"),
        ("workload_family_distributed", "DistributedJob"),
        ("workload_family_benchmark", "BenchmarkJob"),
        ("workload_family_pipeline", "PipelineJob"),
        ("workload_family_replay", "ReplayJob"),
    ]

    for case_name, expected_kind in cases:
        case_path = FIXTURES_ROOT / "positive" / case_name / "job.yaml"
        normalized = normalize_jobspec(case_path)
        req = parse_jobspec_to_submit_request(case_path)

        assert normalized["spec"]["workload"]["kind"] == expected_kind
        assert req.metadata["jobspec_workload"]
        assert json.loads(req.metadata["jobspec_workload"]) == normalized["spec"]["workload"]
        assert req.workload.execution_profile == normalized["spec"]["workload"]["execution_profile"]


def test_jobspec_negative_path_traversal_is_rejected() -> None:
    for case_path in [
        FIXTURES_ROOT / "negative" / "path_traversal" / "job.yaml",
        FIXTURES_ROOT / "negative" / "v1_invalid" / "job.yaml",
    ]:
        with pytest.raises(JobSpecValidationError) as exc:
            parse_jobspec_to_submit_request(case_path)

        fields = {v.field for v in exc.value.violations}
        assert {"spec.program.path", "spec.program_path"} & fields


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
