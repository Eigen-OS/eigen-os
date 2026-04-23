from __future__ import annotations

import grpc
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from eigen_compiler.proto_gen import ensure_generated

ensure_generated()

from eigen.internal.v1 import compilation_service_pb2 as comp_pb  # noqa: E402
from eigen.internal.v1 import compilation_service_pb2_grpc as comp_pb_grpc  # noqa: E402
from eigen.internal.v1 import types_pb2 as types_pb  # noqa: E402


def _extract_bad_request(err: grpc.RpcError) -> error_details_pb2.BadRequest:
    st = rpc_status.from_call(err)
    assert st is not None

    bad = error_details_pb2.BadRequest()
    assert len(st.details) >= 1
    assert st.details[0].Unpack(bad)
    return bad


def test_compile_circuit_happy_path(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    source = b"""
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister, RY, MEASURE

@hybrid_program
def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    RY(1.570796, q[0])
    MEASURE(q[0], c[0])
"""
    resp = stub.CompileCircuit(comp_pb.CompileCircuitRequest(language="eigen-lang", source=source))

    assert resp.circuit.format == types_pb.CIRCUIT_FORMAT_AQO_JSON
    assert resp.metadata["aqo_version"] == "0.1"
    assert len(resp.circuit.data) > 0


def test_compile_circuit_requires_input(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(comp_pb.CompileCircuitRequest(language="eigen-lang"))

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"input"}


def test_compile_circuit_rejects_unsupported_language(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(comp_pb.CompileCircuitRequest(language="qasm3", source=b"OPENQASM 3;"))

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"language"}


def test_compile_job_requires_job_id(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileJob(comp_pb.CompileJobRequest(language="eigen-lang", source_ref="qfs://src.eigen"))

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"job_id"}


def test_compile_circuit_rejects_forbidden_construct(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    source = b"""
from eigen_lang import hybrid_program, QubitRegister, ClassicalRegister

@hybrid_program
def main():
    q = QubitRegister(1)
    c = ClassicalRegister(1)
    eval('1+1')
"""

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(comp_pb.CompileCircuitRequest(language="eigen-lang", source=source))

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"source"}


def test_compile_circuit_requires_single_entrypoint(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    source = b"""
from eigen_lang import hybrid_program

@hybrid_program
def first():
    return None

@hybrid_program
def second():
    return None
"""

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(comp_pb.CompileCircuitRequest(language="eigen-lang", source=source))

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"entrypoint"}
