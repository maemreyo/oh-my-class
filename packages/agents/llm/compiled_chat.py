"""Bridge between PromptCompiler and complete_json_chat.

Provides :func:`compiled_json_chat` which accepts a :class:`CompiledPrompt`
and attaches prompt-provenance metadata as tags before delegating to the
existing :func:`complete_json_chat` transport.

Currently used by:
- **planner** agent (``packages/agents/sub_agents/planner/nodes.py``)
- **content_creator** agent (``packages/agents/sub_agents/content_creator/nodes.py``)

NOT used by:
- **judge** (``packages/quality/layer4_judge/judge_interface.py``) — blocked
  by import boundary (quality cannot import from agents); uses litellm
  transport directly with its own tag mechanism.
- **researcher**, **diagnostician**, **roadmap_agent** — not yet migrated.

Tag contract (sent to 9Router / LiteLLM)::

    prompt_id:planner_v1
    prompt_version:1.0.0
    content_hash:<sha256-prefix-16>
    compiled_hash:<sha256-prefix-16>

These tags are appended to whatever base tags the caller supplies (e.g.
``agent:planner``, ``run:abc``, ``step:3``).  Duplicate tag keys are
resolved by last-writer-wins — provenance tags overwrite any base tag
with the same prefix.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.llm.chat import complete_json_chat

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletionMessageParam

    from packages.agents.prompts.compiler import CompiledPrompt

# Length of the hash prefix included in tags for traceability without bloat.
_HASH_PREFIX_LEN: int = 16


def _provenance_tags(compiled: CompiledPrompt) -> list[str]:
    """Extract provenance tags from a CompiledPrompt's metadata."""
    meta = compiled.metadata
    tags = [
        f"prompt_id:{meta.prompt_id}",
        f"prompt_version:{meta.prompt_version}",
        f"content_hash:{meta.content_hash[:_HASH_PREFIX_LEN]}",
        f"compiled_hash:{meta.compiled_hash[:_HASH_PREFIX_LEN]}",
    ]
    if meta.overlay_ids:
        tags.append(f"overlay_ids:{','.join(meta.overlay_ids)}")
    if meta.structured_output_strategy is not None:
        tags.append(f"json_strategy:{meta.structured_output_strategy}")
    return tags


def _merge_tags(base: list[str], provenance: list[str]) -> list[str]:
    """Merge base tags with provenance tags, provenance wins on key collision.

    Tag format is ``key:value``.  Collision is on the key portion (before
    the first ``:``).
    """
    base_keys: dict[str, str] = {}
    for tag in base:
        key = tag.split(":", 1)[0] if ":" in tag else tag
        base_keys[key] = tag

    provenance_keys: dict[str, str] = {}
    for tag in provenance:
        key = tag.split(":", 1)[0] if ":" in tag else tag
        provenance_keys[key] = tag

    merged: dict[str, str] = {**base_keys, **provenance_keys}
    return list(merged.values())


async def compiled_json_chat(
    *,
    model: str,
    compiled: CompiledPrompt,
    messages: list[ChatCompletionMessageParam],
    temperature: float,
    tags: list[str],
    max_tokens: int | None = None,
) -> str:
    """Send a compiled prompt through the LLM transport with provenance tags.

    This is the preferred entry point for judge, planner, and content-creator
    agent LLM paths.  It attaches compiler-derived metadata as tags so that
    every downstream consumer (9Router, LiteLLM, Langfuse, cost attribution)
    receives full prompt provenance.

    Args:
        model: The LLM model identifier (e.g. ``"openai/deepseek-v4-flash"``).
        compiled: The compiled prompt with metadata.
        messages: Chat messages (system + user).
        temperature: Sampling temperature.
        tags: Base tags (must include ``agent:``, ``run:``, ``step:``, ``task:``).
        max_tokens: Optional max tokens override.

    Returns:
        The LLM response content string.
    """
    enriched_tags = _merge_tags(tags, _provenance_tags(compiled))
    return await complete_json_chat(
        model=model,
        messages=messages,
        temperature=temperature,
        tags=enriched_tags,
        max_tokens=max_tokens,
    )
