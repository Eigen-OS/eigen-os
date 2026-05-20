from __future__ import annotations

from driver_manager.parity import ProviderObservation, ToleranceProfile, evaluate_tolerance


PROFILE = ToleranceProfile(
    policy_version="1.0.0",
    canonical_workload="phase8d_canonical_workload_v1",
    allowed_missing_keys=0,
    max_latency_ratio=5.0,
    max_noise_delta=0.12,
)


def test_cross_provider_tolerance_accepts_simulator_ibm_aws_samples() -> None:
    baseline = ProviderObservation(provider="simulator", counts={"00": 510, "11": 514}, latency_sec=0.12)
    ibm = ProviderObservation(provider="ibm", counts={"00": 495, "11": 529}, latency_sec=0.42)
    aws = ProviderObservation(provider="aws", counts={"00": 501, "11": 523}, latency_sec=0.47)

    ibm_ok, ibm_violations = evaluate_tolerance(baseline=baseline, candidate=ibm, profile=PROFILE)
    aws_ok, aws_violations = evaluate_tolerance(baseline=baseline, candidate=aws, profile=PROFILE)

    assert ibm_ok, ibm_violations
    assert aws_ok, aws_violations


def test_cross_provider_tolerance_fails_closed_on_drift() -> None:
    baseline = ProviderObservation(provider="simulator", counts={"00": 700, "11": 324}, latency_sec=0.10)
    drifted = ProviderObservation(provider="aws", counts={"01": 1024}, latency_sec=1.01)

    ok, violations = evaluate_tolerance(baseline=baseline, candidate=drifted, profile=PROFILE)

    assert not ok
    assert any("result_shape mismatch" in v for v in violations)
    assert any("noise_delta exceeded" in v for v in violations)
    assert any("latency_ratio exceeded" in v for v in violations)
