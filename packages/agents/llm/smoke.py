"""9Router live chat smoke harness.

Probes /v1/models and /v1/chat/completions against a configurable target.
Returns a structured SmokeResult — never raises on network errors.

Usage:
    result = await smoke_probe(SmokeConfig())
    if result.status == "pass":
        ...
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Final

import httpx

_LOGGER: Final = logging.getLogger("packages.agents.llm.smoke")

# Minimal chat payload — one system, one user, max_tokens=8 to minimize cost.
_SMOKE_MESSAGES: Final = [
    {"role": "system", "content": "Reply with a single word."},
    {"role": "user", "content": "ping"},
]


@dataclass(frozen=True, slots=True)
class SmokeConfig:
    """Configurable target for the smoke harness."""

    base_url: str = "http://127.0.0.1:20228"
    model: str = "4omc"
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))


@dataclass(frozen=True, slots=True)
class SmokeResult:
    """Outcome of a smoke probe."""

    status: str  # "pass" | "blocked" | "fail"
    models_endpoint_ok: bool
    chat_endpoint_ok: bool
    model_used: str | None
    elapsed_s: float
    error: str | None


async def _probe_models(client: httpx.AsyncClient, base_url: str) -> tuple[bool, str | None]:
    """Hit /v1/models. Return (ok, error_or_none)."""
    url = f"{base_url}/v1/models"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            return False, "models endpoint returned non-list 'data' field"
        return True, None
    except httpx.HTTPError as exc:
        return False, f"models endpoint error: {type(exc).__name__}: {exc}"
    except (json.JSONDecodeError, ValueError) as exc:
        return False, f"models endpoint returned invalid JSON: {exc}"


async def _probe_chat(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
) -> tuple[bool, str | None]:
    """Hit /v1/chat/completions. Return (ok, error_or_none)."""
    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": _SMOKE_MESSAGES,
        "max_tokens": 8,
        "temperature": 0.0,
        "stream": False,
    }
    try:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict):
            return False, "chat endpoint returned non-object JSON"
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            return False, "chat endpoint returned empty or missing 'choices'"
        first_msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(first_msg, dict):
            return False, "chat response missing message object"
        has_content = bool(first_msg.get("content"))
        has_reasoning = bool(first_msg.get("reasoning_content"))
        if not has_content and not has_reasoning:
            return False, "chat response missing content and reasoning_content"
        return True, None
    except httpx.HTTPError as exc:
        return False, f"chat endpoint error: {type(exc).__name__}: {exc}"
    except (json.JSONDecodeError, ValueError) as exc:
        return False, f"chat endpoint returned invalid JSON: {exc}"


async def smoke_probe(
    cfg: SmokeConfig,
    *,
    _client: httpx.AsyncClient | None = None,
) -> SmokeResult:
    """Run a two-step smoke probe against the configured 9Router target.

    Step 1: GET /v1/models — checks connectivity and basic health.
    Step 2: POST /v1/chat/completions — checks actual inference works.

    Accepts optional ``_client`` for deterministic testing (injected mock).
    In production, creates its own ``httpx.AsyncClient`` with the configured timeout.

    Returns SmokeResult with status:
    - "pass"    — both endpoints responded correctly
    - "blocked" — service unreachable or models endpoint failed
    - "fail"    — models OK but chat endpoint failed
    """
    if not cfg.base_url or not cfg.base_url.startswith(("http://", "https://")):
        return SmokeResult(
            status="blocked",
            models_endpoint_ok=False,
            chat_endpoint_ok=False,
            model_used=None,
            elapsed_s=0.0,
            error=f"invalid base_url: {cfg.base_url!r}",
        )

    started = time.monotonic()

    if _client is not None:
        return await _run_probes(_client, cfg, started)

    async with httpx.AsyncClient(timeout=cfg.timeout_s) as client:
        return await _run_probes(client, cfg, started)


async def _run_probes(
    client: httpx.AsyncClient,
    cfg: SmokeConfig,
    started: float,
) -> SmokeResult:
    """Execute both probe steps against a shared client."""
    # Step 1: /v1/models
    models_ok, models_error = await _probe_models(client, cfg.base_url)

    if not models_ok:
        elapsed = time.monotonic() - started
        _LOGGER.warning(
            "smoke.probe.blocked models_endpoint_failed base_url=%s error=%s",
            cfg.base_url,
            models_error,
        )
        return SmokeResult(
            status="blocked",
            models_endpoint_ok=False,
            chat_endpoint_ok=False,
            model_used=None,
            elapsed_s=elapsed,
            error=models_error,
        )

    # Step 2: /v1/chat/completions
    chat_ok, chat_error = await _probe_chat(client, cfg.base_url, cfg.model)
    elapsed = time.monotonic() - started

    if not chat_ok:
        _LOGGER.warning(
            "smoke.probe.fail chat_endpoint_failed base_url=%s model=%s error=%s",
            cfg.base_url,
            cfg.model,
            chat_error,
        )
        return SmokeResult(
            status="fail",
            models_endpoint_ok=True,
            chat_endpoint_ok=False,
            model_used=None,
            elapsed_s=elapsed,
            error=chat_error,
        )

    _LOGGER.info(
        "smoke.probe.pass base_url=%s model=%s elapsed_s=%.2f",
        cfg.base_url,
        cfg.model,
        elapsed,
    )
    return SmokeResult(
        status="pass",
        models_endpoint_ok=True,
        chat_endpoint_ok=True,
        model_used=cfg.model,
        elapsed_s=elapsed,
        error=None,
    )
