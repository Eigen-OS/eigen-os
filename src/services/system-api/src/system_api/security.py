"""Security/auth configuration for System API MVP.

MVP intentionally supports an explicit allow-all mode so local/dev environments
can run without credentials while still exercising the auth boundary.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import grpc
from .observability import log_authz_denied

_AUTH_ALLOW_ALL = "allow_all"
_AUTH_STATIC_TOKEN = "static_token"
_VALID_AUTH_MODES = {_AUTH_ALLOW_ALL, _AUTH_STATIC_TOKEN}
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "user": {"jobs:*", "devices:list", "devices:status"},
    "readonly": {"jobs:read", "devices:list"},
}


@dataclass(frozen=True)
class SecurityConfig:
    auth_mode: str
    static_token: str
    static_token_subject: str
    static_token_roles: tuple[str, ...]
    static_token_tenant: str

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
        static_token_subject=os.getenv("SYSTEM_API_AUTH_SUBJECT", "static-token-user"),
        static_token_roles=tuple(
            part.strip().lower()
            for part in os.getenv("SYSTEM_API_AUTH_ROLES", "admin").split(",")
            if part.strip()
        ),
        static_token_tenant=os.getenv("SYSTEM_API_AUTH_TENANT", ""),
        max_program_source_bytes=_int_env("SYSTEM_API_MAX_PROGRAM_SOURCE_BYTES", 262_144),
        max_jobspec_yaml_bytes=_int_env("SYSTEM_API_MAX_JOBSPEC_YAML_BYTES", 65_536),
    )


def _metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def enforce_authn(context: grpc.ServicerContext, *, method_name: str) -> None:
    cfg = load_security_config()
    if cfg.auth_mode == _AUTH_ALLOW_ALL:
        return

    md = _metadata(context)
    authorization = md.get("authorization", "")
    expected = f"Bearer {cfg.static_token}"
    if authorization != expected:
        context.abort(
            grpc.StatusCode.UNAUTHENTICATED,
            f"authentication required for {method_name}; configure SYSTEM_API_AUTH_MODE=allow_all for local dev",
        )


def auth_context(context: grpc.ServicerContext) -> tuple[str, tuple[str, ...], str]:
    cfg = load_security_config()
    if cfg.auth_mode == _AUTH_STATIC_TOKEN:
        return cfg.static_token_subject, cfg.static_token_roles, cfg.static_token_tenant

    md = _metadata(context)
    subject = md.get("x-eigen-sub", "anonymous")
    tenant = md.get("x-eigen-tenant", "")
    raw_roles = md.get("x-eigen-roles", "admin")
    roles = tuple(role.strip().lower() for role in raw_roles.split(",") if role.strip())
    if not roles:
        roles = ("admin",)
    return subject, roles, tenant


def _has_permission(roles: tuple[str, ...], permission: str) -> bool:
    for role in roles:
        perms = _ROLE_PERMISSIONS.get(role, set())
        if "*" in perms or permission in perms:
            return True
        prefix, _, _ = permission.partition(":")
        if f"{prefix}:*" in perms:
            return True
    return False


def enforce_authz(context: grpc.ServicerContext, *, required_permission: str) -> None:
    """Enforce coarse-grained method authorization for static-token mode.

    Authorization is intentionally lightweight for MVP:
    - ignored in allow_all mode
    - in static_token mode, caller provides role/permission claims in metadata
      via one of:
        - x-eigen-permissions: comma-separated permissions
        - x-eigen-roles: comma-separated roles
    """

    cfg = load_security_config()
    if cfg.auth_mode == _AUTH_ALLOW_ALL:
        return

    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    raw_permissions = md.get("x-eigen-permissions", "")
    raw_roles = md.get("x-eigen-roles", "")
    granted = {
        item.strip().lower()
        for blob in (raw_permissions, raw_roles)
        for item in blob.split(",")
        if item.strip()
    }

    need = required_permission.strip().lower()
    scope, _, action = need.partition(":")
    wildcard = f"{scope}:*"

    if need in granted or wildcard in granted or "*" in granted:
        return

    context.abort(
        grpc.StatusCode.PERMISSION_DENIED,
        f"permission denied: requires {required_permission}",
    )
