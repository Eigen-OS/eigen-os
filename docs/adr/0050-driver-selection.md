# ADR 0050: explicit driver selection with opt-in auto scheduler

- Status: Accepted
- Date: 2026-09-22

## Context

The driver-manager had implicit behavior: there was effectively a default or
“first available” driver model. This created ambiguity when multiple drivers
exposed multiple devices.

The result:
- requests were not deterministic,
- debugging was unclear,
- tests depended on hidden default ordering,
- “auto” behavior was not auditable.

## Decision

1. Explicit device routing is the default and required path.
2. A concrete `device_id` must be used for normal execution.
3. `driver_selection=auto` is an explicit opt-in mode and never implicit.
4. Auto-selection is performed by the manager only among healthy AQO-capable
   devices, ranked by:
   - online status,
   - queue depth,
   - estimated wait time,
   - deterministic tie-break by driver name and device id.
5. If no candidate exists, execution fails closed.

## Consequences

Positive:
- no silent default driver,
- no implicit fallback to Qiskit or simulator,
- deterministic decision path,
- routing is observable and auditable.

Negative:
- clients must send concrete device ids or explicitly opt into auto mode,
- unsupported/empty candidate sets now fail fast instead of “best effort”.
