# Reference

Reference docs define **source-of-truth contracts**.
They should stay precise, explicit, and implementation-agnostic.

## Index

- JobSpec: [`jobspec.md`](jobspec.md)
- Eigen-Lang language reference: [`eigen-lang.md`](eigen-lang.md)
- Public API: [`api/grpc-public.md`](api/grpc-public.md)
- Explain API (backend selection): [`api/explain-backend-selection.md`](api/explain-backend-selection.md)
- Benchmark Run API: [`api/benchmark-run.md`](api/benchmark-run.md)
- Benchmark observability contract: [`benchmark-observability-contract.md`](benchmark-observability-contract.md)
- Internal API: [`api/grpc-internal.md`](api/grpc-internal.md)
- Error model: [`error-model.md`](error-model.md)
- Error mapping: [`error-mapping.md`](error-mapping.md)
- Multi-device execution (split/merge): [`multi-device-execution-contract.md`](multi-device-execution-contract.md)
- Orchestration observability contract: [`orchestration-observability-contract.md`](orchestration-observability-contract.md)
- Intelligent runtime observability contract: [`intelligent-runtime-observability-contract.md`](intelligent-runtime-observability-contract.md)
- Cluster runtime observability contract: [`cluster-runtime-observability-contract.md`](cluster-runtime-observability-contract.md)
- Formats:
  - [`formats/aqo.md`](formats/aqo.md)
  - [`formats/qfs-layout.md`](formats/qfs-layout.md)
- Public REST API envelope: [`api/rest-public.md`](api/rest-public.md)
- Authorization policy: [`security/authz.md`](security/authz.md)

## Change policy

Any user-facing or cross-service contract update should be accompanied by:
1. RFC/ADR update (if applicable),
2. reference page update,
3. conformance/test update.
