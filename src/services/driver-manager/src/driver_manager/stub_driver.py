"""Built-in stub driver used to satisfy MVP-2 skeleton behavior."""

from __future__ import annotations

from .base_driver import DeviceStatusInfo


class StubDriver:
    name = "stub"

    def __init__(self, types_pb):
        self._types_pb = types_pb

    def initialize(self, config: dict[str, str]) -> None:
        _ = config

    def get_devices(self) -> list[object]:
        return [
            self._types_pb.DeviceInfo(
                device_id="sim:stub",
                name="Stub simulator",
                backend_type="simulator",
                status=self._types_pb.ONLINE,
                queue_depth=0,
                estimated_wait_sec=0,
                capabilities={"shots": "1024"},
            )
        ]

    def execute_circuit(
        self,
        device_id: str,
        circuit: bytes,
        shots: int,
        options: dict[str, str],
    ) -> tuple[dict[str, int], float, dict[str, str]]:
        _ = (device_id, circuit, shots, options)
        return ({"00": 1}, 0.001, {"stub": "true"})

    def get_device_status(self, device_id: str) -> DeviceStatusInfo:
        return DeviceStatusInfo(
            device_id=device_id,
            status=self._types_pb.ONLINE,
            queue_depth=0,
            estimated_wait_sec=0,
            metadata={"stub": "true"},
        )

    def calibrate_device(self, device_id: str, options: dict[str, str]) -> str:
        _ = (options,)
        return f"calib://stub/{device_id}"