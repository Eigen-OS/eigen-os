# Official provider rollback governance runbook

Use this runbook for Phase-8D official matrix incidents involving simulator, IBM Quantum, and AWS Braket.

## Failure classes

1. Provider outage.
2. Provider degradation (latency/noise/result-shape drift beyond tolerance policy).
3. Authentication failure.
4. Quota exhaustion / quota policy changes.

## Deterministic rollback controls

1. **Adapter pin**
   - Freeze adapter package/image digest to last-known-good release.
   - Re-run QDriver conformance smoke against the pinned build.
2. **Adapter quarantine**
   - Move unstable provider adapter to quarantine status in release gating and block new production routing.
   - Keep simulator route open for safe fallback paths.
3. **Official matrix demotion**
   - Demote provider from official matrix publication until conformance and tolerance checks are restored.
   - Publish demotion rationale and owner-approved re-entry criteria.

## Escalation map

- **Primary owners:** Drivers/Provider Integrations.
- **Secondary owners:** Runtime/QA.
- **Operations sign-off required:** SRE/Operations rotation.

Escalation path is considered complete only when all three owner groups acknowledge the incident timeline and rollback action.

## Rehearsal and evidence requirements

- Execute rollback rehearsal for each official provider (simulator, IBM, AWS).
- Every rehearsal must exercise all controls: adapter pin, adapter quarantine, matrix demotion.
- Every rehearsal must cover all failure classes.
- Record evidence in `docs/development/fixtures/phase8d/rollback_rehearsal_matrix_v1.json`.
- Link rehearsal artifact from `docs/development/phase-8d/phase-8d-exit-evidence-bundle.md` before milestone closure.
