# Branching Strategy (Eigen OS)

Eigen OS uses a **GitHub Flow + short-lived branches** approach:
- `main` is always deployable / buildable
- every change happens in a branch
- every branch is linked to an Issue (or RFC)
- branches are **short-lived** and merged in small batches

GitHub recommends **short, descriptive branch names** to make ongoing work obvious at a glance.  
We also follow the idea of keeping feature branches short-lived to reduce merge conflicts and integration risk.

---

## 1) Branch naming convention

**Format**

`<type>/<component>/<issue-id>-<short-slug>`

Example:
- `feat/compiler/204-aqo-compiler`
- `fix/system-api/77-invalid-argument-errors`
- `docs/docs/501-quickstart-local-sim`

### Allowed `<type>` prefixes

Use these prefixes to match the Issue labels and keep history consistent:

| Issue label type | Branch prefix |
|---|---|
| `type/feature` | `feat/` |
| `type/bug` | `fix/` |
| `type/enhancement` | `enh/` *(or `feat/`)* |
| `type/task` | `chore/` |
| `type/rfc` | `rfc/` |
| (docs work) | `docs/` |
| (test-only work) | `test/` |

> Recommended: use the same categories as **Conventional Commits** (`feat`, `fix`, etc.).  
> This makes the repo predictable for contributors and automation.

### Allowed `<component>` names

The component segment should match the repo structure and your GitHub labels:

- `system-api`
- `eigen-kernel`
- `compiler`
- `driver-manager`
- `cli`
- `qfs`
- `docs`
- `tests`

### `<issue-id>` rules

- Always include the GitHub Issue number (or RFC number).
- Use `0000` if work is exploratory and no issue exists yet (temporary only).

Examples:
- `rfc/docs/0012-eigen-lang-v0.1`
- `feat/driver-manager/302-simulator-driver-execute`

### `<short-slug>` rules

- **kebab-case**
- lowercase only
- keep it short (3–6 words max)
- no version suffixes like `final-v7`

✅ Good:
- `feat/compiler/204-aqo-compiler`
- `chore/tests/107-ci-contract-gates`

❌ Bad:
- `featureAddAQOCompiler_Final_v7`
- `mybranch`
- `feat/compiler/new`

---

## 2) Branch lifecycle

### Standard workflow

1. Create an Issue (or select an existing one)
2. Create a branch using the convention above
3. Make changes in small commits
4. Open a PR early (Draft PR is OK)
5. Keep the branch short-lived (merge fast)
6. Merge via PR, then delete the branch

### Best practices

- Prefer **small batches** (avoid giant PRs)
- Rebase / sync often if the branch lives > 1 day
- A PR should ideally be merged within 24–48 hours
- Avoid long-lived feature branches (they increase conflict cost)

---

## 3) Pull Request rules (recommended)

### PR title format

Match your branch type:

- `[FEAT] ...`
- `[FIX] ...`
- `[DOCS] ...`
- `[CHORE] ...`
- `[RFC] ...`

### PR description

A good PR must include:
- Link to Issue: `Closes #123`
- What changed
- Why it changed
- How to test

---

## 4) Commit message convention (recommended)

We recommend using **Conventional Commits**:

`<type>(<scope>): <message>`

Examples:
- `feat(compiler): compile Eigen-Lang to AQO v0.1`
- `fix(system-api): return INVALID_ARGUMENT for bad JobSpec`
- `docs(reference): add Eigen-Lang allowlist rules`

Suggested `scope` values (same as components):
- `system-api`, `compiler`, `kernel`, `driver-manager`, `cli`, `qfs`, `docs`, `tests`

---

## 5) Special branches (post-MVP)

During MVP, stick to `main` + short-lived branches.

After MVP (when releases start), optional branches:

### Release branches
- `release/0.1.0`
- `release/0.2.0`

### Hotfix branches
- `hotfix/0.1.1-critical-grpc-crash`

Releases should follow **Semantic Versioning (SemVer)**:
- MAJOR.MINOR.PATCH
- patch = bug fixes
- minor = backward compatible features
- major = breaking changes

---

## 6) Quick examples (Eigen OS MVP)

**MVP-1**
- `feat/system-api/103-grpc-skeleton`
- `feat/eigen-kernel/104-job-state-machine`
- `chore/tests/107-ci-contract-gates`

**MVP-2**
- `feat/compiler/204-aqo-compiler`
- `feat/cli/202-submit-jobspec-packaging`

**MVP-3**
- `feat/driver-manager/302-simulator-driver-execute`
- `feat/eigen-kernel/301-compile-execute-results`

---

## 7) Enforcement (optional, later)

When the repo grows, enforce:
- branch naming checks in CI
- conventional commits check
- required PR reviews
- required status checks before merge

For MVP, keep it simple: consistency > strict policing.
