# REST API: Explain Backend Selection (POST /explain/backend-selection)

**Version**: 1.0.0  
**Status**: Target Standard  
**Compatibility**: Eigen OS v1.3.0+  
**Transport**: REST + gRPC compatible contract  
**Primary Runtime Owner**: QRTX Scheduler & Explainability Services  
**Security Classification**: Internal Protected API
---

## 1. Purpose

The Explain Backend Selection API provides deterministic and auditable explanations for why a particular backend (simulator or quantum device) was selected by the Eigen OS scheduling and orchestration subsystem.

The endpoint exposes:

- backend scoring rationale,
- eligibility filtering,
- feature/factor contributions,
- tie-break decisions,
- confidence estimation,
- scheduler provenance,
- observability metadata,
- reproducibility guarantees.

This API is part of the Eigen OS explainability and auditability framework and integrates with:

- QRTX,
- Knowledge Base (KB),
- Driver Manager,
- Observability Stack,
- Security Module.

The API acts as a source-of-truth interface for:

- debugging scheduling decisions,
- compliance auditing,
- benchmarking analysis,
- ML feedback loops,
- Continuous Learning pipelines,
- user-facing explainability.

---

## 2. Architectural Alignment with Eigen OS

This document is fully aligned with Eigen OS Target Standard v1.3.0.

The explainability service integrates with:

| **Component**             | **Role** |
|---------------------------|------|
| QRTX                      | Produces backend selection decisions |
| Driver Manager            | Supplies topology, calibration, queue, and hardware metrics |
| Knowledge Base            | Stores historical decision artifacts |
| Observability Stack       | Traces explain requests and scheduler provenance |
| Security Module           | AuthN/AuthZ, audit logging, policy enforcement |
| Continuous Learning Pipeline | Uses explain records for retraining |
| GNN Scheduler/Optimizer   | Generates some scoring features |
| CircuitFS/QFS-L3          | Stores explain snapshots and replay artifacts |

---

## 3. Transport Definition

**REST Endpoint**

```http
POST /explain/backend-selection
```

**gRPC Equivalent**

```protobuf
rpc ExplainBackendSelection(
    ExplainBackendSelectionRequest
) returns (ExplainBackendSelectionResponse);
```

---

## 4. Security Requirements

### Authentication
All requests **MUST** be authenticated.

Supported mechanisms:
- OAuth2 Bearer JWT
- Mutual TLS (mTLS) for internal services

Unauthenticated requests **MUST** return `401 Unauthorized`.

### Authorization
Required scopes:

| Scope              | Description |
|--------------------|-----------|
| `jobs:explain`     | Explain scheduling decisions |
| `jobs:read`        | Read related job metadata |
| `admin:explain`    | Access cross-tenant explain records |

ABAC/RBAC enforcement **MUST** be performed by the Security Module.

### Multi-Tenant Isolation
Explain records **MUST** be tenant-isolated.  
A caller:
- **MAY** access only its own decisions,
- **UNLESS** granted administrative privileges.

Unauthorized access **MUST** return `403 Forbidden`.

### Audit Logging
Every explain request **MUST** generate immutable audit records containing:
- timestamp,
- user_id,
- tenant_id,
- decision_id,
- request_id,
- source_ip,
- auth_method,
- trace_id.

Audit events **MUST** be forwarded into the Observability Stack.

---

## 5. Request Schema

**Content Type**: `application/json`

#### Request JSON

```json
{
  "request_version": "1.0.0",
  "response_version": "1.0.0",
  "decision_id": "backend-selection-decision-001",
  "include_rejected_candidates": true
}
```

#### Fields

| **Field**                   | **Type**    | **Required** | **Description** |
|-----------------------------|---------|----------|-----------|
| `request_version`           | string  | yes      | Request contract version |
| `response_version`          | string  | yes      | Requested response version |
| `decision_id`               | string  | yes      | Scheduler decision identifier |
| `include_rejected_candidates` | boolean | no       | Include rejected candidates |

---

## 6. Request Validation Rules

- `request_version` **MUST** equal `1.0.0`
- `response_version` **MUST** equal `1.0.0`
- `decision_id`: non-empty string, UTF-8, max 256 chars, **MUST** reference existing decision
- `include_rejected_candidates`: defaults to `false`

