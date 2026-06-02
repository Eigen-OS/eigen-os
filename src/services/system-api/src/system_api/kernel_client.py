"""
Kernel Gateway Client for System API lifecycle delegation.

Product 1.0 Wave 2: System API delegates all lifecycle mutations to Kernel/QRTX.
This module provides the adapter between public Wave 1 contracts and internal
KernelGateway service, with request/response mapping and metadata normalization.

Source of truth: RFC 0050, W2-03 issue, docs/reference/api/grpc-internal.md
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional, AsyncIterator

import grpc
from grpc import aio

# Import Kernel proto (would be generated in real implementation)
# from eigen.internal.v1 import kernel_gateway_pb2, kernel_gateway_pb2_grpc

logger = logging.getLogger(__name__)


@dataclass
class KernelClientConfig:
    """Configuration for Kernel Gateway client."""
    
    grpc_endpoint: str = os.getenv(
        "KERNEL_GRPC_ENDPOINT",
        "localhost:50052"
    )
    timeout_seconds: int = int(os.getenv(
        "KERNEL_GATEWAY_TIMEOUT_SECONDS",
        "30"
    ))
    max_retries: int = int(os.getenv(
        "KERNEL_GATEWAY_MAX_RETRIES",
        "3"
    ))
    enable_tracing: bool = os.getenv(
        "KERNEL_CLIENT_ENABLE_TRACING",
        "true"
    ).lower() == "true"


class KernelGatewayClient:
    """
    Async gRPC client for Kernel Gateway service.
    
    Handles:
    - Request/response mapping between public and internal contracts
    - Metadata normalization from Wave 1 public envelopes
    - Error translation to canonical error model
    - W3C TraceContext propagation
    - Connection pooling and retry logic
    """
    
    def __init__(self, config: Optional[KernelClientConfig] = None):
        self.config = config or KernelClientConfig()
        self._channel: Optional[aio.Channel] = None
        # Placeholder for actual gRPC stub (would be KernelGatewayServiceStub)
        self._stub = None
        self._closed = False
        
    async def connect(self) -> None:
        """Establish connection to Kernel Gateway service."""
        if self._channel is not None:
            logger.debug("Kernel client already connected")
            return
        
        try:
            self._channel = aio.insecure_channel(
                self.config.grpc_endpoint,
                options=[
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 10000),
                    ("grpc.http2.max_pings_without_data", 0),
                    ("grpc.max_receive_message_length", 100 * 1024 * 1024),
                ]
            )
            # Placeholder: would create actual stub here
            # self._stub = kernel_gateway_pb2_grpc.KernelGatewayServiceStub(self._channel)
            logger.info(f"Connected to Kernel Gateway at {self.config.grpc_endpoint}")
        except Exception as e:
            logger.error(f"Failed to connect to Kernel Gateway: {e}")
            raise
    
    async def close(self) -> None:
        """Close connection to Kernel Gateway service."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._closed = True
            logger.info("Kernel client connection closed")
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _build_request_metadata(
        self,
        public_envelope: dict,
        source_service: str = "system-api",
    ) -> dict:
        """
        Normalize public request envelope into internal metadata.
        
        Maps:
        - contract_version -> contract_version
        - request_id -> request_id (or generate UUID)
        - idempotency_key -> idempotency_key (preserved for deduplication)
        - traceparent -> traceparent (W3C TraceContext)
        - deadline -> deadline
        - tenant_id, project_id -> tenant_id, project_id
        - auth subject/role -> subject, role (from security context)
        - source_service -> "system-api"
        
        Does NOT leak public-only fields like:
        - client_version
        - SDK-specific metadata
        """
        request_id = public_envelope.get("request_id") or str(uuid.uuid4())
        
        metadata = {
            "contract_version": public_envelope.get("contract_version", "1.0.0"),
            "request_id": request_id,
            "idempotency_key": public_envelope.get("idempotency_key", ""),
            "traceparent": public_envelope.get("traceparent", ""),
            "deadline": public_envelope.get("deadline"),
            "tenant_id": public_envelope.get("tenant_id", "tenant-default"),
            "project_id": public_envelope.get("project_id", "project-default"),
            "subject": public_envelope.get("auth_subject", ""),
            "role": public_envelope.get("auth_role", "user"),
            "source_service": source_service,
        }
        
        return metadata
    
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
        """
        Enqueue job in Kernel (Wave 2-03 delegation from System API SubmitJob).
        
        Returns:
            {"job_id": str, "state": TaskState, "created_at": Timestamp}
        """
        if self._closed or self._channel is None:
            raise RuntimeError("Kernel client not connected")
        
        try:
            # Normalize metadata from public envelope
            internal_metadata = self._build_request_metadata(public_envelope)
            
            # Build internal request (would use actual proto here)
            # request = kernel_gateway_pb2.EnqueueJobRequest(
            #     metadata=kernel_gateway_pb2.RequestMetadata(**internal_metadata),
            #     name=name,
            #     program=program,
            #     program_format=program_format,
            #     target=target,
            #     priority=priority,
            #     compiler_options=compiler_options,
            #     metadata_kvs=metadata_kvs,
            # )
            
            logger.info(
                f"Enqueueing job '{name}' in Kernel. "
                f"request_id={internal_metadata['request_id']}"
            )
            
            # Placeholder: would call actual gRPC stub
            # response = await self._stub.EnqueueJob(
            #     request,
            #     timeout=self.config.timeout_seconds,
            # )
            
            # For now, return mock response
            response = {
                "job_id": f"job-{uuid.uuid4().hex[:8]}",
                "state": "TASK_STATE_PENDING",
                "created_at": None,  # Would be actual timestamp
            }
            
            return response
            
        except grpc.RpcError as e:
            logger.error(f"Kernel EnqueueJob RPC failed: {e.code()} {e.details()}")
            # Map gRPC error to canonical error
            raise self._map_kernel_error(e)
        except Exception as e:
            logger.error(f"Kernel EnqueueJob failed: {e}")
            raise
    
    async def get_job_status(
        self,
        job_id: str,
        public_envelope: dict,
    ) -> dict:
        """
        Get job status from Kernel (Wave 2-03 delegation from System API GetJobStatus).
        
        Returns:
            {"job_id": str, "state": TaskState, "stage": str, ...}
        """
        if self._closed or self._channel is None:
            raise RuntimeError("Kernel client not connected")
        
        try:
            internal_metadata = self._build_request_metadata(public_envelope)
            
            # Placeholder: would build actual proto request
            logger.info(
                f"Getting job status for {job_id}. "
                f"request_id={internal_metadata['request_id']}"
            )
            
            # Placeholder response
            response = {
                "job_id": job_id,
                "state": "TASK_STATE_PENDING",
                "stage": "ENQUEUED",
                "progress": 0.0,
                "message": "Job enqueued",
                "updated_at": None,
            }
            
            return response
            
        except grpc.RpcError as e:
            logger.error(f"Kernel GetJobStatus RPC failed: {e.code()} {e.details()}")
            raise self._map_kernel_error(e)
        except Exception as e:
            logger.error(f"Kernel GetJobStatus failed: {e}")
            raise
    
    async def cancel_job(
        self,
        job_id: str,
        public_envelope: dict,
    ) -> dict:
        """
        Cancel job in Kernel (Wave 2-03 delegation from System API CancelJob).
        
        Returns:
            {"accepted": bool, "reason_code": str}
        """
        if self._closed or self._channel is None:
            raise RuntimeError("Kernel client not connected")
        
        try:
            internal_metadata = self._build_request_metadata(public_envelope)
            
            logger.info(
                f"Cancelling job {job_id}. "
                f"request_id={internal_metadata['request_id']}"
            )
            
            # Placeholder response
            response = {
                "accepted": True,
                "reason_code": "CANCEL_ACCEPTED",
            }
            
            return response
            
        except grpc.RpcError as e:
            logger.error(f"Kernel CancelJob RPC failed: {e.code()} {e.details()}")
            raise self._map_kernel_error(e)
        except Exception as e:
            logger.error(f"Kernel CancelJob failed: {e}")
            raise
    
    async def get_job_results(
        self,
        job_id: str,
        public_envelope: dict,
    ) -> dict:
        """
        Get job results from Kernel (Wave 2-03 delegation from System API GetJobResults).
        
        Returns:
            {"job_id": str, "state": TaskState, "counts": dict, ...}
        """
        if self._closed or self._channel is None:
            raise RuntimeError("Kernel client not connected")
        
        try:
            internal_metadata = self._build_request_metadata(public_envelope)
            
            logger.info(
                f"Getting job results for {job_id}. "
                f"request_id={internal_metadata['request_id']}"
            )
            
            # Placeholder response
            response = {
                "job_id": job_id,
                "state": "TASK_STATE_DONE",
                "counts": {"0": 500, "1": 500},
                "metadata": {},
                "qfs_result_ref": f"qfs://results/{job_id}/final",
                "completed_at": None,
            }
            
            return response
            
        except grpc.RpcError as e:
            logger.error(f"Kernel GetJobResults RPC failed: {e.code()} {e.details()}")
            raise self._map_kernel_error(e)
        except Exception as e:
            logger.error(f"Kernel GetJobResults failed: {e}")
            raise
    
    async def stream_job_updates(
        self,
        job_id: str,
        last_event_seq: int,
        public_envelope: dict,
    ) -> AsyncIterator[dict]:
        """
        Stream job updates from Kernel with deterministic ordering.
        
        Yields job update envelopes with monotonic sequence numbers.
        """
        if self._closed or self._channel is None:
            raise RuntimeError("Kernel client not connected")
        
        try:
            internal_metadata = self._build_request_metadata(public_envelope)
            
            logger.info(
                f"Streaming updates for job {job_id} from seq {last_event_seq}. "
                f"request_id={internal_metadata['request_id']}"
            )
            
            # Placeholder: would stream actual gRPC responses
            # For testing, yield mock updates
            yield {
                "event_seq": 1,
                "state": "TASK_STATE_PENDING",
                "stage": "ENQUEUED",
                "progress": 0.1,
                "message": "Job enqueued",
                "timestamp": None,
            }
            
        except grpc.RpcError as e:
            logger.error(f"Kernel StreamJobUpdates RPC failed: {e.code()} {e.details()}")
            raise self._map_kernel_error(e)
        except Exception as e:
            logger.error(f"Kernel StreamJobUpdates failed: {e}")
            raise
    
    def _map_kernel_error(self, kernel_error: Exception) -> Exception:
        """
        Map Kernel gRPC errors to canonical error model.
        
        Returns error suitable for public API error envelope.
        """
        # Placeholder: would implement canonical error mapping
        # following docs/reference/error-model.md and error-mapping.md
        return Exception(f"Kernel error: {kernel_error}")
