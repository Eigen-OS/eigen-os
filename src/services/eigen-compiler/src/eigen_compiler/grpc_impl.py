"""gRPC implementation for internal CompilationService."""

from __future__ import annotations

import logging
import re

import grpc

from .compiler import CompilerValidationError, compile_eigen_lang
from .errors import abort_invalid_argument
from .validation import validate_compile_circuit, validate_compile_job


class CompilationService:
    """Implementation of eigen.internal.v1.CompilationService."""

    def __init__(self, comp_pb, types_pb):
        self._comp_pb = comp_pb
        self._types_pb = types_pb

    def _compile_response(self, *, source: bytes, source_ref: str | None = None):
        result = compile_eigen_lang(source, source_ref=source_ref)
        return self._comp_pb.CompileCircuitResponse(
            circuit=self._types_pb.CircuitPayload(
                format=self._types_pb.CIRCUIT_FORMAT_AQO_JSON,
                data=result.aqo_json,
            ),
            metadata=result.metadata,
        )

    def CompileCircuit(self, request, context: grpc.ServicerContext):
        _log_start("CompilationService.CompileCircuit", request.job_id, context)
        violations = validate_compile_circuit(request)
        if violations:
            abort_invalid_argument(context, message="validation failed", violations=violations)

        source = request.source if request.WhichOneof("input") == "source" else b""
        source_ref = request.source_ref if request.WhichOneof("input") == "source_ref" else None
        try:
            resp = self._compile_response(source=source, source_ref=source_ref)
            _log_end("CompilationService.CompileCircuit", request.job_id, context)
            return resp
        except CompilerValidationError as exc:
            abort_invalid_argument(context, message="validation failed", violations=exc.violations)

    def CompileJob(self, request, context: grpc.ServicerContext):
        _log_start("CompilationService.CompileJob", request.job_id, context)
        violations = validate_compile_job(request)
        if violations:
            abort_invalid_argument(context, message="validation failed", violations=violations)

        source = request.source if request.WhichOneof("input") == "source" else b""
        source_ref = request.source_ref if request.WhichOneof("input") == "source_ref" else None
        try:
            compiled = self._compile_response(source=source, source_ref=source_ref)
        except CompilerValidationError as exc:
            abort_invalid_argument(context, message="validation failed", violations=exc.violations)

        resp = self._comp_pb.CompileJobResponse(
            job_id=request.job_id,
            circuit=compiled.circuit,
            metadata=compiled.metadata,
        )
        _log_end("CompilationService.CompileJob", request.job_id, context)
        return resp

    def OptimizeCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "OptimizeCircuit is not implemented")

    def ValidateCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ValidateCircuit is not implemented")

_LOG = logging.getLogger("eigen_compiler")
_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-(?P<trace_id>[0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _trace_fields(context: grpc.ServicerContext) -> tuple[str | None, str | None]:
    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    traceparent = md.get("traceparent")
    trace_id = md.get("trace_id")
    if trace_id is None and traceparent:
        match = _TRACEPARENT_RE.match(traceparent)
        if match:
            trace_id = match.group("trace_id")
    return trace_id, traceparent


def _log_start(method: str, job_id: str, context: grpc.ServicerContext) -> None:
    trace_id, traceparent = _trace_fields(context)
    _LOG.info("rpc_start", extra={"method": method, "job_id": job_id, "trace_id": trace_id, "traceparent": traceparent})


def _log_end(method: str, job_id: str, context: grpc.ServicerContext) -> None:
    trace_id, _traceparent = _trace_fields(context)
    _LOG.info("rpc_end", extra={"method": method, "job_id": job_id, "trace_id": trace_id})
