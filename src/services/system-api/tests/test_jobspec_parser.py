from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from system_api.jobspec_parser import JobSpecValidationError, parse_jobspec_to_submit_request


FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "jobspec"


def _positive_cases() -> list[Path]:
    return sorted((FIXTURES_ROOT / "positive").iterdir())


def test_jobspec_positive_fixtures_are_mapped_deterministically() -> None:
    for case_dir in _positive_cases():
        req = parse_jobspec_to_submit_request(case_dir / "job.yaml")
        expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))

        assert req.name == expected["name"]
        assert req.target == expected["target"]
        assert req.priority == expected["priority"]
        assert dict(req.compiler_options) == expected["compiler_options"]
        metadata = dict(req.metadata)
        for k, v in expected["metadata"].items():
            assert metadata.get(k) == v
        assert list(req.dependencies) == expected["dependencies"]

        assert req.eigen_lang.entrypoint == expected["entrypoint"]
        assert req.eigen_lang.sha256 == sha256(bytes(req.eigen_lang.source)).hexdigest()
        assert req.metadata["jobspec_yaml"]


def test_jobspec_negative_path_traversal_is_rejected() -> None:
    case_path = FIXTURES_ROOT / "negative" / "path_traversal" / "job.yaml"

    with pytest.raises(JobSpecValidationError) as exc:
        parse_jobspec_to_submit_request(case_path)

    fields = {v.field for v in exc.value.violations}
    assert "spec.program_path" in fields


def test_jobspec_negative_missing_target_is_rejected() -> None:
    case_path = FIXTURES_ROOT / "negative" / "missing_target" / "job.yaml"

    with pytest.raises(JobSpecValidationError) as exc:
        parse_jobspec_to_submit_request(case_path)

    fields = {v.field for v in exc.value.violations}
    assert "spec.target" in fields
