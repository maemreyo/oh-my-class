"""Tests for 9Router live chat smoke harness.

Covers:
- SmokeConfig defaults and env-var override
- SmokeResult status semantics (pass / blocked / fail)
- smoke_probe against unreachable service → blocked (not crash)
- smoke_probe against mock server → pass with timing
- Adversarial: malformed JSON response
- Adversarial: hung / timeout endpoint (simulated via exception)
- Adversarial: misleading success (200 but garbage body)
- Adversarial: malformed input to smoke_probe (empty base_url)
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest

from packages.agents.llm.smoke import SmokeConfig, SmokeResult, smoke_probe

# ---------------------------------------------------------------------------
# SmokeConfig
# ---------------------------------------------------------------------------


class TestSmokeConfig:
    """SmokeConfig carries the configurable target for the smoke harness."""

    def test_defaults_match_9router(self) -> None:
        cfg = SmokeConfig()
        assert cfg.base_url == "http://127.0.0.1:20228"
        assert cfg.model == "4omc"
        assert cfg.timeout_s > 0

    def test_custom_values_accepted(self) -> None:
        cfg = SmokeConfig(base_url="http://custom:9999", model="f.light", timeout_s=5.0)
        assert cfg.base_url == "http://custom:9999"
        assert cfg.model == "f.light"
        assert cfg.timeout_s == 5.0

    def test_trailing_slash_stripped(self) -> None:
        cfg = SmokeConfig(base_url="http://host:1234/")
        assert cfg.base_url == "http://host:1234"


# ---------------------------------------------------------------------------
# SmokeResult
# ---------------------------------------------------------------------------


class TestSmokeResult:
    """SmokeResult encodes the outcome of a smoke probe."""

    def test_pass_result_fields(self) -> None:
        result = SmokeResult(
            status="pass",
            models_endpoint_ok=True,
            chat_endpoint_ok=True,
            model_used="4omc",
            elapsed_s=0.5,
            error=None,
        )
        assert result.status == "pass"
        assert result.models_endpoint_ok is True
        assert result.chat_endpoint_ok is True

    def test_blocked_result_when_models_unreachable(self) -> None:
        result = SmokeResult(
            status="blocked",
            models_endpoint_ok=False,
            chat_endpoint_ok=False,
            model_used=None,
            elapsed_s=0.1,
            error="Connection refused",
        )
        assert result.status == "blocked"
        assert result.model_used is None


# ---------------------------------------------------------------------------
# smoke_probe — reachable / unreachable (live, no mock)
# ---------------------------------------------------------------------------


class TestSmokeProbeUnreachable:
    """When the service is down, smoke_probe must return 'blocked', not raise."""

    @pytest.mark.asyncio
    async def test_returns_blocked_on_connection_refused(self) -> None:
        cfg = SmokeConfig(base_url="http://127.0.0.1:19999", timeout_s=1.0)
        result = await smoke_probe(cfg)

        assert result.status == "blocked"
        assert result.models_endpoint_ok is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_returns_blocked_on_timeout(self) -> None:
        cfg = SmokeConfig(base_url="http://127.0.0.1:19999", timeout_s=0.01)
        result = await smoke_probe(cfg)

        assert result.status == "blocked"
        assert result.models_endpoint_ok is False


# ---------------------------------------------------------------------------
# smoke_probe — injectable mock client
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal httpx.Response stand-in for deterministic testing."""

    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise json.JSONDecodeError("no content", "", 0)
        return self._payload


class _FakeAsyncClient:
    """Injectable mock client that routes GET/POST to canned responses."""

    def __init__(self, get_resp: _FakeResponse, post_resp: _FakeResponse | None = None) -> None:
        self._get_resp = get_resp
        self._post_resp = post_resp
        self._get_called = False
        self._post_called = False

    async def get(self, url: str, **_kwargs: Any) -> _FakeResponse:
        self._get_called = True
        return self._get_resp

    async def post(self, url: str, **_kwargs: Any) -> _FakeResponse:
        self._post_called = True
        if self._post_resp is None:
            raise httpx.ConnectError("post not configured")
        return self._post_resp


class TestSmokeProbeWithMockServer:
    """When a mock server responds correctly, smoke_probe must return 'pass'."""

    @pytest.mark.asyncio
    async def test_pass_when_models_and_chat_succeed(self) -> None:
        models_resp = _FakeResponse(200, {"data": [{"id": "4omc", "object": "model"}]})
        chat_resp = _FakeResponse(
            200,
            {
                "id": "smoke-test-1",
                "object": "chat.completion",
                "model": "4omc",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
            },
        )
        client = _FakeAsyncClient(models_resp, chat_resp)

        cfg = SmokeConfig(base_url="http://mock:20228", model="4omc", timeout_s=5.0)
        result = await smoke_probe(cfg, _client=client)  # type: ignore[arg-type]

        assert result.status == "pass"
        assert result.models_endpoint_ok is True
        assert result.chat_endpoint_ok is True
        assert result.model_used == "4omc"
        assert result.elapsed_s >= 0
        assert client._get_called is True
        assert client._post_called is True

    @pytest.mark.asyncio
    async def test_blocked_when_models_endpoint_fails(self) -> None:
        models_resp = _FakeResponse(500)
        client = _FakeAsyncClient(models_resp)

        cfg = SmokeConfig(base_url="http://mock:20228", model="4omc")
        result = await smoke_probe(cfg, _client=client)  # type: ignore[arg-type]

        assert result.status == "blocked"
        assert result.models_endpoint_ok is False
        assert result.chat_endpoint_ok is False
        assert client._post_called is False, "chat should not be called if models fails"


