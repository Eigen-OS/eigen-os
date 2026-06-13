"""Security/auth configuration for System API MVP.

MVP intentionally supports an explicit allow-all mode so local/dev environments
can run without credentials while still exercising the auth boundary.
"""

from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import grpc

from .errors import PublicErrorSpec, abort_public
from .observability import log_authz_denied, trace_id_from_traceparent, append_security_audit_event, sanitized_security_metadata

_AUTH_ALLOW_ALL = "allow_all"
_AUTH_STATIC_TOKEN = "static_token"
_AUTH_JWT_OAUTH2 = "jwt_oauth2"
_VALID_AUTH_MODES = {_AUTH_ALLOW_ALL, _AUTH_STATIC_TOKEN, _AUTH_JWT_OAUTH2}
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "user": {"jobs:*", "devices:list", "devices:status"},
    "readonly": {"jobs:read", "devices:list"},
}


@dataclass(frozen=True)
class PolicySnapshot:
    version: str
    issuer: str
    audience: str
    role_permissions: dict[str, set[str]]
    service_permissions: dict[str, set[str]]
    sandbox_profiles: set[str]


@dataclass(frozen=True)
class SecurityContext:
    subject: str
    roles: tuple[str, ...]
    tenant: str
    auth_mode: str
    policy_version: str
    service_identity: str | None
    service_role: str | None
    sandbox_profile: str | None
    claims: dict[str, str]


@dataclass(frozen=True)
class SecurityConfig:
    auth_mode: str
    static_token: str
    static_token_subject: str
    static_token_roles: tuple[str, ...]
    static_token_tenant: str

    max_program_source_bytes: int
    max_jobspec_yaml_bytes: int
    max_submit_metadata_entries: int
    max_submit_metadata_key_bytes: int
    max_submit_metadata_value_bytes: int
    max_submit_dependencies: int
    jwt_secret: str
    jwt_issuer: str
    jwt_audience: str
    policy_snapshot_path: str
    policy_snapshot_json: str
    service_identity: str
    service_role: str
    sandbox_profile: str


def _load_policy_snapshot(cfg: SecurityConfig) -> PolicySnapshot:
    if cfg.policy_snapshot_json.strip():
        payload = json.loads(cfg.policy_snapshot_json)
    elif cfg.policy_snapshot_path.strip():
        try:
            payload = json.loads(Path(cfg.policy_snapshot_path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return PolicySnapshot(version="", issuer=cfg.jwt_issuer, audience=cfg.jwt_audience, role_permissions={}, service_permissions={}, sandbox_profiles=set())
        except json.JSONDecodeError:
            return PolicySnapshot(version="", issuer=cfg.jwt_issuer, audience=cfg.jwt_audience, role_permissions={}, service_permissions={}, sandbox_profiles=set())
    else:
        payload = {
            "version": "1.0.0",
            "issuer": cfg.jwt_issuer,
            "audience": cfg.jwt_audience,
            "role_permissions": {
                "admin": ["*"],
                "user": ["jobs:*", "devices:list", "devices:status"],
                "readonly": ["jobs:read", "devices:list"],
            },
            "service_permissions": {
                "system-api": ["jobs:*", "devices:*"],
                "eigen-kernel": ["jobs:*", "qfs:*", "policy:*"],
            },
            "sandbox_profiles": ["default", "restricted", "strict"],
        }

    role_permissions = {
        key: {str(item).strip().lower() for item in value}
        for key, value in dict(payload.get("role_permissions", {})).items()
    }
    service_permissions = {
        key: {str(item).strip().lower() for item in value}
        for key, value in dict(payload.get("service_permissions", {})).items()
    }
    return PolicySnapshot(
        version=str(payload.get("version", "1.0.0")),
        issuer=str(payload.get("issuer", cfg.jwt_issuer)),
        audience=str(payload.get("audience", cfg.jwt_audience)),
        role_permissions=role_permissions,
        service_permissions=service_permissions,
        sandbox_profiles={str(item).strip().lower() for item in payload.get("sandbox_profiles", ["default"])},
    )


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
        max_submit_metadata_entries=_int_env("SYSTEM_API_MAX_SUBMIT_METADATA_ENTRIES", 64),
        max_submit_metadata_key_bytes=_int_env("SYSTEM_API_MAX_SUBMIT_METADATA_KEY_BYTES", 128),
        max_submit_metadata_value_bytes=_int_env("SYSTEM_API_MAX_SUBMIT_METADATA_VALUE_BYTES", 4096),
        max_submit_dependencies=_int_env("SYSTEM_API_MAX_SUBMIT_DEPENDENCIES", 64),
        jwt_secret=os.getenv("SYSTEM_API_AUTH_JWT_SECRET", "dev-jwt-secret"),
        jwt_issuer=os.getenv("SYSTEM_API_AUTH_ISSUER", "eigen-auth"),
        jwt_audience=os.getenv("SYSTEM_API_AUTH_AUDIENCE", "eigen-api"),
        policy_snapshot_path=os.getenv("SYSTEM_API_POLICY_SNAPSHOT_PATH", ""),
        policy_snapshot_json=os.getenv("SYSTEM_API_POLICY_SNAPSHOT_JSON", ""),
        service_identity=os.getenv("SYSTEM_API_SERVICE_IDENTITY", "system-api"),
        service_role=os.getenv("SYSTEM_API_SERVICE_ROLE", "public-ingress"),
        sandbox_profile=os.getenv("SYSTEM_API_SANDBOX_PROFILE", "default"),
    )


def _metadata(context: grpc.ServicerContext) -> dict[str, str]:
    return {k.lower(): v for k, v in (context.invocation_metadata() or [])}


def _b64url_decode(raw: str) -> bytes:
    padded = raw + "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _jwt_claims(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid JWT shape")
    header = json.loads(_b64url_decode(parts[0]))
    if header.get("alg") != "HS256":
        raise ValueError("unsupported JWT alg")
    claims = json.loads(_b64url_decode(parts[1]))
    signature = _b64url_decode(parts[2])
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    return {"header": header, "claims": claims, "signature": signature, "signing_input": signing_input}


