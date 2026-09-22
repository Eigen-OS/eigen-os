# Product 1.0 Wave 6 Exit Evidence Bundle

**Wave:** Product 1.0 Wave 6 — Driver Manager and QDriver final contract  
**Status:** Template / planning baseline

---

## Evidence to collect before closure

### Contract evidence
- Final QDriver contract diff
- Internal gRPC proto / binding diff
- Driver Manager capability registry / device profile evidence
- Provider matrix and tolerance profile evidence

### Validation evidence
- QDriver conformance report
- Simulator reference backend report
- Provider parity / tolerance suite report
- Secret lifecycle / sandbox policy test report
- Error normalization test report

### Operational evidence
- Structured logs sample
- Metrics snapshot with bounded labels
- Trace continuity sample from kernel to provider adapter
- Rollback / quarantine rehearsal record

### Governance evidence
- Inventory row update
- Manifest row update
- Compatibility report
- Release readiness checklist
- Migration notes for any tightened behavior

### W6-04 normalized results and error mapping evidence

- Normalization matrix
  - counts are sorted and backend-independent
  - metadata keys are deterministic and string-normalized
  - execution timing is rounded to a stable precision
- Error mapping report
  - retryable backend outages and quota pressure include `RetryInfo`
  - backend precondition failures preserve `PreconditionFailure`
  - unsupported payload formats fail closed with `UNIMPLEMENTED`
- Conformance assertions
  - response shape is stable across compatible backends
  - unsupported-operation errors are deterministic

### W6-06 official simulator reference backend and provider matrix parity evidence

- Provider matrix report
  - simulator remains the canonical conformance backend
  - official targets are versioned as simulator / ibm / aws
  - tolerance policy is pinned to `1.0.0`
- Tolerance profile artifact
  - canonical workload is `phase8d_canonical_workload_v1`
  - result-shape drift is governed by the versioned policy fixture
  - latency and noise drift remain bounded by the policy thresholds
- Rollback / demotion rehearsal evidence
  - rollback controls are covered by the rollback governance fixture
  - demotion paths remain auditable
  - provider drift remains fail-closed in conformance gating

### W6-07 observability and reproducibility evidence

- Metrics snapshot
  - bounded driver-manager metrics exported
  - labels remain enumerated and non-sensitive
- Trace continuity report
  - `traceparent` is preserved into DM logs and request handling
  - `trace_id` is derived consistently at the DM boundary
- Release evidence bundle
  - rollback and quarantine evidence links to this bundle
  - release artifacts remain reproducible from the versioned fixtures

---

## Closure note

Wave 6 is not ready to close until each evidence slot above is attached to the issue pack or referenced by the release checklist.

## W6-03 Session lifecycle evidence

- Session lifecycle fixture:
  - created
  - active
  - refreshed
  - invalidated
  - closed

- Calibration lifecycle evidence:
  - artifact reference stable
  - rollback does not mutate reference

- Restart behavior report:
  - invalid sessions are not reused
  - compatible sessions are reused deterministically
  