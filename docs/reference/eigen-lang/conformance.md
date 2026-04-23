# Eigen‑Lang conformance suite (MVP v0.1)

The conformance suite ensures compilers behave consistently and protects the MVP language surface from silent drift.

## Must-have tests
- Parse + validate: accept minimal program, reject banned imports/nodes (INVALID_ARGUMENT).
- Deterministic compilation: same input → identical AQO JSON hash.
- Mapping coverage: QubitRegister/Param/Measurement; optional ExpectationValue/minimize markers.

## Repository layout
The current suite is implemented in the compiler service test package:

- Golden AQO fixtures: `src/services/eigen-compiler/tests/golden/*/`
  - `program.eigen.py` — source fixture
  - `expected.aqo.json` — canonical AQO JSON output
- Negative validation fixtures: `src/services/eigen-compiler/tests/negative/*/request.json`
  - request payload + expected gRPC code + expected field violation list

## CI enforcement
- The CI workflow executes `pytest` in `src/services/eigen-compiler` on every push to `main` and every pull request.
- `tests/test_conformance_suite.py` discovers and runs all golden and negative fixtures.

## Golden update process (required)
Golden outputs are intentionally strict. Any change to `expected.aqo.json` files must follow this process:

1. Update compiler behavior intentionally.
2. Re-run the conformance suite locally:
   - `cd src/services/eigen-compiler && pytest tests/test_conformance_suite.py`
3. Validate each changed `expected.aqo.json` represents intended language behavior (not formatting-only churn).
4. In the PR description, include a **Golden Update** section listing:
   - changed fixture directories,
   - reason for each output change,
   - backward-compatibility impact (if any).
5. Require explicit reviewer approval for golden fixture diffs before merge.

## Notes
- The MVP compiler currently returns a canonical AQO scaffold; fixture growth should track Eigen‑Lang feature additions.
- Add at least one negative fixture for each new validation rule.

