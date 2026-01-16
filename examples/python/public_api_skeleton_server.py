"""Minimal public gRPC API skeleton server (MVP).

This is NOT a production server.
It exists to prove that generated stubs can be imported and wired into a gRPC server.

Run (from repo root):

  python -m pip install grpcio grpcio-tools protobuf
  bash scripts/dev/generate-protos.sh
  python examples/python/public_api_skeleton_server.py
"""

from __future__ import annotations

import sys
from concurrent import futures
from pathlib import Path

import grpc

# Make generated code importable.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "gen" / "python"))

from eigen_api.v1 import device_service_pb2, device_service_pb2_grpc
from eigen_api.v1 import job_service_pb2, job_service_pb2_grpc


class JobService(job_service_pb2_grpc.JobServiceServicer):
    def SubmitJob(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "SubmitJob is not implemented (skeleton server)")

    def GetJobStatus(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetJobStatus is not implemented (skeleton server)")

    def CancelJob(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CancelJob is not implemented (skeleton server)")

    def StreamJobUpdates(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "StreamJobUpdates is not implemented (skeleton server)")
        yield job_service_pb2.JobUpdate()  # unreachable

    def GetJobResults(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetJobResults is not implemented (skeleton server)")


class DeviceService(device_service_pb2_grpc.DeviceServiceServicer):
    def ListDevices(self, request, context):
        return device_service_pb2.ListDevicesResponse(devices=[])

    def GetDeviceDetails(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetDeviceDetails is not implemented (skeleton server)")

    def GetDeviceStatus(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetDeviceStatus is not implemented (skeleton server)")

    def ReserveDevice(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ReserveDevice is not implemented (skeleton server)")


def main() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    job_service_pb2_grpc.add_JobServiceServicer_to_server(JobService(), server)
    device_service_pb2_grpc.add_DeviceServiceServicer_to_server(DeviceService(), server)

    server.add_insecure_port("127.0.0.1:50051")
    server.start()

    print("✅ Public API skeleton server is running on 127.0.0.1:50051")
    print("Press Ctrl+C to stop.")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    main()
