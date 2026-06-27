"""Provider evidence — live 9Router provider status for release evidence.

Probes the 9Router sidecar's /v1/models and /v1/chat/completions endpoints
to record real provider health.  Returns structured evidence — never raises
on network errors.  If the provider is unreachable the status is "blocked",
never faked as "pass".

Usage:
    entries = await collect_provider_evidence([ProviderProbeConfig()])
    for entry in entries:
        print(entry.status)  # "pass" | "blocked" | "fail"
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Final

import httpx

_LOGGER: Final = logging.getLogger("services.gateway.provider_evidence")

# Minimal chat payload — one user message, max_tokens=8 to minimize cost.
_PROVIDER_CHAT_MESSAGES: Final = [
    {"role": "user", "content": "ping"},
]


@dataclass(frozen=True, slots=True)
class ProviderProbeConfig:
    """Config for a single 9Router provider probe."""

    base_url: str = "http://127.0.0.1:20228"
    model: str = "4omc"
    timeout_s: float = 10.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))


@dataclass(frozen=True, slots=True)
class ProviderEvidenceEntry:
    """Structured evidence of a single 9Router provider probe.

    Recorded into release evidence for production-readiness auditing.
    """

    base_url: str
    model: str
    timestamp: str  # ISO 8601
    status: str  # "pass" | "blocked" | "fail"
    elapsed_s: float
    models_endpoint_ok: bool
    chat_endpoint_ok: bool
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProviderEvidenceEntry:
        """Deserialise from a plain dict (JSON round-trip)."""
        return cls(
            base_url=data["base_url"],
            model=data["model"],
            timestamp=data["timestamp"],
            status=data["status"],
            elapsed_s=data["elapsed_s"],
            models_endpoint_ok=data["models_endpoint_ok"],
            chat_endpoint_ok=data["chat_endpoint_ok"],
            error=data.get("error"),
        )


# ── Internal probe helpers ──────────────────────────────────────────


async def _probe_models_endpoint(
    client: httpx.AsyncClient,
    base_url: str,
) -> tuple[bool, str | None]:
    """GET /v1/models — return (ok, error_or_none)."""
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


async def _probe_chat_endpoint(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
) -> tuple[bool, str | None]:
    """POST /v1/chat/completions — return (ok, error_or_none)."""
    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": _PROVIDER_CHAT_MESSAGES,
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


async def _probe_single_provider(
    client: httpx.AsyncClient,
    cfg: ProviderProbeConfig,
    started: float,
) -> ProviderEvidenceEntry:
    """Run both probes against a single provider and return evidence."""
    now_iso = datetime.now(UTC).isoformat()

    models_ok, models_error = await _probe_models_endpoint(client, cfg.base_url)

    if not models_ok:
        elapsed = time.monotonic() - started
        _LOGGER.warning(
            "provider_evidence.blocked models_endpoint_failed base_url=%s error=%s",
            cfg.base_url,
            models_error,
        )
        return ProviderEvidenceEntry(
            base_url=cfg.base_url,
            model=cfg.model,
            timestamp=now_iso,
            status="blocked",
            elapsed_s=elapsed,
            models_endpoint_ok=False,
            chat_endpoint_ok=False,
            error=models_error,
        )

    chat_ok, chat_error = await _probe_chat_endpoint(client, cfg.base_url, cfg.model)
    elapsed = time.monotonic() - started

    if not chat_ok:
        _LOGGER.warning(
            "provider_evidence.fail chat_endpoint_failed base_url=%s model=%s error=%s",
            cfg.base_url,
            cfg.model,
            chat_error,
        )
        return ProviderEvidenceEntry(
            base_url=cfg.base_url,
            model=cfg.model,
            timestamp=now_iso,
            status="fail",
            elapsed_s=elapsed,
            models_endpoint_ok=True,
            chat_endpoint_ok=False,
            error=chat_error,
        )

    _LOGGER.info(
        "provider_evidence.pass base_url=%s model=%s elapsed_s=%.2f",
        cfg.base_url,
        cfg.model,
        elapsed,
    )
    return ProviderEvidenceEntry(
        base_url=cfg.base_url,
        model=cfg.model,
        timestamp=now_iso,
        status="pass",
        elapsed_s=elapsed,
        models_endpoint_ok=True,
        chat_endpoint_ok=True,
        error=None,
    )


# ── Public API ──────────────────────────────────────────────────────


async def collect_provider_evidence(
    configs: list[ProviderProbeConfig],
    *,
    _client: httpx.AsyncClient | None = None,
) -> list[ProviderEvidenceEntry]:
    """Probe one or more 9Router providers and return structured evidence.

    Each config produces one ``ProviderEvidenceEntry``.  Probes are executed
    sequentially (not in parallel) to avoid thundering-herd on a single
    sidecar instance.

    Accepts optional ``_client`` for deterministic testing.  In production,
    creates its own ``httpx.AsyncClient`` per probe.

    If a provider is unreachable the entry status is "blocked" — never
    "pass".  No paid fallbacks are attempted.
    """
    entries: list[ProviderEvidenceEntry] = []

    for cfg in configs:
        started = time.monotonic()

        if not cfg.base_url or not cfg.base_url.startswith(("http://", "https://")):
            entries.append(
                ProviderEvidenceEntry(
                    base_url=cfg.base_url,
                    model=cfg.model,
                    timestamp=datetime.now(UTC).isoformat(),
                    status="blocked",
                    elapsed_s=0.0,
                    models_endpoint_ok=False,
                    chat_endpoint_ok=False,
                    error=f"invalid base_url: {cfg.base_url!r}",
                )
            )
            continue

        if _client is not None:
            entry = await _probe_single_provider(_client, cfg, started)
        else:
            async with httpx.AsyncClient(timeout=cfg.timeout_s) as client:
                entry = await _probe_single_provider(client, cfg, started)

        entries.append(entry)

    return entries
