from __future__ import annotations

import hashlib
import json
import logging
import socket
import sys
import time
import types
from pathlib import Path
import grpc

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
EIGEN_ROOT = PACKAGE_ROOT / "eigen"
if "eigen" not in sys.modules:
    eigen_module = types.ModuleType("eigen")
    eigen_module.__path__ = [str(EIGEN_ROOT)]  # type: ignore[attr-defined]
    sys.modules["eigen"] = eigen_module
else:
    eigen_module = sys.modules["eigen"]
    package_path = list(getattr(eigen_module, "__path__", []))
    if str(EIGEN_ROOT) not in package_path:
        package_path.insert(0, str(EIGEN_ROOT))
        try:
            eigen_module.__path__ = package_path  # type: ignore[attr-defined]
        except Exception:
            pass
import pytest
from google.rpc import error_details_pb2
from grpc_status import rpc_status

from eigen_compiler.compiler import compile_eigen_lang
from eigen_compiler.proto_gen import ensure_generated

ensure_generated()

from eigen.internal.v1 import compilation_service_pb2 as comp_pb  # noqa: E402
from eigen.internal.v1 import compilation_service_pb2_grpc as comp_pb_grpc  # noqa: E402
from eigen.internal.v1 import neuro_symbolic_service_pb2 as nsc_pb  # noqa: E402
from eigen.internal.v1 import kernel_gateway_pb2 as kernel_pb  # noqa: E402
from eigen.internal.v1 import neuro_symbolic_service_pb2_grpc as nsc_pb_grpc  # noqa: E402
from eigen.internal.v1 import types_pb2 as types_pb  # noqa: E402


def _enum_value(module, *names: str) -> int:
    for name in names:
        if hasattr(module, name):
            return int(getattr(module, name))
    raise AttributeError(f"None of enum names exist: {names}")


def _extract_bad_request(err: grpc.RpcError) -> error_details_pb2.BadRequest:
    st = rpc_status.from_call(err)
    assert st is not None

    bad = error_details_pb2.BadRequest()
    assert len(st.details) >= 1
    assert st.details[0].Unpack(bad)
    return bad


def _redact_feature_vector(raw_feature_vector):
    from eigen_compiler.grpc_impl import _redact_feature_vector as _impl_redact_feature_vector

    return _impl_redact_feature_vector(raw_feature_vector)


def _extract_error_info(err: grpc.RpcError) -> error_details_pb2.ErrorInfo:
    st = rpc_status.from_call(err)
    assert st is not None
    info = error_details_pb2.ErrorInfo()
    assert len(st.details) >= 2
    for detail in st.details:
        if detail.Is(error_details_pb2.ErrorInfo.DESCRIPTOR):
            assert detail.Unpack(info)
            return info
    raise AssertionError("expected ErrorInfo in grpc status details")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stable_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _trace_digest_payload(
    *,
    rpc: str,
    request_id: str,
    trace_id: str,
    source_sha256: str,
    request_sha256: str,
    aqo_sha256: str,
    pattern_signature: str,
    compiler_status: str,
    failure_stage: str = "",
    failure_reason: str = "",
    compiler_replay_sha256: str = "",
    compiler_diagnostics_sha256: str = "",
) -> dict[str, str]:
    return {
        "rpc": rpc,
        "request_id": request_id,
        "trace_id": trace_id,
        "source_sha256": source_sha256,
        "request_sha256": request_sha256,
        "aqo_sha256": aqo_sha256,
        "pattern_signature": pattern_signature,
        "compiler_status": compiler_status,
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "compiler_replay_sha256": compiler_replay_sha256,
        "compiler_diagnostics_sha256": compiler_diagnostics_sha256,
    }


@pytest.fixture(scope="module")
def kb_server() -> Iterator[str]:
    neuro_package_root = Path(__file__).resolve().parents[2] / "neuro-symbolic-service" / "src"
    if str(neuro_package_root) not in sys.path:
        sys.path.insert(0, str(neuro_package_root))
    import eigen

    neuro_eigen_root = neuro_package_root / "eigen"
    if str(neuro_eigen_root) not in list(getattr(eigen, "__path__", [])):
        try:
            eigen.__path__.append(str(neuro_eigen_root))
        except Exception:
            pass

    from neuro_symbolic_service.grpc_server import serve

    addr = f"127.0.0.1:{_free_port()}"
    server = serve(bind=addr)
    time.sleep(0.05)
    yield addr
    server.stop(grace=None)


