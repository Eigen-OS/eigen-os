"""In-memory driver registry for plugin lifecycle and device lookup."""

from __future__ import annotations

from dataclasses import dataclass

from .base_driver import BaseDriver, DriverCapabilities, DriverHealth


@dataclass(frozen=True)
class RegisteredDriver:
    name: str
    driver: BaseDriver
    device_ids: frozenset[str]
    capabilities: DriverCapabilities


@dataclass(frozen=True)
class PluginRuntimeSpec:
    artifact_type: str
    runtime: str
    rootless: bool
    read_only_fs: bool
    network_disabled: bool
    dropped_capabilities: bool
    cpu_limit: str
    memory_limit: str
    pid_limit: int


@dataclass(frozen=True)
class DriverSignatureEnvelope:
    artifact_digest: str
    manifest_digest: str
    signature_ref: str
    signer_identity: str
    trust_profile: str


@dataclass(frozen=True)
class OfficialDriverMatrixEntry:
    provider: str
    driver: str
    driver_version: str
    artifact_digest: str
    manifest_digest: str


@dataclass(frozen=True)
class DeviceProfileSnapshot:
    profile_name: str
    profile_version: str
    device_id: str
    driver_name: str
    backend_type: str
    capability_descriptors: dict[str, str]


class DriverRegistry:
    """Manage registered drivers and reverse index device_id -> driver."""

    def __init__(self) -> None:
        self._sessions = {}
        self._drivers: dict[str, RegisteredDriver] = {}
        self._device_to_driver: dict[str, str] = {}
        self._device_profiles: dict[str, DeviceProfileSnapshot] = {}
        self._policy_reject_counters: dict[str, int] = {
            "plugin_runtime_boundary_reject_total": 0,
            "plugin_in_process_reject_total": 0,
            "plugin_sandbox_policy_reject_total": 0,
            "driver_signature_reject_total": 0,
            "driver_matrix_mismatch_reject_total": 0,
        }

    def get_or_create_session(
        self,
        driver_name: str,
        session_key: str,
    ):
        key = (driver_name, session_key)

        if key in self._sessions:
            return self._sessions[key]

        self._sessions[key] = {
            "state": "active",
            "driver": driver_name,
        }
        return self._sessions[key]

    def invalidate_session(
        self,
        driver_name: str,
        session_key: str,
    ) -> None:
        key = (driver_name, session_key)
        if key in self._sessions:
            self._sessions[key]["state"] = "invalidated"

    def add_plugin_driver(
        self,
        name: str,
        driver: BaseDriver,
        runtime_spec: PluginRuntimeSpec,
        signature: DriverSignatureEnvelope,
        official_entry: OfficialDriverMatrixEntry,
    ) -> None:
        self._enforce_plugin_runtime_policy(runtime_spec)
        self._enforce_signature_policy(name=name, signature=signature, official_entry=official_entry)
        self.add_driver(name=name, driver=driver)

    def _enforce_signature_policy(
        self,
        name: str,
        signature: DriverSignatureEnvelope,
        official_entry: OfficialDriverMatrixEntry,
    ) -> None:
        if not signature.signature_ref.strip() or not signature.signer_identity.strip():
            self._policy_reject_counters["driver_signature_reject_total"] += 1
            raise ValueError(
                f"DRIVER_SIGNATURE_REQUIRED: driver={name} has missing signature metadata"
            )

        if signature.trust_profile != "sigstore-keyless-v1":
            self._policy_reject_counters["driver_signature_reject_total"] += 1
            raise ValueError(
                f"DRIVER_SIGNATURE_TRUST_PROFILE_UNSUPPORTED: driver={name} trust_profile={signature.trust_profile}"
            )

        if signature.artifact_digest != official_entry.artifact_digest:
            self._policy_reject_counters["driver_matrix_mismatch_reject_total"] += 1
            raise ValueError(
                f"DRIVER_MATRIX_METADATA_MISMATCH: driver={name} field=artifact_digest"
            )
        if signature.manifest_digest != official_entry.manifest_digest:
            self._policy_reject_counters["driver_matrix_mismatch_reject_total"] += 1
            raise ValueError(
                f"DRIVER_MATRIX_METADATA_MISMATCH: driver={name} field=manifest_digest"
            )

    def add_driver(self, name: str, driver: BaseDriver) -> None:
        if not name:
            raise ValueError("driver name is required")
        if name in self._drivers:
            raise ValueError(f"driver already registered: {name}")
        
        capabilities = driver.capability_handshake()
        if not capabilities.driver_api_version:
            raise ValueError(f"driver {name} capability handshake missing driver_api_version")

        device_ids = []
        device_records: dict[str, object] = {}
        for device in driver.get_devices():
            device_id = getattr(device, "device_id", "")
            if not device_id:
                raise ValueError(f"driver {name} produced device with empty device_id")
            if device_id in self._device_to_driver:
                existing = self._device_to_driver[device_id]
                raise ValueError(
                    f"device_id '{device_id}' already owned by driver '{existing}'"
                )
            device_ids.append(device_id)
            device_records[device_id] = device

        for device_id in device_ids:
            self._device_to_driver[device_id] = name
        for device_id, device in device_records.items():
            self._device_profiles[device_id] = self._build_device_profile(
                driver_name=name,
                capabilities=capabilities,
                device=device,
            )

        self._drivers[name] = RegisteredDriver(
            name=name,
            driver=driver,
            device_ids=frozenset(device_ids),
            capabilities=capabilities,
        )

    def _enforce_plugin_runtime_policy(self, runtime_spec: PluginRuntimeSpec) -> None:
        if runtime_spec.runtime == "in_process":
            self._policy_reject_counters["plugin_in_process_reject_total"] += 1
            raise ValueError("PLUGIN_RUNTIME_IN_PROCESS_FORBIDDEN: in-process plugin runtime is not allowed")
        if runtime_spec.artifact_type != "oci" or runtime_spec.runtime != "runsc":
            self._policy_reject_counters["plugin_runtime_boundary_reject_total"] += 1
            raise ValueError("PLUGIN_RUNTIME_BOUNDARY_REQUIRED: only OCI artifacts under runsc are allowed")

        baseline_ok = (
            runtime_spec.rootless
            and runtime_spec.read_only_fs
            and runtime_spec.network_disabled
            and runtime_spec.dropped_capabilities
            and bool(runtime_spec.cpu_limit)
            and bool(runtime_spec.memory_limit)
            and runtime_spec.pid_limit > 0
        )
        if not baseline_ok:
            self._policy_reject_counters["plugin_sandbox_policy_reject_total"] += 1
            raise ValueError("PLUGIN_SANDBOX_PROFILE_VIOLATION: plugin runtime spec violates baseline profile")

    def remove_driver(self, name: str) -> bool:
        registered = self._drivers.pop(name, None)
        if registered is None:
            return False

        for device_id in registered.device_ids:
            self._device_to_driver.pop(device_id, None)
            self._device_profiles.pop(device_id, None)

        return True

    def get_driver(self, name: str) -> BaseDriver | None:
        registered = self._drivers.get(name)
        return None if registered is None else registered.driver

    def get_driver_for_device(self, device_id: str) -> BaseDriver | None:
        driver_name = self._device_to_driver.get(device_id)
        if driver_name is None:
            return None
        return self._drivers[driver_name].driver

    def get_device_profile(self, device_id: str) -> DeviceProfileSnapshot | None:
        return self._device_profiles.get(device_id)

    def device_profile_snapshot(self) -> list[DeviceProfileSnapshot]:
        return [self._device_profiles[device_id] for device_id in sorted(self._device_profiles)]

    def resolve_device_profile(
        self,
        device_id: str,
        requested_profile: str | None = None,
    ) -> DeviceProfileSnapshot:
        profile = self._device_profiles.get(device_id)
        if profile is None:
            raise ValueError(f"unknown device_id: {device_id}")

        requested = (requested_profile or "").strip()
        if not requested:
            return profile
        if requested in {profile.profile_name, profile.driver_name, profile.backend_type, profile.profile_version, profile.device_id}:
            return profile

        simulator_profile = next(
            (
                candidate
                for candidate in self.device_profile_snapshot()
                if candidate.profile_name == "simulator"
                or candidate.driver_name == "simulator"
                or candidate.backend_type == "simulator"
            ),
            None,
        )
        if simulator_profile is not None:
            return simulator_profile

        raise ValueError(f"unsupported device profile '{requested}' for device_id '{device_id}'")

    def negotiate_device_profile(
        self,
        device_id: str,
        requested_profile: str | None = None,
    ) -> DeviceProfileSnapshot:
        return self.resolve_device_profile(device_id, requested_profile=requested_profile)

    def list_devices(self) -> list[object]:
        devices: list[object] = []
        for registered in self._drivers.values():
            devices.extend(registered.driver.get_devices())
        return sorted(devices, key=lambda device: getattr(device, "device_id", ""))

    def health_snapshot(self) -> dict[str, DriverHealth]:
        return {name: self._drivers[name].driver.healthcheck() for name in sorted(self._drivers)}

    def capability_snapshot(self) -> dict[str, DriverCapabilities]:
        return {name: self._drivers[name].capabilities for name in sorted(self._drivers)}

    def policy_reject_snapshot(self) -> dict[str, int]:
        return dict(self._policy_reject_counters)

    def _build_device_profile(
        self,
        *,
        driver_name: str,
        capabilities: DriverCapabilities,
        device: object,
    ) -> DeviceProfileSnapshot:
        raw_descriptors = getattr(device, "capabilities", {}) or {}
        if isinstance(raw_descriptors, dict):
            capability_descriptors = {str(k): str(v) for k, v in raw_descriptors.items()}
        else:
            capability_descriptors = {}

        profile_name = (
            capability_descriptors.get("provider")
            or capability_descriptors.get("profile")
            or getattr(device, "name", "")
            or driver_name
        )
        backend_type = str(
            getattr(device, "backend_type", "")
            or capability_descriptors.get("backend_type", "")
            or capability_descriptors.get("provider", "")
            or profile_name
        )

        return DeviceProfileSnapshot(
            profile_name=str(profile_name),
            profile_version=str(capabilities.driver_api_version),
            device_id=str(getattr(device, "device_id", "")),
            driver_name=driver_name,
            backend_type=backend_type,
            capability_descriptors=dict(sorted(capability_descriptors.items())),
        )
