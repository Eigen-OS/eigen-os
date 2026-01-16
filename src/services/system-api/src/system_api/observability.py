"""Minimal observability helpers for System API.

Issue #24 requires logs to include a trace identifier (or traceparent) and a
per-request id.

For MVP we implement:
- request_id: uuid4 per RPC
- traceparent: raw header, if supplied
- trace_id: best-effort extracted from traceparent (W3C)

We keep this intentionally lightweight (standard library logging).
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass

import grpc

_LOG = logging.getLogger("system_api")

_TRACEPARENT_RE = re.compile(
    r"^(?P<version>[0-9a-f]{2})-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<trace_flags>[0-9a-f]{2})$"
)


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    traceparent: str | None
    trace_id: str | None


def new_request_context(context: grpc.ServicerContext) -> RequestContext:
    md = {k.lower(): v for (k, v) in (context.invocation_metadata() or [])}

    traceparent = md.get("traceparent")
    trace_id = md.get("trace_id")

    if trace_id is None and traceparent:
        m = _TRACEPARENT_RE.match(traceparent)
        if m:
            trace_id = m.group("trace_id")

    return RequestContext(
        request_id=str(uuid.uuid4()),
        traceparent=traceparent,
        trace_id=trace_id,
    )


def log_request_start(method: str, rc: RequestContext) -> None:
    _LOG.info(
        "rpc_start method=%s request_id=%s trace_id=%s traceparent=%s",
        method,
        rc.request_id,
        rc.trace_id,
        rc.traceparent,
    )


def log_request_end(method: str, rc: RequestContext) -> None:
    _LOG.info(
        "rpc_end method=%s request_id=%s trace_id=%s",
        method,
        rc.request_id,
        rc.trace_id,
    )
