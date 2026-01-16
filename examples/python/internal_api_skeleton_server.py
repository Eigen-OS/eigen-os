"""Minimal internal gRPC skeleton server (MVP).

This server exposes KernelGateway / DriverManagerService / CompilationService.
It exists to prove generated stubs wiring for internal contracts.

Run (from repo root):

  python -m pip install grpcio grpcio-tools protobuf
  bash scripts/dev/generate-protos.sh
  python examples/python/internal_api_skeleton_server.py
"""

from __future__ import annotations

import sys
from concurrent import futures
from pathlib import Path

import grpc

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "gen" / "python"))

from eigen_internal.v1 import (
    compilation_service_pb2,
    compilation_service_pb2_grpc,
    driver_manager_service_pb2,
    driver_manager_service_pb2_grpc,
    kernel_gateway_pb2,
    kernel_gateway_pb2_grpc,
)


class KernelGateway(kernel_gateway_pb2_grpc.KernelGatewayServicer):
    def EnqueueJob(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "EnqueueJob is not implemented (skeleton server)")

    def GetJobStatus(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetJobStatus is not implemented (skeleton server)")

    def CancelJob(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CancelJob is not implemented (skeleton server)")

    def GetJobResults(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetJobResults is not implemented (skeleton server)")


class DriverManagerService(driver_manager_service_pb2_grpc.DriverManagerServiceServicer):
    def ListDevices(self, request, context):
        return driver_manager_service_pb2.ListDevicesResponse(devices=[])

    def GetDeviceStatus(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "GetDeviceStatus is not implemented (skeleton server)")

    def ExecuteCircuit(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ExecuteCircuit is not implemented (skeleton server)")

    def CalibrateDevice(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CalibrateDevice is not implemented (skeleton server)")


class CompilationService(compilation_service_pb2_grpc.CompilationServiceServicer):
    def CompileCircuit(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "CompileCircuit is not implemented (skeleton server)")

    def OptimizeCircuit(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "OptimizeCircuit is not implemented (skeleton server)")

    def ValidateCircuit(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ValidateCircuit is not implemented (skeleton server)")


def main() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    kernel_gateway_pb2_grpc.add_KernelGatewayServicer_to_server(KernelGateway(), server)
    driver_manager_service_pb2_grpc.add_DriverManagerServiceServicer_to_server(DriverManagerService(), server)
    compilation_service_pb2_grpc.add_CompilationServiceServicer_to_server(CompilationService(), server)

    server.add_insecure_port("127.0.0.1:50052")
    server.start()

    print("✅ Internal API skeleton server is running on 127.0.0.1:50052")
    print("Press Ctrl+C to stop.")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    main()
