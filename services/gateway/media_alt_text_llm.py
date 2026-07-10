"""Best-guess alt-text generation for teacher-uploaded images (SDX-04).

Finding: no vision/image-understanding capability exists anywhere in this
codebase's LLM setup. `packages/agents/llm/chat.py::_chat_message` coerces
any non-string `content` to `str(content)` before it reaches
`packages.llm_client.client.ChatMessage` (whose `content` field is `str`
only) — an image content block would be flattened to its Python repr, not
understood. There is no other image-understanding integration anywhere in
the repo (`vision`/`image_url`/`multimodal` greps outside this docstring turn
up nothing relevant).

So this function cannot produce a true visual description. Per the SDX-04
issue's own fallback guidance, it degrades to a *best-guess* description
built from the filename, the teacher's tags, and optional slide/caption
context — text-only signal, not image understanding. The teacher always
sees the before/after confirmation modal (SDX-04 editor action) before this
text is ever saved, so a wrong guess is always caught before publish.
"""

from __future__ import annotations

import json
import re
from typing import Final

from pydantic import BaseModel, ConfigDict

_SYSTEM_PROMPT: Final = (
    "You help teachers write WCAG-style alt text for images in classroom slide "
    "decks. You cannot see the image — you only have its filename, tags, and "
    "optional slide context. Write your best-guess, genuinely descriptive alt "
    "text implied by those signals. Do not write a generic label like "
    '"image" or "illustration" alone.\n\n'
    'Respond ONLY with a JSON object: {"alt_text": "<your best-guess description>"}. '
    "No prose, no explanation, no markdown fences."
)

_FILENAME_WORD_PATTERN: Final = re.compile(r"[a-zA-Z]+")


class _AltTextResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    alt_text: str = ""


def _filename_hint(filename: str) -> str:
    """Turns "frog-lifecycle_diagram.png" into "frog lifecycle diagram"."""
    words = _FILENAME_WORD_PATTERN.findall(filename)
    return " ".join(words) if words else filename


async def generate_alt_text_for_image(
    *,
    run_id: str,
    filename: str,
    tags: list[str],
    context: str | None = None,
) -> str | None:
    """Best-guess alt text from filename/tags/context; None on any LLM failure.

    Caller (the `/media-assets/{id}/generate-alt-text` route) shows the
    result to the teacher in a before/after confirmation modal — never
    auto-saved — so a None here just means "no candidate to show."
    """
    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    user_prompt = (
        f"Filename hint: {_filename_hint(filename)}\n"
        f"Tags: {', '.join(tags) if tags else '(none)'}\n"
        f"Slide context: {context or '(none)'}"
    )
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="media_asset_library",
        run_id=run_id,
        step=stage_number(StageEnum.ARTIFACT_WORKFLOW),
        step_label=StageEnum.ARTIFACT_WORKFLOW.value,
        model=MODELS.content_creator,
        base_temperature=0.4,
        retry_temperature=0.2,
    ))
    messages = runtime.messages(_SYSTEM_PROMPT, user_prompt)

    def parse(content: str) -> str:
        data = json.loads(extract_json_text(content))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object with an alt_text key")
        alt_text = _AltTextResponse.model_validate(data).alt_text.strip()
        if not alt_text:
            raise ValueError("empty alt_text")
        return alt_text[:500]  # schema constraint: SlideDeckMedia.alt_text max_length=500

    try:
        return await runtime.complete_json_with_retries(
            messages=messages,
            parse=parse,
            retry_messages=lambda _err, _content: runtime.messages(
                _SYSTEM_PROMPT,
                "Invalid response. Return ONLY the JSON object with the exact "
                "alt_text key requested.",
            ),
            extra_tags=("phase:media_asset_alt_text",),
        )
    except Exception:  # noqa: BLE001 - any LLM failure means "no candidate", never a placeholder
        return None
