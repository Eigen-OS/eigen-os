# Contributing to Eigen OS

Thanks for contributing to Eigen OS.

## Code of Conduct

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

### Prerequisites

    - Git
    - Rust (stable)
    - Python 3.12+

### Clone and bootstrap

```bash
git clone https://github.com/eigen-os/eigen-os.git
cd eigen-os
```

6. **Commit Your Changes**

We follow [Conventional Commits](https://www.conventionalcommits.org).

**Commit Message Format:**
```test
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Proposing Changes

### Small changes

For docs fixes, typo fixes, and scoped bug fixes:

1. Open (or reference) an issue.
2. Create a branch from `main`.
3. Open a PR with a clear description and test evidence.

### RFCs (required for significant changes)

Use an RFC for architectural or behavior changes, including API changes, protocol/schema changes, language semantics, scheduler behavior, or security model changes.

1. Copy `rfcs/TEMPLATE.md` to a new numbered file in `rfcs/`.
2. Fill in motivation, design, alternatives, migration, and rollout sections.
3. Open a PR titled `RFC: <short title>`.
4. Link related issues and request review from maintainers.
5. Iterate until accepted; implementation PRs must reference the accepted RFC.

## Running Tests

Run the most relevant tests for your change before opening a PR.

### Rust

```bash
cargo test --manifest-path src/rust/Cargo.toml --workspace
```

### Python services

```bash
pytest src/services/eigen-compiler/tests
pytest src/services/system-api/tests
pytest src/services/driver-manager/tests
```

### Helper scripts

```bash
./scripts/test/run-unit-tests.sh
./scripts/test/run-integration-tests.sh
```

## Pull Request Checklist

- [ ] Issue linked (or created)
- [ ] RFC linked (if required)
- [ ] Relevant tests added/updated
- [ ] Local tests pass
- [ ] Docs updated if behavior changed

## Commit Style

Use [Conventional Commits](https://www.conventionalcommits.org/), for example:

- `feat(kernel): add queue backpressure checks`
- `fix(system-api): validate empty device id`
- `docs(roadmap): align milestones with MVP`
