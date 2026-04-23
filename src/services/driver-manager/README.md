# driver-manager (MVP skeleton)

Internal gRPC service implementing `eigen.internal.v1.DriverManagerService`.

Implemented in this milestone:

- Service bootstrap and gRPC server.
- `ListDevices` / `GetDeviceStatus` stub behavior.
- `BaseDriver` (`QDriver`) interface.
- In-memory `DriverRegistry` with device-to-driver lookup.

## Run

```bash
python -m driver_manager.main
```

## Tests

```bash
pytest src/services/driver-manager/tests -q
```