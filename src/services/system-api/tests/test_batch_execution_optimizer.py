from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from system_api.grpc_impl import JobService
from system_api.proto_gen import ensure_generated
from system_api.qfs_store import QFS_STORE

ensure_generated()

from eigen.api.v1 import job_service_pb2 as job_pb  # noqa: E402
from eigen.api.v1 import types_pb2 as types_pb  # noqa: E402


class _Context:
    def invocation_metadata(self):
        return []

    def abort(self, code, details):
        raise RuntimeError(f"{code}: {details}")


def _make_service(monkeypatch, *, batch_mode: str, batch_size: str = "4", wait_window: str = "0.2") -> JobService:
    monkeypatch.setenv("EIGEN_BATCH_MODE", batch_mode)
    monkeypatch.setenv("EIGEN_BATCH_SIZE", batch_size)
    monkeypatch.setenv("EIGEN_BATCH_WAIT_WINDOW_SEC", wait_window)
    return JobService(job_pb=job_pb, types_pb=types_pb)


def _submit(service: JobService, *, name: str, runtime_sec: str = "1.0") -> str:
    req = job_pb.SubmitJobRequest(
        name=name,
        target="sim:local",
        priority=50,
        metadata={"simulate_runtime_sec": runtime_sec},
        eigen_lang=types_pb.EigenLangSource(source=b"def main():\n return 'ok'\n", entrypoint="main"),
    )
    resp = service.SubmitJob(req, _Context())
    return resp.job_id


def test_batch_mode_kill_switch_disables_batch_manifest(monkeypatch):
    service = _make_service(monkeypatch, batch_mode="0", batch_size="2", wait_window="0.0")
    job_id = _submit(service, name="kill-switch-job")
    rationale = service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=job_id), _Context())

    assert "SINGLE_DISPATCH" in rationale.rationale.reason_codes
    assert "BATCH_EXECUTION_V1" not in rationale.rationale.reason_codes
    assert rationale.rationale.attributes["batch_mode_enabled"] == "false"


def test_batch_manifest_versioning_and_reason_code(monkeypatch):
    QFS_STORE.clear()
    service = _make_service(monkeypatch, batch_mode="1", batch_size="2", wait_window="5.0")

    first_id = _submit(service, name="batched-1")
    second_id = _submit(service, name="batched-2")

    first = service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=first_id), _Context()).rationale
    second = service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=second_id), _Context()).rationale

    assert "BATCH_EXECUTION_V1" in first.reason_codes
    assert "BATCH_EXECUTION_V1" in second.reason_codes
    assert first.attributes["batch_manifest_ref"] == second.attributes["batch_manifest_ref"]

    manifest_ref = first.attributes["batch_manifest_ref"]
    payload = QFS_STORE.get_bytes(manifest_ref)
    assert payload is not None
    manifest = json.loads(payload.decode("utf-8"))

    assert manifest["version"] == "1.0.0"
    assert manifest["schema_version"] == "batch_manifest.v1"
    assert manifest["size"] == 2
    assert set(manifest["jobs"]) == {first_id, second_id}


def test_benchmark_batching_improves_throughput_within_latency_bound(monkeypatch):
    jobs_count = 8
    checkpoint_after_submit_sec = 1.0
    max_latency_regression_sec = 0.2

    batched = _make_service(monkeypatch, batch_mode="1", batch_size="4", wait_window="5.0")
    unbatched = _make_service(monkeypatch, batch_mode="0", batch_size="4", wait_window="5.0")

    batched_ids = [_submit(batched, name=f"batched-{idx}") for idx in range(jobs_count)]
    unbatched_ids = [_submit(unbatched, name=f"single-{idx}") for idx in range(jobs_count)]

    now = datetime.now(timezone.utc)
    checkpoint_dt = now - timedelta(seconds=checkpoint_after_submit_sec)
    for job_id in batched_ids:
        rec = batched._jobs[job_id]
        rec.created_at_dt = checkpoint_dt
        batched._advance_job(rec)
    for job_id in unbatched_ids:
        rec = unbatched._jobs[job_id]
        rec.created_at_dt = checkpoint_dt
        unbatched._advance_job(rec)

    batched_done = sum(1 for job_id in batched_ids if batched._jobs[job_id].updates[-1].state == types_pb.JOB_STATE_DONE)
    unbatched_done = sum(
        1 for job_id in unbatched_ids if unbatched._jobs[job_id].updates[-1].state == types_pb.JOB_STATE_DONE
    )
    assert batched_done > unbatched_done

    batched_max_delay = max(batched._jobs[job_id].queue_delay_sec for job_id in batched_ids)
    unbatched_max_delay = max(unbatched._jobs[job_id].queue_delay_sec for job_id in unbatched_ids)
    assert batched_max_delay <= unbatched_max_delay + max_latency_regression_sec

def test_priority_quota_and_starvation_hooks_are_deterministic(monkeypatch):
    monkeypatch.setenv("EIGEN_SCHED_QUOTA_PER_TARGET", "1")
    monkeypatch.setenv("EIGEN_SCHED_STARVATION_SEC", "0.0")
    service = _make_service(monkeypatch, batch_mode="0")

    first_id = _submit(service, name="quota-1")
    second_id = _submit(service, name="quota-2")
    first = service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=first_id), _Context()).rationale
    second = service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=second_id), _Context()).rationale

    assert first.attributes["quota_state"] == "eligible"
    assert second.attributes["quota_state"] == "throttled"
    assert "TARGET_QUOTA_DELAY" in second.reason_codes
    assert first.attributes["starvation_guard"] == "promoted"
    assert "STARVATION_PROTECTION" in first.reason_codes


def test_topology_noise_fallback_is_explicit(monkeypatch):
    service = _make_service(monkeypatch, batch_mode="0")
    req = job_pb.SubmitJobRequest(
        name="fallback-hooks",
        target="sim:local",
        priority=42,
        metadata={"topology_fallback": "cluster-fallback/partition-0"},
        eigen_lang=types_pb.EigenLangSource(source=b"def main():\n return 'ok'\n", entrypoint="main"),
    )
    job_id = service.SubmitJob(req, _Context()).job_id
    rationale = service.GetDispatchRationale(job_pb.GetDispatchRationaleRequest(job_id=job_id), _Context()).rationale
    assert rationale.attributes["topology_hook_status"] == "fallback"
    assert rationale.attributes["noise_hook_status"] == "fallback"
    assert rationale.attributes["fallback_reason"] == "TOPOLOGY_TELEMETRY_MISSING|NOISE_TELEMETRY_MISSING"
    