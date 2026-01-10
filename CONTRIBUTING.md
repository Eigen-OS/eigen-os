# Contributing to Eigen OS

Thank you for your interest in contributing to Eigen OS! This document provides guidelines and instructions for contributing to our project. We welcome contributions from everyone who shares our vision of making quantum computing accessible and efficient.

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Getting Started](#-getting-started)
- [Development Workflow](#-development-workflow)
- [Code Standards](#-code-standards)
- [Pull Request Process](#-pull-request-process)
- [Areas for Contribution](#-areas-for-contribution)
- [Community](#-community)
- [FAQ](#-faq)

## 🤝 Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating. We are committed to providing a welcoming and inclusive environment for all contributors.

## 🚀 Getting Started

### Prerequisites

- **Git** for version control
- **Rust 1.92+** for kernel components (`eigen-kernel`, `eigen-qdal`, `eigen-cli`)
- **Python 3.12+** for DSL and compiler components (`eigen-lang`, `eigen-compiler`, `system-api`)
- **Docker** (optional, for containerized development)
- **Basic understanding of quantum computing** (recommended but not required for all contributions)

### First Time Setup

1. **Fork the Repository**
   - Click the "Fork" button at the top right of the [Eigen OS repository](https://github.com/eigen-os/eigen-os)
   - This creates your personal copy of the project

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/eigen-os.git
   cd eigen-os
   ```

3. **Set Up Development Environment**
    ```bash
    # Set up Python components
    cd src/eigen-lang && pip install -e .
    cd ../eigen-compiler && pip install -e .

    # Set up Rust components
    cargo build --workspace
    ```
4. **Explore the Project**

    - Read the [Architecture Documentation](docs/architecture/overview.md)

    - Check out the [examples](examples/)

    - Run the existing tests: `./scripts/test/run-unit-tests.sh`

## 🔄 Development Workflow

1. **Find or Create an Issue**

    - **First-time contributors**: Look for issues labeled [good-first-issue](https://github.com/eigen-os/eigen-os/issues?q=is%253Aopen+is%253Aissue+label%253A%2522good+first+issue%2522)

    - **Experienced contributors**: Check [help-wanted](https://github.com/eigen-os/eigen-os/issues?q=is%253Aopen+is%253Aissue+label%253A%2522help+wanted%2522) issues

    - **New features**: Create a new issue to discuss before starting implementation

2. **Claim the Issue**

    - Comment on the issue to let others know you're working on it

    - This helps prevent duplicate work

3. **Create a Branch**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

**Branch Naming Convention:**
    
- `feature`/ - New functionality

- `fix`/ - Bug fixes

- `docs`/ - Documentation changes

- `test`/ - Test additions/improvements

- `refactor`/ - Code refactoring

- `chore`/ - Maintenance tasks

4. **Make Your Changes**

    - Write clear, focused commits

    - Follow the Code Standards

    - Update documentation as needed

    - Add or update tests

5. **Test Your Changes**
```bash
# Run Rust tests
cargo test --workspace

# Run Python tests
cd src/eigen-lang && pytest
cd ../eigen-compiler && pytest

# Or use the provided scripts
./scripts/test/run-unit-tests.sh
```

6. **Commit Your Changes**

We follow [Conventional Commits](https://www.conventionalcommits.org).

**Commit Message Format:**
```test
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Common Types:**

- `feat`: New feature

- `fix`: Bug fix

- `docs`: Documentation changes

- `style`: Code style/formatting changes

- `refactor`: Code restructuring

- `test`: Test-related changes

- `chore`: Maintenance tasks

- `perf`: Performance improvements

**Examples:**

- `feat(compiler): add noise-aware optimization pass`

- `fix(qrtx): handle edge case in DAG scheduling`

- `docs: update getting started tutorial`

-  `test(kernel): add unit tests for resource manager`

7. **Push and Create a Pull Request**
```bash
git push origin your-branch-name
```

Then create a Pull Request from your fork to the main repository.

## 📏 Code Standards

### Python Components (`eigen-lang`, `eigen-compiler`, `system-api`)

**Formatting:**

- Use [Black](https://black.readthedocs.io/en/stable/) for code formatting

- Use [isort](https://pycqa.github.io/isort/) for import sorting

- Maximum line length: 88 characters
```bash
# Auto-format Python code
black .
isort .
```

**Linting:**

- Follow [PEP 8](https://peps.python.org/pep-0008/)

- Use type hints for all public APIs

- Document public functions with docstrings (Google style)

**Testing:**

- Write unit tests using [pytest](https://docs.pytest.org/en/stable/)

- Aim for meaningful tests over high coverage percentages

- Mock external dependencies when appropriate

### Rust Components (`eigen-kernel`, `eigen-qdal`, `eigen-cli`)

**Formatting:**

- Use `rustfmt` with project configuration
```bash
cargo fmt
```

**Linting:**

- Use `clippy` for additional checks
```bash
cargo clippy --workspace
```

**Testing:**

- Write unit tests in the same file as the code being tested

- Use integration tests for cross-module functionality

- Follow Rust's testing conventions

### Documentation Standards

**Code Documentation:**

- Document all public APIs, modules, and types

- Use clear examples in docstrings

- Keep documentation close to the code it describes

**Architectural Documentation:**

- Update [RFCs](rfcs/) when making significant changes

- Keep architecture diagrams current

- Document design decisions

## 🔍 Pull Request Process

### PR Checklist

Before submitting a PR, ensure:

- Code follows project standards

- Tests pass locally

- Documentation is updated

- No new warnings are introduced

- Changes are focused and logical

- Commit messages follow conventional format

### PR Template

When creating a PR, you'll see this template. Please fill it out completely:
```markdown
## Description
<!-- Briefly describe what this PR does -->

## Related Issue
<!-- Link to the issue this PR addresses (e.g., "Fixes #123") -->

## Type of Change
<!-- Check all that apply -->
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
<!-- Describe how you tested these changes -->

## Screenshots/Screen Recordings
<!-- If applicable, add screenshots or recordings to help explain your changes -->

## Additional Notes
<!-- Any additional information reviewers should know -->
```

**Review Process**

1. **Initial Review**: A maintainer will review your PR within 3 business days

2. **Feedback**: You may receive suggestions for improvements

3. **Iteration**: Make requested changes and push updates to your branch

4. **Approval**: Once approved, a maintainer will merge your PR

5. **Celebration**: Your contribution is now part of Eigen OS! 🎉

## 🎯 Areas for Contribution

### For Beginners

- **Documentation**: Fix typos, improve clarity, add examples

- **Tests**: Add unit tests for existing code

- **Examples**: Create simple demonstration programs

- **Tooling**: Improve development scripts

### For Intermediate Contributors

- **Bug Fixes**: Address issues in the tracker

- **Feature Implementation**: Work on well-defined features

- **Performance Improvements**: Optimize existing code

- **Integration Tests**: Ensure components work together

## For Advanced Contributors

- **Architectural Changes**: Implement new RFCs

- **Core Algorithms**: Work on compiler optimizations, scheduler improvements

- **Hardware Integration**: Add support for new quantum backends

- **Research Contributions**: Implement novel quantum computing techniques

### Component-Specific Guidance

| Component | Language | Focus Areas |
|-------------------|-------------------|-------------------|
| **eigen-kernel** | Rust | Scheduler, storage, resource management |
| **eigen-lang** | Python | DSL syntax, type system, decorators |
| **eigen-compiler** | Python | Neuro-symbolic compilation, optimization passes |
| **eigen-qdal** | Rust | Hardware abstraction, driver interface |
| **system-api** | Python | API design, authentication, client libraries |

## 👥 Community

### Communication Channels

- **GitHub Issues**: For bug reports and feature requests

- **GitHub Discussions**: For questions and general discussion

- **RFC Process**: For architectural proposals (see [rfcs/](rfcs/))

- **Discord**: For real-time chat (coming soon)

### Getting Help

- Check the [documentation](docs/) first

- Search existing issues and discussions

- Ask in GitHub Discussions for general questions

- Use GitHub Issues for bug reports

### Recognition

All contributors are recognized in:

- The project's [CONTRIBUTORS.md](CONTRIBUTORS.md) file

- Release notes

- Community highlights

## ❓ FAQ

### Do I need to sign a CLA?

Not currently. All contributions are licensed under Apache 2.0 when merged.

### Can I contribute without deep quantum computing knowledge?

Yes! Many areas (documentation, tooling, testing, UI) don't require quantum expertise.

### How do I propose a major new feature?

1. Create a discussion thread in GitHub Discussions

2. If there's consensus, write an RFC in the `rfcs/` directory

3. Once the RFC is approved, you can implement it

### What if I get stuck?

Ask for help! Use GitHub Discussions or comment on your PR. We're here to help.

### Can I contribute to multiple components in one PR?

Yes, but keep PRs focused. If changes span many components, consider whether they should be separate PRs.

### How are decisions made?

We follow an [RFC process](GOVERNANCE.md) for significant changes. Smaller decisions are made through PR review and community discussion.

## 📚 Additional Resources

- [Architecture Overview](docs/architecture/overview.mdd)

- [RFC Process](rfcs/TEMPLATE.md)

- [Development Setup](docs/developer/development.md)

- [Testing Guide](docs/developer/testing.md)

- [Release Process](docs/developer/release-process.md)

### Thank you for contributing to Eigen OS! Together, we're building the future of quantum computing. 🌟

*Have questions not answered here? Please open a discussion or issue!*