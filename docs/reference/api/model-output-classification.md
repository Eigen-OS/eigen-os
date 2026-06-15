# Model Output Classification

**Document status:** Normative  
**Subsystem:** NeuroSymbolicService, Optimizer Service, model-adjacent response envelopes  
**Contract version:** `1.0.0`

This document defines the canonical model output classification label used by the internal optimizer and NeuroSymbolic response surfaces.

## Contract

Every model response MUST include a bounded `classification_label`.

Allowed values are exactly:

- `Advisory`
- `Optimization`
- `Recommendation`
- `Informational`

## Validation

- Unknown or empty values MUST be rejected.
- Rejection MUST be fail-closed and use `INVALID_ARGUMENT` at the service boundary.
- Classification labels MUST remain stable within the same contract major version.

## Notes

The label is a response classification, not a free-form confidence string. Consumers MUST NOT infer additional labels beyond the four approved values.
