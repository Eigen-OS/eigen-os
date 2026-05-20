# Stage-9A rollback runbook (LQM / QFS L2 / policy engine / driver trust)

Use this runbook for Stage-9A incidents where production safety depends on deterministic rollback to known-good core behavior.

## Scope and objective

This runbook covers rollback execution for the four Stage-9A critical paths:

1. LQM atomic allocation and offline failover regressions.
2. QFS L2 retention/quota/restore-cache regressions.
3. Policy-engine (PDP) enforcement regressions.
4. Driver trust/signature enforcement regressions.

**MTTR target:** restore service safety and deterministic behavior in **<= 30 minutes** from incident declaration.

## Failure classes

1. **Safety regression**: incorrect qubit ownership, restore corruption risk, or unauthorized action allowed.
2. **Availability regression**: persistent allocation failure, restore-path outage, or policy deadlock causing fail-stop.
3. **Conformance regression**: drift from documented contract/error taxonomy/signature policy.
4. **Release-gate regression**: CI fail-closed gates tripped by drift or trust-policy mismatch after rollout.

## Rollback levers (authorized controls)

All rollback actions require incident ticket + operator identity recorded in audit trail.

1. **Pin to last-known-good artifact**
   - Pin runtime component version/digest for impacted domain (LQM, QFS, PDP, driver-manager).
   - Re-run smoke/conformance checks for the pinned version before traffic normalization.
2. **Quarantine**
   - Quarantine affected driver/provider/build profile from production routing.
   - Keep simulator/local-safe profile available for degraded but deterministic execution.
3. **Gate-disable policy (break-glass, time-bound)**
   - Allowed only for non-safety gates and only with dual approval (component owner + SRE).
   - Mandatory expiry window: <= 24h, tracked with explicit rollback/remediation ticket.
   - Never disable signature verification or PDP deny-by-default controls.

## Approval and escalation policy

- **Incident commander (IC):** on-call SRE.
- **Primary owner (by domain):**
  - LQM: Runtime/Kernel owner.
  - QFS L2: Runtime/Data Fabric owner.
  - Policy engine: Security owner.
  - Driver trust: Drivers/Platform Integrity owner.
- **Required approvers for gate-disable policy:** primary owner + SRE lead.
- **Escalation SLA:** if no stable rollback state in 15 minutes, escalate to Engineering Director + Security lead.

## Drill-backed rollback procedures

### A) LQM regression rollback

1. Declare incident with domain `lqm` and freeze rollout.
2. Pin LQM + dependent HAL adapter to last-known-good digest.
3. Drain/stop new allocations on affected nodes.
4. Validate anti-double-booking invariants using allocation audit checks.
5. Re-enable traffic gradually and monitor allocation error classes.

**Exit checks**
- No duplicate qubit assignment events.
- Allocation and deallocation error taxonomy matches spec.
- Offline/reconnect state transitions return to deterministic profile.

### B) QFS L2 regression rollback

1. Declare incident with domain `qfs-l2` and freeze retention-policy updates.
2. Pin QFS L2 service/image and restore-cache policy bundle.
3. Quarantine nodes with restore-cache corruption indicators.
4. Run checkpoint restore smoke matrix on pinned version.
5. Resume retention/quota tasks after deterministic recovery confirmation.

**Exit checks**
- Restore success rate and integrity checks back within SLO.
- Deterministic quota exceedance error classes restored.
- No unrecoverable checkpoint artifacts introduced during incident window.

### C) Policy engine regression rollback

1. Declare incident with domain `pdp` and freeze policy-bundle promotion.
2. Pin policy bundle + policy engine runtime to last-known-good.
3. If outage persists, enable time-bound break-glass for non-safety gate only (dual approval required).
4. Re-run authorization conformance set (allow/deny/audit reason codes).
5. Resume normal policy update flow after conformance is green.

**Exit checks**
- Deny-by-default behavior is intact.
- Decision reason codes and audit metadata stable.
- Cross-tenant unauthorized-path negatives pass.

### D) Driver trust regression rollback

1. Declare incident with domain `driver-trust` and freeze driver onboarding.
2. Pin official driver matrix to previous signed version.
3. Quarantine affected driver artifacts/providers from routing.
4. Re-run signature and metadata conformance on pinned matrix.
5. Re-enable provider routing only after trusted profile is green.

**Exit checks**
- Unsigned/tampered driver rejection restored.
- Official matrix fixture validation passes.
- Driver load/activation path emits stable trust-audit reasons.

## Drill evidence requirements

For each domain, drills must record:

- incident start/end timestamps (UTC);
- rollback lever sequence used (pin/quarantine/gate-disable if applicable);
- approvals and escalation timeline;
- measured MTTR and target comparison;
- lessons learned and preventive follow-up actions.

Canonical evidence artifact:
`docs/development/fixtures/phase9a/rollback_drill_evidence_v1.json`.

## Lessons-learned template

For every drill or real rollback event capture:

1. What detection signal triggered first?
2. Which rollback lever restored service fastest?
3. What approval/escalation delay was observed?
4. Which automation should be added before Stage-9A close?
5. Which contract or runbook section needs update?