def test_compile_circuit_happy_path(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    resp = stub.CompileCircuit(
        comp_pb.CompileCircuitRequest(
            language="eigen-lang",
            source=(
                b"from eigen_lang import hybrid_program\n\n"
                b"@hybrid_program()\n"
                b"def main():\n"
                b"    ry(0, theta=1.0)\n"
            ),
        )
    )

    assert resp.circuit.format == _enum_value(types_pb, "CIRCUIT_FORMAT_AQO_JSON", "AQO_JSON")
    assert resp.metadata["aqo_version"] == "1.0.0"
    assert resp.metadata["workload_profile"] == "QuantumJob"
    assert len(resp.circuit.data) > 0
    assert resp.metadata["distributed.execution_metadata_version"] == "1.0.0"
    assert resp.metadata["distributed.enabled"] == "false"
    assert resp.metadata["compiler_replay_json"]
    assert len(resp.metadata["compiler_replay_sha256"]) == 64
    assert len(resp.metadata["symbolic_candidate_set_sha256"]) == 64

    candidate_set = json.loads(resp.metadata["symbolic_candidate_set_json"])
    assert candidate_set["version"] == "1.0.0"
    assert candidate_set["candidate_budget"] == 8
    assert candidate_set["candidate_count"] == len(candidate_set["candidates"])
    assert candidate_set["candidate_count"] <= candidate_set["candidate_budget"]
    assert candidate_set["ranker"] == {
        "model_family": "gnn",
        "model_version": "logical-rewrite-ranker-v1",
        "graph_schema_version": "logical-compiler-graph-v1",
        "objective": "expected_usefulness",
    }
    assert candidate_set["selected_candidate_id"] == candidate_set["ranked_candidates"][0]["candidate_id"]
    assert candidate_set["legal_candidate_count"] == len(candidate_set["ranked_candidates"])
    assert [candidate["rank"] for candidate in candidate_set["ranked_candidates"]] == list(
        range(1, len(candidate_set["ranked_candidates"]) + 1)
    )
    assert all({"candidate_id", "features", "legal", "legality_reason"} <= set(candidate) for candidate in candidate_set["candidates"])
    assert all({"candidate_id", "rank", "confidence", "graph_encoding", "expected_usefulness_score"} <= set(candidate) for candidate in candidate_set["ranked_candidates"])
    assert all(candidate["graph_encoding"]["schema_version"] == "logical-compiler-graph-v1" for candidate in candidate_set["ranked_candidates"])
    assert all(candidate["graph_encoding"]["graph_kind"] == "rewrite_candidate" for candidate in candidate_set["ranked_candidates"])


def test_compile_job_indexes_trace_and_rewrite_paths_in_kb(
    grpc_addr: str,
    kb_server: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_KB_GRPC_ENDPOINT", kb_server)
    monkeypatch.setenv("EIGEN_KB_AUTH_TOKEN", "kb-test-token")
    monkeypatch.setenv("EIGEN_KB_SERVICE_IDENTITY", "eigen-compiler")
    monkeypatch.setenv("EIGEN_KB_SERVICE_ROLE", "compiler")
    monkeypatch.setenv("EIGEN_KB_ROLES", "kb:read,kb:write")
    monkeypatch.setenv("EIGEN_KB_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_MODEL_VERSION", "model-2026-06-23")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION", "policy-2026-06-15")

    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    request_metadata = kernel_pb.RequestMetadata()
    request_metadata.contract_version = "1.0.0"
    request_metadata.request_id = "req-kb-001"
    request_metadata.trace_id = "trace-kb-001"
    request_metadata.traceparent = "00-11111111111111111111111111111111-2222222222222222-01"
    request_metadata.deadline.seconds = 60
    request_metadata.retry_policy = "retry-none"
    request_metadata.security_context = "compiler-test"
    request_metadata.tenant_id = "tenant-a"
    request_metadata.project_id = "project-a"
    request_metadata.workload.kind = kernel_pb.WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW
    request_metadata.workload.execution_profile = "hybrid"
    request_metadata.workload.backend_target = "sim:local"

    resp = stub.CompileJob(
        comp_pb.CompileJobRequest(
            job_id="job-kb-001",
            language="eigen-lang",
            source=(
                b"from eigen_lang import hybrid_program, ry\n\n"
                b"@hybrid_program(target=\"sim\", shots=1000)\n"
                b"def main():\n"
                b"    ry(0, theta=1.0)\n"
            ),
            request_metadata=request_metadata,
        )
    )

    candidate_set = json.loads(resp.metadata["symbolic_candidate_set_json"])
    assert candidate_set["candidate_count"] >= 2
    selected = next(
        candidate["candidate_id"]
        for candidate in candidate_set["candidates"]
        if candidate["legal"] and candidate.get("features", {}).get("candidate_kind") == "terminal_measurement_normalized"
    )
    rejected = next(candidate["candidate_id"] for candidate in candidate_set["candidates"] if candidate["candidate_id"] != selected)

    trace_payload = _trace_digest_payload(
        rpc="CompileJob",
        request_id=request_metadata.request_id,
        trace_id=request_metadata.trace_id,
        source_sha256=resp.metadata["source_sha256"],
        request_sha256=resp.metadata["request_sha256"],
        aqo_sha256=resp.metadata["aqo_sha256"],
        pattern_signature=selected,
        compiler_status="success",
        compiler_replay_sha256=resp.metadata["compiler_replay_sha256"],
        compiler_diagnostics_sha256=hashlib.sha256(resp.metadata["compiler_diagnostics_json"].encode("utf-8")).hexdigest(),
    )
    trace_digest = hashlib.sha256(_stable_json(trace_payload).encode("utf-8")).hexdigest()

    from eigen.api.v1 import knowledge_base_service_pb2 as kb_pb
    from eigen.api.v1 import knowledge_base_service_pb2_grpc as kb_pb_grpc
    from eigen.api.v1 import types_pb2 as api_types_pb2

    kb_channel = grpc.insecure_channel(kb_server)
    kb_stub = kb_pb_grpc.KnowledgeBaseServiceStub(kb_channel)
    envelope = kb_pb.ApiContractEnvelope(
        contract_version="1.0.0",
        request=api_types_pb2.ApiRequestEnvelope(
            contract_version="1.0.0",
            request_id=request_metadata.request_id,
            tenant_id="tenant-a",
            project_id="project-a",
            client_version="eigen-compiler/1.0.0",
            traceparent=request_metadata.traceparent,
        ),
    )

    records = kb_stub.QueryRecords(
        kb_pb.QueryRecordsRequest(
            envelope=envelope,
            filter=kb_pb.QueryFilter(
                trace_id=request_metadata.trace_id,
                trace_digest_sha256=trace_digest,
                pattern_signature=selected,
            ),
            page_size=10,
        )
    )
    assert [record.record_id for record in records.records] == [records.records[0].record_id]
    assert records.records[0].attributes["trace_digest_sha256"] == trace_digest
    assert records.records[0].attributes["pattern_signature"] == selected
    assert records.records[0].attributes["compiler_status"] == "success"
    assert json.loads(records.records[0].attributes["accepted_rewrite_ids"]) == [selected]
    assert rejected in json.loads(records.records[0].attributes["rejected_rewrite_ids"])

    accepted_logs = kb_stub.QueryDecisionLogs(
        kb_pb.QueryDecisionLogsRequest(
            envelope=envelope,
            trace_id=request_metadata.trace_id,
            trace_digest_sha256=trace_digest,
            pattern_signature=selected,
            model_version="model-2026-06-23",
            page_size=10,
        )
    )
    assert len(accepted_logs.decision_logs) == 1
    assert accepted_logs.decision_logs[0].selected_action == selected
    assert accepted_logs.decision_logs[0].feature_snapshot["rewrite_outcome"] == "accepted"
    assert accepted_logs.decision_logs[0].feature_snapshot["trace_digest_sha256"] == trace_digest

    rejected_logs = kb_stub.QueryDecisionLogs(
        kb_pb.QueryDecisionLogsRequest(
            envelope=envelope,
            trace_id=request_metadata.trace_id,
            trace_digest_sha256=trace_digest,
            pattern_signature=rejected,
            model_version="model-2026-06-23",
            page_size=10,
        )
    )
    assert len(rejected_logs.decision_logs) == 1
    assert rejected_logs.decision_logs[0].selected_action == rejected
    assert rejected_logs.decision_logs[0].feature_snapshot["rewrite_outcome"] == "rejected"
    assert rejected_logs.decision_logs[0].feature_snapshot["trace_digest_sha256"] == trace_digest


def test_compile_job_uses_request_metadata_workload_profile(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    request_metadata = kernel_pb.RequestMetadata()
    request_metadata.contract_version = "1.0.0"
    request_metadata.request_id = "req-hybrid-001"
    request_metadata.trace_id = "trace-hybrid-001"
    request_metadata.traceparent = "00-11111111111111111111111111111111-2222222222222222-01"
    request_metadata.deadline.seconds = 60
    request_metadata.retry_policy = "retry-none"
    request_metadata.security_context = "compiler-test"
    request_metadata.tenant_id = "tenant-a"
    request_metadata.project_id = "project-a"
    request_metadata.workload.kind = kernel_pb.WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW
    request_metadata.workload.execution_profile = "hybrid"
    request_metadata.workload.backend_target = "sim:local"

    resp = stub.CompileJob(
        comp_pb.CompileJobRequest(
            job_id="job-hybrid-001",
            language="eigen-lang",
            source=(
                b"from eigen_lang import hybrid_program, ry\n\n"
                b"@hybrid_program(target=\"sim\", shots=1000)\n"
                b"def main():\n"
                b"    ry(0, theta=1.0)\n"
            ),
            request_metadata=request_metadata,
        )
    )

    diagnostics = json.loads(resp.metadata["compiler_diagnostics_json"])
    replay = json.loads(resp.metadata["compiler_replay_json"])
    candidate_set = json.loads(resp.metadata["symbolic_candidate_set_json"])
    assert resp.metadata["workload_profile"] == "HybridWorkflow"
    assert diagnostics["workload_profile"] == "HybridWorkflow"
    assert replay["replay_mode"] == "deterministic"
    assert diagnostics["symbolic_candidate_set"] == candidate_set
    assert replay["symbolic_candidate_set"]["candidate_count"] == candidate_set["candidate_count"]
    assert [rule["rule"] for rule in replay["symbolic_rules"]] == [
        "compiler.source.lower_to_ir",
        "compiler.rewrite.terminal_measurement",
        "compiler.aqo.validate",
        "compiler.aqo.canonicalize",
    ]


def test_compile_circuit_exposes_diagnostics_payload(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)
    resp = stub.CompileCircuit(comp_pb.CompileCircuitRequest(language="eigen-lang", source=b"from eigen_lang import hybrid_program\n@hybrid_program(target=\"sim\")\ndef main():\n    ry(0, theta=1.0)\n"))
    diagnostics = json.loads(resp.metadata["compiler_diagnostics_json"])
    replay = diagnostics["replay"]
    assert diagnostics["contract_version"] == "1.0.0"
    assert diagnostics["stage_order"] == ["parse", "validate_ast", "annotate", "lower_to_ir", "eigen_dpda", "canonicalize_aqo", "emit"]
    assert diagnostics["backend_contract"]["backend_target_class"] == "implicit"
    assert diagnostics["explainability"]["decision"] == "compiler_to_optimizer_handoff"
    assert replay["replay_mode"] == "deterministic"
    assert set(replay["model_snapshot"]) == {"model_version", "policy_snapshot_version"}


def test_compile_circuit_emits_distributed_metadata_hints(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    resp = stub.CompileCircuit(
        comp_pb.CompileCircuitRequest(
            language="eigen-lang",
            source=(
                b"from eigen_lang import hybrid_program\n\n"
                b"@hybrid_program()\n"
                b"def main():\n"
                b"    ry(0, theta=1.0)\n"
            ),
            options={
                "distributed.enabled": "true",
                "distributed.target": "cluster",
                "distributed.partition_count": "8",
                "distributed.queue_provider": "redis",
                "distributed.topology_hint": "data_parallel",
            },
        )
    )

    assert resp.metadata["distributed.execution_metadata_version"] == "1.0.0"
    assert resp.metadata["distributed.topology_hints_version"] == "1.0.0"
    assert resp.metadata["distributed.enabled"] == "true"
    assert resp.metadata["workload_profile"] == "DistributedJob"
    assert resp.metadata["distributed.target"] == "cluster"
    assert resp.metadata["distributed.partition_count"] == "8"
    assert resp.metadata["distributed.queue_provider"] == "redis"
    assert resp.metadata["distributed.topology_hint"] == "data_parallel"


def test_compile_circuit_accepts_cluster_auto_distributed_target(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    resp = stub.CompileCircuit(
        comp_pb.CompileCircuitRequest(
            language="eigen-lang",
            source=(
                b"from eigen_lang import hybrid_program\n\n"
                b"@hybrid_program()\n"
                b"def main():\n"
                b"    ry(0, theta=1.0)\n"
            ),
            options={
                "distributed.enabled": "true",
                "distributed.target": "cluster:auto",
                "distributed.partition_count": "8",
                "distributed.queue_provider": "redis",
                "distributed.topology_hint": "data_parallel",
            },
        )
    )

    assert resp.metadata["distributed.enabled"] == "true"
    assert resp.metadata["distributed.target"] == "cluster:auto"
    assert resp.metadata["workload_profile"] == "DistributedJob"


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


def test_compile_circuit_rejects_forbidden_import(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=b"import os\nfrom eigen_lang import *\n",
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"source"}


def test_compile_circuit_enforces_source_size_limit(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_COMPILER_MAX_SOURCE_BYTES", "12")
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(language="eigen-lang", source=b"from eigen_lang import *")
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"source"}


def test_compile_circuit_rejects_invalid_syntax(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=b"from eigen_lang import hybrid_program\n\ndef broken(:\n    pass\n",
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"source"}

def test_compile_circuit_requires_single_hybrid_program_entrypoint(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=(
                    b"from eigen_lang import hybrid_program\n\n"
                    b"def not_entrypoint():\n"
                    b"    ry(0, theta=1.0)\n"
                ),
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert {v.field for v in bad.field_violations} == {"source"}
    assert any("exactly one @hybrid_program entrypoint is required" in v.description for v in bad.field_violations)


def test_compile_circuit_returns_structured_violations(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=(
                    b"import os\n\n"
                    b"def bad_program():\n"
                    b"    eval('1+1')\n"
                    b"    os.system('echo hi')\n"
                ),
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert len(bad.field_violations) >= 3
    descriptions = [v.description for v in bad.field_violations]
    assert any("import 'os'" in desc for desc in descriptions)
    assert any("call 'eval'" in desc for desc in descriptions)
    assert any("dynamic I/O call 'os.system'" in desc for desc in descriptions)


def test_compile_circuit_rejects_unsupported_distributed_config(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=(
                    b"from eigen_lang import hybrid_program\n\n"
                    b"@hybrid_program()\n"
                    b"def main():\n"
                    b"    ry(0, theta=1.0)\n"
                ),
                options={
                    "distributed.enabled": "false",
                    "distributed.target": "cluster",
                    "distributed.partition_count": "0",
                    "distributed.queue_provider": "unknown",
                    "distributed.topology_hint": "mesh",
                },
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    assert [v.field for v in bad.field_violations] == [
        "options.distributed.partition_count",
        "options.distributed.queue_provider",
        "options.distributed.topology_hint",
        "options.distributed.target",
        "options.distributed.partition_count",
        "options.distributed.queue_provider",
        "options.distributed.topology_hint",
    ]


def test_compile_circuit_rejects_backend_target_mismatch(grpc_addr: str) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=(
                    b"from eigen_lang import hybrid_program\n\n"
                    b"@hybrid_program()\n"
                    b"def main():\n"
                    b"    ry(0, theta=1.0)\n"
                ),
                options={
                    "spec.workload.kind": "DistributedJob",
                    "distributed.enabled": "true",
                    "distributed.target": "cluster",
                    "distributed.partition_count": "2",
                    "spec.workload.backend_target": "sim:local",
                },
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    info = _extract_error_info(e.value)
    fields = {v.field for v in bad.field_violations}
    assert "options.spec.workload.backend_target" in fields
    descriptions = [v.description for v in bad.field_violations]
    assert info.metadata["stage"] == "eigen_dpda"
    assert info.metadata["rule"] == "compiler.profile.distributed.target_mismatch"
    diagnostics = json.loads(info.metadata["diagnostics_json"])
    assert diagnostics[0]["stage"] == "eigen_dpda"
    assert diagnostics[0]["rule"] == "compiler.profile.distributed.target_mismatch"
    assert any("distributed backend target" in v.description or "unsupported backend target" in v.description for v in bad.field_violations)


@pytest.mark.parametrize(
    "options,expected_fields,expected_snippet",
    [
        (
            {
                "workload.kind": "BenchmarkJob",
                "spec.workload.backend_target": "sim:local",
            },
            {"options.spec.workload.seed"},
            "BenchmarkJob requires spec.workload.seed",
        ),
        (
            {
                "workload.kind": "ReplayJob",
                "spec.workload.replay.enabled": "true",
            },
            {"source_ref"},
            "ReplayJob requires source_ref",
        ),
        (
            {
                "workload.kind": "PipelineJob",
                "spec.workload.pipeline.stage_id": "stage-1",
            },
            {"options.spec.workload.pipeline.handoff_ref", "source_ref"},
            "PipelineJob requires",
        ),
    ],
)
def test_compile_circuit_rejects_profile_specific_constraints(
    grpc_addr: str,
    options: dict[str, str],
    expected_fields: set[str],
    expected_snippet: str,
) -> None:
    channel = grpc.insecure_channel(grpc_addr)
    stub = comp_pb_grpc.CompilationServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.CompileCircuit(
            comp_pb.CompileCircuitRequest(
                language="eigen-lang",
                source=(
                    b"from eigen_lang import hybrid_program\n\n"
                    b"@hybrid_program()\n"
                    b"def main():\n"
                    b"    ry(0, theta=1.0)\n"
                ),
                options=options,
            )
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    bad = _extract_bad_request(e.value)
    info = _extract_error_info(e.value)
    assert expected_fields <= {v.field for v in bad.field_violations}
    assert any(expected_snippet in v.description for v in bad.field_violations)
    assert info.metadata["stage"] in {"request_validation", "eigen_dpda"}
    assert info.metadata["rule"]
    diagnostics = json.loads(info.metadata["diagnostics_json"])
    assert diagnostics


def _nsc_request(
    *,
    contract_version: str = "1.0.0",
    request_id: str = "req-nsc-001",
    tenant_id: str = "tenant-a",
    project_id: str = "project-a",
    feature_schema_version: str = "features.v1",
    policy_snapshot_version: str = "policy-2026-06-15",
    subject_id: str = "subject-007",
    workload_id: str = "workload-compiler-01",
    authz_decision_id: str = "authz-dec-abc123",
    feature_vector: bytes = b'{"redacted":true,"signals":[1,2,3]}',
    feature_digest_sha256: str | None = None,
    deterministic_seed: int = 7,
    model_hint: str = "dpda",
) -> nsc_pb.ScoreCompilationPlanRequest:
    return nsc_pb.ScoreCompilationPlanRequest(
        envelope=nsc_pb.NeuroSymbolicContractEnvelope(contract_version=contract_version),
        context=nsc_pb.NeuroSymbolicRequestContext(
            request_id=request_id,
            tenant_id=tenant_id,
            project_id=project_id,
            feature_schema_version=feature_schema_version,
            policy_snapshot_version=policy_snapshot_version,
            trace_id="0123456789abcdef0123456789abcdef",
            traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
            subject_id=subject_id,
            workload_id=workload_id,
            authz_decision_id=authz_decision_id,
        ),
        feature_vector=feature_vector,
        feature_digest_sha256=feature_digest_sha256 or hashlib.sha256(feature_vector).hexdigest(),
        deterministic_seed=deterministic_seed,
        model_hint=model_hint,
    )


def _nsc_metadata(tenant_id: str = "tenant-a", project_id: str = "project-a") -> tuple[tuple[str, str], ...]:
    return (
        ("authorization", "Bearer unit-test-token"),
        ("x-eigen-service-id", "eigen-kernel"),
        ("x-eigen-tenant-id", tenant_id),
        ("x-eigen-project-id", project_id),
    )


def _nsc_metadata(
    *,
    tenant_id: str = "tenant-a",
    project_id: str = "project-a",
    authorization: str = "Bearer unit-test-token",
    service_id: str = "eigen-kernel",
) -> tuple[tuple[str, str], ...]:
    return (
        ("authorization", authorization),
        ("x-eigen-service-id", service_id),
        ("x-eigen-tenant-id", tenant_id),
        ("x-eigen-project-id", project_id),
    )


class _FakeServicerRpcError(grpc.RpcError):
    def __init__(self, code: grpc.StatusCode, details: str):
        super().__init__()
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


class _FakeServicerContext:
    def __init__(self, metadata: tuple[tuple[str, str], ...]):
        self._metadata = metadata

    def invocation_metadata(self):
        return self._metadata

    def abort(self, code, details):
        raise _FakeServicerRpcError(code, details)


def test_neuro_symbolic_service_scores_internal_requests(grpc_addr: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_MODEL_VERSION", "dpda-model-unit-test")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    resp = stub.ScoreCompilationPlan(
         _nsc_request(),
        metadata=_nsc_metadata()
    )

    assert resp.contract_version == "1.0.0"
    assert resp.request_id == "req-nsc-001"
    assert resp.tenant_id == "tenant-a"
    assert resp.project_id == "project-a"
    assert resp.feature_schema_version == "features.v1"
    assert resp.policy_snapshot_version == "policy-2026-06-15"
    assert resp.model_version == "dpda-model-unit-test"
    assert resp.decision in {
        nsc_pb.ADVISORY_DECISION_ACCEPT,
        nsc_pb.ADVISORY_DECISION_REVIEW,
        nsc_pb.ADVISORY_DECISION_REJECT,
    }
    assert 0.0 <= resp.score <= 1.0
    assert 0.55 <= resp.confidence <= 0.99
    assert resp.explanation_ref.startswith("nsc://explanations/req-nsc-001/")
    assert len(resp.replay_digest) == 64
    assert resp.deterministic_compatible is True


def test_neuro_symbolic_service_fails_closed_without_internal_identity(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.ScoreCompilationPlan(
            _nsc_request(),
            metadata=(
                ("x-eigen-service-id", "eigen-kernel"),
                ("x-eigen-tenant-id", "tenant-a"),
                ("x-eigen-project-id", "project-a"),
            ),
        )

    assert e.value.code() == grpc.StatusCode.UNAUTHENTICATED


def test_neuro_symbolic_service_rejects_unsupported_contract_version(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.ScoreCompilationPlan(
            _nsc_request(contract_version="2.0.0"),
            metadata=_nsc_metadata(),
        )

    assert e.value.code() == grpc.StatusCode.FAILED_PRECONDITION


def test_neuro_symbolic_service_rejects_tenant_project_scope_mismatch(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.ScoreCompilationPlan(
            _nsc_request(),
            metadata=(
                ("authorization", "Bearer unit-test-token"),
                ("x-eigen-service-id", "eigen-kernel"),
                ("x-eigen-tenant-id", "tenant-b"),
                ("x-eigen-project-id", "project-b"),
            ),
        )

    assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED


def test_neuro_symbolic_feature_redaction_masks_sensitive_values() -> None:
    raw_feature_vector = json.dumps(
        {
            "authorization": "Bearer sk-test-secret-token",
            "api_key": "sk-live-1234567890",
            "credentials": {
                "session_cookie": "sessionid=abc123",
                "password": "super-secret-password",
            },
            "contact": {
                "email": "alice@example.com",
                "phone": "+1 (555) 123-4567",
            },
            "internal_id": "7e3b7e77-4b2d-4c85-a8f5-0d9307cc0a11",
            "signals": [{"label": "ok"}],
        },
        sort_keys=True,
    ).encode("utf-8")

    result = _redact_feature_vector(raw_feature_vector)
    decoded = json.loads(result.feature_vector.decode("utf-8"))

    assert decoded["authorization"] == "[REDACTED]"
    assert decoded["api_key"] == "[REDACTED]"
    assert decoded["credentials"] == "[REDACTED]"
    assert decoded["contact"]["email"] == "[REDACTED_EMAIL]"
    assert decoded["contact"]["phone"] == "[REDACTED_PHONE]"
    assert decoded["internal_id"] == "[REDACTED_ID]"
    assert all(secret not in result.feature_vector.decode("utf-8") for secret in [
        "sk-test-secret-token",
        "alice@example.com",
        "+1 (555) 123-4567",
        "7e3b7e77-4b2d-4c85-a8f5-0d9307cc0a11",
    ])
    assert any(field.endswith(":deleted") for field in result.redacted_fields)
    assert any(field.endswith(":masked_email") for field in result.redacted_fields)
    assert any(field.endswith(":masked_phone") for field in result.redacted_fields)
    assert any(field.endswith(":masked_identifier") for field in result.redacted_fields)


def test_neuro_symbolic_feature_redaction_removes_stack_traces_endpoints_paths_and_sensitive_headers() -> None:
    raw_feature_vector = json.dumps(
        {
            "diagnostics": "Traceback (most recent call last):\n  File \"/app/main.py\", line 12, in run\n    raise RuntimeError('boom')",
            "callback_url": "grpc://internal-api.svc.cluster.local:8443/v1/compile",
            "artifact_path": "/var/lib/eigen/secret/pipelines/private/server.key",
            "header_blob": "Authorization: Bearer sk-test-secret-token\nX-API-Key: sk-live-1234567890\nX-Auth-Token: token-abcdef123456",
            "signals": [{"label": "ok"}],
        },
        sort_keys=True,
    ).encode("utf-8")

    result = _redact_feature_vector(raw_feature_vector)
    decoded = json.loads(result.feature_vector.decode("utf-8"))

    assert decoded["diagnostics"] == "[REDACTED]"
    assert decoded["callback_url"] == "[REDACTED]"
    assert decoded["artifact_path"] == "[REDACTED]"
    assert all(line == "[REDACTED]" for line in decoded["header_blob"].splitlines())

    rendered = result.feature_vector.decode("utf-8")
    assert "Traceback (most recent call last):" not in rendered
    assert "internal-api.svc.cluster.local" not in rendered
    assert "server.key" not in rendered
    assert "sk-test-secret-token" not in rendered
    assert "sk-live-1234567890" not in rendered
    assert any(field.endswith(":deleted") for field in result.redacted_fields)
    assert any(field.endswith(":masked_endpoint") for field in result.redacted_fields)
    assert any(field.endswith(":masked_path") for field in result.redacted_fields)
    assert any(field.endswith(":masked_header") for field in result.redacted_fields)


def test_compile_eigen_lang_redacts_security_context_in_metadata() -> None:
    result = compile_eigen_lang(
        source=(
            b"from eigen_lang import hybrid_program\n\n"
            b"@hybrid_program()\n"
            b"def main():\n"
            b"    ry(0, theta=1.0)\n"
        ),
        request_context={
            "request_id": "req-1",
            "trace_id": "0123456789abcdef0123456789abcdef",
            "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
            "deadline": "5s",
            "retry_policy": "none",
            "security_context": "authorization: Bearer sk-test-secret-token",
            "sandbox_profile": "strict",
            "tenant_id": "tenant-a",
            "project_id": "project-a",
        },
    )

    assert result.metadata["security_context"] == "[REDACTED]"
    assert "sk-test-secret-token" not in result.metadata["request_context_json"]


def test_neuro_symbolic_service_redacts_sensitive_feature_payload(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_MODEL_VERSION", "dpda-model-unit-test")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION", "policy-2026-06-15")
    caplog.set_level(logging.INFO, logger="eigen_compiler")

    raw_feature_vector = json.dumps(
        {
            "authorization": "Bearer sk-test-secret-token",
            "api_key": "sk-live-1234567890",
            "contact": {
                "email": "alice@example.com",
                "phone": "+1 (555) 123-4567",
            },
            "internal_id": "7e3b7e77-4b2d-4c85-a8f5-0d9307cc0a11",
            "signals": [{"label": "ok"}],
        },
        sort_keys=True,
    ).encode("utf-8")

    redacted = _redact_feature_vector(raw_feature_vector)

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)
    resp = stub.ScoreCompilationPlan(
        _nsc_request(
            feature_vector=raw_feature_vector,
            feature_digest_sha256=hashlib.sha256(redacted.feature_vector).hexdigest(),
        ),
        metadata=_nsc_metadata()
    )

    redacted = _redact_feature_vector(raw_feature_vector)
    assert len(resp.replay_digest) == 64
    int(resp.replay_digest, 16)

    repeat = stub.ScoreCompilationPlan(
        _nsc_request(
            feature_vector=raw_feature_vector,
            feature_digest_sha256=hashlib.sha256(redacted.feature_vector).hexdigest(),
        ),
        metadata=_nsc_metadata()
    )

    assert repeat.replay_digest == resp.replay_digest
    assert resp.policy_snapshot_version == "policy-2026-06-15"
    assert resp.model_version == "dpda-model-unit-test"

    scoring_logs = [record for record in caplog.records if record.getMessage() == "neuro-symbolic scoring completed"]
    assert scoring_logs, "expected a scoring log record"
    record = scoring_logs[-1]
    assert "feature_redaction_fields" in record.__dict__
    assert record.feature_redaction_count == len(redacted.redacted_fields)
    assert any(field.endswith(":deleted") for field in record.feature_redaction_fields)
    assert any(field.endswith(":masked_email") for field in record.feature_redaction_fields)
    assert any(field.endswith(":masked_phone") for field in record.feature_redaction_fields)
    assert any(field.endswith(":masked_identifier") for field in record.feature_redaction_fields)


def test_neuro_symbolic_service_minimizes_payload_before_scoring(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_MODEL_VERSION", "dpda-model-unit-test")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION", "policy-2026-06-15")
    caplog.set_level(logging.INFO, logger="eigen_compiler")

    raw_feature_vector = json.dumps(
        {
            "normalized_features": {
                "candidate_count": 4,
                "stage_count": 7,
            },
            "request_body": {
                "source": "def main(): pass",
                "arguments": ["--unsafe", "--debug"],
            },
            "trace_dump": "TRACE-" + ("x" * 1024),
            "stack_trace": "STACK-" + ("y" * 1024),
            "raw_payload": {
                "bytes": "z" * 2048,
            },
            "signals": [{"label": "ok"}],
        },
        sort_keys=True,
    ).encode("utf-8")
    minimized = _redact_feature_vector(raw_feature_vector)

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    resp = stub.ScoreCompilationPlan(
        _nsc_request(
            feature_vector=raw_feature_vector,
            feature_digest_sha256=hashlib.sha256(minimized.feature_vector).hexdigest(),
        ),
        metadata=_nsc_metadata()
    )

    variant_feature_vector = json.dumps(
        {
            "normalized_features": {
                "candidate_count": 4,
                "stage_count": 7,
            },
            "request_body": {
                "source": "def main(): pass",
                "arguments": ["--very-verbose", "--another-debug-flag"],
            },
            "trace_dump": "TRACE-" + ("a" * 4096),
            "stack_trace": "STACK-" + ("b" * 4096),
            "raw_payload": {
                "bytes": "c" * 8192,
            },
            "signals": [{"label": "ok"}],
        },
        sort_keys=True,
    ).encode("utf-8")
    variant_minimized = _redact_feature_vector(variant_feature_vector)

    assert variant_minimized.feature_vector == minimized.feature_vector

    repeat = stub.ScoreCompilationPlan(
        _nsc_request(
            feature_vector=variant_feature_vector,
            feature_digest_sha256=hashlib.sha256(variant_minimized.feature_vector).hexdigest(),
        ),
        metadata=_nsc_metadata(),
    )

    assert repeat.replay_digest == resp.replay_digest

    scoring_logs = [record for record in caplog.records if record.getMessage() == "neuro-symbolic scoring completed"]
    assert scoring_logs, "expected a scoring log record"
    record = scoring_logs[-1]
    assert record.feature_payload_bytes > record.feature_payload_minimized_bytes
    assert record.feature_payload_limit_bytes >= record.feature_payload_minimized_bytes
    assert any(field.endswith("request_body:deleted") for field in record.feature_redaction_fields)
    assert any(field.endswith("trace_dump:deleted") for field in record.feature_redaction_fields)
    assert any(field.endswith("stack_trace:deleted") for field in record.feature_redaction_fields)
    assert any(field.endswith("raw_payload:deleted") for field in record.feature_redaction_fields)


def test_neuro_symbolic_service_enforces_policy_feature_payload_limit(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_MAX_FEATURE_VECTOR_BYTES", "64")

    oversized = json.dumps(
        {
            "normalized_features": {
                "feature_a": "x" * 256,
                "feature_b": "y" * 256,
            },
            "signals": [{"label": "ok"}],
        },
        sort_keys=True,
    ).encode("utf-8")
    oversized_minimized = _redact_feature_vector(oversized)

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with pytest.raises(grpc.RpcError) as e:
        stub.ScoreCompilationPlan(
            _nsc_request(
                feature_vector=oversized,
                feature_digest_sha256=hashlib.sha256(oversized_minimized.feature_vector).hexdigest(),
            ),
            metadata=_nsc_metadata(),
        )

    assert e.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED


def test_neuro_symbolic_service_rejects_digest_mismatch(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    bad = _nsc_request(
        feature_vector=b'{"redacted":true,"signals":[1,2,4]}',
        feature_digest_sha256="0" * 64,
    )

    with pytest.raises(grpc.RpcError) as e:
        stub.ScoreCompilationPlan(
            bad,
            metadata=_nsc_metadata(),
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_neuro_symbolic_service_uses_frozen_policy_snapshot_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION", "policy-locked-1")

    # Instantiate the concrete implementation directly so the frozen snapshot can be verified in-process.
    from eigen_compiler.grpc_impl import NeuroSymbolicService

    svc = NeuroSymbolicService(nsc_pb=nsc_pb)
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_POLICY_SNAPSHOT_VERSION", "policy-locked-2")

    resp = svc.ScoreCompilationPlan(
        _nsc_request(policy_snapshot_version="policy-locked-1"),
        _FakeServicerContext(_nsc_metadata()),
    )

    assert resp.policy_snapshot_version == "policy-locked-1"

    with pytest.raises(_FakeServicerRpcError) as e:
        svc.ScoreCompilationPlan(
            _nsc_request(policy_snapshot_version="policy-locked-2"),
            _FakeServicerContext(_nsc_metadata()),
        )

    assert e.value.code() == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.parametrize(
    ("field_name", "mutator"),
    [
        ("tenant_id", lambda req: setattr(req.context, "tenant_id", "")),
        ("project_id", lambda req: setattr(req.context, "project_id", "")),
        ("subject_id", lambda req: setattr(req.context, "subject_id", "")),
        ("workload_id", lambda req: setattr(req.context, "workload_id", "")),
        ("policy_snapshot_version", lambda req: setattr(req.context, "policy_snapshot_version", "")),
        ("authz_decision_id", lambda req: setattr(req.context, "authz_decision_id", "")),
    ],
)
def test_neuro_symbolic_service_rejects_missing_security_context_field(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    mutator,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    request = _nsc_request()
    mutator(request)

    with pytest.raises(grpc.RpcError) as e:
        stub.ScoreCompilationPlan(
            request,
            metadata=_nsc_metadata(),
        )

    assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert f"context.{field_name} is required" in e.value.details()


def test_neuro_symbolic_service_audits_security_context(
    grpc_addr: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_SERVICE_TOKEN", "unit-test-token")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_ALLOWED_CALLERS", "eigen-kernel,eigen-compiler")
    monkeypatch.setenv("EIGEN_NEURO_SYMBOLIC_MODEL_VERSION", "dpda-model-unit-test")

    channel = grpc.insecure_channel(grpc_addr)
    stub = nsc_pb_grpc.NeuroSymbolicServiceStub(channel)

    with caplog.at_level("INFO", logger="eigen_compiler"):
        resp = stub.ScoreCompilationPlan(
            _nsc_request(),
            metadata=_nsc_metadata(),
        )

    records = [record for record in caplog.records if getattr(record, "rpc", "") == "ScoreCompilationPlan"]
    assert records
    record = records[-1]
    assert getattr(record, "subject_id") == "subject-007"
    assert getattr(record, "workload_id") == "workload-compiler-01"
    assert getattr(record, "authz_decision_id") == "authz-dec-abc123"
    assert getattr(record, "tenant_id") == "tenant-a"
    assert getattr(record, "project_id") == "project-a"
    assert getattr(record, "policy_snapshot_version") == "policy-2026-06-15"

    envelope = getattr(record, "explainability_envelope")
    assert envelope["model_version"] == "dpda-model-unit-test"
    assert envelope["feature_set"]["schema_version"] == "features.v1"
    assert envelope["feature_set"]["feature_digest_sha256"] == hashlib.sha256(b'{"redacted":true,"signals":[1,2,3]}').hexdigest()
    assert envelope["confidence"] == resp.confidence
    assert envelope["explanation_ref"] == resp.explanation_ref
    assert envelope["retrieval_reference_count"] == 3
    assert envelope["retrieval_references"] == [
        "nsc://feature-set/tenant-a/project-a/req-nsc-001/" + hashlib.sha256(b'{"redacted":true,"signals":[1,2,3]}').hexdigest(),
        "nsc://policy-snapshot/policy-2026-06-15",
        "nsc://model/dpda-model-unit-test",
    ]
    assert getattr(record, "explainability_envelope_json")
