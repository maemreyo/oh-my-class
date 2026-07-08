"""Custom promptfoo provider — calls the real, governed LLMClient.

9Router responds to /v1/chat/completions with Content-Type: text/event-stream
and an SSE-style `data: [DONE]` trailer even for non-streaming requests. The
`openai` Python SDK tolerates this; promptfoo's built-in openai-compatible
Node.js provider does not (strict JSON.parse on the full body fails on the
trailing SSE content). Rather than depend on a third-party HTTP client that
mishandles 9Router's response shape, this provider routes through the same
LLMClient every other real LLM call in this repo uses — proven to work
against 9Router in this exact scenario (see the real-LLM-integration design
interview, 2026-07-08).

Promptfoo Python provider protocol: a module-level `call_api(prompt, options,
context)` returning {"output": str} (or {"error": str} on failure).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
    del options, context  # required by promptfoo's provider protocol, unused here
    return asyncio.run(_call_api_async(prompt))


async def _call_api_async(prompt: str) -> dict[str, str]:
    from packages.llm_client.client import ChatMessage, LLMClient

    client = LLMClient()
    try:
        response = await client.chat(
            "4omc",
            [ChatMessage(role="user", content=prompt)],
            agent="promptfoo_security_suite",
            task="content_generation",
            # Red-team assertions (not-contains AND llm-rubric) need the most
            # reproducible output this model can give — temperature=0 reduces
            # (does not eliminate — some providers are non-deterministic even
            # at temp=0) run-to-run variance in what gets checked.
            temperature=0.0,
        )
    except Exception as exc:  # noqa: BLE001 — promptfoo needs a string error, not a raised exception
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"output": response.content}
