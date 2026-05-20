# Phase-9B Compatibility Report

## Version context

- Stage: Phase-9B (Intelligence closure)
- Baseline contract set: TZ v1.3.0 alignment package
- Normative versioning policy: `rfcs/0032-phase7-api-and-contract-versioning-policy-v1.md`

## Version impact decision

- **Overall impact:** `MINOR`
- **Reasoning:** Phase-9B introduces backward-compatible governance and evidence surfaces (new reports, closure criteria, and mapping requirements) without removing or redefining existing stable payload fields.
- **Breaking marker:** `false`
- **Migration notes required:** `None`

## Affected interfaces

| Interface / artifact | Impact | Notes |
|---|---|---|
| Compatibility matrix documentation artifacts | MINOR | Added mandatory Stage-B closure artifacts and linkage discipline. |
| CLI payloads | NONE | No envelope or parser contract deltas in this issue. |
| Plugin envelopes | NONE | No plugin schema changes in this issue. |
| JobSpec | NONE | No JobSpec field or semantic changes. |
| AQO | NONE | No AQO schema changes. |
| QFS | NONE | No QFS envelope changes; referenced only for evidence mapping. |
| Metrics | NONE | Existing metric schema references are synchronized; no field-level contract delta in this change set. |

## Contract drift controls

- Conformance remains fail-closed on undocumented contract drift.
- Compatibility report is part of release closure evidence and must be updated when contract surfaces change.
- Any future Phase-9B breaking updates must switch impact to `MAJOR` and include migration notes.

## Deprecation policy reminder

Any deprecation introduced under Phase-9B successors must preserve support for **2 minor releases or 90 days (whichever is longer)** per RFC 0032.
