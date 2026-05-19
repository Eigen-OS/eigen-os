# Eigen OS VS Code Integration Skeleton (Phase-8D / P8D-06)

> **Non-GA Surface**
>
> This extension contract is a bootstrap skeleton and is not GA.

## Purpose

Minimal command set for editor-driven workflow:

- submit current JobSpec/program,
- check status,
- fetch results.

## Proposed commands

- `eigen.submitJob`
- `eigen.watchJobStatus`
- `eigen.fetchJobResults`

## Contract alignment

Commands proxy to System API parity routes only and reuse stable payloads.
No extension-specific stable contract is introduced in this phase.

## Simulator walkthrough

Run the walkthrough in `docs/howto/surfaces-vscode-simulator-walkthrough.md`.
