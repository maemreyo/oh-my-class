"""Deterministic tests for 9Router provider evidence collection.

Covers:
  - ProviderEvidenceEntry: frozen, serialisation round-trip
  - ProviderProbeConfig: defaults, trailing-slash strip
  - collect_provider_evidence: pass / blocked / fail paths via mock client
  - Adversarial: malformed JSON, misleading success, invalid base_url
  - No paid fallback: sequential probing only, no retry to different provider
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from services.gateway.provider_evidence import (
    ProviderEvidenceEntry,
    ProviderProbeConfig,
    collect_provider_evidence,
)

# ---------------------------------------------------------------------------
# ProviderProbeConfig
# ---------------------------------------------------------------------------


class TestProviderProbeConfig:
    def test_defaults(self) -> None:
        cfg = ProviderProbeConfig()
        assert cfg.base_url == "http://127.0.0.1:20228"
        assert cfg.model == "4omc"
        assert cfg.timeout_s > 0

    def test_custom_values(self) -> None:
        cfg = ProviderProbeConfig(base_url="http://custom:9999", model="f.light")
        assert cfg.base_url == "http://custom:9999"
        assert cfg.model == "f.light"

    def test_trailing_slash_stripped(self) -> None:
        cfg = ProviderProbeConfig(base_url="http://host:1234/")
        assert cfg.base_url == "http://host:1234"


# ---------------------------------------------------------------------------
# ProviderEvidenceEntry
# ---------------------------------------------------------------------------


class TestProviderEvidenceEntry:
    def test_frozen(self) -> None:
        entry = ProviderEvidenceEntry(
            base_url="http://x:1",
            model="4omc",
            timestamp="t",
            status="pass",
            elapsed_s=0.1,
            models_endpoint_ok=True,
            chat_endpoint_ok=True,
            error=None,
        )
        with pytest.raises(AttributeError):
            entry.status = "blocked"  # type: ignore[misc]

    def test_to_dict_round_trip(self) -> None:
        original = ProviderEvidenceEntry(
            base_url="http://router:20228",
            model="4omc",
            timestamp="2026-06-28T00:00:00+00:00",
            status="pass",
            elapsed_s=0.42,
            models_endpoint_ok=True,
            chat_endpoint_ok=True,
            error=None,
        )
        d = original.to_dict()
        restored = ProviderEvidenceEntry.from_dict(d)
        assert restored == original

    def test_to_dict_blocked_has_error(self) -> None:
        entry = ProviderEvidenceEntry(
            base_url="http://x:1",
            model="4omc",
            timestamp="t",
            status="blocked",
            elapsed_s=0.0,
            models_endpoint_ok=False,
            chat_endpoint_ok=False,
            error="Connection refused",
        )
        d = entry.to_dict()
        assert d["status"] == "blocked"
        assert d["error"] == "Connection refused"
        restored = ProviderEvidenceEntry.from_dict(d)
        assert restored.error == "Connection refused"


# ---------------------------------------------------------------------------
# Mock HTTP client helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
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
    def __init__(
        self,
        get_resp: _FakeResponse,
        post_resp: _FakeResponse | None = None,
    ) -> None:
        self._get_resp = get_resp
        self._post_resp = post_resp
        self._get_called = False
        self._post_called = False

    async def get(self, url: str, **_kw: Any) -> _FakeResponse:
        self._get_called = True
        return self._get_resp

    async def post(self, url: str, **_kw: Any) -> _FakeResponse:
        self._post_called = True
        if self._post_resp is None:
            raise httpx.ConnectError("post not configured")
        return self._post_resp


# ---------------------------------------------------------------------------
# collect_provider_evidence — pass path
# ---------------------------------------------------------------------------


class TestCollectProviderEvidencePass:
    @pytest.mark.asyncio
    async def test_pass_when_both_endpoints_ok(self) -> None:
        models_resp = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        chat_resp = _FakeResponse(
            200,
            {
                "choices": [{"message": {"content": "pong"}, "finish_reason": "stop"}],
            },
        )
        client = _FakeAsyncClient(models_resp, chat_resp)

        cfg = ProviderProbeConfig(base_url="http://mock:20228", model="4omc")
        entries = await collect_provider_evidence([cfg], _client=client)  # type: ignore[arg-type]

        assert len(entries) == 1
        e = entries[0]
        assert e.status == "pass"
        assert e.models_endpoint_ok is True
        assert e.chat_endpoint_ok is True
        assert e.error is None
        assert e.base_url == "http://mock:20228"
        assert e.model == "4omc"
        assert client._get_called is True
        assert client._post_called is True

    @pytest.mark.asyncio
    async def test_pass_accepts_reasoning_content(self) -> None:
        models_resp = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        chat_resp = _FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {"content": "", "reasoning_content": "thinking"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )
        client = _FakeAsyncClient(models_resp, chat_resp)

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=client)  # type: ignore[arg-type]

        assert entries[0].status == "pass"


# ---------------------------------------------------------------------------
# collect_provider_evidence — blocked path (unreachable)
# ---------------------------------------------------------------------------


class TestCollectProviderEvidenceBlocked:
    @pytest.mark.asyncio
    async def test_blocked_when_connection_refused(self) -> None:
        class _RefusedClient:
            async def get(self, url: str, **_kw: Any) -> Any:
                raise httpx.ConnectError("Connection refused")

            async def post(self, url: str, **_kw: Any) -> Any:  # pragma: no cover
                raise httpx.ConnectError("Connection refused")

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=_RefusedClient())  # type: ignore[arg-type]

        assert len(entries) == 1
        e = entries[0]
        assert e.status == "blocked"
        assert e.models_endpoint_ok is False
        assert e.error is not None
        assert "error" in e.error.lower() or "connection" in e.error.lower()

    @pytest.mark.asyncio
    async def test_blocked_when_invalid_base_url(self) -> None:
        cfg = ProviderProbeConfig(base_url="", model="4omc")
        entries = await collect_provider_evidence([cfg])

        assert len(entries) == 1
        assert entries[0].status == "blocked"
        assert "invalid" in entries[0].error.lower()

    @pytest.mark.asyncio
    async def test_blocked_when_non_http_scheme(self) -> None:
        cfg = ProviderProbeConfig(base_url="ftp://weird:1234")
        entries = await collect_provider_evidence([cfg])

        assert entries[0].status == "blocked"

    @pytest.mark.asyncio
    async def test_chat_not_called_when_models_fails(self) -> None:
        models_resp = _FakeResponse(500)
        client = _FakeAsyncClient(models_resp)

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=client)  # type: ignore[arg-type]

        assert entries[0].status == "blocked"
        assert client._post_called is False


# ---------------------------------------------------------------------------
# collect_provider_evidence — fail path (models OK, chat fails)
# ---------------------------------------------------------------------------


class TestCollectProviderEvidenceFail:
    @pytest.mark.asyncio
    async def test_fail_when_chat_returns_empty_choices(self) -> None:
        models_resp = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        chat_resp = _FakeResponse(200, {"choices": []})
        client = _FakeAsyncClient(models_resp, chat_resp)

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=client)  # type: ignore[arg-type]

        assert entries[0].status == "fail"
        assert entries[0].models_endpoint_ok is True
        assert entries[0].chat_endpoint_ok is False

    @pytest.mark.asyncio
    async def test_fail_when_chat_message_missing_content(self) -> None:
        models_resp = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        chat_resp = _FakeResponse(
            200,
            {
                "choices": [{"message": {"role": "assistant"}}],
            },
        )
        client = _FakeAsyncClient(models_resp, chat_resp)

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=client)  # type: ignore[arg-type]

        assert entries[0].status == "fail"
        assert "content" in (entries[0].error or "").lower()


# ---------------------------------------------------------------------------
# Adversarial: malformed JSON
# ---------------------------------------------------------------------------


class TestCollectProviderEvidenceMalformedJson:
    @pytest.mark.asyncio
    async def test_blocked_on_garbled_models_json(self) -> None:
        fake_req = httpx.Request("GET", "http://mock:20228/v1/models")
        resp = httpx.Response(200, text="{not valid json {{{", request=fake_req)

        class _GarbledClient:
            async def get(self, url: str, **_kw: Any) -> httpx.Response:
                return resp

            async def post(self, url: str, **_kw: Any) -> httpx.Response:  # pragma: no cover
                return httpx.Response(200, json={})

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=_GarbledClient())  # type: ignore[arg-type]

        assert entries[0].status == "blocked"
        assert entries[0].error is not None
        assert "json" in entries[0].error.lower() or "decode" in entries[0].error.lower()


# ---------------------------------------------------------------------------
# Adversarial: misleading success (200 but wrong structure)
# ---------------------------------------------------------------------------


class TestCollectProviderEvidenceMisleadingSuccess:
    @pytest.mark.asyncio
    async def test_blocked_when_models_missing_data_key(self) -> None:
        models_resp = _FakeResponse(200, {"message": "hello"})
        client = _FakeAsyncClient(models_resp)

        cfg = ProviderProbeConfig(base_url="http://mock:20228")
        entries = await collect_provider_evidence([cfg], _client=client)  # type: ignore[arg-type]

        assert entries[0].status == "blocked"
        assert entries[0].models_endpoint_ok is False


# ---------------------------------------------------------------------------
# Multiple configs — sequential probing
# ---------------------------------------------------------------------------


class TestCollectProviderEvidenceMultipleConfigs:
    @pytest.mark.asyncio
    async def test_probes_each_config_sequentially(self) -> None:
        pass_models = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        pass_chat = _FakeResponse(
            200,
            {
                "choices": [{"message": {"content": "pong"}}],
            },
        )

        call_log: list[str] = []

        class _SequentialClient:
            async def get(self, url: str, **_kw: Any) -> _FakeResponse:
                call_log.append(f"GET:{url}")
                return pass_models

            async def post(self, url: str, **_kw: Any) -> _FakeResponse:
                call_log.append(f"POST:{url}")
                return pass_chat

        cfgs = [
            ProviderProbeConfig(base_url="http://a:20228", model="4omc"),
            ProviderProbeConfig(base_url="http://b:20228", model="f.light"),
        ]
        entries = await collect_provider_evidence(cfgs, _client=_SequentialClient())  # type: ignore[arg-type]

        assert len(entries) == 2
        assert entries[0].status == "pass"
        assert entries[1].status == "pass"
        assert entries[0].base_url == "http://a:20228"
        assert entries[1].base_url == "http://b:20228"
        assert len(call_log) == 4  # 2 GET + 2 POST

    @pytest.mark.asyncio
    async def test_mixed_pass_and_blocked(self) -> None:
        pass_models = _FakeResponse(200, {"data": [{"id": "4omc"}]})
        pass_chat = _FakeResponse(
            200,
            {
                "choices": [{"message": {"content": "pong"}}],
            },
        )

        class _MixedClient:
            _call_count = 0

            async def get(self, url: str, **_kw: Any) -> _FakeResponse:
                _MixedClient._call_count += 1
                if "a:" in url:
                    return pass_models
                raise httpx.ConnectError("Connection refused to b")

            async def post(self, url: str, **_kw: Any) -> _FakeResponse:  # pragma: no cover
                return pass_chat

        client = _MixedClient()
        cfgs = [
            ProviderProbeConfig(base_url="http://a:20228"),
            ProviderProbeConfig(base_url="http://b:20228"),
        ]
        entries = await collect_provider_evidence(cfgs, _client=client)  # type: ignore[arg-type]

        assert entries[0].status == "pass"
        assert entries[1].status == "blocked"


# ---------------------------------------------------------------------------
# No paid fallback verification
# ---------------------------------------------------------------------------


class TestNoPaidFallback:
    @pytest.mark.asyncio
    async def test_no_fallback_to_different_provider(self) -> None:
        """When a provider is blocked, no retry to a paid provider occurs.

        collect_provider_evidence probes each config exactly once.
        If it fails, the entry is 'blocked' — no automatic retry or fallback.
        """
        call_count = 0

        class _FailOnceClient:
            async def get(self, url: str, **_kw: Any) -> Any:
                nonlocal call_count
                call_count += 1
                raise httpx.ConnectError("down")

            async def post(self, url: str, **_kw: Any) -> Any:  # pragma: no cover
                raise httpx.ConnectError("down")

        cfg = ProviderProbeConfig(base_url="http://only-one:20228")
        entries = await collect_provider_evidence([cfg], _client=_FailOnceClient())  # type: ignore[arg-type]

        assert entries[0].status == "blocked"
        assert call_count == 1, "Should probe exactly once — no retry or paid fallback"

    @pytest.mark.asyncio
    async def test_each_config_probed_exactly_once(self) -> None:
        call_count = 0

        class _CountingClient:
            async def get(self, url: str, **_kw: Any) -> _FakeResponse:
                nonlocal call_count
                call_count += 1
                return _FakeResponse(200, {"data": []})

            async def post(self, url: str, **_kw: Any) -> _FakeResponse:  # pragma: no cover
                return _FakeResponse(200, {"choices": [{"message": {"content": ""}}]})

        cfgs = [
            ProviderProbeConfig(base_url="http://a:20228"),
            ProviderProbeConfig(base_url="http://b:20228"),
            ProviderProbeConfig(base_url="http://c:20228"),
        ]
        await collect_provider_evidence(cfgs, _client=_CountingClient())  # type: ignore[arg-type]

        assert call_count == 3, "Each config probed exactly once"
