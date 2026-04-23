"""Security/auth configuration for System API MVP.

MVP intentionally supports an explicit allow-all mode so local/dev environments
can run without credentials while still exercising the auth boundary.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import grpc

_AUTH_ALLOW_ALL = "allow_all"
_AUTH_STATIC_TOKEN = "static_token"
_VALID_AUTH_MODES = {_AUTH_ALLOW_ALL, _AUTH_STATIC_TOKEN}


@dataclass(frozen=True)
class SecurityConfig:
    auth_mode: str
    static_token: str

    max_program_source_bytes: int
    max_jobspec_yaml_bytes: int


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def load_security_config() -> SecurityConfig:
    auth_mode = os.getenv("SYSTEM_API_AUTH_MODE", _AUTH_ALLOW_ALL).strip().lower()
    if auth_mode not in _VALID_AUTH_MODES:
        auth_mode = _AUTH_ALLOW_ALL

    return SecurityConfig(
        auth_mode=auth_mode,
        static_token=os.getenv("SYSTEM_API_AUTH_TOKEN", "dev-token"),
        max_program_source_bytes=_int_env("SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES", 262_144),
        max_jobspec_yaml_bytes=_int_env("SYSTEM_API_MAX_JOBSPEC_YAML_BYTES", 65_536),
    )


def enforce_authn(context: grpc.ServicerContext, *, method_name: str) -> None:
    cfg = load_security_config()
    if cfg.auth_mode == _AUTH_ALLOW_ALL:
        return

    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    authorization = md.get("authorization", "")
    expected = f"Bearer {cfg.static_token}"
    if authorization != expected:
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            f"authentication required for {method_name}; configure SYSTEM_API_AUTH_MODE=allow_all for local dev",
        )
