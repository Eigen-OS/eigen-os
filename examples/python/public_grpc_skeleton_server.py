"""Minimal skeleton server for the public Eigen API.

This is NOT production-ready; it exists to prove the generated stubs are usable.

Run:
  python -m pip install grpcio grpcio-tools protobuf
  bash scripts/dev/generate-protos.sh
  python examples/python/public_grpc_skeleton_server.py
"""

from __future__ import annotations

import sys
from concurrent import futures
from pathlib import Path

import grpc

# Make generated stubs importable.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "gen" / "python"))

from eigen_api.v1 import job_service_pb2_grpc
from eigen_api.v1 import device_service_pb2_grpc


class JobService(job_service_pb2_grpc.JobServiceServicer):
    pass


class DeviceService(device_service_pb2_grpc.DeviceServiceServicer):
    pass


def main() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    job_service_pb2_grpc.add_JobServiceServicer_to_server(JobService(), server)
    device_service_pb2_grpc.add_DeviceServiceServicer_to_server(DeviceService(), server)

    server.add_insecure_port("[::]:50051")
    server.start()
    print("✅ Public gRPC skeleton server started on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
