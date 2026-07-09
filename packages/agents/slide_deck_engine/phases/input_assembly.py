from __future__ import annotations

import re

from common.contracts.run_contract import JsonObject

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.structure_presets import SLIDE_DECK_STRUCTURE_PRESETS

_REQUEST_PREFIX_RE = re.compile(r"^[A-Z0-9_\-]+(?:\s+[0-9a-fA-F-]{32,36})?:\s*")
_DECK_REQUEST_RE = re.compile(
    r"\b(?:generate|create|make|build)\s+(?:a\s+)?(?:slide\s+deck|slidedeck|presentation\s+deck)\s+for\s+",
    re.IGNORECASE,
)
_TRAILING_INSTRUCTION_RE = re.compile(
    r"\s+(?:include|with|and include|please include)\b.*$",
    re.IGNORECASE,
)


def assemble_input(request: SlideDeckEngineRequest) -> AssembledSlideDeckInput:
    topic = _clean_topic(str(request.lesson_blueprint.get("topic", "Teaching Deck")))
    grade_level = str(request.lesson_blueprint.get("grade_level", "Grade 5"))
    locale = str(request.teacher_constraints.get("locale", "en-US"))
    theme = str(request.teacher_constraints.get("theme", "default"))
    sources = request.research_brief.get("sources")
    source = sources[0] if isinstance(sources, list) and sources else {}
    if not isinstance(source, dict):
        source = {}
    effective_constraints, pedagogical_emphasis = _resolve_structure_preset(
        request.structure_preset, request.teacher_constraints,
    )
    return AssembledSlideDeckInput(
        run_id=request.run_id,
        topic=topic,
        grade_level=grade_level,
        locale=locale,
        theme=theme,
        source=source,
        pedagogical_emphasis=pedagogical_emphasis,
        effective_teacher_constraints=effective_constraints,
    )


def _resolve_structure_preset(
    structure_preset: str | None, teacher_constraints: JsonObject,
) -> tuple[JsonObject, str]:
    """Merge a named preset's config under explicit teacher_constraints.

    Explicit teacher_constraints always win over the preset default, so a
    preset only fills in gaps. No preset (or an unrecognized key) resolves
    to today's exact behavior: raw teacher_constraints, no emphasis.
    """
    preset = SLIDE_DECK_STRUCTURE_PRESETS.get(structure_preset or "", {})
    merged = {**preset, **teacher_constraints}
    pedagogical_emphasis = str(merged.pop("pedagogical_emphasis", ""))
    return merged, pedagogical_emphasis


def _clean_topic(topic: str) -> str:
    cleaned = _REQUEST_PREFIX_RE.sub("", topic.strip())
    request_match = _DECK_REQUEST_RE.search(cleaned)
    if request_match is not None:
        cleaned = cleaned[request_match.end():]
    cleaned = _TRAILING_INSTRUCTION_RE.sub("", cleaned)
    first_sentence = cleaned.split(".", maxsplit=1)[0].strip()
    return first_sentence or "Teaching Deck"
