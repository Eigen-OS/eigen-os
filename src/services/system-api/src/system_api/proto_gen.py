"""Protobuf codegen helper for system-api.

Issue #24 requires system-api to be runnable locally.
The protobuf sources live in the repo root under `proto/`.

This module provides a small utility to generate Python gRPC stubs using
`grpcio-tools` when they are missing.

Generated files are written into the *service python src root*:
`src/services/system-api/src/`.

That makes them importable as:
    eigen_api.v1.job_service_pb2
    eigen_api.v1.job_service_pb2_grpc

NOTE: In a production setup we may prefer generating into `gen/python/` and
packaging a separate SDK. For MVP scaffolding, local generation is acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ProtoGenPaths:
    repo_root: Path
    proto_root: Path
    out_dir: Path


def _find_repo_root(start: Path) -> Path:
    """Walk upwards until we find a directory that looks like the repo root."""
    for p in [start, *start.parents]:
        if (p / "proto").is_dir() and (p / "rfcs").is_dir():
            return p
    raise RuntimeError("Could not locate repo root (expected to find proto/ and rfcs/)")


def _grpc_tools_proto_include() -> Path:
    """Return the include dir that contains google/protobuf/*.proto."""
    import importlib.resources

    # grpc_tools ships protos under grpc_tools/_proto
    return Path(importlib.resources.files("grpc_tools").joinpath("_proto"))


def _default_proto_files(proto_root: Path) -> list[Path]:
    """Collect proto files needed for public System API (MVP)."""
    return sorted(
        [
            proto_root / "eigen_api" / "v1" / "types.proto",
            proto_root / "eigen_api" / "v1" / "job_service.proto",
            proto_root / "eigen_api" / "v1" / "device_service.proto",
        ]
    )


def get_paths() -> ProtoGenPaths:
    here = Path(__file__).resolve()
    repo_root = _find_repo_root(here)

    proto_root = repo_root / "proto"
    out_dir = repo_root / "src" / "services" / "system-api" / "src"

    return ProtoGenPaths(repo_root=repo_root, proto_root=proto_root, out_dir=out_dir)


def ensure_generated(files: Iterable[Path] | None = None) -> None:
    """Generate python stubs if they're missing."""
    paths = get_paths()
    if files is None:
        files = _default_proto_files(paths.proto_root)

    # Heuristic: check a representative output file.
    sentinel = paths.out_dir / "eigen_api" / "v1" / "job_service_pb2.py"
    if sentinel.exists():
        return

    try:
        from grpc_tools import protoc
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "grpcio-tools is required to generate protobuf stubs. "
            "Install it into the system-api environment."
        ) from e

    grpc_inc = _grpc_tools_proto_include()
    cmd = [
        "protoc",
        f"-I{paths.proto_root}",
        f"-I{grpc_inc}",
        f"--python_out={paths.out_dir}",
        f"--grpc_python_out={paths.out_dir}",
    ] + [str(p.relative_to(paths.proto_root)) for p in files]

    # protoc.main returns 0 on success.
    rc = protoc.main(cmd)
    if rc != 0:  # pragma: no cover
        raise RuntimeError(f"protoc failed with exit code {rc}: {' '.join(cmd)}")
