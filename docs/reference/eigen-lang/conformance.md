# Eigen‑Lang conformance suite (MVP v0.1)

The conformance suite ensures compilers behave consistently.

## Must-have tests
- Parse + validate: accept minimal program, reject banned imports/nodes (INVALID_ARGUMENT).
- Deterministic compilation: same input → identical AQO JSON hash.
- Mapping coverage: QubitRegister/Param/Measurement; optional ExpectationValue/minimize markers.

## Artifacts
- Golden AQO JSON files under `tests/golden/`
- Negative cases under `tests/negative/`
