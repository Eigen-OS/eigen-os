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
  