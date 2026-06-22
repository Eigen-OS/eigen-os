"""Stable symbolic rewrite pipeline for eigen-compiler.

This module exposes the deterministic compilation stages as explicit steps so
callers can inspect, invoke, and log parse/normalize/candidate generation/
legality/rewrite/AQO emission independently.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Callable, TypeVar

from .compiler import (
    AQO_VERSION,
    CompileRequestContext,
    CompilationResult,
    CompilerPassPipeline,
    CompilerValidationError,
    DistributedCompileConfig,
    _build_aqo_payload,
    _build_compiler_pass_pipeline,
    _canonical_json_bytes,
    _canonical_json_text,
    _call_name,
    _compiler_replay_bundle,
    _collect_expectation_annotation,
    _collect_observable_bindings,
    _collect_operations,
    _collect_params,
    _distributed_compile_config,
    _enforce_resource_limits,
    _normalize_options,
    _normalize_request_context,
    _parse_python_source,
    _relabel_violations,
    _reject_dynamic_control_flow,
    _reject_forbidden_calls,
    _reject_forbidden_imports,
    _resolve_source_bytes,
    _validate_lowering_payload,
    _validate_single_entrypoint,
)
from .errors import FieldViolation
from .validation import backend_contract_payload, resolve_workload_profile, validate_workload_profile, workload_profile_payload

T = TypeVar("T")
StageObserver = Callable[[str, float, str], None]

SYMBOLIC_REWRITE_STAGE_ORDER = (
    "parse",
    "normalize",
    "candidate_generation",
    "legality_check",
    "rewrite",
    "emit_aqo",
)


def _run_stage(stage: str, observer: StageObserver | None, fn: Callable[[], T]) -> T:
    start = perf_counter()
    try:
        result = fn()
    except Exception:
        if observer is not None:
            observer(stage, perf_counter() - start, "failure")
        raise
    if observer is not None:
        observer(stage, perf_counter() - start, "success")
    return result


def _stage_violation(field: str, description: str, *, stage: str, rule: str, pass_name: str) -> CompilerValidationError:
    return CompilerValidationError(
        violations=(
            FieldViolation(
                field=field,
                description=description,
                stage=stage,
                rule=rule,
                pass_name=pass_name,
            ),
        )
    )


@dataclass
class SymbolicRewriteState:
    source: bytes
    source_ref: str | None = None
    options: dict[str, str] | None = None
    request_context: dict[str, str] | None = None

    normalized_options: dict[str, str] = field(default_factory=dict)
    normalized_request_context: CompileRequestContext | None = None
    resolved_source: bytes = b""
    source_precedence: str = ""
    source_digest: str = ""
    tree: ast.AST | None = None

    params: dict[str, dict[str, object]] = field(default_factory=dict)
    observable_bindings: dict[str, dict[str, object]] = field(default_factory=dict)
    expectation_annotation: dict[str, object] | None = None
    operations: list[dict[str, object]] = field(default_factory=list)
    qubits: int = 0
    has_minimize: bool = False
    has_expectation: bool = False
    distributed: DistributedCompileConfig = field(
        default_factory=lambda: DistributedCompileConfig(
            enabled=False,
            target=None,
            partition_count=None,
            queue_provider=None,
            topology_hint=None,
        )
    )

    workload_profile: object | None = None
    workload_profile_json: str = ""
    backend_contract: dict[str, object] = field(default_factory=dict)
    backend_contract_json: str = ""
    request_digest: str = ""
    aqo_request_digest: str = ""

    candidate_aqo: dict[str, object] = field(default_factory=dict)
    legal_aqo: dict[str, object] = field(default_factory=dict)
    pass_pipeline: CompilerPassPipeline | None = None
    rewritten_aqo: dict[str, object] = field(default_factory=dict)
    aqo_bytes: bytes = b""
    aqo_digest: str = ""
    result: CompilationResult | None = None


class SymbolicRewritePipeline:
    """Public facade for the symbolic rewrite pipeline."""

    def __init__(self, *, observer: StageObserver | None = None) -> None:
        self._observer = observer

    def parse(
        self,
        source: bytes,
        *,
        source_ref: str | None = None,
        options: dict[str, str] | None = None,
        request_context: dict[str, str] | None = None,
    ) -> SymbolicRewriteState:
        """Parse source bytes and establish the normalized compile envelope."""

        def _parse() -> SymbolicRewriteState:
            normalized_options = _normalize_options(options)
            normalized_request_context = _normalize_request_context(request_context)
            resolved_source, source_precedence = _resolve_source_bytes(source, source_ref)
            source_digest = hashlib.sha256(resolved_source).hexdigest()
            try:
                tree = _parse_python_source(resolved_source)
            except CompilerValidationError as exc:
                raise CompilerValidationError(
                    violations=_relabel_violations(
                        exc.violations,
                        stage="parse",
                        rule="compiler.symbolic.parse",
                        pass_name="parse",
                    )
                ) from None
            return SymbolicRewriteState(
                source=source,
                source_ref=source_ref,
                options=options,
                request_context=request_context,
                normalized_options=normalized_options,
                normalized_request_context=normalized_request_context,
                resolved_source=resolved_source,
                source_precedence=source_precedence,
                source_digest=source_digest,
                tree=tree,
            )

        return _run_stage("parse", self._observer, _parse)

    def normalize(self, state: SymbolicRewriteState) -> SymbolicRewriteState:
        """Validate and lower the parsed tree into symbolic rewrite inputs."""

        def _normalize() -> SymbolicRewriteState:
            if state.tree is None:
                raise _stage_violation(
                    "tree",
                    "parse stage must run before normalize",
                    stage="normalize",
                    rule="compiler.symbolic.normalize.precondition",
                    pass_name="normalize",
                )

            try:
                violations = (
                    _enforce_resource_limits(state.tree)
                    + _reject_forbidden_imports(state.tree)
                    + _reject_forbidden_calls(state.tree)
                    + _reject_dynamic_control_flow(state.tree)
                    + _validate_single_entrypoint(state.tree)
                )
                if violations:
                    raise CompilerValidationError(violations=violations)
                params, param_violations = _collect_params(state.tree)
                if param_violations:
                    raise CompilerValidationError(violations=param_violations)
                observable_bindings, observable_violations = _collect_observable_bindings(state.tree)
                if observable_violations:
                    raise CompilerValidationError(violations=observable_violations)
                expectation_annotation = _collect_expectation_annotation(state.tree, observable_bindings)
                operations, qubits = _collect_operations(state.tree, params)
                has_minimize = any(
                    isinstance(node, ast.Call) and _call_name(node.func) == "minimize" for node in ast.walk(state.tree)
                )
                has_expectation = any(
                    isinstance(node, ast.Call) and _call_name(node.func) == "ExpectationValue"
                    for node in ast.walk(state.tree)
                )
                distributed = _distributed_compile_config(state.normalized_options)
            except CompilerValidationError as exc:
                raise CompilerValidationError(
                    violations=_relabel_violations(
                        exc.violations,
                        stage="normalize",
                        rule="compiler.symbolic.normalize",
                        pass_name="normalize",
                    )
                ) from None

            return replace(
                state,
                params=params,
                observable_bindings=observable_bindings,
                expectation_annotation=expectation_annotation,
                operations=operations,
                qubits=qubits,
                has_minimize=has_minimize,
                has_expectation=has_expectation,
                distributed=distributed,
            )

        return _run_stage("normalize", self._observer, _normalize)

    def generate_candidates(self, state: SymbolicRewriteState) -> SymbolicRewriteState:
        """Build the candidate AQO payload before legality and rewrite checks."""

        def _generate() -> SymbolicRewriteState:
            if not state.operations:
                raise _stage_violation(
                    "operations",
                    "normalize stage must populate operations before candidate generation",
                    stage="candidate_generation",
                    rule="compiler.symbolic.candidate_generation.precondition",
                    pass_name="candidate_generation",
                )

            try:
                workload_profile, selection_violations = resolve_workload_profile(
                    state.normalized_options,
                    has_expectation=state.has_expectation,
                    has_minimize=state.has_minimize,
                )
                if selection_violations:
                    raise CompilerValidationError(violations=selection_violations)

                profile_violations = validate_workload_profile(
                    workload_profile,
                    state.normalized_options,
                    source_ref_present=state.source_ref is not None,
                    has_expectation=state.has_expectation,
                    has_minimize=state.has_minimize,
                )
                if profile_violations:
                    raise CompilerValidationError(violations=profile_violations)

                workload_profile_json = _canonical_json_text(workload_profile_payload(workload_profile))
                backend_contract = backend_contract_payload(workload_profile, state.normalized_options)
                backend_contract_json = _canonical_json_text(backend_contract)

                request_context_payload = (
                    state.normalized_request_context.__dict__ if state.normalized_request_context is not None else {}
                )
                request_digest_payload = {
                    "options": state.normalized_options,
                    "request_context": request_context_payload,
                    "source_sha256": state.source_digest,
                    "advisory_snapshot": {"model_version": "", "policy_snapshot_version": ""},
                }
                aqo_request_digest = hashlib.sha256(_canonical_json_bytes(request_digest_payload)).hexdigest()

                request_payload = {
                    "options": state.normalized_options,
                    "request_context": request_context_payload,
                    "source_precedence": state.source_precedence,
                    "workload_profile": getattr(workload_profile, "kind", ""),
                    "workload_profile_json": workload_profile_json,
                    "source_ref": state.source_ref or "",
                    "source_sha256": state.source_digest,
                    "advisory_snapshot": {"model_version": "", "policy_snapshot_version": ""},
                }
                request_digest = hashlib.sha256(_canonical_json_bytes(request_payload)).hexdigest()

                candidate_aqo = _build_aqo_payload(
                    qubits=state.qubits,
                    operations=state.operations,
                    params=state.params,
                    source_digest=state.source_digest,
                    source_ref=state.source_ref,
                    request_digest=aqo_request_digest,
                    has_expectation=state.has_expectation,
                    has_minimize=state.has_minimize,
                    observable_bindings=state.observable_bindings,
                    expectation_annotation=state.expectation_annotation,
                    distributed=state.distributed,
                )
            except CompilerValidationError as exc:
                raise CompilerValidationError(
                    violations=_relabel_violations(
                        exc.violations,
                        stage="candidate_generation",
                        rule="compiler.symbolic.candidate_generation",
                        pass_name="candidate_generation",
                    )
                ) from None

            return replace(
                state,
                workload_profile=workload_profile,
                workload_profile_json=workload_profile_json,
                backend_contract=backend_contract,
                backend_contract_json=backend_contract_json,
                request_digest=request_digest,
                aqo_request_digest=aqo_request_digest,
                candidate_aqo=candidate_aqo,
            )

        return _run_stage("candidate_generation", self._observer, _generate)

    def check_legality(self, state: SymbolicRewriteState) -> SymbolicRewriteState:
        """Validate the candidate AQO and build the legal rewrite pipeline."""

        def _check() -> SymbolicRewriteState:
            if not state.candidate_aqo:
                raise _stage_violation(
                    "candidate_aqo",
                    "candidate generation must run before legality check",
                    stage="legality_check",
                    rule="compiler.symbolic.legality_check.precondition",
                    pass_name="legality_check",
                )

            try:
                legal_aqo = _validate_lowering_payload(state.candidate_aqo)
                pass_pipeline = _build_compiler_pass_pipeline(
                    qubits=state.qubits,
                    operations=state.operations,
                    params=state.params,
                    source_digest=state.source_digest,
                    source_precedence=state.source_precedence,
                    request_digest=state.aqo_request_digest,
                    has_expectation=state.has_expectation,
                    has_minimize=state.has_minimize,
                    observable_bindings=state.observable_bindings,
                    expectation_annotation=state.expectation_annotation,
                    distributed=state.distributed,
                )
            except CompilerValidationError as exc:
                raise CompilerValidationError(
                    violations=_relabel_violations(
                        exc.violations,
                        stage="legality_check",
                        rule="compiler.symbolic.legality_check",
                        pass_name="legality_check",
                    )
                ) from None

            return replace(state, legal_aqo=legal_aqo, pass_pipeline=pass_pipeline)

        return _run_stage("legality_check", self._observer, _check)

    def rewrite(self, state: SymbolicRewriteState) -> SymbolicRewriteState:
        """Materialize the rewritten AQO payload from the legal pipeline."""

        def _rewrite() -> SymbolicRewriteState:
            if state.pass_pipeline is None:
                raise _stage_violation(
                    "pass_pipeline",
                    "legality check must run before rewrite",
                    stage="rewrite",
                    rule="compiler.symbolic.rewrite.precondition",
                    pass_name="rewrite",
                )
            return replace(state, rewritten_aqo=state.pass_pipeline.aqo)

        return _run_stage("rewrite", self._observer, _rewrite)

    def emit_aqo(self, state: SymbolicRewriteState) -> CompilationResult:
        """Canonicalize the AQO payload and return the final compilation result."""

        def _emit() -> CompilationResult:
            aqo = state.rewritten_aqo or state.legal_aqo or state.candidate_aqo
            aqo_bytes = _canonical_json_bytes(aqo)
            aqo_digest = hashlib.sha256(aqo_bytes).hexdigest()

            pass_pipeline = state.pass_pipeline or CompilerPassPipeline(records=(), aqo=aqo)
            compiler_stage_order = list(SYMBOLIC_REWRITE_STAGE_ORDER)
            handoff_stage_order = list(SYMBOLIC_REWRITE_STAGE_ORDER)

            replay_bundle, replay_bundle_sha256 = _compiler_replay_bundle(
                request_context=state.normalized_request_context or CompileRequestContext(),
                workload_profile=getattr(state.workload_profile, "kind", ""),
                source_precedence=state.source_precedence,
                source_digest=state.source_digest,
                request_digest=state.request_digest,
                aqo_digest=aqo_digest,
                compiler_stage_order=compiler_stage_order,
                handoff_stage_order=handoff_stage_order,
                pass_pipeline=pass_pipeline,
            )

            request_id = state.normalized_request_context.request_id if state.normalized_request_context else ""
            trace_id = state.normalized_request_context.trace_id if state.normalized_request_context else ""
            traceparent = state.normalized_request_context.traceparent if state.normalized_request_context else ""

            decision_lineage = {
                "contract_version": "1.0.0",
                "compiler_contract_version": "1.0.0",
                "optimizer_contract_version": "1.0.0",
                "source_precedence": state.source_precedence,
                "stage_order": handoff_stage_order,
                "request_id": request_id,
                "trace_id": trace_id,
                "traceparent": traceparent,
                "workload_profile": getattr(state.workload_profile, "kind", ""),
                "source_sha256": state.source_digest,
                "aqo_sha256": aqo_digest,
                "request_sha256": state.request_digest,
                "replay_mode": "deterministic",
                "replay_bundle_sha256": replay_bundle_sha256,
                "model_snapshot": replay_bundle["model_snapshot"],
            }
            observability = {
                "contract_version": "1.0.0",
                "trace_fields": ["request_id", "trace_id", "traceparent"],
                "metric_fields": ["rpc", "stage", "outcome", "elapsed_ms"],
                "metric_bounds": {
                    "labels_bounded": True,
                    "request_ids_in_metrics": False,
                    "trace_ids_in_metrics": False,
                    "tenant_ids_in_metrics": False,
                    "project_ids_in_metrics": False,
                },
                "lineage_sha256": state.request_digest,
            }
            explainability = {
                "contract_version": "1.0.0",
                "decision": "compiler_to_optimizer_handoff",
                "trace_fields": ["request_id", "trace_id", "traceparent"],
                "lineage": decision_lineage,
                "bounded_fields": [
                    "request_id",
                    "trace_id",
                    "traceparent",
                    "source_sha256",
                    "aqo_sha256",
                    "request_sha256",
                    "replay_bundle_sha256",
                ],
            }
            compiler_diagnostics = {
                "contract_version": "1.0.0",
                "stage_order": compiler_stage_order,
                "workload_profile": getattr(state.workload_profile, "kind", ""),
                "backend_contract": state.backend_contract,
                "decision_lineage": {
                    **decision_lineage,
                    "stage_order": compiler_stage_order,
                },
                "replay": replay_bundle,
                "observability": observability,
                "explainability": {
                    **explainability,
                    "lineage": {
                        **decision_lineage,
                        "stage_order": compiler_stage_order,
                    },
                },
            }
            metadata = {
                "compiler": "eigen-compiler",
                "compiler_contract_version": "1.0.0",
                "eigen_lang_version": "1.0",
                "aqo_version": AQO_VERSION,
                "input_bytes": str(len(state.source)),
                "source_sha256": state.source_digest,
                "aqo_sha256": aqo_digest,
                "request_sha256": state.request_digest,
                "source_precedence": state.source_precedence,
                "compiler_pass_pipeline_version": "1.0.0",
                "compiler_passes_json": _canonical_json_text(
                    {
                        "version": "1.0.0",
                        "passes": [
                            {
                                "name": record.name,
                                "kind": record.kind,
                                "rule": record.rule,
                                "preconditions": list(record.preconditions),
                                "postconditions": list(record.postconditions),
                                "input": record.input,
                                "output": record.output,
                            }
                            for record in pass_pipeline.records
                        ],
                    }
                ),
                "compiler_replay_json": _canonical_json_text(replay_bundle),
                "compiler_replay_sha256": replay_bundle_sha256,
                "workload_profile": getattr(state.workload_profile, "kind", ""),
                "workload_profile_json": state.workload_profile_json,
                "backend_contract_version": "1.0.0",
                "backend_contract_json": state.backend_contract_json,
                "compiler_diagnostics_json": _canonical_json_text(compiler_diagnostics),
                "decision_lineage_json": _canonical_json_text(decision_lineage),
                "observability_json": _canonical_json_text(observability),
                "explainability_json": _canonical_json_text(explainability),
            }
            if state.has_minimize:
                metadata["hybrid_plan_marker"] = "minimize"
            if state.source_ref:
                metadata["source_ref"] = state.source_ref
            if state.distributed.enabled:
                metadata["distributed.execution_metadata_version"] = "1.0.0"
                metadata["distributed.topology_hints_version"] = "1.0.0"
                metadata["distributed.enabled"] = "true"
                metadata["distributed.target"] = state.distributed.target or "cluster"
                metadata["distributed.partition_count"] = str(state.distributed.partition_count or 1)
                metadata["distributed.topology_hint"] = state.distributed.topology_hint or "data_parallel"
                if state.distributed.queue_provider:
                    metadata["distributed.queue_provider"] = state.distributed.queue_provider

            result = CompilationResult(aqo_json=aqo_bytes, metadata=metadata)
            state.aqo_bytes = aqo_bytes
            state.aqo_digest = aqo_digest
            state.result = result
            return result

        return _run_stage("emit_aqo", self._observer, _emit)

    def compile(
        self,
        source: bytes,
        *,
        source_ref: str | None = None,
        options: dict[str, str] | None = None,
        request_context: dict[str, str] | None = None,
    ) -> CompilationResult:
        """Convenience helper that runs all symbolic rewrite stages."""

        state = self.parse(
            source,
            source_ref=source_ref,
            options=options,
            request_context=request_context,
        )
        state = self.normalize(state)
        state = self.generate_candidates(state)
        state = self.check_legality(state)
        state = self.rewrite(state)
        return self.emit_aqo(state)
