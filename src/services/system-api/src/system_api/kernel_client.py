"""Kernel Gateway client for System API lifecycle delegation."""

from __future__ import annotations

import asyncio
import json
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
    
    def _build_request_metadata(self, public_envelope: dict, source_service: str = "system-api", workload: object | None = None) -> dict:
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
            "workload": workload,
        }

    @staticmethod
    def _synthetic_traceparent(seed: str) -> str:
        digest = sha256(seed.encode("utf-8")).hexdigest()
        trace_id = digest[:32]
        span_id = digest[32:48]
        return f"00-{trace_id}-{span_id}-01"

    @staticmethod
    def _workload_context(metadata_kvs: dict, workload: object | None) -> object | None:
        raw = (metadata_kvs or {}).get("jobspec_workload")
        if isinstance(raw, str) and raw.strip():
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Ignoring malformed jobspec_workload metadata")
        return workload

    @staticmethod
    def _workload_proto(workload: object | None) -> kernel_pb.WorkloadContract | None:
        if workload is None:
            return None

        def _get(obj: object, key: str, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        def _nested(obj: object, key: str) -> object:
            if isinstance(obj, dict):
                return obj.get(key) or {}
            return getattr(obj, key, None) or {}

        def _kind_name(raw_kind: object) -> str:
            kind_aliases = {
                1: "QuantumJob",
                2: "HybridWorkflow",
                3: "DistributedJob",
                4: "BenchmarkJob",
                5: "PipelineJob",
                6: "ReplayJob",
                "QuantumJob": "QuantumJob",
                "HybridWorkflow": "HybridWorkflow",
                "DistributedJob": "DistributedJob",
                "BenchmarkJob": "BenchmarkJob",
                "PipelineJob": "PipelineJob",
                "ReplayJob": "ReplayJob",
                "WORKLOAD_FAMILY_KIND_QUANTUM_JOB": "QuantumJob",
                "WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW": "HybridWorkflow",
                "WORKLOAD_FAMILY_KIND_DISTRIBUTED_JOB": "DistributedJob",
                "WORKLOAD_FAMILY_KIND_BENCHMARK_JOB": "BenchmarkJob",
                "WORKLOAD_FAMILY_KIND_PIPELINE_JOB": "PipelineJob",
                "WORKLOAD_FAMILY_KIND_REPLAY_JOB": "ReplayJob",
            }
            try:
                return kind_aliases[int(raw_kind)]
            except Exception:
                return kind_aliases.get(raw_kind, "QuantumJob")

        kind_name = _kind_name(_get(workload, "kind", "QuantumJob"))
        kind_map = {
            "QuantumJob": kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_QUANTUM_JOB,
            "HybridWorkflow": kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_HYBRID_WORKFLOW,
            "DistributedJob": kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_DISTRIBUTED_JOB,
            "BenchmarkJob": kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_BENCHMARK_JOB,
            "PipelineJob": kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_PIPELINE_JOB,
            "ReplayJob": kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_REPLAY_JOB,
        }

        artifact = _nested(workload, "artifact_lineage")
        observability = _nested(workload, "observability")
        security = _nested(workload, "security")
        return kernel_pb.WorkloadContract(
            kind=kind_map.get(kind_name, kernel_pb.WorkloadFamilyKind.WORKLOAD_FAMILY_KIND_QUANTUM_JOB),
            execution_profile=str(_get(workload, "execution_profile", "")),
            replayable=bool(_get(workload, "replayable", False)),
            artifact_lineage=kernel_pb.WorkloadArtifactLineage(
                root_ref=str(_get(artifact, "root_ref", "")),
                parent_ref=str(_get(artifact, "parent_ref", "")),
                policy_snapshot_ref=str(_get(artifact, "policy_snapshot_ref", "")),
                execution_ref=str(_get(artifact, "execution_ref", "")),
            ),
            observability=kernel_pb.WorkloadObservability(
                traceparent=str(_get(observability, "traceparent", "")),
                trace_id=str(_get(observability, "trace_id", "")),
                trace_ref=str(_get(observability, "trace_ref", "")),
                emit_metrics=bool(_get(observability, "emit_metrics", False)),
            ),
            security=kernel_pb.WorkloadSecurity(
                tenant_id=str(_get(security, "tenant_id", "")),
                project_id=str(_get(security, "project_id", "")),
                service_identity=str(_get(security, "service_identity", "")),
                policy_snapshot_ref=str(_get(security, "policy_snapshot_ref", "")),
                fail_closed=bool(_get(security, "fail_closed", False)),
            ),
            backend_target=str(_get(workload, "backend_target", "")),
        )

    def _request_metadata_proto(self, public_envelope: dict, workload: object | None = None) -> kernel_pb.RequestMetadata:
        md = self._build_request_metadata(public_envelope, workload=workload)
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

        workload_obj = self._workload_proto(md.get("workload"))
        if workload_obj is not None:
            payload["workload"] = workload_obj
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
        workload: object | None = None,
    ) -> dict:
        if self._closed or self._stub is None:
            self.connect()

        assert self._stub is not None
        workload_context = self._workload_context(metadata_kvs, workload)
        request = kernel_pb.EnqueueJobRequest(
            metadata=self._request_metadata_proto(public_envelope, workload=workload_context),
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

    async def get_job_status(self, job_id: str, public_envelope: dict, workload: object | None = None) -> dict:
        if self._closed or self._stub is None:
            self.connect()

        assert self._stub is not None
        request = kernel_pb.GetJobStatusRequest(
            metadata=self._request_metadata_proto(public_envelope, workload=workload),
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

    async def cancel_job(self, job_id: str, public_envelope: dict, workload: object | None = None) -> dict:
        if self._closed or self._stub is None:
            self.connect()
        assert self._stub is not None

        request = kernel_pb.CancelJobRequest(
            metadata=self._request_metadata_proto(public_envelope, workload=workload),
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
        workload: object | None = None,
    ) -> AsyncIterator[dict]:
        if self._closed or self._stub is None:
            self.connect()

        assert self._stub is not None
        request = kernel_pb.StreamJobUpdatesRequest(
            metadata=self._request_metadata_proto(public_envelope, workload=workload),
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
            
    async def get_job_results(self, job_id: str, public_envelope: dict, workload: object | None = None) -> dict:
        if self._closed or self._stub is None:
            self.connect()
        assert self._stub is not None
        request = kernel_pb.GetJobResultsRequest(metadata=self._request_metadata_proto(public_envelope, workload=workload), job_id=job_id)
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
