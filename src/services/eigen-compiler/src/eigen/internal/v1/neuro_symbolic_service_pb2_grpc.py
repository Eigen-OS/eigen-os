"""gRPC helpers for eigen.internal.v1.NeuroSymbolicService."""

from __future__ import annotations

import grpc

from . import neuro_symbolic_service_pb2 as neuro__symbolic__service__pb2


class NeuroSymbolicServiceStub:
    def __init__(self, channel):
        self.ScoreCompilationPlan = channel.unary_unary(
            "/eigen.internal.v1.NeuroSymbolicService/ScoreCompilationPlan",
            request_serializer=neuro__symbolic__service__pb2.ScoreCompilationPlanRequest.SerializeToString,
            response_deserializer=neuro__symbolic__service__pb2.ScoreCompilationPlanResponse.FromString,
        )


class NeuroSymbolicServiceServicer:
    def ScoreCompilationPlan(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError()


def add_NeuroSymbolicServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "ScoreCompilationPlan": grpc.unary_unary_rpc_method_handler(
            servicer.ScoreCompilationPlan,
            request_deserializer=neuro__symbolic__service__pb2.ScoreCompilationPlanRequest.FromString,
            response_serializer=neuro__symbolic__service__pb2.ScoreCompilationPlanResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "eigen.internal.v1.NeuroSymbolicService",
        rpc_method_handlers,
    )
    server.add_generic_rpc_handlers((generic_handler,))


__all__ = [
    "NeuroSymbolicServiceServicer",
    "NeuroSymbolicServiceStub",
    "add_NeuroSymbolicServiceServicer_to_server",
]