def _verify_hs256(token: str, secret: str) -> dict[str, Any]:
    parsed = _jwt_claims(token)
    expected = hmac.new(secret.encode("utf-8"), parsed["signing_input"], hashlib.sha256).digest()
    if not hmac.compare_digest(expected, parsed["signature"]):
        raise ValueError("JWT signature mismatch")
    return dict(parsed["claims"])


def _service_context(md: dict[str, str], cfg: SecurityConfig, snapshot: PolicySnapshot) -> tuple[str | None, str | None]:
    identity = md.get("x-eigen-service", cfg.service_identity).strip() or cfg.service_identity
    role = md.get("x-eigen-service-role", cfg.service_role).strip() or cfg.service_role
    return identity, role.lower() if role else None


def _security_audit(
    method_name: str,
    decision: str,
    ctx: SecurityContext,
    reason: str,
    trace_id: str | None = None,
    traceparent: str | None = None,
) -> None:
    append_security_audit_event(
        {
            "method": method_name,
            "decision": decision,
            "reason": reason,
            "trace_id": trace_id or "",
            "traceparent": traceparent or "",
            **sanitized_security_metadata(
                subject=ctx.subject,
                roles=ctx.roles,
                auth_mode=ctx.auth_mode,
                policy_version=ctx.policy_version,
                service_identity=ctx.service_identity,
                sandbox_profile=ctx.sandbox_profile,
                replay_marker=ctx.claims.get("replay_marker"),
            ),
        }
    )


def enforce_authn(context: grpc.ServicerContext, *, method_name: str) -> None:
    cfg = load_security_config()
    if cfg.auth_mode == _AUTH_ALLOW_ALL:
        return

    md = _metadata(context)
    authorization = md.get("authorization", "")
    expected = f"Bearer {cfg.static_token}"
    if cfg.auth_mode == _AUTH_STATIC_TOKEN:
        if authorization != expected:
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.UNAUTHENTICATED,
                    message=f"authentication required for {method_name}",
                    reason="EIGEN_PUBLIC_UNAUTHENTICATED",
                    retryable=True,
                    metadata={"auth_mode": cfg.auth_mode},
                    detail="Authenticate with a valid bearer token before retrying.",
                ),
            )
        return

    if cfg.auth_mode == _AUTH_JWT_OAUTH2:
        if not authorization.startswith("Bearer "):
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.UNAUTHENTICATED,
                    message=f"authentication required for {method_name}",
                    reason="EIGEN_PUBLIC_UNAUTHENTICATED",
                    retryable=True,
                    metadata={"auth_mode": cfg.auth_mode},
                    detail="Provide a valid OAuth2/JWT bearer token.",
                ),
            )
        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = _verify_hs256(token, cfg.jwt_secret)
            now = int(time.time())
            if int(claims.get("exp", 0)) <= now or claims.get("iss") != cfg.jwt_issuer or cfg.jwt_audience not in str(claims.get("aud", "")):
                raise ValueError("JWT claims failed validation")
        except Exception:
            abort_public(
                context,
                PublicErrorSpec(
                    grpc_code=grpc.StatusCode.UNAUTHENTICATED,
                    message=f"authentication required for {method_name}",
                    reason="EIGEN_PUBLIC_UNAUTHENTICATED",
                    retryable=True,
                    metadata={"auth_mode": cfg.auth_mode},
                    detail="JWT validation failed.",
                ),
            )
        return

    # allow_all mode intentionally returns without checking auth.


