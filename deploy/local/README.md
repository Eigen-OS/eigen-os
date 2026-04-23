# Local deployment (all services)

This directory contains a simple local profile for bringing up the full Eigen OS MVP stack.

## Services

- `system-api` (`50051`, metrics `9090`)
- `eigen-kernel` (`50052`)
- `eigen-compiler` (`50071`, metrics `9093`)
- `driver-manager` (`50061`, metrics `9092`)

## Run everything

From repository root:

```bash
./deploy/local/dev_env.sh up
```

Stop and remove containers:

```bash
./deploy/local/dev_env.sh down
```

## Config

`local_config.yaml` documents the default local endpoints used by the stack.
