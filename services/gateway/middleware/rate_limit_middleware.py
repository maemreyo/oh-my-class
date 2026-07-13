"""HTTP-surface rate limiting (SEC-01) -- per-IP and per-token, Redis-backed.

Two middlewares, wired in `main.py` on either side of `JWTMiddleware`:

* ``IPRateLimitMiddleware`` runs *before* auth (cheap rejection first): it
  enforces a max request body size (413), a per-IP request budget on every
  path -- including unauthenticated ones like `/auth/login`, the
  credential-stuffing target this exists for -- and a stricter login-specific
  budget. It also carries the abuse-escalation block for IPs.
* ``TokenRateLimitMiddleware`` runs *after* auth resolves `request.state.
  user_id`/`user_role` (set by `JWTMiddleware`): it enforces a per-principal
  budget, tiered by role and by endpoint class (mutating vs read).

Both fail *open* on a Redis outage (log + allow) -- the same tradeoff
`teaching_session/live_sync.py` already makes for this Redis instance:
availability over strict enforcement when the shared store itself is down.
"""

from __future__ import annotations

import os

import redis.exceptions
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..auth.models import Role
from ..logging_config import get_logger
from ..rate_limiting import (
    RateLimitTier,
    check_rate_limit,
    is_blocked,
    rate_limit_redis_client,
    record_violation,
)

_logger = get_logger("services.gateway.rate_limit_middleware")

_RETRY_AFTER_HEADER = "Retry-After"

# ── Config (env-overridable; defaults sized for the north-star ~1,000-teacher scale) ──

MAX_BODY_BYTES = int(os.getenv("OMC_MAX_BODY_BYTES", str(2 * 1024 * 1024)))  # 2 MB

_IP_GENERAL_TIER = RateLimitTier(
    limit=int(os.getenv("OMC_IP_RATE_LIMIT", "300")), window_seconds=60
)
_IP_LOGIN_TIER = RateLimitTier(
    limit=int(os.getenv("OMC_IP_LOGIN_RATE_LIMIT", "10")), window_seconds=60
)

_LOGIN_PATHS = frozenset({"/auth/login"})

# role -> (read tier, mutate tier). Admin roles get materially more headroom.
_TOKEN_TIERS: dict[Role, tuple[RateLimitTier, RateLimitTier]] = {
    Role.TEACHER: (
        RateLimitTier(limit=int(os.getenv("OMC_TEACHER_READ_RATE_LIMIT", "120")), window_seconds=60),
        RateLimitTier(limit=int(os.getenv("OMC_TEACHER_MUTATE_RATE_LIMIT", "30")), window_seconds=60),
    ),
    Role.ADMIN: (
        RateLimitTier(limit=int(os.getenv("OMC_ADMIN_READ_RATE_LIMIT", "300")), window_seconds=60),
        RateLimitTier(limit=int(os.getenv("OMC_ADMIN_MUTATE_RATE_LIMIT", "100")), window_seconds=60),
    ),
    Role.SCHOOL_ADMIN: (
        RateLimitTier(limit=int(os.getenv("OMC_ADMIN_READ_RATE_LIMIT", "300")), window_seconds=60),
        RateLimitTier(limit=int(os.getenv("OMC_ADMIN_MUTATE_RATE_LIMIT", "100")), window_seconds=60),
    ),
    Role.SYSTEM_ADMIN: (
        RateLimitTier(limit=int(os.getenv("OMC_ADMIN_READ_RATE_LIMIT", "300")), window_seconds=60),
        RateLimitTier(limit=int(os.getenv("OMC_ADMIN_MUTATE_RATE_LIMIT", "100")), window_seconds=60),
    ),
}

