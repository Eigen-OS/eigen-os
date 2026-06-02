"""
System API gRPC service delegation to Kernel/QRTX.

Product 1.0 Wave 2: Updates to grpc_impl.py service methods to delegate
all lifecycle mutations to Kernel/QRTX via KernelGatewayClient.

This module demonstrates the delegation pattern for JobService methods:
- SubmitJob
- GetJobStatus
- CancelJob
- StreamJobUpdates
- GetJobResults

Source of truth: RFC 0050, W2-03 issue
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, AsyncIterator

import grpc

from .kernel_client import KernelGatewayClient, KernelClientConfig
from .lifecycle import apply_signal

logger = logging.getLogger(__name__)


class DelegationHandler:
    """
    Manages delegation of System API public methods to Kernel/QRTX.
    
    Responsibilities:
    - Delegate lifecycle mutations to Kernel
    - Translate internal errors to public error model
    - Preserve Wave 1 public API contract
    - Map public states to internal TaskStates
    - Propagate trace context and metadata
    """
    
    def __init__(self, kernel_client: Optional[KernelGatewayClient] = None):
        self.kernel_client = kernel_client or KernelGatewayClient()
        self._state_mapping = {
            "TASK_STATE_PENDING": "PENDING",
            "TASK_STATE_COMPILING": "COMPILING",
            "TASK_STATE_OPTIMIZING": "COMPILING",  # Map to public COMPILING
            "TASK_STATE_QUEUED": "QUEUED",
            "TASK_STATE_RUNNING": "RUNNING",
            "TASK_STATE_DONE": "DONE",
            "TASK_STATE_ERROR": "ERROR",
            "TASK_STATE_CANCELLED": "CANCELLED",
            "TASK_STATE_TIMEOUT": "TIMEOUT",
        }
    
    async def submit_job_delegated(
        self,
        name: str,
        program: bytes,
        program_format: str,
        target: str,
        priority: int,
        compiler_options: dict,
        metadata_kvs: dict,
        public_envelope: dict,
    ) -> tuple[str, str]:
        """
        Delegate SubmitJob to Kernel/QRTX.
        
        Preserves Wave 1 behavior:
        - Accepts job and returns job_id
        - Enforces payload limits (pre-validated by caller)
        - Maintains idempotency semantics through Kernel
        - Returns public JobStatus state
        
        Returns:
            (job_id, public_state)
        """
        try:
            # Connect if needed
            if self.kernel_client._closed:
                await self.kernel_client.connect()
            
            # Delegate to Kernel
            kernel_response = await self.kernel_client.enqueue_job(
                name=name,
                program=program,
                program_format=program_format,
                target=target,
                priority=priority,
                compiler_options=compiler_options,
                metadata_kvs=metadata_kvs,
                public_envelope=public_envelope,
            )
            
            job_id = kernel_response["job_id"]
            
            # Map internal state to public state
            internal_state = kernel_response.get("state", "TASK_STATE_PENDING")
            public_state = self._map_internal_state_to_public(internal_state)
            
            logger.info(
                f"SubmitJob delegated to Kernel: job_id={job_id}, state={public_state}, "
                f"request_id={public_envelope.get('request_id')}"
            )
            
            return job_id, public_state
            
        except Exception as e:
            logger.error(f"SubmitJob delegation failed: {e}")
            raise self._translate_error_to_public(e)
    
    async def get_job_status_delegated(
        self,
        job_id: str,
        public_envelope: dict,
    ) -> dict:
        """
        Delegate GetJobStatus to Kernel/QRTX.
        
        Returns:
            {
                "job_id": str,
                "state": JobState (public),
                "stage": str,
                "progress": float,
                "message": str,
                "error_code": str (if ERROR),
                "error_summary": str,
                "updated_at": Timestamp,
            }
        """
        try:
            if self.kernel_client._closed:
                await self.kernel_client.connect()
            
            # Delegate to Kernel
            kernel_response = await self.kernel_client.get_job_status(
                job_id=job_id,
                public_envelope=public_envelope,
            )
            
            # Map response to public API format
            public_response = {
                "job_id": kernel_response["job_id"],
                "state": self._map_internal_state_to_public(
                    kernel_response.get("state", "TASK_STATE_PENDING")
                ),
                "stage": kernel_response.get("stage", ""),
                "progress": kernel_response.get("progress", 0.0),
                "message": kernel_response.get("message", ""),
                "updated_at": kernel_response.get("updated_at"),
            }
            
            # Include error fields if present
            if kernel_response.get("error_code"):
                public_response["error_code"] = kernel_response["error_code"]
                public_response["error_summary"] = kernel_response.get("error_summary", "")
                public_response["error_details_ref"] = kernel_response.get(
                    "error_details_ref", ""
                )
            
            logger.info(
                f"GetJobStatus delegated to Kernel: job_id={job_id}, "
                f"state={public_response['state']}"
            )
            
            return public_response
            
        except Exception as e:
            logger.error(f"GetJobStatus delegation failed: {e}")
            raise self._translate_error_to_public(e)
    
    async def cancel_job_delegated(
        self,
        job_id: str,
        public_envelope: dict,
    ) -> bool:
        """
        Delegate CancelJob to Kernel/QRTX.
        
        Returns:
            True if cancellation was accepted, False otherwise.
        """
        try:
            if self.kernel_client._closed:
                await self.kernel_client.connect()
            
            # Delegate to Kernel
            kernel_response = await self.kernel_client.cancel_job(
                job_id=job_id,
                public_envelope=public_envelope,
            )
            
            accepted = kernel_response.get("accepted", False)
            reason = kernel_response.get("reason_code", "UNKNOWN")
            
            logger.info(
                f"CancelJob delegated to Kernel: job_id={job_id}, "
                f"accepted={accepted}, reason={reason}"
            )
            
            return accepted
            
        except Exception as e:
            logger.error(f"CancelJob delegation failed: {e}")
            raise self._translate_error_to_public(e)
    
    async def get_job_results_delegated(
        self,
        job_id: str,
        public_envelope: dict,
    ) -> dict:
        """
        Delegate GetJobResults to Kernel/QRTX.
        
        Returns:
            {
                "job_id": str,
                "state": JobState (public),
                "counts": dict,
                "metadata": dict,
                "qfs_result_ref": str,
                "error_code": str (if ERROR),
                "error_summary": str,
                "completed_at": Timestamp,
            }
        """
        try:
            if self.kernel_client._closed:
                await self.kernel_client.connect()
            
            # Delegate to Kernel
            kernel_response = await self.kernel_client.get_job_results(
                job_id=job_id,
                public_envelope=public_envelope,
            )
            
            # Map response to public API format
            public_response = {
                "job_id": kernel_response["job_id"],
                "state": self._map_internal_state_to_public(
                    kernel_response.get("state", "TASK_STATE_PENDING")
                ),
                "counts": kernel_response.get("counts", {}),
                "metadata": kernel_response.get("metadata", {}),
                "qfs_result_ref": kernel_response.get("qfs_result_ref", ""),
                "completed_at": kernel_response.get("completed_at"),
            }
            
            # Include error fields if present
            if kernel_response.get("error_code"):
                public_response["error_code"] = kernel_response["error_code"]
                public_response["error_summary"] = kernel_response.get("error_summary", "")
                public_response["error_details_ref"] = kernel_response.get(
                    "error_details_ref", ""
                )
            
            logger.info(
                f"GetJobResults delegated to Kernel: job_id={job_id}, "
                f"state={public_response['state']}"
            )
            
            return public_response
            
        except Exception as e:
            logger.error(f"GetJobResults delegation failed: {e}")
            raise self._translate_error_to_public(e)
    
    async def stream_job_updates_delegated(
        self,
        job_id: str,
        last_event_seq: int,
        public_envelope: dict,
    ) -> AsyncIterator[dict]:
        """
        Delegate StreamJobUpdates to Kernel/QRTX.
        
        Yields public JobUpdate messages with mapped states.
        """
        try:
            if self.kernel_client._closed:
                await self.kernel_client.connect()
            
            # Delegate to Kernel and map responses
            async for kernel_update in self.kernel_client.stream_job_updates(
                job_id=job_id,
                last_event_seq=last_event_seq,
                public_envelope=public_envelope,
            ):
                # Map internal update to public update
                public_update = {
                    "job_id": job_id,
                    "event_seq": kernel_update.get("event_seq", 0),
                    "state": self._map_internal_state_to_public(
                        kernel_update.get("state", "TASK_STATE_PENDING")
                    ),
                    "stage": kernel_update.get("stage", ""),
                    "progress": kernel_update.get("progress", 0.0),
                    "message": kernel_update.get("message", ""),
                    "timestamp": kernel_update.get("timestamp"),
                }
                
                yield public_update
            
        except Exception as e:
            logger.error(f"StreamJobUpdates delegation failed: {e}")
            raise self._translate_error_to_public(e)
    
    def _map_internal_state_to_public(self, internal_state: str) -> str:
        """
        Map Kernel internal TaskState to public JobState.
        
        Ensures Wave 1 public state names are preserved:
        - PENDING, COMPILING, QUEUED, RUNNING, DONE, ERROR, CANCELLED, TIMEOUT
        """
        return self._state_mapping.get(internal_state, "PENDING")
    
    def _translate_error_to_public(self, error: Exception) -> Exception:
        """
        Translate Kernel error to public error model.
        
        Maps to canonical errors in docs/reference/error-model.md.
        """
        # Placeholder: would implement full error translation
        return error
