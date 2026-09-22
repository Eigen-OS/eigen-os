from __future__ import annotations

from dataclasses import dataclass

import pytest

from driver_manager.base_driver import DriverCapabilities, DriverHealth
from driver_manager.registry import (
    DriverRegistry,
    DriverSignatureEnvelope,
    OfficialDriverMatrixEntry,
    PluginRuntimeSpec,
)


@dataclass(frozen=True)
class _Device:
    device_id: str


class _Driver:
    def __init__(self, devices: list[str]):
        self._devices = devices
    
    def initialize(self, config: dict[str, str]) -> None:
        _ = config

    def capability_handshake(self) -> DriverCapabilities:
        return DriverCapabilities(driver_api_version="1.0", features={"test": "true"})

    def healthcheck(self) -> DriverHealth:
        return DriverHealth(ready=True)

    def get_devices(self) -> list[_Device]:
        return [_Device(device_id=d) for d in self._devices]


def _signature() -> DriverSignatureEnvelope:
    return DriverSignatureEnvelope(
        artifact_digest="sha256:driver-artifact",
        manifest_digest="sha256:driver-manifest",
        signature_ref="oci://signatures/driver",
        signer_identity="driver-release@eigenos.dev",
        trust_profile="sigstore-keyless-v1",
    )


def _official_entry() -> OfficialDriverMatrixEntry:
    return OfficialDriverMatrixEntry(
        provider="ibm",
        driver="qiskit-runtime",
        driver_version="1.3.0",
        artifact_digest="sha256:driver-artifact",
        manifest_digest="sha256:driver-manifest",
    )

def test_add_and_lookup_by_device_id() -> None:
    registry = DriverRegistry()
    driver = _Driver(devices=["sim:1", "sim:2"])

    registry.add_driver("sim", driver)

    assert registry.get_driver("sim") is driver
    assert registry.get_driver_for_device("sim:1") is driver
    assert registry.get_driver_for_device("unknown") is None


def test_remove_driver_clears_device_lookup() -> None:
    registry = DriverRegistry()
    driver = _Driver(devices=["sim:1"])
    registry.add_driver("sim", driver)

    assert registry.remove_driver("sim") is True
    assert registry.remove_driver("sim") is False
    assert registry.get_driver_for_device("sim:1") is None


def test_duplicate_device_id_rejected() -> None:
    registry = DriverRegistry()
    registry.add_driver("d1", _Driver(devices=["sim:shared"]))

    with pytest.raises(ValueError, match="already owned"):
        registry.add_driver("d2", _Driver(devices=["sim:shared"]))


def test_health_and_capabilities_snapshots() -> None:
    registry = DriverRegistry()
    registry.add_driver("d1", _Driver(devices=["sim:1"]))

    health = registry.health_snapshot()
    caps = registry.capability_snapshot()

    assert health["d1"].ready is True
    assert caps["d1"].driver_api_version == "1.0"
    

def test_add_plugin_driver_rejects_in_process_runtime() -> None:
    registry = DriverRegistry()
    runtime = PluginRuntimeSpec(
        artifact_type="oci",
        runtime="in_process",
        rootless=True,
        read_only_fs=True,
        network_disabled=True,
        dropped_capabilities=True,
        cpu_limit="500m",
        memory_limit="512Mi",
        pid_limit=128,
    )

    with pytest.raises(ValueError, match="PLUGIN_RUNTIME_IN_PROCESS_FORBIDDEN"):
        registry.add_plugin_driver("p1", _Driver(devices=["plugin:1"]), runtime, _signature(), _official_entry())

    counters = registry.policy_reject_snapshot()
    assert counters["plugin_in_process_reject_total"] == 1


def test_add_plugin_driver_rejects_non_runsc_runtime_boundary() -> None:
    registry = DriverRegistry()
    runtime = PluginRuntimeSpec(
        artifact_type="oci",
        runtime="runc",
        rootless=True,
        read_only_fs=True,
        network_disabled=True,
        dropped_capabilities=True,
        cpu_limit="500m",
        memory_limit="512Mi",
        pid_limit=128,
    )

    with pytest.raises(ValueError, match="PLUGIN_RUNTIME_BOUNDARY_REQUIRED"):
        registry.add_plugin_driver("p1", _Driver(devices=["plugin:1"]), runtime, _signature(), _official_entry())

    counters = registry.policy_reject_snapshot()
    assert counters["plugin_runtime_boundary_reject_total"] == 1


def test_add_plugin_driver_rejects_baseline_profile_violations() -> None:
    registry = DriverRegistry()
    runtime = PluginRuntimeSpec(
        artifact_type="oci",
        runtime="runsc",
        rootless=True,
        read_only_fs=False,
        network_disabled=True,
        dropped_capabilities=True,
        cpu_limit="500m",
        memory_limit="512Mi",
        pid_limit=128,
    )

    with pytest.raises(ValueError, match="PLUGIN_SANDBOX_PROFILE_VIOLATION"):
        registry.add_plugin_driver("p1", _Driver(devices=["plugin:1"]), runtime, _signature(), _official_entry())

    counters = registry.policy_reject_snapshot()
    assert counters["plugin_sandbox_policy_reject_total"] == 1

def test_add_plugin_driver_rejects_missing_signature_metadata() -> None:
    registry = DriverRegistry()
    runtime = PluginRuntimeSpec(
        artifact_type="oci",
        runtime="runsc",
        rootless=True,
        read_only_fs=True,
        network_disabled=True,
        dropped_capabilities=True,
        cpu_limit="500m",
        memory_limit="512Mi",
        pid_limit=128,
    )

    with pytest.raises(ValueError, match="DRIVER_SIGNATURE_REQUIRED"):
        registry.add_plugin_driver(
            "p1",
            _Driver(devices=["plugin:1"]),
            runtime,
            DriverSignatureEnvelope(
                artifact_digest="sha256:driver-artifact",
                manifest_digest="sha256:driver-manifest",
                signature_ref="",
                signer_identity="",
                trust_profile="sigstore-keyless-v1",
            ),
            _official_entry(),
        )


def test_add_plugin_driver_rejects_matrix_digest_mismatch() -> None:
    registry = DriverRegistry()
    runtime = PluginRuntimeSpec(
        artifact_type="oci",
        runtime="runsc",
        rootless=True,
        read_only_fs=True,
        network_disabled=True,
        dropped_capabilities=True,
        cpu_limit="500m",
        memory_limit="512Mi",
        pid_limit=128,
    )

    with pytest.raises(ValueError, match="DRIVER_MATRIX_METADATA_MISMATCH"):
        registry.add_plugin_driver(
            "p1",
            _Driver(devices=["plugin:1"]),
            runtime,
            DriverSignatureEnvelope(
                artifact_digest="sha256:tampered",
                manifest_digest="sha256:driver-manifest",
                signature_ref="oci://signatures/driver",
                signer_identity="driver-release@eigenos.dev",
                trust_profile="sigstore-keyless-v1",
            ),
            _official_entry(),
        )

    counters = registry.policy_reject_snapshot()
    assert counters["driver_matrix_mismatch_reject_total"] == 1
    