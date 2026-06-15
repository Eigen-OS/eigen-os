from __future__ import annotations

import json
from types import SimpleNamespace

from system_api.grpc_impl import JobService, QFS_STORE


def _eigen_lang_request(source: bytes):
    return SimpleNamespace(
        WhichOneof=lambda name: "eigen_lang" if name == "program" else None,
        eigen_lang=SimpleNamespace(source=source),
        aqo_ref=SimpleNamespace(qfs_ref=""),
    )


def test_provision_temporary_artifacts_writes_non_empty_aqo(monkeypatch):
    service = JobService.__new__(JobService)

    written: dict[str, bytes] = {}

    def _capture_put(ref: str, payload: bytes) -> None:
        written[ref] = payload

    monkeypatch.setattr(QFS_STORE, "put_bytes", _capture_put)

    record = SimpleNamespace(
        job_id="job-1",
        results_metadata={"qfs_compiled_aqo": "qfs://jobs/job-1/compiled/circuit.aqo.json"},
        temp_refs=[],
    )
    request = _eigen_lang_request(
        b"from eigen_lang import hybrid_program\n\n"
        b"@hybrid_program()\n"
        b"def main():\n"
        b"    ry(0, theta=1.0)\n"
    )

    service._provision_temporary_artifacts(record, request)

    aqo = json.loads(written["qfs://jobs/job-1/compiled/circuit.aqo.json"].decode("utf-8"))
    assert aqo["version"] == "1.0.0"
    assert aqo["operations"], "compiled AQO must not be empty"
    assert aqo["operations"][0]["op"] == "RY"
    assert aqo["operations"][-1]["op"] == "MEASURE"
    