# P9B-05 — Continuous Learning Reproducible Retrain + Model Registry Digests

## Implemented contract updates

- `optimizer_evaluation` contract advanced to `1.4.0`.
- Continuous learning policy advanced to `1.3.0`.
- Retrain trigger policy now enforces three deterministic rules:
  - `new_data_threshold` (`N` new records),
  - `time_cap_exceeded` (max interval since previous training),
  - `manual_override`.
- Every trigger evaluation emits an audit event (`RETRAIN_TRIGGER_EVALUATED`) with actor, reason code, and rule outcomes.
- Produced model versions include reproducibility evidence:
  - dataset snapshot manifest,
  - training config digest,
  - model artifact digest set,
  - deterministic reproduce command and expected lineage hash.
- Model production emits audit linkage (`MODEL_VERSION_PRODUCED`) with digest references and linked model version.

## CI and release expectations

- Reproducibility evidence fields are covered by unit tests in `benchmark-service`.
- Trigger rule variants (threshold, time cap, manual override) are fixture-tested.
