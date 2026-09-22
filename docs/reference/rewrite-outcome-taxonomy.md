# Rewrite Outcome Taxonomy

**Document status:** Normative  
**Subsystem:** Knowledge Base, Ranking, Model Training  
**Contract version:** `1.0.0`

This document defines the canonical rewrite-outcome labels used by KB records, ranking pipelines, review tooling, and model-training datasets.

The canonical label set is exhaustive. Implementations MUST use exactly one of the following labels for each rewrite-outcome record:

| Label | Meaning |
|---|---|
| `accepted` | The rewrite preserves intent and satisfies product, quality, and policy constraints. |
| `rejected` | The rewrite must not be used because it fails product or quality constraints. |
| `equivalent` | The rewrite is semantically equivalent to the source for downstream use. |
| `unsafe` | The rewrite violates safety, policy, or harm-prevention constraints and MUST be excluded from positive serving or training signals. |

---

## 1. Normative requirements

- Labels MUST be stored as lower-case ASCII strings.
- Labels MUST NOT be aliased, translated, camel-cased, or expanded into intermediate values.
- One record MUST carry exactly one canonical rewrite-outcome label.
- Unknown labels MUST be rejected at ingestion.
- Derived analytics MAY group labels, but the source-of-truth record MUST preserve the canonical label.

---

## 2. Usage across KB and model training

- KB records and annotation tools MUST use the same four labels.
- Model training datasets MUST consume the same labels without renaming them.
- `unsafe` MUST be treated as a hard safety exclusion in ranking and training pipelines.
- `accepted`, `rejected`, and `equivalent` MAY be used as supervised signals only when provenance is preserved.

---

## 3. Compatibility

- Adding this taxonomy is backward-compatible for consumers that already treat labels as opaque strings.
- Consumers that validate label enums MUST be updated before new data is ingested.
