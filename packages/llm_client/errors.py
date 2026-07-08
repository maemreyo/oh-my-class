"""Typed LLM provider error hierarchy.

TransientProviderError  → retryable (free-tier, 429, all-providers-down, timeout)
PermanentProviderError  → non-retryable (bad prompt, schema validation, budget ceiling)
"""
from __future__ import annotations

from openai import OpenAIError as OpenAIError  # re-exported for callers outside llm_client


class LLMProviderError(Exception):
    """Base for all LLM transport errors."""


class TransientProviderError(LLMProviderError):
    """Retryable: free-tier-exhausted, 429, all-providers-down, timeout."""

    def __init__(self, message: str, retry_after_seconds: int = 60) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


class FreeTierExhaustedError(TransientProviderError):
    """9Router free-tier quota reached."""


class ProviderRateLimitError(TransientProviderError):
    """HTTP 429 from a provider."""


class ProviderTimeoutError(TransientProviderError):
    """Request timed out."""


class AllProvidersDownError(TransientProviderError):
    """All configured providers are unavailable."""


class PermanentProviderError(LLMProviderError):
    """Non-retryable: bad prompt, schema validation failure, hard budget ceiling."""


class BadPromptError(PermanentProviderError):
    """The prompt was rejected by the provider (HTTP 400)."""


def classify_openai_error(exc: Exception) -> LLMProviderError:
    """Map openai/httpx exceptions to typed provider errors.

    Import openai lazily so the module is usable without openai installed
    (e.g. in tests that patch at the boundary).
    """
    try:
        import openai
    except ImportError:
        return PermanentProviderError(str(exc))

    # Timeout
    if isinstance(exc, openai.APITimeoutError):
        return ProviderTimeoutError(str(exc), retry_after_seconds=30)

    # Rate-limit / quota
    if isinstance(exc, openai.RateLimitError):
        body = getattr(exc, "body", None) or {}
        message = str(body.get("message", "")) if isinstance(body, dict) else str(exc)
        if "free_tier_exhausted" in message or "free tier" in message.lower():
            return FreeTierExhaustedError(str(exc), retry_after_seconds=300)
        return ProviderRateLimitError(str(exc), retry_after_seconds=60)

    # HTTP 400 → bad prompt / schema error → permanent
    if isinstance(exc, openai.BadRequestError):
        return BadPromptError(str(exc))

    # Connection / service unavailable
    if isinstance(exc, (openai.APIConnectionError, openai.InternalServerError)):
        return AllProvidersDownError(str(exc), retry_after_seconds=120)

    # Catch-all: treat unknown API errors as transient to avoid data loss
    if isinstance(exc, openai.APIError):
        return TransientProviderError(str(exc), retry_after_seconds=60)

    return PermanentProviderError(str(exc))
