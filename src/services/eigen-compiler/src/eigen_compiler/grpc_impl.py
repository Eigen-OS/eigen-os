"""gRPC implementation for internal CompilationService."""

from __future__ import annotations

from collections import Counter, defaultdict
import logging
import re
import threading
from typing import Callable

import grpc

from .compiler import CompilerValidationError, compile_eigen_lang
from .errors import abort_invalid_argument
from .validation import validate_compile_circuit, validate_compile_job


_LOG = logging.getLogger("eigen_compiler")

_METRIC_LOCK = threading.Lock()
_RPC_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_STAGE_COUNT_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_STAGE_SECONDS_TOTALS: defaultdict[tuple[tuple[str, str], ...], float] = defaultdict(float)
_VALIDATION_FAILURE_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_AQO_DIGEST_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_REPLAY_TOTALS: Counter[tuple[tuple[str, str], ...]] = Counter()
_SEEN_AQO_DIGESTS: set[str] = set()

_STAGE_LABELS = {
    "request_validation",
    "parse",
    "validate_ast",
    "annotate",
    "lower_to_ir",
    "eigen_dpda",
    "canonicalize_aqo",
    "emit",
}


def _label_tuple(**labels: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((k, str(v)) for k, v in labels.items()))


def _fmt_labels(label_items: tuple[tuple[str, str], ...]) -> str:
    if not label_items:
        return ""
    rendered = ",".join(f'{k}="{v}"' for k, v in label_items)
    return f"{{{rendered}}}"


def _bump(counter: Counter[tuple[tuple[str, str], ...]], **labels: str) -> None:
    with _METRIC_LOCK:
        counter[_label_tuple(**labels)] += 1


def _bump_stage(stage: str, elapsed_seconds: float, outcome: str) -> None:
    if stage not in _STAGE_LABELS:
        stage = "emit"
    labels = _label_tuple(stage=stage, outcome=outcome)
    with _METRIC_LOCK:
        _STAGE_COUNT_TOTALS[labels] += 1
        _STAGE_SECONDS_TOTALS[labels] += elapsed_seconds


def _record_rpc(rpc: str, outcome: str) -> None:
    _bump(_RPC_TOTALS, rpc=rpc, outcome=outcome)


def _record_validation_failure(stage: str, reason: str) -> None:
    _bump(_VALIDATION_FAILURE_TOTALS, stage=stage, reason=reason)


def _record_digest_emitted(kind: str = "aqo") -> None:
    _bump(_AQO_DIGEST_TOTALS, kind=kind)


def _record_replay(kind: str = "duplicate") -> None:
    _bump(_REPLAY_TOTALS, kind=kind)


def reset_metrics() -> None:
    with _METRIC_LOCK:
        _RPC_TOTALS.clear()
        _STAGE_COUNT_TOTALS.clear()
        _STAGE_SECONDS_TOTALS.clear()
        _VALIDATION_FAILURE_TOTALS.clear()
        _AQO_DIGEST_TOTALS.clear()
        _REPLAY_TOTALS.clear()
        _SEEN_AQO_DIGESTS.clear()


def _validation_reason(violations) -> str:
    text = " ".join(v.description for v in violations).lower()
    if "not found" in text:
        return "not_found"
    if "limit exceeded" in text:
        return "resource_exhausted"
    if "unsupported" in text:
        return "unimplemented"
    return "invalid_argument"


def _render_counter_family(name: str, counter: Counter[tuple[tuple[str, str], ...]]) -> list[str]:
    lines = [f"# TYPE {name} counter"]
    for labels, value in sorted(counter.items(), key=lambda item: item[0]):
        lines.append(f"{name}{_fmt_labels(labels)} {int(value)}")
    return lines


