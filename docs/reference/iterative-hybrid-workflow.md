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
- **Checkpoint** persists the next candidate, opaque optimizer state, completed
  step/evaluation counters, and prior objective in the QFS checkpoint envelope.
  Resume restores exactly this state and never replays or invents evaluations.
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

## Terminal outcomes

| Reason | Meaning |
|---|---|
| `CONVERGED` | An objective or parameter tolerance was met. |
| `MAX_ITERATIONS` | The configured optimizer steps completed without convergence. |
| `FAILED` | Validation, Driver Manager evaluation, optimizer, checkpoint, or finalization failed. The first failure is retained deterministically. |
| `CANCELLED` | Cancellation was observed before an evaluation or optimizer step. |

An evaluator failure is terminal and propagates unchanged through the Kernel
result surface. The engine makes no provider-specific retry decision.

## Compatibility

This is an additive Kernel/AQO Hybrid IR runtime contract. Existing single-shot
`QuantumJob` execution is unchanged. Optimizer plugin API v`1.0.0` remains the
plugin boundary; the engine uses its existing initialize, step, state, restore,
and finalize operations.
