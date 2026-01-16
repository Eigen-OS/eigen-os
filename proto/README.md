# Protobuf contracts (placeholder)

This directory will contain **all** `.proto` definitions for Eigen OS.

Design principle:
- **Protobuf contracts are the source of truth** for all gRPC APIs.
- Generated clients/servers must be derived from these files.

The directory is intentionally present early so tooling and CI can be wired before the first API lands.
