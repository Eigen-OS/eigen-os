# RFC 0001: RFC Process and Conventions

- **Status**: Discussion

- **Authors**: NYankovich

- **Created**: 2026-01-08

- **Target Milestone**: Phase 0 (MVP)

- **Tracking Issue**: (to be defined)

- **Replaces / Related**: —

## Summary

Defines the process for creating, reviewing, adopting, versioning, and tracking proposals for **Eigen OS**.

## Motivation

**Eigen OS** is a modular system built on stable interfaces (QDriver API, JobSpec, AQO). To prevent integration breakdowns and scale community contributions, we need a lightweight yet rigorous design process.

## Goals

- Provide a **single source of truth** for interface changes.

- Clearly define **review criteria** (compatibility, security, observability, tests).

- Support the **open modularity** and **interface-based abstraction** principles of Eigen OS.

## Non-Goals

- **Replacing GitHub Issues/Pull Requests** — RFCs complement, but do not replace, regular issues and PRs. They are for **significant changes to interfaces, architecture, or data formats**.

- **Heavy bureaucracy** — the process should remain **lightweight during MVP**, evolving as the project grows.

## Guide-level Explanation

1. Initiation

    - Create a **GitHub Issue** describing the problem or opportunity.

    - If the change impacts **APIs, architecture, or data formats**, proceed to step 2.

2. RFC Draft

    - Create a file in `rfcs/` using the `TEMPLATE.md`.

    - **File naming**: `NNNN-short-title.md` (e.g., `0001-rfc-process.md`).

    - Set status to **Draft**.

3. Discussion

    - After drafting, the RFC enters "**Discussion**" status.

    - Discussion happens in **GitHub Discussions** (RFCS-Discussion).

    - Engage relevant contributors and maintainers.

4. Review

    - Requires **at least 1 maintainer** for each affected subsystem.

    - Review criteria: compatibility, security, observability, testing, alignment with architectural principles.

5. Decision

    - **Accepted** → RFC moves to "Accepted" status, an implementation owner is assigned.

    - **Rejected** → with clear reasoning.

    - **Deferred** → moved to a future milestone.

6. Implementation

    - Pull Requests implementing the RFC **must reference the RFC number**.

    - After merging, the RFC status changes to "**Implemented**".

**RFC Status Lifecycle:**
`Draft → Discussion → Accepted → Implemented → Deprecated/Superseded`

## Reference-level Design

## nterfaces / APIs

- RFCs touching QDriver API, System API, Eigen-Lang must include **usage examples and backward compatibility considerations**.

## Data Models

- Changes to JobSpec, AQO, Quantum State formats must be **versioned** and documented.

## Error Model

- (No specific requirements for this RFC. For future RFCs: define error types, propagation, and handling.)

## Security and Privacy

- RFCs modifying external interfaces must include **threat model notes** and **authorization considerations**.

## Observability

- RFCs affecting execution paths must describe **required metrics, logs, traces** and impact on SLOs.

## Performance

- RFCs touching critical paths must include **complexity estimates** and a **benchmarking plan**.

## Testing Plan

- Each accepted RFC must include **unit/integration tests** and, if applicable, **compatibility tests**.

## Implementation / Migration

- **Phase 0 (MVP)**: No strict semantic versioning, but RFCs are required for critical changes. Breaking changes require an RFC and a changelog entry.

- **Phase 1+**: Semantic versioning for QDriver API, JobSpec, AQO.

- **Protobuf**: Use Buf for linting and breaking-change detection in CI (`buf lint`, `buf breaking`).

## Considered Alternatives

- **Direct changes via Pull Request** — rejected, leads to fragmentation and loss of interface control.

- **Heavyweight process like KEP/EP** — deferred, too heavy for MVP.

## Open Questions

- Who will be the **initial maintainers** for each subsystem (QRTX, Eigen-Lang, QDriver API)?

- What is the **minimum quorum** for RFC acceptance during MVP?