def auth_context(context: grpc.ServicerContext) -> tuple[str, tuple[str, ...], str]:
    cfg = load_security_config()
    md = _metadata(context)
    if cfg.auth_mode == _AUTH_STATIC_TOKEN:
        tenant = md.get("x-eigen-tenant", "") or cfg.static_token_tenant
        raw_roles = md.get("x-eigen-roles", "")
        roles = tuple(role.strip().lower() for role in raw_roles.split(",") if role.strip())
        return cfg.static_token_subject, roles or cfg.static_token_roles, tenant

    subject = md.get("x-eigen-sub", "anonymous")
    tenant = md.get("x-eigen-tenant", "")
    raw_roles = md.get("x-eigen-roles", "admin")
    roles = tuple(role.strip().lower() for role in raw_roles.split(",") if role.strip())
    if not roles:
        roles = ("admin",)
    return subject, roles, tenant


def security_context(context: grpc.ServicerContext, *, method_name: str) -> SecurityContext:
    cfg = load_security_config()
    snapshot = _load_policy_snapshot(cfg)
    subject, roles, tenant = auth_context(context)
    md = _metadata(context)
    service_identity, service_role = _service_context(md, cfg, snapshot)

    replay_marker = (
        md.get("x-eigen-replay-marker")
        or md.get("replay-marker")
        or ""
    ).strip()
    
    return SecurityContext(
        subject=subject,
        roles=roles,
        tenant=tenant,
        auth_mode=cfg.auth_mode,
        policy_version=snapshot.version,
        service_identity=service_identity,
        service_role=service_role,
        sandbox_profile=md.get("x-eigen-sandbox-profile", cfg.sandbox_profile).strip() or cfg.sandbox_profile,
        claims={
            "method": method_name,
            "replay_marker": replay_marker,
            "policy_snapshot": snapshot.version,
        },
    )


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
    snapshot = _load_policy_snapshot(cfg)

    md = {k.lower(): v for k, v in (context.invocation_metadata() or [])}
    trace_id = md.get("trace_id") or trace_id_from_traceparent(md.get("traceparent"))
    traceparent = md.get("traceparent") or ""
    replay_marker = (md.get("x-eigen-replay-marker") or md.get("replay-marker") or "").strip()
    raw_permissions = md.get("x-eigen-permissions", "")
    raw_roles = md.get("x-eigen-roles", "")
    granted = {
        item.strip().lower()
        for blob in (raw_permissions, raw_roles)
        for item in blob.split(",")
        if item.strip()
    }

    # In static_token mode, explicitly configured token roles are baseline claims.
    # Per-request metadata can still add explicit permissions/roles for tests/dev.
    env_roles = os.getenv("SYSTEM_API_AUTH_ROLES")
    if env_roles is not None:
        granted.update(role.lower() for role in cfg.static_token_roles)
        for role in cfg.static_token_roles:
            granted.update(_ROLE_PERMISSIONS.get(role.lower(), set()))

    # Versioned policy snapshot is the authoritative runtime baseline.
    for role in tuple(granted):
        granted.update(snapshot.role_permissions.get(role, set()))

    need = required_permission.strip().lower()
    scope, _, action = need.partition(":")
    wildcard = f"{scope}:*"

    subject, _, tenant = auth_context(context)
    if not subject.strip() or not tenant.strip():
        _security_audit(
            "authz",
            "deny",
            SecurityContext(
                subject=subject,
                roles=tuple(sorted(granted)),
                tenant=tenant,
                auth_mode=cfg.auth_mode,
                policy_version=snapshot.version,
                service_identity=cfg.service_identity,
                service_role=cfg.service_role,
                sandbox_profile=cfg.sandbox_profile,
                claims={"replay_marker": replay_marker},
            ),
            "POLICY_DENY_MISSING_AUTH_CONTEXT",
            trace_id=trace_id,
        )
        log_authz_denied(
            method=getattr(context, "_rpc_event_call_details", None).method if hasattr(context, "_rpc_event_call_details") else "unknown",
            subject=subject or "unknown",
            permission="POLICY_DENY_MISSING_AUTH_CONTEXT",
            trace_id=trace_id,
            traceparent=traceparent,
        )
        abort_public(
            context,
            PublicErrorSpec(
                grpc_code=grpc.StatusCode.PERMISSION_DENIED,
                message="subject and tenant are required",
                reason="EIGEN_PUBLIC_PERMISSION_DENIED",
                retryable=False,
                metadata={"policy": "POLICY_DENY_MISSING_AUTH_CONTEXT"},
                detail="Provide authenticated subject and tenant context.",
            ),
        )

    if snapshot.version.strip() == "":
        abort_public(
            context,
            PublicErrorSpec(
                grpc_code=grpc.StatusCode.PERMISSION_DENIED,
                message="policy backend unavailable",
                reason="EIGEN_PUBLIC_POLICY_BACKEND_UNAVAILABLE",
                retryable=False,
                metadata={"policy": "POLICY_BACKEND_UNAVAILABLE"},
                detail="Security policy snapshot could not be loaded; fail closed.",
            ),
        )

    if need in granted or wildcard in granted or "*" in granted:
        _security_audit(
            "authz",
            "allow",
            SecurityContext(subject=subject, roles=tuple(sorted(granted)), tenant=tenant, auth_mode=cfg.auth_mode, policy_version=snapshot.version, service_identity=cfg.service_identity, service_role=cfg.service_role, sandbox_profile=cfg.sandbox_profile, claims={"replay_marker": replay_marker}),
            need,
            trace_id=trace_id,
            traceparent=traceparent,
        )
        return

    policy_marker = "POLICY_DENY_PERMISSION_REQUIRED"
    log_authz_denied(
        method=getattr(context, "_rpc_event_call_details", None).method if hasattr(context, "_rpc_event_call_details") else "unknown",
        subject=subject,
        permission=f"{policy_marker}:{need}",
        trace_id=trace_id,
        traceparent=traceparent,
    )
    _security_audit(
        "authz",
        "deny",
        SecurityContext(subject=subject, roles=tuple(granted), tenant=tenant, auth_mode=cfg.auth_mode, policy_version=snapshot.version, service_identity=cfg.service_identity, service_role=cfg.service_role, sandbox_profile=cfg.sandbox_profile, claims={"replay_marker": replay_marker}),
        f"{policy_marker}:{need}",
        trace_id=trace_id,
        traceparent=traceparent,
    )
    abort_public(
        context,
        PublicErrorSpec(
            grpc_code=grpc.StatusCode.PERMISSION_DENIED,
            message=f"requires {required_permission}",
            reason="EIGEN_PUBLIC_PERMISSION_DENIED",
            retryable=False,
            metadata={"policy": "POLICY_DENY_PERMISSION_REQUIRED", "permission": required_permission},
            detail="Caller lacks the required permission for this public API method.",
        ),
    )


def enforce_sandbox_policy(context: grpc.ServicerContext, *, sandbox_profile: str) -> None:
    cfg = load_security_config()
    snapshot = _load_policy_snapshot(cfg)
    requested = (sandbox_profile or cfg.sandbox_profile).strip().lower() or cfg.sandbox_profile
    if requested not in snapshot.sandbox_profiles:
        abort_public(
            context,
            PublicErrorSpec(
                grpc_code=grpc.StatusCode.PERMISSION_DENIED,
                message="sandbox profile denied",
                reason="EIGEN_PUBLIC_SANDBOX_PROFILE_DENIED",
                retryable=False,
                metadata={"sandbox_profile": requested, "policy": snapshot.version},
                detail="Requested sandbox profile is not allowed by the active policy snapshot.",
            ),
        )
