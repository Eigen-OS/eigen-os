# Product 1.0 Wave 7 Handoff Schema

This note records the compiler-to-optimizer boundary for W7-03.

## Stable identifiers

- compiler contract version
- optimizer contract version
- AQO version
- request SHA-256
- source SHA-256
- AQO SHA-256
- source precedence
- request ID
- trace ID
- traceparent

## Boundary rules

- Only canonical AQO bytes and frozen metadata cross the boundary.
- No model state, candidate list, ranking cache, or fallback state may cross the boundary.
- Source precedence must stay deterministic when both `source` and `source_ref` exist.
- The optimizer-facing envelope must be replay-stable for identical compiler inputs.
