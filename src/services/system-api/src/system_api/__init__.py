"""Eigen OS system-api package (scaffold)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import grpc
from google.rpc import code_pb2, status_pb2

_GRPC_STATUS_DETAILS_BIN = "grpc-status-details-bin"

_STATUS_CODE_BY_NUMBER = {
    code.value[0]: code for code in grpc.StatusCode
}

_STATUS_NUMBER_BY_CODE = {
    code: code.value[0] for code in grpc.StatusCode
}


def _status_code_from_number(number: int) -> grpc.StatusCode:
    return _STATUS_CODE_BY_NUMBER.get(number, grpc.StatusCode.UNKNOWN)


@dataclass(frozen=True)
class _RpcStatusCompat:
    """Minimal grpc-status compatibility shim for tests and local server code."""

    def to_status(self, status: status_pb2.Status) -> grpc.Status:
        grpc_status = grpc.Status()
        grpc_status.code = _status_code_from_number(int(status.code))
        grpc_status.details = status.message
        grpc_status.trailing_metadata = (
            (_GRPC_STATUS_DETAILS_BIN, status.SerializeToString()),
        )
        return grpc_status

    def from_call(self, err) -> Optional[status_pb2.Status]:
        metadata = None
        if hasattr(err, "trailing_metadata") and callable(err.trailing_metadata):
            try:
                metadata = err.trailing_metadata()
            except Exception:
                metadata = None
        if metadata:
            for key, value in metadata:
                if key == _GRPC_STATUS_DETAILS_BIN and value:
                    status = status_pb2.Status()
                    status.ParseFromString(value)
                    return status

        status = status_pb2.Status()
        code = getattr(err, "code", lambda: grpc.StatusCode.UNKNOWN)()
        if isinstance(code, grpc.StatusCode):
            status.code = _STATUS_NUMBER_BY_CODE.get(code, code_pb2.UNKNOWN)
        else:
            status.code = code_pb2.UNKNOWN
        status.message = getattr(err, "details", lambda: "")() or ""
        return status


rpc_status = _RpcStatusCompat()

__all__ = ["rpc_status"]
