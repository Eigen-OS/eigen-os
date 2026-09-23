# Optimizer Plugin SDK and Runtime Contract v1

The Optimizer Plugin SDK is the execution boundary for iterative-hybrid optimizers. It is additive to the existing versioned `plugin_type = "optimizer"` manifest and lifecycle policy: manifests are discovered, validated for trust and compatibility, activated in the platform sandbox, then registered with this runtime. Workflow code selects an activated plugin by identifier and never imports plugin code or reads plugin artifacts directly.

## API and lifecycle

The API version is `1.0.0`. An optimizer implementation supplies `initialize`, `step`, `state`, `restore`, and `finalize`. The permitted lifecycle is `DISCOVERED → VALIDATED → ACTIVE → DEACTIVATED`; calls outside `ACTIVE` fail closed. Activation rejects a non-optimizer manifest type or an API-version mismatch.

`initialize` receives non-empty finite initial parameters plus bounded metadata.
`step` receives the parameter vector evaluated by the Kernel/Driver Manager path,
its finite objective value, an optional finite gradient of the same dimension,
and iteration context. When `max_iterations` is present, it must be positive and
the zero-based `iteration` must be smaller than that bound. The call returns the
next parameter vector, opaque deterministic state bytes, and bounded step
metadata. The SDK validates these invariants before mutating optimizer state.
An observation's parameter vector must exactly match the currently pending
candidate returned by `initialize`, `restore`, or the preceding `step`; stale,
cross-run, or substituted observations fail closed without changing state.
The next candidate is also required to remain finite. If a valid observation
would produce an infinite candidate (for example, after restoring an unusually
large finite trust-region radius), `step` rejects it and retains the previous
pending candidate and state.

This is a backward-compatible validation tightening: the optimizer-plugin
envelope and serialized state schema are unchanged. Callers should handle the
existing `InvalidInput` step failure and may safely retry or inspect the
unchanged state without restoring a checkpoint.
`state` and `restore` use deterministic JSON serialization of a typed state
record. Restore rejects malformed, non-finite, or internally inconsistent state,
so a restored optimizer produces the same next output for the same objective
observation. `finalize` releases runtime-local state only.

Plugins do **not** receive provider credentials, QFS handles, backend-execution APIs, filesystem or network APIs, or user source. The Driver Manager remains the sole circuit/provider boundary and QFS remains the durable checkpoint authority. The caller stores state bytes in the existing QFS checkpoint envelope; the SDK never writes checkpoints itself.

## Reference optimizer

`io.eigen.optimizer.cobyla` is the bundled deterministic COBYLA-compatible reference. It uses derivative-free coordinate trust-region polling: after each objective observation it either accepts the evaluated point or reverses direction and contracts its radius, then produces the next candidate. Thus `method: COBYLA` results in parameter changes driven by actual objective evaluations rather than a label-only selection.

A second optimizer only implements the same trait and is activated through the same lifecycle manager; generic iterative workflow orchestration does not need optimizer-specific code.

## Versioning and compatibility

This is an additive `MINOR` Plugin-envelopes and Kernel interface. Existing non-iterative workloads and plugin manifests keep their behavior. A future change that alters a required lifecycle method or serialized-state semantics is breaking and requires a `MAJOR` release.