## 7. Success Response

**HTTP Status**: `200 OK`

#### Response Schema

```json
{
  "explain_contract_version": "1.0.0",
  "request_version": "1.0.0",
  "response_version": "1.0.0",
  "scoring_contract_version": "1.0.0",
  "profile_schema_version": "1.0.0",
  "profile_version": "1.0.0",

  "decision_id": "backend-selection-decision-001",
  "job_id": "job_0192ab",
  "scheduler_trace_id": "trace_7f8c12",
  "selected_backend_id": "sim:cpu-a",

  "decision_timestamp": "2026-05-26T14:22:11Z",

  "tie_break_trace": [
    "score-desc",
    "lower-queue-length",
    "higher-fidelity"
  ],

  "candidate_scores": [
    {
      "backend_id": "sim:cpu-a",
      "score_millis": 942,
      "eligible": true,
      "ineligibility_reason": null,
      "estimated_runtime_ms": 1820,
      "estimated_queue_delay_ms": 120,
      "predicted_error_rate": 0.0012,

      "feature_contributions": [
        {
          "feature": "queue_length",
          "contribution_millis": 197
        },
        {
          "feature": "fidelity",
          "contribution_millis": 412
        }
      ]
    }
  ],

  "factor_contributions": [
    {
      "backend_id": "sim:cpu-a",
      "factor": "queue_length",
      "contribution_millis": 197
    }
  ],

  "confidence": {
    "score_margin_millis": 3,
    "selected_score_millis": 942,
    "runner_up_score_millis": 939,
    "confidence": 0.0031847133757961785
  },

  "provenance": {
    "scheduler_version": "1.3.0",
    "gnn_model_version": "gnn-routing-v5",
    "policy_version": "scheduler-policy-2026.05",
    "driver_snapshot_version": "drivers-2026.05.21"
  }
}
```

---

## 8. Response Field Semantics

#### selected_backend_id

The backend selected by QRTX scheduling logic.

May be:

- simulator,
- quantum device,
- virtual backend.

May be `null` if:

- no backend satisfied constraints,
- all candidates failed eligibility checks.

#### tie_break_trace

Deterministic ordered list of tie-break operations used by scheduler.

The Explain API MUST NOT recompute tie-break logic.

Values are copied from scheduler decision artifacts.

#### candidate_scores

Represents all evaluated candidates.

Each candidate includes:

| **Field** | **Meaning** |
|------------|-----------|
| `score_millis` | Final normalized scheduler score |
| `eligible` | Eligibility outcome |
| `estimated_runtime_ms` | Predicted runtime |
| `estimated_queue_delay_ms` | Predicted queue delay |
| `predicted_error_rate` | Predicted execution error |
| `feature_contributions` | Per-factor additive scoring |

#### factor_contributions

Flattened deterministic representation of all contributions.

Sorting order:

1. `backend_id`
2. `factor`

Lexicographic ascending.

#### confidence

Confidence metrics are computed ONLY across eligible candidates.

Formula:

```text
confidence =
(selected_score - runner_up_score)
/
selected_score
```

If selected score is zero:

```json
{
  "confidence": 0.0
}
```

#### provenance

Provides reproducibility metadata.

Required for:

- audit replay,
- deterministic debugging,
- Continuous Learning,
- scheduler validation.

---

## 9. Runtime Semantics

#### Determinism

Explain responses MUST be deterministic.

The same:

- decision artifact,
- scoring profile,
- model versions,
- scheduler policies,

MUST produce identical explain responses.

#### Replayability

Explain responses MUST be reproducible offline using:

- stored scheduler artifacts,
- topology snapshots,
- driver metadata,
- scoring profiles,
- model versions.

#### Idempotency

This endpoint is read-only and inherently idempotent.

Repeated requests MUST return identical responses.

#### Rejected Candidates

If:

```json
"include_rejected_candidates": false
```

then all:

```json
"eligible": false
```

entries MUST be omitted from:

- `candidate_scores`
- `factor_contributions`

---

## 10. Error Model

All errors follow the standard Eigen OS error envelope.

