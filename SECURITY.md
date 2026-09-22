# Security Policy

## Reporting a Vulnerability

Please **do not** open public GitHub issues for security reports.

Use one of the following private channels:

1. GitHub Security Advisories: <https://github.com/eigen-os/eigen-os/security/advisories/new>
2. Email: `security@eigen-os.org`

Include:

- Affected component(s) and version/commit
- Reproduction steps
- Impact and potential exploitability
- Any proof-of-concept details

## Response Process

- **Acknowledgment target:** within 3 business days
- **Triage update target:** within 7 business days
- **Fix and disclosure:** coordinated with the reporter based on severity and release risk

## Disclosure Policy

We follow coordinated disclosure:

1. Private report and triage
2. Patch development and validation
3. Security advisory publication
4. Release notes and mitigation guidance


## Scope

This policy applies to code and documentation in this repository, including:

- Rust crates under `src/rust/`
- Python services under `src/services/`
- API/protocol definitions under `proto/`
- Build/deploy/test scripts under `scripts/` and `deploy/`

Third-party dependencies and external platforms should be reported to their maintainers first when appropriate.