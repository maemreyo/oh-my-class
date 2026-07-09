"""Real LLM call for ContentMaterializer wording (SDE-01).

Schema-bound request/response contract for the one wording call ContentMaterializer
makes per deck (vocabulary, example, practice, and exit slide text). Mirrors the
calling convention `hierarchical.py::_generate_section_prose` (LIC-02) uses for
content_creator's other artifact types: same `AgentRuntime`/`llm_client` import
path, same `complete_json_with_retries` + `extract_json_text` parse pattern.

On any failure (timeout, connection error, invalid JSON, schema violation),
`generate_slide_deck_wording` returns None instead of raising. The caller
(`content_materialization.py`) then falls back to the engine's existing
deterministic per-topic wording — real curated classroom content, not a
placeholder — so a slide deck is always produced.
"""

from __future__ import annotations

import json
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

_SYSTEM_PROMPT: Final = (
    "You are an expert K-12 teaching content writer authoring wording for a "
    "6-slide classroom slide deck. Write concise, age-appropriate, classroom-ready "
    "text for each field below, grounded ONLY in the given topic and learning goal "
    "— do not invent facts, names, or numbers not implied by the topic.\n\n"
    "The deck's title slide also carries an illustrative image; write "
    '"image_alt_text" as a genuinely descriptive WCAG-style alt text for that '
    "image (what it depicts, in the context of the topic) — not a generic label "
    'like "image" or "illustration".\n\n'
    'Respond ONLY with a JSON object with these exact keys: "vocabulary_body", '
    '"vocabulary_practice_body", "example_body", "sentence_stem", "check_prompt", '
    '"practice_correct_option", "practice_distractor_a", "practice_distractor_b", '
    '"teacher_rationale", "exit_prompt", "image_alt_text". No prose, no explanation, '
    "no markdown fences."
)


class SlideDeckWordingResponse(BaseModel):
    """Schema-bound LLM response contract for ContentMaterializer's wording fields.

    Every field defaults to "" ("not provided"). The caller treats an empty field
    as missing and substitutes the deterministic per-topic wording for that field
    alone, so a partial response still degrades gracefully.
    """

    model_config = ConfigDict(extra="ignore")

    vocabulary_body: str = ""
    vocabulary_practice_body: str = ""
    example_body: str = ""
    sentence_stem: str = ""
    check_prompt: str = ""
    practice_correct_option: str = ""
    practice_distractor_a: str = ""
    practice_distractor_b: str = ""
    teacher_rationale: str = ""
    exit_prompt: str = ""
    image_alt_text: str = ""


async def generate_slide_deck_wording(
    *,
    run_id: str,
    topic: str,
    grade_level: str,
    locale: str,
    learning_goal: str,
) -> SlideDeckWordingResponse | None:
    """Call llm_client for real slide wording; None on timeout/invalid schema."""
    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    user_prompt = (
        f"Topic: {topic}\nGrade level: {grade_level}\nLocale: {locale}\n"
        f"Learning goal: {learning_goal}"
    )
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="slide_deck_engine",
        run_id=run_id,
        step=stage_number(StageEnum.ARTIFACT_WORKFLOW),
        step_label=StageEnum.ARTIFACT_WORKFLOW.value,
        model=MODELS.content_creator,
        base_temperature=0.4,
        retry_temperature=0.2,
    ))
    messages = runtime.messages(_SYSTEM_PROMPT, user_prompt)

    def parse(content: str) -> SlideDeckWordingResponse:
        data = json.loads(extract_json_text(content))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object of slide deck wording fields")
        return SlideDeckWordingResponse.model_validate(data)

    try:
        return await runtime.complete_json_with_retries(
            messages=messages,
            parse=parse,
            retry_messages=lambda _err, _content: runtime.messages(
                _SYSTEM_PROMPT,
                "Invalid response. Return ONLY the JSON object with the exact keys requested.",
            ),
            extra_tags=("phase:content_materialization",),
        )
    except Exception:  # noqa: BLE001 - any LLM failure falls back to deterministic wording, never a silent placeholder
        return None


_TRANSLATION_SYSTEM_PROMPT_TEMPLATE: Final = (
    "You are a professional {source_language}-to-{target_language} translator for "
    "K-12 classroom slide deck content. Translate each value in the given JSON object "
    "1:1 into {target_language}, preserving meaning, tone, and classroom register. Do "
    "not add, remove, merge, or reorder entries — return exactly the same set of keys. "
    'Leave placeholder blanks (e.g. "___") and numbers as-is.\n\n'
    'Respond ONLY with a JSON object of the exact shape {{"translations": '
    '{{"<same key>": "<translated value>", ...}}}}. No prose, no explanation, no '
    "markdown fences."
)


class SlideDeckTranslationResponse(BaseModel):
    """Schema-bound LLM response contract for SDX-01's deck-wide translation pass.

    ``translations`` maps each input text's stable key (see
    ``packages.agents.slide_deck_engine.translation._collect_translatable_texts``)
    to its translated string. A missing or blank value for a key is treated by the
    caller as "not translated" and falls back to that field's original text alone —
    the same per-field graceful degradation `SlideDeckWordingResponse` uses, just
    keyed dynamically since a deck's translatable strings aren't a fixed field set.
    """

    model_config = ConfigDict(extra="ignore")

    translations: dict[str, str] = Field(default_factory=dict)


async def translate_slide_deck_wording(
    *,
    run_id: str,
    texts: dict[str, str],
    source_language: str,
    target_language: str,
) -> dict[str, str] | None:
    """Call llm_client to translate a deck's text 1:1; None on timeout/invalid schema.

    Mirrors ``generate_slide_deck_wording``'s exact calling convention (same
    ``AgentRuntime``/``llm_client`` import path, same `complete_json_with_retries` +
    `extract_json_text` parse pattern) — SDX-01 reuses SDE-01's real-LLM plumbing
    rather than inventing a parallel one. One call translates the whole deck's text
    at once, matching SDE-01's "one wording call per deck" cost shape.
    """
    from packages.agents.config.models import MODELS
    from packages.agents.llm import extract_json_text
    from packages.agents.runtime import AgentRuntime, AgentRuntimeConfig
    from packages.agents.teaching_pack.stages import StageEnum, stage_number

    if not texts:
        return {}

    system_prompt = _TRANSLATION_SYSTEM_PROMPT_TEMPLATE.format(
        source_language=source_language,
        target_language=target_language,
    )
    user_prompt = json.dumps(texts, ensure_ascii=False)
    runtime = AgentRuntime(AgentRuntimeConfig(
        agent="slide_deck_engine",
        run_id=run_id,
        step=stage_number(StageEnum.ARTIFACT_WORKFLOW),
        step_label=StageEnum.ARTIFACT_WORKFLOW.value,
        model=MODELS.content_creator,
        base_temperature=0.2,
        retry_temperature=0.0,
    ))
    messages = runtime.messages(system_prompt, user_prompt)

    def parse(content: str) -> dict[str, str]:
        data = json.loads(extract_json_text(content))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object with a translations map")
        return SlideDeckTranslationResponse.model_validate(data).translations

    try:
        return await runtime.complete_json_with_retries(
            messages=messages,
            parse=parse,
            retry_messages=lambda _err, _content: runtime.messages(
                system_prompt,
                "Invalid response. Return ONLY the JSON object with the exact translations shape requested.",
            ),
            extra_tags=("phase:content_materialization", "slide_deck_translation"),
        )
    except Exception:  # noqa: BLE001 - any LLM failure falls back per-block to original text, never a placeholder
        return None
