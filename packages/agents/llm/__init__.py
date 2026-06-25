"""Shared LLM client for all agents.

Routes through LiteLLM proxy (prod) or 9Router directly (dev).
"""

from __future__ import annotations

import json as _json
import os
from typing import Any

# Model name → 9Router combo mapping (same as LiteLLM config.yaml)
MODEL_COMBO_MAP: dict[str, str] = {
    "f.light": "openai/f.light",
    "f.pro": "openai/f.pro",
    "gpt-5.4": "openai/f.pro",
    "deepseek-v4-flash": "openai/f.light",
    "deepseek-free": "openai/f.light",
    "content-fusion": "openai/f.pro",
    "deepseek-compressed": "openai/f.light",
    "deepseek-direct": "openai/f.light",
}


def get_llm_config() -> dict[str, Any]:
    """Get LLM configuration from environment.

    Priority:
    1. LITELLM_API_BASE set → route through LiteLLM proxy
    2. Otherwise → route directly to 9Router
    """
    proxy_url = os.environ.get("LITELLM_API_BASE", "")
    nine_router_key = os.environ.get("NINEROUTER_API_KEY", "")

    if proxy_url:
        # Route through LiteLLM proxy (prod/staging)
        return {
            "api_base": proxy_url,
            "api_key": os.environ.get("LITELLM_MASTER_KEY", ""),
        }
    else:
        # Route directly to 9Router (dev)
        return {
            "api_base": "http://localhost:20128/v1",
            "api_key": nine_router_key,
        }


def resolve_model(combo_name: str) -> str:
    """Resolve a 9Router combo name to an litellm-compatible model string.

    Examples:
        "f.light" → "openai/f.light"
        "deepseek-v4-flash" → "openai/f.light"
        "gpt-5.4" → "openai/f.pro"
    """
    return MODEL_COMBO_MAP.get(combo_name, f"openai/{combo_name}")


def extract_json_text(content: Any, reasoning_content: Any = None) -> str:
    """Extract JSON string from LLM response content.

    Handles: str, dict, list, None — normalizes to a JSON-parseable string.
    Falls back to reasoning_content when content is empty (reasoning models).
    """
    if isinstance(content, (dict, list)):
        return _json.dumps(content)
    text = str(content).strip() if content else ""
    if not text and reasoning_content:
        if isinstance(reasoning_content, list):
            parts = [
                p.get("text", str(p)) if isinstance(p, dict) else str(p)
                for p in reasoning_content
            ]
            text = "".join(parts).strip()
        else:
            text = str(reasoning_content).strip()
    if not text:
        raise ValueError("LLM returned empty content")
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text
