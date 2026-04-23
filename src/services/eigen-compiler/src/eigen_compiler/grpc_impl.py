"""gRPC implementation for internal CompilationService."""

from __future__ import annotations

import grpc

from .compiler import CompilationValidationError, compile_eigen_lang
from .errors import FieldViolation, abort_invalid_argument
from .validation import validate_compile_circuit, validate_compile_job


class CompilationService:
    """Implementation of eigen.internal.v1.CompilationService."""

    def __init__(self, comp_pb, types_pb):
        self._comp_pb = comp_pb
        self._types_pb = types_pb

    def _compile_response(
        self,
        *,
        source: bytes,
        context: grpc.ServicerContext,
        source_ref: str | None = None,
    ):
        try:
            result = compile_eigen_lang(source, source_ref=source_ref)
        except CompilationValidationError as exc:
            abort_invalid_argument(
                context,
                message="validation failed",
                violations=[
                    FieldViolation(field=v.field, description=v.description) for v in exc.violations
                ],
            )

        return self._comp_pb.CompileCircuitResponse(
            circuit=self._types_pb.CircuitPayload(
                format=self._types_pb.CIRCUIT_FORMAT_AQO_JSON,
                data=result.aqo_json,
            ),
            metadata=result.metadata,
        )

    def CompileCircuit(self, request, context: grpc.ServicerContext):
        violations = validate_compile_circuit(request)
        if violations:
            abort_invalid_argument(context, message="validation failed", violations=violations)

        source = request.source if request.WhichOneof("input") == "source" else b""
        source_ref = request.source_ref if request.WhichOneof("input") == "source_ref" else None
        return self._compile_response(source=source, source_ref=source_ref, context=context)

    def CompileJob(self, request, context: grpc.ServicerContext):
        violations = validate_compile_job(request)
        if violations:
            abort_invalid_argument(context, message="validation failed", violations=violations)

        source = request.source if request.WhichOneof("input") == "source" else b""
        source_ref = request.source_ref if request.WhichOneof("input") == "source_ref" else None
        compiled = self._compile_response(source=source, source_ref=source_ref, context=context)

        return self._comp_pb.CompileJobResponse(
            job_id=request.job_id,
            circuit=compiled.circuit,
            metadata=compiled.metadata,
        )

    def OptimizeCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "OptimizeCircuit is not implemented")

    def ValidateCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ValidateCircuit is not implemented")
