"""neuro-symbolic-service entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Sequence

from eigen.api.v1 import knowledge_base_service_pb2 as kb_pb
from eigen.api.v1 import types_pb2 as types_pb

from .grpc_server import serve
from .knowledge_base import KnowledgeBaseService
from .observability import JsonFormatter, start_metrics_server
from .production_trace_training import prepare_training_dataset_manifest


def _load_manifest(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _serve() -> int:
    metrics_port = int(os.getenv("NEURO_SYMBOLIC_METRICS_PORT", "50082"))
    start_metrics_server(metrics_port)
    server = serve()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:  # pragma: no cover
        server.stop(grace=0)
    return 0


def _ingest_dataset(manifest_path: Path, *, caller_identity: str) -> int:
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    summary = service.ingest_training_dataset(_load_manifest(manifest_path), caller_identity=caller_identity)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


def _ingest_production_traces(manifest_path: Path, *, caller_identity: str) -> int:
    service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    bundle = _load_manifest(manifest_path)
    dataset_manifest = prepare_training_dataset_manifest(bundle, caller_identity=caller_identity)
    summary = service.ingest_training_dataset(dataset_manifest, caller_identity=caller_identity)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="neuro-symbolic-service")
    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser("ingest-dataset", help="Ingest a KB-backed training dataset manifest")
    ingest.add_argument("--manifest", required=True, type=Path, help="Path to the dataset manifest JSON")
    ingest.add_argument(
        "--caller-identity",
        default=os.getenv("NEURO_SYMBOLIC_CLI_CALLER_IDENTITY", os.getenv("NEURO_SYMBOLIC_SERVICE_IDENTITY", "neuro-symbolic-service")),
        help="Internal caller identity that must match the manifest ownership",
    )

    production = subparsers.add_parser(
        "ingest-production-traces",
        help="Promote redacted production execution traces into the KB-backed training corpus",
    )
    production.add_argument("--manifest", required=True, type=Path, help="Path to the production trace bundle JSON")
    production.add_argument(
        "--caller-identity",
        default=os.getenv("NEURO_SYMBOLIC_CLI_CALLER_IDENTITY", os.getenv("NEURO_SYMBOLIC_SERVICE_IDENTITY", "neuro-symbolic-service")),
        help="Internal caller identity that must match the manifest ownership",
    )

    parser.add_argument("--log-level", default=os.getenv("NEURO_SYMBOLIC_LOG_LEVEL", "INFO"), help=argparse.SUPPRESS)

    args = parser.parse_args(list(argv) if argv is not None else None)

    level = str(getattr(args, "log_level", os.getenv("NEURO_SYMBOLIC_LOG_LEVEL", "INFO")))
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]

    if args.command == "ingest-dataset":
        return _ingest_dataset(args.manifest, caller_identity=args.caller_identity)
    if args.command == "ingest-production-traces":
        return _ingest_production_traces(args.manifest, caller_identity=args.caller_identity)
    return _serve()


if __name__ == "__main__":
    raise SystemExit(main())
