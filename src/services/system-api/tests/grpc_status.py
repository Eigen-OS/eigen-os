from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import grpc
from google.rpc import status_pb2
from google.protobuf.any_pb2 import Any as AnyMessage


_CODE_MAP = {code.value[0]: code for code in grpc.StatusCode}


def _status_code_from_number(number: int) -> grpc.StatusCode:
    return _CODE_MAP.get(int(number), grpc.StatusCode.UNKNOWN)


@dataclass
class _RpcStatusCompat:
    def from_call(self, err) -> Optional[status_pb2.Status]:
        trailing = None
        try:
            trailing = err.trailing_metadata()
        except Exception:
            trailing = None
        if trailing:
            for key, value in trailing:
                if key == "grpc-status-details-bin":
                    status = status_pb2.Status()
                    try:
                        status.ParseFromString(value)
                    except Exception:
                        return None
                    return status
        code = getattr(err, "code", lambda: None)()
        details = getattr(err, "details", lambda: "")()
        if code is None and not details:
            return None
        status = status_pb2.Status()
        status.message = str(details or "")
        return status

    def to_status(self, status: status_pb2.Status) -> grpc.Status:
        grpc_status = grpc.Status()
        grpc_status.code = _status_code_from_number(status.code)
        grpc_status.details = status.message or ""
        grpc_status.trailing_metadata = (("grpc-status-details-bin", status.SerializeToString()),)
        return grpc_status


rpc_status = _RpcStatusCompat()
