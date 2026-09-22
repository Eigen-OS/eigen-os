from __future__ import annotations

from dataclasses import dataclass

import grpc
from google.protobuf import any_pb2, message as _message
from google.rpc import status_pb2

_GRPC_STATUS_DETAILS_BIN = "grpc-status-details-bin"


@dataclass(frozen=True)
class _GrpcStatus:
    status: status_pb2.Status

    def abort(self, context: grpc.ServicerContext) -> None:
        context.set_trailing_metadata(((_GRPC_STATUS_DETAILS_BIN, self.status.SerializeToString()),))
        code_name = grpc.StatusCode(self.status.code).name if self.status.code in [int(c.value[0]) for c in grpc.StatusCode] else "UNKNOWN"
        context.abort(grpc.StatusCode(self.status.code), self.status.message)


def to_status(status: status_pb2.Status) -> _GrpcStatus:
    return _GrpcStatus(status=status)


def from_call(call) -> status_pb2.Status | None:
    trailing = call.trailing_metadata() or ()
    for key, value in trailing:
        if key == _GRPC_STATUS_DETAILS_BIN:
            st = status_pb2.Status()
            st.ParseFromString(value)
            return st
    return None
