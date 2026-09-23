# Iterative Hybrid Workflow Runtime Contract v1

The Kernel-owned `IterativeHybridWorkflowEngine` executes the generic
`annotations.iterative_hybrid_workflow` IR produced by Eigen-Lang `minimize`.
It is generic infrastructure: it contains no VQE, H2, or provider-specific
logic. The Kernel binds each candidate to immutable AQO, evaluates the declared
objective through Driver Manager, and supplies only the observation to the
activated optimizer plugin.

## Lifecycle

The lifecycle is strictly ordered:
`initialize → evaluate → optimize → checkpoint → converge → finalize`.

- **Initialize** activates or restores the optimizer state and validates finite,
  non-empty parameters and convergence settings.
- **Evaluate** binds candidate parameters and invokes the Driver Manager
  objective boundary once. An initial evaluation happens before any optimizer
  step.
- **Optimize** supplies the evaluated parameters, objective, and iteration
  context to the activated optimizer plugin. Plugins cannot execute circuits or
  persist checkpoints.
- **Checkpoint** persists an immutable QFS `CheckpointEnvelopeV1` after every
  completed optimizer step. Its state payload contains the next candidate,
  opaque optimizer state, completed step/evaluation counters, prior objective,
  and the complete evaluation and optimizer-step histories accumulated so far.
  Each retained evaluation includes its parameter vector and finite objective
  value. Its pinned provenance contains the workflow ID, optimizer plugin
  ID/version/API version, seed, backend, shots, source checksum, compiled AQO
  artifact reference, configuration checksum, and compatibility metadata.
  These are identifiers and checksums only: credentials and raw provider
  payloads are never written to checkpoint or lineage artifacts. Resume reads
  the newest checkpoint only after envelope, payload-hash, runtime-version,
  and complete provenance validation. A corrupt or incompatible checkpoint
  fails the workflow rather than silently starting again at iteration zero.
  Restore begins at the checkpoint's next evaluation, so it neither replays nor invents evaluations.
- **Converge** evaluates the configured termination policy after each objective
  observation.
- **Finalize** runs for every terminal result, including failure and
  cancellation.

## Convergence and accounting

`max_iterations` limits completed optimizer steps. The engine also accepts
non-negative finite absolute-objective, relative-objective, and per-parameter
tolerances. Absolute convergence is `abs(objective) <= tolerance`. Relative
convergence compares consecutive observations using
`abs(current - previous) <= tolerance * max(abs(previous), 1)`. Parameter
convergence requires every candidate coordinate to differ from the preceding
evaluated candidate by no more than its tolerance.

Each evaluation record includes the completed-step iteration, one-based actual
evaluation count, evaluated parameters, objective value, elapsed time, optimizer
state, and bounded metadata. Results and metrics consumers can rely on:

- `claimed_iterations == actual_optimizer_steps`;
- for the initial-evaluate model,
  `actual_evaluations >= actual_optimizer_steps + 1` for successful/max-iteration
  terminal runs; and
- counters describe completed work only, including after a failure.

When a workflow resumes, the Kernel restores the persisted histories before
performing the next evaluation. Therefore the final `WorkflowReport` and its
VQE projection account for the entire execution rather than only the segment
that ran after the last resume. Checkpoints written by earlier runtimes remain
readable: absent history fields decode as empty histories. They cannot,
however, reconstruct observations that were never persisted, so a report
resumed from a legacy checkpoint only includes observations made after that
checkpoint.

## Terminal outcomes

| Reason | Meaning |
|---|---|
| `CONVERGED` | An objective or parameter tolerance was met. |
| `MAX_ITERATIONS` | The configured optimizer steps completed without convergence. |
| `FAILED` | Validation, Driver Manager evaluation, optimizer, checkpoint validation/persistence, or finalization failed. The first failure is retained deterministically. |
| `CANCELLED` | Cancellation was observed before an evaluation or optimizer step. |

An evaluator failure is terminal and propagates unchanged through the Kernel
result surface. The engine makes no provider-specific retry decision.

## VQE result projection

VQE is a minimization use of the generic workflow. Once a workflow report is
available, the Kernel exposes the stable `VqeResult` projection (schema version
`1.0.0`) for VQE consumers; it does not give VQE-specific privileges to an
optimizer plugin or Driver Manager.

| Field | Meaning |
|---|---|
| `termination_reason` | The terminal workflow reason: `CONVERGED`, `MAX_ITERATIONS`, `FAILED`, or `CANCELLED`. |
| `optimal_energy` | The lowest finite objective from a completed evaluation, interpreted as VQE energy. `NaN` and positive or negative infinity are ignored. It is absent if no finite evaluation completed. |
| `optimal_parameters` | The parameter vector evaluated for `optimal_energy`; absent together with the energy. |
| `optimal_evaluation` | The one-based evaluation number that produced the optimum. Equal energies select the earliest evaluation deterministically. |
| `claimed_iterations`, `actual_optimizer_steps`, `actual_evaluations` | Completed-work counters with the accounting guarantees above. |
| `error` | Terminal failure text, if any. A partial optimum remains available when earlier evaluations completed before a later failure. |

The result intentionally reports the best **observed finite** energy rather than
the last candidate or checkpoint cursor. Consumers must treat an absent optimum
as an unsuccessful evaluation, not as a zero energy or an empty parameter
vector. Non-finite evaluator output must not be presented as an optimum.

The generic `WorkflowReport` retains the full evaluation and optimizer-step
history for diagnostics; `VqeResult` is its concise result surface.

## Compatibility

This is an additive Kernel/AQO Hybrid IR runtime contract. Existing single-shot
`QuantumJob` execution is unchanged. Optimizer plugin API v`1.0.0` remains the
plugin boundary; the engine uses its existing initialize, step, state, restore,
and finalize operations.

Checkpoint persistence and restore are likewise additive QFS behavior. The
existing `CheckpointEnvelopeV1` schema and runtime compatibility rules remain
unchanged; iterative workflows only use that envelope to persist their cursor
and optimizer state. Consequently, this contract has a **MINOR** version
impact, is backward-compatible for existing workloads and checkpoint readers,
and requires no migration.

## Checkpoint layout and replay lineage

For workflow `<workflow-id>` and completed optimizer step `<N>`, the Kernel
writes immutable artifacts under
`qfs://jobs/<workflow-id>/checkpoints/iterative/<N padded to 20 digits>/`:

- `state.json` is the hash-verified serialized cursor and opaque optimizer
  state; and
- `envelope.json` is the QFS checkpoint envelope referring to that payload and
  the compiled artifact lineage.

`run_or_resume` selects the lexically latest envelope, validates it against the
current runtime and all pinned deterministic inputs, restores the optimizer,
and continues with cursor `N + 1`. No “best effort” substitution of optimizer
state, backend, plugin, source, compiled artifact, seed, shots, or
configuration is permitted. Backend result comparison remains subject to the
configured backend determinism tolerance; checkpoint cursor and provenance
comparison are exact.