def render_metrics_text() -> str:
    with _METRIC_LOCK:
        lines = [
            "# TYPE eigen_compiler_contract_info gauge",
            'eigen_compiler_contract_info{version="1.0.0"} 1',
        ]
        lines.extend(_render_counter_family("eigen_compiler_rpc_total", _RPC_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_stage_duration_seconds_count", _STAGE_COUNT_TOTALS))
        lines.append("# TYPE eigen_compiler_stage_duration_seconds_sum counter")
        for labels, value in sorted(_STAGE_SECONDS_TOTALS.items(), key=lambda item: item[0]):
            lines.append(f"eigen_compiler_stage_duration_seconds_sum{_fmt_labels(labels)} {value:.9f}")
        lines.extend(_render_counter_family("eigen_compiler_validation_failures_total", _VALIDATION_FAILURE_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_aqo_digest_emitted_total", _AQO_DIGEST_TOTALS))
        lines.extend(_render_counter_family("eigen_compiler_replay_compiles_total", _REPLAY_TOTALS))
        return "\n".join(lines) + "\n"


def _rpc_metadata_map(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def _request_context_from_rpc(request, context: grpc.ServicerContext) -> dict[str, str]:
    rpc_md = _rpc_metadata_map(context)
    request_md = request.request_metadata if request.HasField("request_metadata") else None

    def pick(field: str, header_key: str) -> str:
        if request_md is not None:
            value = getattr(request_md, field, "")
            if value:
                return value
        return rpc_md.get(header_key, "")

    deadline = pick("deadline", "x-eigen-deadline")
    if not deadline:
        remaining = context.time_remaining()
        if remaining is not None:
            deadline = f"{remaining:.6f}s"

    return {
        "request_id": pick("request_id", "x-eigen-request-id"),
        "trace_id": pick("trace_id", "x-eigen-trace-id"),
        "traceparent": pick("traceparent", "traceparent"),
        "deadline": deadline,
        "retry_policy": pick("retry_policy", "x-eigen-retry-policy"),
        "security_context": pick("security_context", "authorization"),
        "tenant_id": pick("tenant_id", "x-eigen-tenant-id"),
        "project_id": pick("project_id", "x-eigen-project-id"),
    }


def _circuit_format_value(types_pb, *names: str) -> int:
    for name in names:
        if hasattr(types_pb, name):
            return int(getattr(types_pb, name))
    raise AttributeError(f"None of the enum names exist: {names}")


class CompilationService:
    """Implementation of eigen.internal.v1.CompilationService."""

    def __init__(self, comp_pb, types_pb):
        self._comp_pb = comp_pb
        self._types_pb = types_pb

    def _compile_response(
        self,
        *,
        rpc: str,
        source: bytes,
        source_ref: str | None = None,
        options: dict[str, str] | None = None,
        request_context: dict[str, str] | None = None,
    ):
        result = compile_eigen_lang(
            source,
            source_ref=source_ref,
            options=options,
            observer=self._stage_observer(
                rpc=rpc,
                request_context=request_context or {},
            ),
        )

        return self._comp_pb.CompileCircuitResponse(
            circuit=self._types_pb.CircuitPayload(
                format=_circuit_format_value(
                    self._types_pb,
                    "CIRCUIT_FORMAT_AQO_JSON",
                    "AQO_JSON",
                ),
                data=result.aqo_json,
            ),
            metadata=result.metadata,
        )

    def _stage_observer(
        self,
        *,
        rpc: str,
        request_context: dict[str, str],
    ) -> Callable[[str, float, str], None]:

        def _observe(stage: str, elapsed_seconds: float, outcome: str) -> None:
            _bump_stage(stage, elapsed_seconds, outcome)

            _LOG.info(
                "compiler_stage",
                extra={
                    "rpc": rpc,
                    "stage": stage,
                    "outcome": outcome,
                    "elapsed_ms": round(elapsed_seconds * 1000.0, 3),
                    "request_id": request_context.get("request_id", ""),
                    "trace_id": request_context.get("trace_id", ""),
                    "traceparent": request_context.get("traceparent", ""),
                },
            )

        return _observe

    def CompileCircuit(self, request, context: grpc.ServicerContext):
        request_context = _request_context_from_rpc(request, context)

        _log_start(
            "CompilationService.CompileCircuit",
            "",
            request_context,
            context,
        )

        violations = validate_compile_circuit(request)

        if violations:
            _record_rpc("CompileCircuit", "failure")

            _record_validation_failure(
                "request_validation",
                _validation_reason(violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=violations,
            )

        source = request.source if request.source else b""
        source_ref = request.source_ref or None

        try:
            resp = self._compile_response(
                rpc="CompileCircuit",
                source=source,
                source_ref=source_ref,
                options=dict(request.options),
                request_context=request_context,
            )

            _record_rpc("CompileCircuit", "success")

            aqo_sha = resp.metadata.get("aqo_sha256", "")

            if aqo_sha:
                _record_digest_emitted("aqo")

                replay_detected = False

                with _METRIC_LOCK:
                    if aqo_sha in _SEEN_AQO_DIGESTS:
                        replay_detected = True
                    else:
                        _SEEN_AQO_DIGESTS.add(aqo_sha)

                if replay_detected:
                    _record_replay("duplicate")

            _log_end(
                "CompilationService.CompileCircuit",
                "",
                request_context,
                context,
                resp.metadata,
            )

            return resp

        except CompilerValidationError as exc:
            _record_rpc("CompileCircuit", "failure")

            _record_validation_failure(
                "compile",
                _validation_reason(exc.violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=exc.violations,
            )

    def CompileJob(self, request, context: grpc.ServicerContext):
        request_context = _request_context_from_rpc(request, context)

        _log_start(
            "CompilationService.CompileJob",
            request.job_id,
            request_context,
            context,
        )

        violations = validate_compile_job(request)

        if violations:
            _record_rpc("CompileJob", "failure")

            _record_validation_failure(
                "request_validation",
                _validation_reason(violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=violations,
            )

        source = request.source if request.source else b""
        source_ref = request.source_ref or None

        try:
            compiled = self._compile_response(
                rpc="CompileJob",
                source=source,
                source_ref=source_ref,
                options=dict(request.options),
                request_context=request_context,
            )

        except CompilerValidationError as exc:
            _record_rpc("CompileJob", "failure")

            _record_validation_failure(
                "compile",
                _validation_reason(exc.violations),
            )

            abort_invalid_argument(
                context,
                message="validation failed",
                violations=exc.violations,
            )

        resp = self._comp_pb.CompileJobResponse(
            job_id=request.job_id,
            circuit=compiled.circuit,
            metadata=compiled.metadata,
        )

        _record_rpc("CompileJob", "success")

        aqo_sha = compiled.metadata.get("aqo_sha256", "")

        if aqo_sha:
            _record_digest_emitted("aqo")

            replay_detected = False

            with _METRIC_LOCK:
                if aqo_sha in _SEEN_AQO_DIGESTS:
                    replay_detected = True
                else:
                    _SEEN_AQO_DIGESTS.add(aqo_sha)

            if replay_detected:
                _record_replay("duplicate")

        _log_end(
            "CompilationService.CompileJob",
            request.job_id,
            request_context,
            context,
            compiled.metadata,
        )

        return resp

    def OptimizeCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "OptimizeCircuit is not implemented")

    def ValidateCircuit(self, request, context: grpc.ServicerContext):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "ValidateCircuit is not implemented")

_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-(?P<trace_id>[0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _trace_fields(context: grpc.ServicerContext) -> tuple[str | None, str | None]:
    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    traceparent = md.get("traceparent")
    trace_id = md.get("x-eigen-trace-id")
    if trace_id is None and traceparent:
        match = _TRACEPARENT_RE.match(traceparent)
        if match:
            trace_id = match.group("trace_id")
    return trace_id, traceparent


def _log_start(
    method: str,
    job_id: str,
    request_context: dict[str, str],
    context: grpc.ServicerContext,
) -> None:
    trace_id, traceparent = _trace_fields(context)
    _LOG.info(
        "rpc_start",
        extra={
            "rpc": method,
            "job_id": job_id,
            "request_id": request_context.get("request_id", ""),
            "trace_id": trace_id or request_context.get("trace_id", ""),
            "traceparent": traceparent or request_context.get("traceparent", ""),
            "stage": "rpc",
            "outcome": "start",
        },
    )


def _log_end(
    method: str,
    job_id: str,
    request_context: dict[str, str],
    context: grpc.ServicerContext,
    metadata: dict[str, str] | None = None,
) -> None:
    trace_id, _traceparent = _trace_fields(context)
    metadata = metadata or {}
    _LOG.info(
        "rpc_end",
        extra={
            "rpc": method,
            "job_id": job_id,
            "request_id": request_context.get("request_id", ""),
            "trace_id": trace_id or request_context.get("trace_id", ""),
            "traceparent": request_context.get("traceparent", ""),
            "stage": "rpc",
            "outcome": "success",
            "source_sha256": metadata.get("source_sha256", ""),
            "aqo_sha256": metadata.get("aqo_sha256", ""),
        },
    )