#### Error Envelope

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "decision artifact not found",
    "details": [
      {
        "field": "decision_id",
        "code": "unknown_decision_id",
        "message": "No scheduling decision exists for the provided decision_id"
      }
    ]
  }
}
```

---

## 11. Standard Error Codes

| **HTTP** | **Code**            | **Meaning** |
|------|-------------------------|-------|
| 400  | INVALID_ARGUMENT        | Invalid request |
| 401  | UNAUTHENTICATED         | Missing/invalid token |
| 403  | PERMISSION_DENIED       | Access denied |
| 404  | NOT_FOUND               | Unknown decision |
| 409  | VERSION_CONFLICT        | Contract mismatch |
| 429  | RESOURCE_EXHAUSTED      | Rate limit exceeded |
| 500  | INTERNAL                | Internal failure |
| 503  | UNAVAILABLE             | Service unavailable |

---

## 12. Knowledge Base Integration

All explain artifacts SHOULD be persisted into the Knowledge Base.

Stored metadata:

- scheduler trace,
- scoring profile,
- backend rankings,
- selected backend,
- confidence metrics,
- model versions,
- hardware topology snapshot.

Explain artifacts MAY later be used for:

- scheduler retraining,
- anomaly detection,
- routing optimization,
- fairness analysis,
- benchmarking replay.

---

## 13. Observability Requirements

### OpenTelemetry

Each request MUST create spans:

```text
ExplainBackendSelection
ExplainBackendSelection.LoadDecision
ExplainBackendSelection.BuildResponse
ExplainBackendSelection.Authorize
```

### Metrics

Required Prometheus metrics:

| **Metric** | **Type** |
|------------|-----------|
| `explain_backend_selection_requests_total` | counter |
| `explain_backend_selection_failures_total` | counter |
| `explain_backend_selection_latency_ms` | histogram |
| `explain_backend_selection_not_found_total` | counter |


### Structured Logs

Each explain request MUST produce structured logs containing:

- request_id,
- decision_id,
- user_id,
- tenant_id,
- latency_ms,
- result_status,
- trace_id.

---

## 14. Persistence Requirements

Explain artifacts MUST be durably persisted.

Minimum retained entities:

- scoring decision,
- topology snapshot,
- backend telemetry,
- candidate list,
- confidence metrics,
- policy snapshot.

### Storage location:

- QFS Level 3 (CircuitFS),
- PostgreSQL metadata,
- Knowledge Base.

---

## 15. Continuous Learning Integration

Explain records MUST feed Continuous Learning pipelines.

Training usage examples:

- identifying unstable scheduling heuristics,
- improving backend ranking models,
- training confidence predictors,
- validating GNN scheduling quality.

---

## 16. Compatibility Rules

Backward Compatibility

Minor versions MAY:

- add optional fields,
- add metrics,
- extend provenance.

Major versions MUST be used for:

- field removal,
- semantic changes,
- response structure changes.

---

## 17. Acceptance Criteria

The implementation is compliant only if:

- REST and gRPC transports exist,
- all calls require authentication,
- deterministic replay passes fixture tests,
- observability instrumentation exists,
- audit events are emitted,
- explain responses are reproducible,
- multi-tenant isolation is enforced,
- OpenTelemetry traces are generated,
- persistence is durable,
- CI contract tests prevent schema drift.

---

## 18. Implementation Tasks

### Mandatory

1. Implement REST handler:

- POST /explain/backend-selection

2. Implement gRPC service.
3. Add JWT/OAuth2 validation.
4. Add RBAC/ABAC enforcement.
5. Persist explain artifacts into KB.
6. Add OpenTelemetry instrumentation.
7. Add Prometheus metrics.
8. Add audit logging.
9. Add deterministic replay tests.
10. Add PostgreSQL persistence.
11. Add topology snapshot persistence.
12. Integrate explain traces with QRTX job lifecycle.

---

## 19. Source of Truth Statement

This document is the authoritative specification for backend-selection explainability APIs in Eigen OS.

Any implementation:

- Rust,
- Python,
- REST,
- gRPC,
- CLI,
- SDK,

MUST conform to this contract.

If implementation behavior diverges from this document, the implementation MUST be corrected.
