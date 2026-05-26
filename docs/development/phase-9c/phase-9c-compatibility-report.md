# Phase-9C Compatibility Report

## Version context

- Stage: Phase-9C (Multi-tenant policy + plugin-first expansion)
- Baseline contract set: TZ v1.3.0 alignment package
- Normative versioning policy: `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

## Version impact decision

- **Overall impact:** `MINOR`
- **Reasoning:** Phase-9C introduces backward-compatible governance artifacts and a versioned compatibility matrix update (`policy_capability_matrix.v1` -> `1.1.0`) that clarifies core-vs-plugin ownership and deterministic fallback semantics without removing existing stable interfaces.
- **Breaking marker:** `false`
- **Migration notes required:** `None`

## Affected interfaces

| Interface / artifact | Impact | Notes |
|---|---|---|
| Compatibility matrix artifacts (`policy_capability_matrix.v1`) | MINOR | Matrix version advanced to `1.1.0` with explicit fallback semantics and evidence metadata. |
| CLI payloads | NONE | No CLI envelope delta in this issue scope. |
| Plugin envelopes | NONE | No plugin wire-schema field change in this issue scope. |
| JobSpec | NONE | No JobSpec field additions/removals in this issue scope. |
| AQO | NONE | No AQO schema changes in this issue scope. |
| QFS | NONE | No QFS payload changes; references are documentary only. |
| Metrics | NONE | No metric schema changes; reason-code references remain stable. |

## Contract drift controls

- Compatibility matrix remains a versioned, fixture-locked artifact.
- CI must fail closed on undocumented matrix drift and conformance regressions.
- Any future Phase-9C contract break must be marked `MAJOR` with explicit migration notes.

## Deprecation policy reminder

Any deprecation introduced under Phase-9C successors must preserve support for **2 minor releases or 90 days (whichever is longer)** per RFC 0032.
