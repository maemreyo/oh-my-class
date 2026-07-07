from __future__ import annotations

import re

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, SlideDeckEngineRequest

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
    return AssembledSlideDeckInput(
        run_id=request.run_id,
        topic=topic,
        grade_level=grade_level,
        locale=locale,
        theme=theme,
        source=source,
    )


def _clean_topic(topic: str) -> str:
    cleaned = _REQUEST_PREFIX_RE.sub("", topic.strip())
    request_match = _DECK_REQUEST_RE.search(cleaned)
    if request_match is not None:
        cleaned = cleaned[request_match.end():]
    cleaned = _TRAILING_INSTRUCTION_RE.sub("", cleaned)
    first_sentence = cleaned.split(".", maxsplit=1)[0].strip()
    return first_sentence or "Teaching Deck"
