from __future__ import annotations

import hashlib
import json
from pathlib import Path

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from eigen_compiler.compiler import compile_eigen_lang
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


@pytest.mark.parametrize("case_dir", sorted(GOLDEN_ROOT.iterdir()), ids=lambda p: p.name)
def test_golden_cases_match_expected_aqo(case_dir: Path) -> None:
    source = (case_dir / "program.eigen.py").read_bytes()
    expected = json.loads((case_dir / "expected.aqo.json").read_text(encoding="utf-8"))

    first = compile_eigen_lang(source).aqo_json
    second = compile_eigen_lang(source).aqo_json

    assert first == second, "AQO output must be deterministic for the same source"
    assert json.loads(first.decode("utf-8")) == expected


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
