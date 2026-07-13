"""Tests for SEC-01 rate limiting: core Redis primitives + middleware wiring.

Uses a real dev Redis (docker-compose's `redis` service), mirroring the skip
pattern `test_teaching_session_live_sync.py` already established for this
Redis instance -- there is no fakeredis dependency in this repo, and a real
Redis is the whole point of a horizontal-safe counter store (SEC-01's
"Shared, horizontal-safe counter store" requirement).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from services.gateway.auth.jwt_handler import create_access_token
from services.gateway.auth.models import Role, User
from services.gateway.middleware.auth_middleware import JWTMiddleware
from services.gateway.middleware.rate_limit_middleware import (
    IPRateLimitMiddleware,
    TokenRateLimitMiddleware,
)
from services.gateway.rate_limiting import (
    RateLimitTier,
    check_rate_limit,
    enforce_payload_size_limits,
    is_blocked,
    rate_limit_redis_client,
    record_violation,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

TEST_REDIS_URL = "redis://:omc_redis_secret@localhost:6379"


def _test_client() -> redis.Redis:
    return redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)


async def _skip_if_unreachable(client: redis.Redis) -> None:
    try:
        await client.ping()
    except (redis.RedisError, OSError):
        pytest.skip("Redis is not reachable in this environment")


# ── Core primitives (services/gateway/rate_limiting.py) ──────────────────


class TestCheckRateLimit:
    async def test_allows_traffic_under_the_limit(self) -> None:
        client = _test_client()
        await _skip_if_unreachable(client)
        key = f"test:{uuid4()}"
        tier = RateLimitTier(limit=5, window_seconds=60)

        for _ in range(5):
            outcome = await check_rate_limit(client, key, tier)
            assert outcome.allowed

    async def test_blocks_once_over_the_limit_with_retry_after(self) -> None:
        client = _test_client()
        await _skip_if_unreachable(client)
        key = f"test:{uuid4()}"
        tier = RateLimitTier(limit=3, window_seconds=60)

        for _ in range(3):
            assert (await check_rate_limit(client, key, tier)).allowed

        outcome = await check_rate_limit(client, key, tier)
        assert not outcome.allowed
        assert outcome.retry_after_seconds > 0


class TestAbuseEscalation:
    async def test_repeated_violations_trigger_an_escalating_block(self) -> None:
        client = _test_client()
        await _skip_if_unreachable(client)
        principal = f"test:{uuid4()}"

        block_seconds = None
        for _ in range(5):
            block_seconds = await record_violation(client, principal, reason="test")

        assert block_seconds is not None
        assert await is_blocked(client, principal) is not None

    async def test_below_threshold_does_not_block(self) -> None:
        client = _test_client()
        await _skip_if_unreachable(client)
        principal = f"test:{uuid4()}"

        for _ in range(2):
            result = await record_violation(client, principal, reason="test")
            assert result is None
        assert await is_blocked(client, principal) is None


class TestPayloadSizeLimits:
    def test_normal_payload_is_allowed(self) -> None:
        enforce_payload_size_limits("a short teaching request", {"grade": 5})

    def test_oversized_raw_request_is_rejected_with_413(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            enforce_payload_size_limits("x" * 100_000, {})
        assert exc_info.value.status_code == 413

    def test_oversized_class_info_is_rejected_with_413(self) -> None:
        huge_class_info = {"student_evidence": {"notes": "x" * 100_000}}
        with pytest.raises(HTTPException) as exc_info:
            enforce_payload_size_limits("normal request", huge_class_info)
        assert exc_info.value.status_code == 413


# ── Middleware wiring (IPRateLimitMiddleware / TokenRateLimitMiddleware) ──

_JWT_SECRET = "test-secret-minimum-32-characters"


def _build_app(
    *,
    ip_general_tier: RateLimitTier | None = None,
    ip_login_tier: RateLimitTier | None = None,
    token_tiers: dict[Role, tuple[RateLimitTier, RateLimitTier]] | None = None,
    max_body_bytes: int | None = None,
) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/health")
    async def health() -> dict[str, bool]:
        # Public path per JWTMiddleware.PUBLIC_PATHS -- used by the anonymous
        # (no-Authorization) per-IP tests below.
        return {"ok": True}

    @app.post("/mutate")
    async def mutate() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/auth/login")
    async def login() -> dict[str, bool]:
        return {"ok": True}

    # Registration order matters the same way it does in main.py: the first
    # add_middleware() call ends up innermost (closest to the router), so
    # TokenRateLimitMiddleware (needs JWT-populated request.state) is added
    # first, then JWTMiddleware, then IPRateLimitMiddleware (runs first,
    # before auth) -- see main.py's comment for the full reasoning.
    app.add_middleware(TokenRateLimitMiddleware, tiers=token_tiers)
    app.add_middleware(JWTMiddleware)
    app.add_middleware(
        IPRateLimitMiddleware,
        general_tier=ip_general_tier,
        login_tier=ip_login_tier,
        max_body_bytes=max_body_bytes,
    )
    return app


def _bearer(role: Role, user_id: str) -> str:
    token = create_access_token(User(user_id=user_id, username=user_id, role=role))
    return f"Bearer {token.access_token}"


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", _JWT_SECRET)
    # Middleware resolves its Redis client the same way live_sync.py does
    # (env-based `resolve_redis_url()`) -- point it at the same dev Redis
    # `TEST_REDIS_URL` above hardcodes credentials for.
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_AUTH", "omc_redis_secret")


@pytest.fixture(autouse=True)
def _require_redis() -> None:
    anyio.run(_skip_if_unreachable, _test_client())


@pytest.fixture
def trusted_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMC_TRUST_PROXY_HEADERS", "true")


class TestPerIPRateLimit:
    def test_per_ip_limit_exceeded_returns_429_with_retry_after(
        self, trusted_proxy: None
    ) -> None:
        app = _build_app(ip_general_tier=RateLimitTier(limit=2, window_seconds=60))
        ip = f"10.0.0.{uuid4().int % 250}"
        with TestClient(app) as client:
            for _ in range(2):
                resp = client.get("/health", headers={"X-Forwarded-For": ip})
                assert resp.status_code == 200

            resp = client.get("/health", headers={"X-Forwarded-For": ip})
            assert resp.status_code == 429
            assert int(resp.headers["Retry-After"]) > 0

    def test_per_ip_limit_on_unauthenticated_login_path(self, trusted_proxy: None) -> None:
        app = _build_app(ip_login_tier=RateLimitTier(limit=1, window_seconds=60))
        ip = f"10.0.1.{uuid4().int % 250}"
        with TestClient(app) as client:
            ok = client.post("/auth/login", headers={"X-Forwarded-For": ip})
            assert ok.status_code == 200

            blocked = client.post("/auth/login", headers={"X-Forwarded-For": ip})
            assert blocked.status_code == 429

    def test_below_threshold_traffic_is_unaffected(self, trusted_proxy: None) -> None:
        app = _build_app(ip_general_tier=RateLimitTier(limit=100, window_seconds=60))
        ip = f"10.0.2.{uuid4().int % 250}"
        with TestClient(app) as client:
            for _ in range(10):
                assert client.get("/health", headers={"X-Forwarded-For": ip}).status_code == 200

    def test_oversized_body_rejected_with_413(self, trusted_proxy: None) -> None:
        app = _build_app(max_body_bytes=10)
        ip = f"10.0.3.{uuid4().int % 250}"
        with TestClient(app) as client:
            resp = client.post(
                "/mutate",
                content=b"x" * 1000,
                headers={"X-Forwarded-For": ip, "Content-Type": "application/octet-stream"},
            )
            assert resp.status_code == 413


class TestPerTokenRateLimit:
    def test_per_token_limit_exceeded_returns_429_with_retry_after(self) -> None:
        tiny_tier = RateLimitTier(limit=2, window_seconds=60)
        app = _build_app(
            ip_general_tier=RateLimitTier(limit=1000, window_seconds=60),
            token_tiers={Role.TEACHER: (tiny_tier, tiny_tier)},
        )
        headers = {"Authorization": _bearer(Role.TEACHER, f"teacher-{uuid4()}")}
        with TestClient(app) as client:
            for _ in range(2):
                assert client.get("/ping", headers=headers).status_code == 200

            resp = client.get("/ping", headers=headers)
            assert resp.status_code == 429
            assert int(resp.headers["Retry-After"]) > 0

    def test_teacher_and_admin_have_different_tiers(self) -> None:
        teacher_tier = RateLimitTier(limit=2, window_seconds=60)
        admin_tier = RateLimitTier(limit=10, window_seconds=60)
        app = _build_app(
            ip_general_tier=RateLimitTier(limit=1000, window_seconds=60),
            token_tiers={
                Role.TEACHER: (teacher_tier, teacher_tier),
                Role.SYSTEM_ADMIN: (admin_tier, admin_tier),
            },
        )
        teacher_headers = {"Authorization": _bearer(Role.TEACHER, f"teacher-{uuid4()}")}
        admin_headers = {"Authorization": _bearer(Role.SYSTEM_ADMIN, f"admin-{uuid4()}")}

        with TestClient(app) as client:
            # Teacher trips its (lower) limit at request 3.
            for _ in range(2):
                assert client.get("/ping", headers=teacher_headers).status_code == 200
            assert client.get("/ping", headers=teacher_headers).status_code == 429

            # Admin, same call count, stays under its higher limit.
            for _ in range(3):
                assert client.get("/ping", headers=admin_headers).status_code == 200

    def test_below_threshold_traffic_is_unaffected(self) -> None:
        generous_tier = RateLimitTier(limit=100, window_seconds=60)
        app = _build_app(
            ip_general_tier=RateLimitTier(limit=1000, window_seconds=60),
            token_tiers={Role.TEACHER: (generous_tier, generous_tier)},
        )
        headers = {"Authorization": _bearer(Role.TEACHER, f"teacher-{uuid4()}")}
        with TestClient(app) as client:
            for _ in range(10):
                assert client.get("/ping", headers=headers).status_code == 200

    def test_unauthenticated_requests_are_not_token_rate_limited(self) -> None:
        """Public paths (no request.state.user_id) skip the token limiter entirely."""
        app = _build_app(
            ip_general_tier=RateLimitTier(limit=1000, window_seconds=60),
            token_tiers={Role.TEACHER: (RateLimitTier(limit=1, window_seconds=60),) * 2},
        )
        with TestClient(app) as client:
            for _ in range(5):
                assert client.post("/auth/login").status_code == 200
