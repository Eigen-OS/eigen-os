# Reference

Reference docs define **source-of-truth contracts**.
They should stay precise, explicit, and implementation-agnostic.

## Index

- JobSpec: [`jobspec.md`](jobspec.md)
- Eigen-Lang submission: [`eigen-lang-submission.md`](eigen-lang-submission.md)
- Public API: [`api/grpc-public.md`](api/grpc-public.md)
- Benchmark Run API: [`api/benchmark-run.md`](api/benchmark-run.md)
- Internal API: [`api/grpc-internal.md`](api/grpc-internal.md)
- Error model: [`error-model.md`](error-model.md)
- Error mapping: [`error-mapping.md`](error-mapping.md)
- Multi-device execution (split/merge): [`multi-device-execution-contract.md`](multi-device-execution-contract.md)
- Orchestration observability contract: [`orchestration-observability-contract.md`](orchestration-observability-contract.md)
- Formats:
  - [`formats/aqo.md`](formats/aqo.md)
  - [`formats/qfs-layout.md`](formats/qfs-layout.md)
- Eigen-Lang language reference: [`eigen-lang/README.md`](eigen-lang/README.md)

## Change policy

Any user-facing or cross-service contract update should be accompanied by:
1. RFC/ADR update (if applicable),
2. reference page update,
3. conformance/test update.