_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _client_ip(request: Request) -> str:
    """Resolve the client IP, honoring X-Forwarded-For only if explicitly trusted.

    # ponytail: a single on/off flag, not a trusted-proxy CIDR allowlist --
    # fine for a single reverse-proxy fronting the fleet (the only topology
    # this deployment has today); add an allowlist if untrusted intermediary
    # proxies ever sit in front of the trusted one.
    """
    if os.getenv("OMC_TRUST_PROXY_HEADERS", "").casefold() in {"1", "true", "yes", "on"}:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit_response(retry_after_seconds: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": detail},
        headers={_RETRY_AFTER_HEADER: str(max(retry_after_seconds, 1))},
    )


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limit + max body size, applied before auth resolves.

    Tiers/limits default to the module-level env-configured constants but can
    be overridden per-instance (tests pass small tiers so they don't need to
    wait out a real 60s window).
    """

    def __init__(
        self,
        app,
        *,
        general_tier: RateLimitTier | None = None,
        login_tier: RateLimitTier | None = None,
        max_body_bytes: int | None = None,
    ) -> None:
        super().__init__(app)
        self._general_tier = general_tier or _IP_GENERAL_TIER
        self._login_tier = login_tier or _IP_LOGIN_TIER
        self._max_body_bytes = MAX_BODY_BYTES if max_body_bytes is None else max_body_bytes

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > self._max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request body exceeds {self._max_body_bytes} bytes"},
                    )
            except ValueError:
                pass  # malformed header -- let downstream parsing reject it

        client_ip = _client_ip(request)
        client = rate_limit_redis_client()
        principal_key = f"ip:{client_ip}"

        try:
            blocked_ttl = await is_blocked(client, principal_key)
            if blocked_ttl is not None:
                return _rate_limit_response(blocked_ttl, "Too many requests -- temporarily blocked")

            is_login = request.url.path in _LOGIN_PATHS
            tier = self._login_tier if is_login else self._general_tier
            key = f"{principal_key}:{'login' if is_login else 'all'}"
            outcome = await check_rate_limit(client, key, tier)
            if not outcome.allowed:
                await record_violation(client, principal_key, reason=f"ip_rate_limit:{request.url.path}")
                return _rate_limit_response(outcome.retry_after_seconds, "Rate limit exceeded")
        except (redis.exceptions.RedisError, OSError):
            _logger.warning("rate_limit.redis_unavailable scope=ip path=%s", request.url.path)

        return await call_next(request)


class TokenRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-token rate limit, applied after JWTMiddleware resolves the principal."""

    def __init__(
        self,
        app,
        *,
        tiers: dict[Role, tuple[RateLimitTier, RateLimitTier]] | None = None,
    ) -> None:
        super().__init__(app)
        self._tiers = tiers or _TOKEN_TIERS

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            # No authenticated principal (public path, or auth already failed
            # and short-circuited upstream) -- nothing to key a token budget on.
            return await call_next(request)

        role_value = getattr(request.state, "user_role", None)
        try:
            role = Role(role_value)
        except ValueError:
            role = Role.TEACHER
        read_tier, mutate_tier = self._tiers.get(role, self._tiers[Role.TEACHER])
        endpoint_class = "read" if request.method in _READ_METHODS else "mutate"
        tier = read_tier if endpoint_class == "read" else mutate_tier

        client = rate_limit_redis_client()
        principal_key = f"token:{user_id}"

        try:
            blocked_ttl = await is_blocked(client, principal_key)
            if blocked_ttl is not None:
                return _rate_limit_response(blocked_ttl, "Too many requests -- temporarily blocked")

            outcome = await check_rate_limit(client, f"{principal_key}:{endpoint_class}", tier)
            if not outcome.allowed:
                await record_violation(client, principal_key, reason=f"token_rate_limit:{endpoint_class}")
                return _rate_limit_response(outcome.retry_after_seconds, "Rate limit exceeded")
        except (redis.exceptions.RedisError, OSError):
            _logger.warning("rate_limit.redis_unavailable scope=token user_id=%s", user_id)

        return await call_next(request)
