# P9C-01 — Core Tenant Envelope + Baseline Quotas Contract

## Contract version

- Tenant envelope contract: `1.0.0`.
- Public gRPC `SubmitJobRequest` now includes `tenant` envelope (`SubmitJobRequest.TenantQuotaEnvelope`).

## Canonical fields

- `tenant.contract_version` — SemVer marker for envelope contract.
- `tenant.tenant_id` — canonical tenant id.
- `tenant.project_id` — canonical project id.
- `tenant.tenant_max_queued_jobs` — baseline tenant queued-job quota.
- `tenant.project_max_queued_jobs` — baseline project queued-job quota.

## Deterministic defaults

When tenant metadata is missing:

- `tenant_id` defaults to authenticated tenant from auth context, otherwise `tenant-default`.
- `project_id` defaults to `project-default`.
- `tenant_max_queued_jobs` defaults to `EIGEN_SCHED_TENANT_QUOTA_MAX_QUEUED` or `16`.
- `project_max_queued_jobs` defaults to `EIGEN_SCHED_PROJECT_QUOTA_MAX_QUEUED` or `8`.

## Kernel-path quota reason codes

Scheduler path emits deterministic quota reason codes:

- `TARGET_QUOTA_DELAY`
- `TENANT_BASELINE_QUOTA_DELAY`
- `PROJECT_BASELINE_QUOTA_DELAY`

Additional deterministic attributes:

- `tenant_quota_state`
- `project_quota_state`

## Migration notes

- This is a backward-compatible additive change.
- Existing clients without `tenant` envelope remain valid and receive deterministic defaults.
- No wire-level field removals or renames.
