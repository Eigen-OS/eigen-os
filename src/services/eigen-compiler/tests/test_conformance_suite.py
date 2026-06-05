from __future__ import annotations

import hashlib
import json
from pathlib import Path

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from eigen_compiler.compiler import CompilerValidationError, compile_eigen_lang, _encode_aqo_payload
from eigen_compiler.proto_gen import ensure_generated

ensure_generated()

from eigen.internal.v1 import compilation_service_pb2 as comp_pb  # noqa: E402
from eigen.internal.v1 import compilation_service_pb2_grpc as comp_pb_grpc  # noqa: E402

TESTS_ROOT = Path(__file__).parent
GOLDEN_ROOT = TESTS_ROOT / "golden"
NEGATIVE_ROOT = TESTS_ROOT / "negative"


def _extract_bad_request(err: grpc.RpcError) -> error_details_pb2.BadRequest:
    status = rpc_status.from_call(err)
    assert status is not None

    bad = error_details_pb2.BadRequest()
    assert len(status.details) >= 1
    assert status.details[0].Unpack(bad)
    return bad


def _normalize_aqo_for_compare(aqo: dict[str, object]) -> dict[str, object]:
    normalized = json.loads(json.dumps(aqo))
    normalized["version"] = "1.0.0"

    parameters = normalized.get("parameters")
    if isinstance(parameters, list):
        param_obj: dict[str, object] = {}
        for entry in parameters:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                param_obj[entry["name"]] = entry.get("default", entry["name"])
        normalized["parameters"] = param_obj
    return normalized


@pytest.mark.parametrize("case_dir", sorted(GOLDEN_ROOT.iterdir()), ids=lambda p: p.name)
def test_golden_cases_match_expected_aqo(case_dir: Path) -> None:
    source = (case_dir / "program.eigen.py").read_bytes()
    expected = json.loads((case_dir / "expected.aqo.json").read_text(encoding="utf-8"))

    first = compile_eigen_lang(source).aqo_json
    second = compile_eigen_lang(source).aqo_json

    assert first == second, "AQO output must be deterministic for the same source"
    actual = json.loads(first.decode("utf-8"))
    assert actual["version"] == "1.0.0"
    assert isinstance(actual["operations"], list)
    if "parameters" in actual:
        assert isinstance(actual["parameters"], dict)
    assert _normalize_aqo_for_compare(actual) == _normalize_aqo_for_compare(expected)


