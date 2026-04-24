# Local deployment (MVP stack)

This directory provides a simple local profile to run the Eigen OS MVP services together

## Services

- `system-api` (`50051`, metrics `9090`)
- `eigen-kernel` (`50052`)
- `eigen-compiler` (`50071`, metrics `9093`)
- `driver-manager` (`50061`, metrics `9092`)

## Start stack

From repository root:

```bash
./deploy/local/dev_env.sh up
```

## Stop stack

```bash
./deploy/local/dev_env.sh down
```

## Configuration

- `local_config.yaml` defines default local endpoints and service wiring.
- Use this profile for smoke checks and local integration validation.