# ---------------------------------------------------------------------------
# Adversarial: malformed JSON response
# ---------------------------------------------------------------------------


class TestSmokeProbeAdversarialMalformedJson:
    """Server returns 200 but body is not valid JSON."""

    @pytest.mark.asyncio
    async def test_returns_blocked_on_garbled_models_json(self) -> None:
        # httpx.Response with text that won't parse as JSON — attach a dummy request
        fake_req = httpx.Request("GET", "http://mock:20228/v1/models")
        resp = httpx.Response(200, text="{not valid json {{{", request=fake_req)

        class _GarbledClient:
            async def get(self, url: str, **_kw: Any) -> httpx.Response:
                return resp

            async def post(self, url: str, **_kw: Any) -> httpx.Response:  # pragma: no cover
                return httpx.Response(200, json={})

        cfg = SmokeConfig(base_url="http://mock:20228")
        result = await smoke_probe(cfg, _client=_GarbledClient())  # type: ignore[arg-type]

        assert result.status == "blocked"
        assert result.error is not None
        err_lower = result.error.lower()
        assert "json" in err_lower or "decode" in err_lower


# ---------------------------------------------------------------------------
# Adversarial: misleading success (200 but wrong structure)
# ---------------------------------------------------------------------------


class TestSmokeProbeAdversarialMisleadingSuccess:
    """Server returns 200 with valid JSON but wrong shape — should not count as pass."""

    @pytest.mark.asyncio
    async def test_returns_blocked_when_models_missing_data_key(self) -> None:
        models_resp = _FakeResponse(200, {"message": "hello"})
        client = _FakeAsyncClient(models_resp)

        cfg = SmokeConfig(base_url="http://mock:20228")
        result = await smoke_probe(cfg, _client=client)  # type: ignore[arg-type]

        # Models endpoint returned 200 but missing 'data' list — NOT a pass
        assert result.status == "blocked"
        assert result.models_endpoint_ok is False

    @pytest.mark.asyncio
    async def test_returns_fail_when_chat_has_no_choices(self) -> None:
        models_resp = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        chat_resp = _FakeResponse(200, {"id": "x", "model": "4omc", "choices": []})
        client = _FakeAsyncClient(models_resp, chat_resp)

        cfg = SmokeConfig(base_url="http://mock:20228")
        result = await smoke_probe(cfg, _client=client)  # type: ignore[arg-type]

        # Models OK but chat returned empty choices — fail, not pass
        assert result.models_endpoint_ok is True
        assert result.chat_endpoint_ok is False
        assert result.status == "fail"


# ---------------------------------------------------------------------------
# Adversarial: hung / timeout (simulated via exception)
# ---------------------------------------------------------------------------


class TestSmokeProbeAdversarialTimeout:
    """Server accepts connection but never responds — must not hang forever.

    In real life, httpx timeout raises ReadTimeout / ConnectTimeout.
    We simulate this by having the client raise ConnectTimeout directly.
    """

    @pytest.mark.asyncio
    async def test_timeout_yields_blocked(self) -> None:
        class _TimeoutClient:
            async def get(self, url: str, **_kw: Any) -> Any:
                raise httpx.ConnectTimeout("simulated timeout")

            async def post(self, url: str, **_kw: Any) -> Any:  # pragma: no cover
                raise httpx.ConnectTimeout("simulated timeout")

        cfg = SmokeConfig(base_url="http://mock:20228", timeout_s=0.1)
        start = time.monotonic()
        result = await smoke_probe(cfg, _client=_TimeoutClient())  # type: ignore[arg-type]
        elapsed = time.monotonic() - start

        assert result.status == "blocked"
        assert result.models_endpoint_ok is False
        assert elapsed < 2.0, f"Smoke probe took {elapsed:.1f}s — hung instead of timing out"

    @pytest.mark.asyncio
    async def test_read_timeout_yields_blocked(self) -> None:
        class _ReadTimeoutClient:
            async def get(self, url: str, **_kw: Any) -> Any:
                raise httpx.ReadTimeout("read timed out")

            async def post(self, url: str, **_kw: Any) -> Any:  # pragma: no cover
                raise httpx.ReadTimeout("read timed out")

        cfg = SmokeConfig(base_url="http://mock:20228")
        result = await smoke_probe(cfg, _client=_ReadTimeoutClient())  # type: ignore[arg-type]

        assert result.status == "blocked"
        assert "timeout" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# Adversarial: malformed input to smoke_probe
# ---------------------------------------------------------------------------


class TestSmokeProbeAdversarialBadInput:
    """Empty base_url or absurd values must not crash the harness."""

    @pytest.mark.asyncio
    async def test_empty_base_url_returns_blocked(self) -> None:
        cfg = SmokeConfig(base_url="", model="4omc")
        result = await smoke_probe(cfg)
        assert result.status == "blocked"

    @pytest.mark.asyncio
    async def test_non_http_scheme_returns_blocked(self) -> None:
        cfg = SmokeConfig(base_url="ftp://weird:1234", model="4omc")
        result = await smoke_probe(cfg)
        assert result.status == "blocked"