def test_aqo_json_is_canonical_bytes_without_whitespace() -> None:
    source = (
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program(target=\"sim\", shots=1000)\n"
        b"def main():\n"
        b"    ry(0, theta=1.570796)\n"
    )
    compiled = compile_eigen_lang(source)
    payload = json.loads(compiled.aqo_json.decode("utf-8"))
    assert compiled.aqo_json == json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert payload["version"] == "1.0.0"


def test_aqo_sha256_matches_payload_and_is_stable() -> None:
    source = (
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program(target=\"sim\", shots=1000)\n"
        b"def main():\n"
        b"    ry(0, theta=1.570796)\n"
    )

    first = compile_eigen_lang(source)
    second = compile_eigen_lang(source)

    expected_hash = hashlib.sha256(first.aqo_json).hexdigest()

    assert first.metadata["aqo_sha256"] == expected_hash
    assert first.metadata["aqo_version"] == "1.0.0"
    assert second.metadata["aqo_sha256"] == expected_hash


def test_no_synthetic_gate_stub_is_emitted() -> None:
    source = (
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program(target=\"sim\", shots=1000)\n"
        b"def main():\n"
        b"    pass\n"
    )

    compiled = json.loads(compile_eigen_lang(source).aqo_json.decode("utf-8"))

    assert compiled["operations"] == [{"op": "MEASURE", "q": [0], "c": [0]}]


def test_distributed_metadata_contract_is_deterministic() -> None:
    source = (
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program()\n"
        b"def main():\n"
        b"    ry(0, theta=1.0)\n"
    )
    options = {
        "distributed.enabled": "true",
        "distributed.target": "cluster",
        "distributed.partition_count": "4",
        "distributed.queue_provider": "memory",
        "distributed.topology_hint": "pipeline",
    }

    first = compile_eigen_lang(source, options=options)
    second = compile_eigen_lang(source, options=options)

    first_aqo = json.loads(first.aqo_json.decode("utf-8"))
    second_aqo = json.loads(second.aqo_json.decode("utf-8"))

    assert first_aqo == second_aqo
    assert first_aqo["distributed_execution"] == {
        "version": "1.0.0",
        "target": "cluster",
        "partition_count": 4,
        "queue_provider": "memory",
        "hints": {"version": "1.0.0", "topology_hint": "pipeline"},
    }
    assert first.metadata["distributed.execution_metadata_version"] == "1.0.0"
    assert first.metadata["distributed.topology_hints_version"] == "1.0.0"


def test_aqo_validation_rejects_unknown_opcode() -> None:
    with pytest.raises(CompilerValidationError) as exc:
        _encode_aqo_payload(
            {
                "version": "1.0.0",
                "qubits": 1,
                "operations": [{"op": "FOO", "q": [0]}],
            }
        )
    assert any(v.field == "operations[0].op" for v in exc.value.violations)


def test_aqo_validation_rejects_invalid_measurement_shape() -> None:
    with pytest.raises(CompilerValidationError) as exc:
        _encode_aqo_payload(
            {
                "version": "1.0.0",
                "qubits": 2,
                "operations": [{"op": "MEASURE", "q": [0, 1], "c": [0]}],
            }
        )
    assert any(v.field == "operations[0].c" for v in exc.value.violations)


def test_compile_job_request_metadata_is_propagated(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)
    source = (
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program(target=\"sim\", shots=1000)\n"
        b"def main():\n"
        b"    ry(0, theta=1.0)\n"
    )
    request = comp_pb.CompileJobRequest(
        job_id="job-123",
        language="eigen-lang",
        source=source,
        source_ref="qfs://jobs/job-123/input/program.eigen.py",
        options={"beta": "2", "alpha": "1"},
        request_metadata=comp_pb.RequestMetadata(
            request_id="req-123",
            trace_id="trace-456",
            traceparent="00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01",
            deadline="2026-06-06T12:00:00Z",
            retry_policy="idempotent",
            security_context="mTLS",
            tenant_id="tenant-a",
            project_id="project-x",
        ),
    )

    response = stub.CompileJob(request)

    assert response.metadata["request_id"] == "req-123"
    assert response.metadata["trace_id"] == "trace-456"
    assert response.metadata["tenant_id"] == "tenant-a"
    assert response.metadata["project_id"] == "project-x"
    assert response.metadata["source_precedence"] == "source"
    assert response.metadata["options_json"] == '{"alpha":"1","beta":"2"}'

    expected_request_digest = hashlib.sha256(
        json.dumps(
            {
                "options": {"alpha": "1", "beta": "2"},
                "request_context": {
                    "deadline": "2026-06-06T12:00:00Z",
                    "project_id": "project-x",
                    "request_id": "req-123",
                    "retry_policy": "idempotent",
                    "security_context": "mTLS",
                    "tenant_id": "tenant-a",
                    "trace_id": "trace-456",
                    "traceparent": "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01",
                },
                "source_precedence": "source",
                "source_ref": "qfs://jobs/job-123/input/program.eigen.py",
                "source_sha256": hashlib.sha256(source).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert response.metadata["request_sha256"] == expected_request_digest


def test_source_ref_is_resolved_from_qfs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = (
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program(target=\"sim\", shots=1000)\n"
        b"def main():\n"
        b"    ry(0, theta=1.0)\n"
    )
    qfs_root = tmp_path / "circuit_fs"
    program_path = qfs_root / "jobs" / "job-1" / "input" / "program.eigen.py"
    program_path.parent.mkdir(parents=True)
    program_path.write_bytes(source)
    monkeypatch.setenv("EIGEN_QFS_ROOT", str(qfs_root))

    from_ref = compile_eigen_lang(b"", source_ref="jobs/job-1/input/program.eigen.py")
    direct = compile_eigen_lang(source)
    with_source_and_ref = compile_eigen_lang(
        source,
        source_ref="jobs/job-1/input/program.eigen.py",
    )

    assert from_ref.aqo_json == direct.aqo_json
    assert from_ref.metadata["source_precedence"] == "source_ref"
    assert with_source_and_ref.aqo_json == direct.aqo_json
    assert with_source_and_ref.metadata["source_precedence"] == "source"


@pytest.mark.parametrize("case_file", sorted(NEGATIVE_ROOT.glob("*/request.json")), ids=lambda p: p.parent.name)
def test_negative_cases_return_expected_validation_errors(grpc_addr: str, case_file: Path) -> None:
    case = json.loads(case_file.read_text(encoding="utf-8"))
    expected = case["expected"]

    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    rpc = case["rpc"]
    request = case["request"]

    with pytest.raises(grpc.RpcError) as exc:
        if rpc == "CompileCircuit":
            payload = request.copy()
            if "source" in payload:
                payload["source"] = payload["source"].encode("utf-8")
            stub.CompileCircuit(comp_pb.CompileCircuitRequest(**payload))
        elif rpc == "CompileJob":
            stub.CompileJob(comp_pb.CompileJobRequest(**request))
        else:  # pragma: no cover
            raise AssertionError(f"Unsupported rpc in case file {case_file}: {rpc}")

    assert exc.value.code().name == expected["code"]
    bad_request = _extract_bad_request(exc.value)
    assert sorted(v.field for v in bad_request.field_violations) == sorted(expected["fields"])
