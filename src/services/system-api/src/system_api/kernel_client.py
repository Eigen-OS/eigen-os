"""Kernel Gateway client for System API lifecycle delegation."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import AsyncIterator, Optional

import grpc
from google.protobuf.duration_pb2 import Duration
from google.protobuf.timestamp_pb2 import Timestamp

from .proto_gen import ensure_generated

ensure_generated()

from eigen.internal.v1 import kernel_gateway_pb2 as kernel_pb  # noqa: E402
from eigen.internal.v1 import kernel_gateway_pb2_grpc as kernel_pb_grpc  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KernelClientConfig:
    """Configuration for Kernel Gateway client."""
    
    grpc_endpoint: str = field(
        default_factory=lambda: os.getenv(
            "EIGEN_KERNEL_ADDR",
            os.getenv("KERNEL_ENDPOINT", os.getenv("KERNEL_GRPC_ENDPOINT", "localhost:50052")),
        )
    )
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("KERNEL_GATEWAY_TIMEOUT_SECONDS", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("KERNEL_GATEWAY_MAX_RETRIES", "3")))
    enable_tracing: bool = field(default_factory=lambda: os.getenv("KERNEL_CLIENT_ENABLE_TRACING", "true").lower() == "true")


class KernelGatewayClient:
    """gRPC client for the Kernel/QRTX internal gateway."""
    
    def __init__(self, config: Optional[KernelClientConfig] = None):
        self.config = config or KernelClientConfig()
        self._channel: grpc.Channel | None = None
        self._stub: kernel_pb_grpc.KernelGatewayServiceStub | None = None
        self._closed = True
        self._job_topologies: dict[str, dict[str, str]] = {}

    def connect(self) -> None:
        if self._channel is not None and self._stub is not None:
            return

        self._channel = grpc.insecure_channel(self.config.grpc_endpoint)
        self._stub = kernel_pb_grpc.KernelGatewayServiceStub(self._channel)
        try:
            grpc.channel_ready_future(self._channel).result(timeout=self.config.timeout_seconds)
        except Exception as exc:  # pragma: no cover - connectivity failure path
            self._channel = None
            self._stub = None
            raise RuntimeError("failed to connect to Kernel Gateway") from exc
        self._closed = False
        
        logger.info("Connected to Kernel Gateway at %s", self.config.grpc_endpoint)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
            self._closed = True
            logger.info("Kernel client connection closed")
    
    async def __aenter__(self):
        self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _build_request_metadata(self, public_envelope: dict, source_service: str = "system-api") -> dict:
        request_id = public_envelope.get("request_id") or str(uuid.uuid4())
        
        traceparent = public_envelope.get("traceparent") or self._synthetic_traceparent(request_id)

        return {
            "contract_version": public_envelope.get("contract_version", "1.0.0"),
            "request_id": request_id,
            "idempotency_key": public_envelope.get("idempotency_key", ""),
            "traceparent": traceparent,
            "deadline": public_envelope.get("deadline"),
            "tenant_id": public_envelope.get("tenant_id", "tenant-default"),
            "project_id": public_envelope.get("project_id", "project-default"),
            "subject": public_envelope.get("auth_subject", ""),
            "role": public_envelope.get("auth_role", "user"),
            "source_service": source_service,
            "trace_id": public_envelope.get("trace_id", ""),
            "retry_policy": public_envelope.get("retry_policy", ""),
            "security_context": public_envelope.get("security_context", ""),
        }

    @staticmethod
    def _synthetic_traceparent(seed: str) -> str:
        digest = sha256(seed.encode("utf-8")).hexdigest()
        trace_id = digest[:32]
        span_id = digest[32:48]
        return f"00-{trace_id}-{span_id}-01"

    def _request_metadata_proto(self, public_envelope: dict) -> kernel_pb.RequestMetadata:
        md = self._build_request_metadata(public_envelope)
        payload = {
            "contract_version": md["contract_version"],
            "request_id": md["request_id"],
            "idempotency_key": md["idempotency_key"],
            "traceparent": md["traceparent"],
            "tenant_id": md["tenant_id"],
            "project_id": md["project_id"],
            "subject": md["subject"],
            "role": md["role"],
            "source_service": md["source_service"],
            "trace_id": md["trace_id"],
            "retry_policy": md["retry_policy"],
            "security_context": md["security_context"],
        }
        deadline = md.get("deadline")
        if isinstance(deadline, Duration):
            payload["deadline"] = deadline
        elif deadline is not None:
            payload["deadline"] = Duration(seconds=int(deadline))
        return kernel_pb.RequestMetadata(**payload)

    @staticmethod
    def _state_name(state: int) -> str:
        try:
            return kernel_pb.TaskState.Name(state)
        except Exception:
            return "TASK_STATE_UNSPECIFIED"
    
    @staticmethod
    def _timestamp(value) -> Timestamp | None:
        if value is None:
            return None
        if isinstance(value, Timestamp):
            return value
        ts = Timestamp()
        if isinstance(value, datetime):
            ts.FromDatetime(value)
        else:
            ts.FromDatetime(datetime.fromtimestamp(float(value), tz=UTC))
        return ts

    async def enqueue_job(
        self,
        name: str,
        program: bytes,
        program_format: str,
        target: str,
        priority: int,
        compiler_options: dict,
        metadata_kvs: dict,
        public_envelope: dict,
    ) -> dict:
        if self._closed or self._stub is None:
            self.connect()

        assert self._stub is not None
        request = kernel_pb.EnqueueJobRequest(
            metadata=self._request_metadata_proto(public_envelope),
            name=name,
            program=program,
            program_format=program_format,
            target=target,
            priority=int(priority),
            compiler_options={str(k): str(v) for k, v in dict(compiler_options).items()},
            metadata_kvs={str(k): str(v) for k, v in dict(metadata_kvs).items()},
        )
        response = await asyncio.to_thread(self._stub.EnqueueJob, request, timeout=self.config.timeout_seconds)
        topology = dict(public_envelope.get("topology", {}))
        if topology:
            self._job_topologies[response.job_id] = topology
        return {
            "job_id": response.job_id,
            "state": self._state_name(response.state),
            "created_at": response.created_at,
        }

    async def get_job_status(self, job_id: str, public_envelope: dict) -> dict:
        if self._closed or self._stub is None:
            self.connect()

        assert self._stub is not None
        request = kernel_pb.GetJobStatusRequest(
            metadata=self._request_metadata_proto(public_envelope),
            job_id=job_id,
        )
        logger.info("Getting job status for %s; request_id=%s", job_id, public_envelope.get("request_id"))
        response = await asyncio.to_thread(
            self._stub.GetJobStatus,
            request,
            timeout=self.config.timeout_seconds,
        )
        result = {
            "job_id": response.job_id,
            "state": self._state_name(response.state),
            "stage": response.stage,
            "progress": float(response.progress),
            "message": response.message,
            "created_at": None,
            "updated_at": response.updated_at,
            "topology": self._job_topologies.get(job_id, dict(public_envelope.get("topology", {}))),
        }
        if response.error_code:
            result.update(
                {
                    "error_code": response.error_code,
                    "error_summary": response.error_summary,
                    "error_details_ref": response.error_details_ref,
                }
            )
        return result

    async def cancel_job(self, job_id: str, public_envelope: dict) -> dict:
        if self._closed or self._stub is None:
            self.connect()
        assert self._stub is not None

        request = kernel_pb.CancelJobRequest(
            metadata=self._request_metadata_proto(public_envelope),
            job_id=job_id,
        )
        response = await asyncio.to_thread(
            self._stub.CancelJob,
            request,
            timeout=self.config.timeout_seconds,
        )
        return {
            "accepted": bool(response.accepted),
            "reason_code": response.reason_code,
        }
    
    async def stream_job_updates(
        self,
        job_id: str,
        last_event_seq: int,
        public_envelope: dict,
    ) -> AsyncIterator[dict]:
        if self._closed or self._stub is None:
            self.connect()

        assert self._stub is not None
        request = kernel_pb.StreamJobUpdatesRequest(
            metadata=self._request_metadata_proto(public_envelope),
            job_id=job_id,
            last_event_seq=int(last_event_seq),
        )
        call = self._stub.StreamJobUpdates(request, timeout=self.config.timeout_seconds)
        for response in call:
            update = response.update
            yield {
                "job_id": job_id,
                "event_seq": int(update.event_seq),
                "state": self._state_name(update.state),
                "stage": update.stage,
                "progress": float(update.progress),
                "message": update.message,
                "timestamp": update.timestamp,
                "topology": self._job_topologies.get(job_id, dict(public_envelope.get("topology", {}))),
            }
            
    async def get_job_results(self, job_id: str, public_envelope: dict) -> dict:
        if self._closed or self._stub is None:
            self.connect()
        assert self._stub is not None
        request = kernel_pb.GetJobResultsRequest(metadata=self._request_metadata_proto(public_envelope), job_id=job_id)
        response = await asyncio.to_thread(self._stub.GetJobResults, request, timeout=self.config.timeout_seconds)
        result = {
            "job_id": response.job_id,
            "state": self._state_name(response.state),
            "counts": dict(response.counts),
            "metadata": dict(response.metadata),
            "qfs_result_ref": response.qfs_result_ref,
            "completed_at": response.completed_at,
            "topology": self._job_topologies.get(job_id, dict(public_envelope.get("topology", {}))),
        }
        if response.error_code:
            result.update(
                {
                    "error_code": response.error_code,
                    "error_summary": response.error_summary,
                    "error_details_ref": response.error_details_ref,
                }
            )
        return result

    async def get_dispatch_rationale(self, job_id: str, public_envelope: dict) -> dict:
        if self._closed or self._stub is None:
            self.connect()
        assert self._stub is not None
        request = kernel_pb.GetDispatchRationaleRequest(metadata=self._request_metadata_proto(public_envelope), job_id=job_id)
        response = await asyncio.to_thread(
            self._stub.GetDispatchRationale,
            request,
            timeout=self.config.timeout_seconds,
        )
        rationale = response.rationale
        return {
            "version": rationale.version,
            "policy_version": rationale.policy_version,
            "reason_codes": list(rationale.reason_codes),
            "selected_backend": rationale.selected_backend,
            "selected_queue": rationale.selected_queue,
            "attributes": dict(rationale.attributes),
            "timeline_ref": rationale.timeline_ref,
            "logs_ref": rationale.logs_ref,
            "trace_id": rationale.trace_id,
            "trace_ref": rationale.trace_ref,
            "topology": self._job_topologies.get(job_id, dict(public_envelope.get("topology", {}))),
        }
