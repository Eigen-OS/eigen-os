# Driver selection policy

Driver routing is explicit and deterministic:

* Explicit mode (default): caller passes a concrete `device_id` and registry
  resolves it to exactly one driver.
* Auto mode: caller passes `driver_selection=auto` and the manager selects
  among healthy AQO-capable devices using online status, queue depth and
  estimated wait time. If no candidate is suitable, the request fails closed.
* There is no implicit default provider (Qiskit/simulator/first driver).
* Driver override values are treated as consistency checks, not fallback.

This removes ambiguous fallback behavior and makes audit and debugging deterministic.