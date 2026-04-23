"""Minimal Eigen-Lang -> AQO JSON compiler for MVP RPC scaffolding."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class CompilationResult:
    aqo_json: bytes
    metadata: dict[str, str]


def compile_eigen_lang(source: bytes, *, source_ref: str | None = None) -> CompilationResult:
    """Compile source bytes into a tiny AQO v0.1 payload.

    This is an MVP stub used to prove RPC contract wiring.
    """

    digest = hashlib.sha256(source).hexdigest() if source else ""
    aqo = {
        "version": "0.1",
        "qubits": 1,
        "operations": [
            {"op": "RY", "q": [0], "params": {"theta": 1.570796}},
            {"op": "MEASURE", "q": [0], "c": [0]},
        ],
    }
    aqo_bytes = json.dumps(aqo, separators=(",", ":"), sort_keys=True).encode("utf-8")

    metadata = {
        "compiler": "eigen-compiler",
        "aqo_version": "0.1",
        "input_bytes": str(len(source)),
        "source_sha256": digest,
    }
    if source_ref:
        metadata["source_ref"] = source_ref

    return CompilationResult(aqo_json=aqo_bytes, metadata=metadata)
