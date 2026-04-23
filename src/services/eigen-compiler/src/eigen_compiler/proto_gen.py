"""Protobuf codegen helper for eigen-compiler internal API."""

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
    for p in [start, *start.parents]:
        if (p / "proto").is_dir() and ((p / "rfcs").is_dir() or (p / "src" / "services").is_dir()):
            return p
    raise RuntimeError("Could not locate repo root (expected proto/ and either rfcs/ or src/services/)")


def _grpc_tools_proto_include() -> Path:
    import importlib.resources

    return Path(importlib.resources.files("grpc_tools").joinpath("_proto"))


def _default_proto_files(proto_root: Path) -> list[Path]:
    return sorted(
        [
            proto_root / "eigen" / "internal" / "v1" / "types.proto",
            proto_root / "eigen" / "internal" / "v1" / "compilation_service.proto",
        ]
    )


def get_paths() -> ProtoGenPaths:
    here = Path(__file__).resolve()
    repo_root = _find_repo_root(here)
    proto_root = repo_root / "proto"
    out_dir = repo_root / "src" / "services" / "eigen-compiler" / "src"
    return ProtoGenPaths(repo_root=repo_root, proto_root=proto_root, out_dir=out_dir)


def ensure_generated(files: Iterable[Path] | None = None) -> None:
    paths = get_paths()
    if files is None:
        files = _default_proto_files(paths.proto_root)

    sentinel = paths.out_dir / "eigen" / "internal" / "v1" / "compilation_service_pb2.py"
    if sentinel.exists():
        return

    try:
        from grpc_tools import protoc
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "grpcio-tools is required to generate protobuf stubs for eigen-compiler"
        ) from e

    grpc_inc = _grpc_tools_proto_include()
    cmd = [
        "protoc",
        f"-I{paths.proto_root}",
        f"-I{grpc_inc}",
        f"--python_out={paths.out_dir}",
        f"--grpc_python_out={paths.out_dir}",
    ] + [str(p.relative_to(paths.proto_root)) for p in files]

    rc = protoc.main(cmd)
    if rc != 0:  # pragma: no cover
        raise RuntimeError(f"protoc failed with exit code {rc}: {' '.join(cmd)}")
