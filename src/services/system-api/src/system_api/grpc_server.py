from __future__ import annotations

import contextvars
import logging
import os
import uuid
from concurrent import futures
from typing import Any, Callable

import grpc
from google.rpc import code_pb2, status_pb2, error_details_pb2
from grpc_status import rpc_status

from .grpc_impl import DeviceService, JobService, KnowledgeBaseService
from .knowledge_base import KnowledgeBaseService
from .observability import trace_id_from_traceparent
from .proto_gen import ensure_generated

_LOG = logging.getLogger("system_api")

# Thread-safe context storage for distributed tracing and logging
ctx_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="N/A")
ctx_traceparent: contextvars.ContextVar[str] = contextvars.ContextVar("traceparent", default="N/A")
ctx_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="N/A")


class ValidationError(Exception):
    """Custom exception raised by services or validators when a request fails basic field checks."""
    def __init__(self, violations: dict[str, str]):
        self.violations = violations
        super().__init__("Request validation failed")


# --- Interceptors ---

class TracingAndLoggingInterceptor(grpc.ServerInterceptor):
    """Extracts distributed tracing IDs or generates local execution tokens, 

    injecting them into the log context window.
    """
    def intercept_service(
        self, continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler], 
        handler_call_details: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler:
        
        metadata = dict(handler_call_details.invocation_metadata)
        
        # Pull traceparent (W3C standard) or fallback to basic trace_id
        raw_traceparent = metadata.get("traceparent")
        raw_trace_id = metadata.get("trace_id")
        traceparent = raw_traceparent or raw_trace_id or f"root-{uuid.uuid4()}"
        trace_id = raw_trace_id or trace_id_from_traceparent(raw_traceparent) or traceparent
        request_id = metadata.get("x-request-id") or str(uuid.uuid4())
        
        # Bind tokens to the async execution context
        token_trace = ctx_trace_id.set(trace_id)
        token_traceparent = ctx_traceparent.set(traceparent)
        token_req = ctx_request_id.set(request_id)
        
        try:
            return continuation(handler_call_details)
        finally:
            # Reset context back to clean state post-call
            ctx_traceparent.reset(token_traceparent)
            ctx_trace_id.reset(token_trace)
            ctx_request_id.reset(token_req)


class ValidationAndExceptionInterceptor(grpc.ServerInterceptor):
    """Catches ValidationErrors and transforms them into rich gRPC Status 

    payloads utilizing google.rpc.BadRequest field violations.
    """
    def intercept_service(
        self, continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler], 
        handler_call_details: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler:
        
        handler = continuation(handler_call_details)
        if handler is None:
            return handler

        # Wrap Unary-Unary RPC handlers
        if handler.unary_unary:
            original_behavior = handler.unary_unary

            def new_behavior(request: Any, context: grpc.ServicerContext) -> Any:
                try:
                    # Optional: Insert automated structural validation hooks here if needed
                    return original_behavior(request, context)
                except ValidationError as ex:
                    _LOG.warning("Validation failure detected for request: %s", ex.violations)
                    
                    # 1. Build core Status object using google.rpc codes
                    status_proto = status_pb2.Status(
                        code=code_pb2.INVALID_ARGUMENT,
                        message="Request field validation failed.",
                    )
                    
                    # 2. Append rich BadRequest metadata structures
                    bad_request = error_details_pb2.BadRequest()
                    for field, description in ex.violations.items():
                        violation = bad_request.field_violations.add()
                        violation.field = field
                        violation.description = description
                    
                    # 3. Pack structural detail into the status wrapper
                    status_proto.details.add().Pack(bad_request)
                    
                    # 4. Terminate pipeline with high-fidelity status mapping
                    context.abort_with_status(rpc_status.to_status(status_proto))
                except Exception as ex:
                    if _is_grpc_abort_exception(context):
                        raise
                    _LOG.exception("Unhandled application state caught by interceptor")
                    context.abort(grpc.StatusCode.INTERNAL, "An unexpected system error occurred.")

            return grpc.unary_unary_rpc_method_handler(
                new_behavior,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        
        return handler


# --- Logging Helpers ---

def _is_grpc_abort_exception(context: grpc.ServicerContext) -> bool:
    state = getattr(context, "_state", None)
    if state is not None and getattr(state, "code", None) is not None:
        return True
    code_fn = getattr(context, "code", None)
    if callable(code_fn):
        try:
            return code_fn() is not None
        except Exception:
            return False
    return False


class StructuredTraceFilter(logging.Filter):
    """Dynamically injects active trace context data straight into standard log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "trace_id", None):
            record.trace_id = ctx_trace_id.get()
        if not getattr(record, "traceparent", None):
            record.traceparent = ctx_traceparent.get()
        if not getattr(record, "request_id", None):
            record.request_id = ctx_request_id.get()
        return True


def configure_logging():
    """Applies a strict formatting pipeline ensuring explicit log visibility 

    for system traces and processing IDs.
    """
    handler = logging.StreamHandler()
    handler.addFilter(StructuredTraceFilter())
    
    # Modern scannable format including trace parameters
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [TraceID: %(trace_id)s | TraceParent: %(traceparent)s | ReqID: %(request_id)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Clear out generic stdout formats to prevent visual collision
    root_logger.handlers = [handler]


# --- Core Server Hook ---

def serve(bind: str | None = None) -> grpc.Server:
    """Create, configure interceptors, spin up, and return the running gRPC server."""
    
    # Configure telemetry strings prior to startup print
    configure_logging()
    
    ensure_generated()

    from eigen.api.v1 import device_service_pb2 as dev_pb
    from eigen.api.v1 import device_service_pb2_grpc as dev_pb_grpc
    from eigen.api.v1 import job_service_pb2 as job_pb
    from eigen.api.v1 import job_service_pb2_grpc as job_pb_grpc
    from eigen.api.v1 import knowledge_base_service_pb2 as kb_pb
    from eigen.api.v1 import knowledge_base_service_pb2_grpc as kb_pb_grpc
    from eigen.api.v1 import types_pb2 as types_pb

    # Initialize server infrastructure with tracing and error safety-nets
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=16),
        interceptors=[
            TracingAndLoggingInterceptor(),
            ValidationAndExceptionInterceptor()
        ]
    )

    # Dependency Injection & Mapping Layer
    # Note: Retained KnowledgeBaseService as required by your core architecture hierarchy
    kb_service = KnowledgeBaseService(kb_pb=kb_pb, types_pb=types_pb)
    
    job_pb_grpc.add_JobServiceServicer_to_server(
        JobService(job_pb=job_pb, types_pb=types_pb, kb_service=kb_service),
        server,
    )
    dev_pb_grpc.add_DeviceServiceServicer_to_server(
        DeviceService(dev_pb=dev_pb, types_pb=types_pb),
        server,
    )
    kb_pb_grpc.add_KnowledgeBaseServiceServicer_to_server(
        kb_service,
        server,
    )

    addr = bind or os.getenv("SYSTEM_API_GRPC_BIND", "0.0.0.0:50051")
    server.add_insecure_port(addr)

    server.start()
    _LOG.info("system-api gRPC server started on %s", addr)

    return server