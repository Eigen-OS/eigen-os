# ADR 0017 — Phase-6 plugin contract RFC package acceptance baseline

- **Status**: Accepted
- **Date**: 2026-04-29
- **Deciders**: Eigen OS maintainers
- **Supersedes / Related**: RFC 0029, RFC 0030, RFC 0031, ADR 0016

## Context

Phase-6 plugin ecosystem work requires a formal governance baseline before implementation can be stabilized. The required RFC package for plugin contracts is available and accepted:

- RFC 0029: plugin SDK and manifest contract v1;
- RFC 0030: plugin lifecycle and runtime isolation contract v1;
- RFC 0031: plugin compatibility and trust policy contract v1.

Without an ADR checkpoint, Phase-6 acceptance state is not captured in the architecture-decision ledger and release governance cannot consistently trace RFC-package closure.

## Decision

1. Record that the required Phase-6 plugin RFC package (0029/0030/0031) is accepted and indexed in development/roadmap documentation.
2. Adopt contract baseline `1.0.0` governance for Phase-6 plugin-facing artifacts and envelopes:
   - plugin manifest schema;
   - lifecycle event + isolation contract envelope;
   - compatibility and trust policy envelope.
3. Enforce SemVer change discipline for plugin contracts:
   - incompatible plugin API hook/required manifest/trust-policy semantic changes => `MAJOR`;
   - backward-compatible additive capabilities/diagnostics/extension points => `MINOR`;
   - non-semantic fixes only => `PATCH`.
4. Freeze mandatory version markers in loadable plugin artifacts:
   - `plugin_api_version`;
   - `eigen_os_compatibility`.
5. Require compatibility + test-plan sections in each Phase-6 plugin contract RFC and keep explicit RFC status transitions (`Draft`/`Accepted`/`Implemented`).

## Consequences

### Positive

- Phase-6 governance baseline is explicitly captured in ADR history.
- RFC-package closure for P6-08 becomes auditable and reproducible across docs.
- Plugin contract evolution has explicit SemVer guardrails prior to implementation.

### Trade-offs

- Future contract changes must go through stricter RFC+ADR synchronization.
- Additional documentation overhead is required for every status/version transition.

## Evidence package

- RFC set:
  - `rfcs/0029-phase6-plugin-sdk-and-manifest-contract-v1.md`
  - `rfcs/0030-phase6-plugin-lifecycle-and-runtime-isolation-contract-v1.md`
  - `rfcs/0031-phase6-plugin-compatibility-and-trust-policy-contract-v1.md`
- Development package:
  - `docs/development/phase-6-plugin-ecosystem.md`
  - `docs/development/phase-6-issue-pack.md`
  - `docs/development/phase-6-rfc-adr-gap-analysis.md`

## Rollout / governance

- This ADR records Phase-6 RFC-package acceptance (P6-08 governance closure checkpoint).
- As implementation advances, status progression to `Implemented` in RFCs must be mirrored by follow-up ADR synchronization and release closure artifacts.
- Phase-6 release sign-off depends on compatibility report + release-readiness checklist in addition to this ADR baseline record.
