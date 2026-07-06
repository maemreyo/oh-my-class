from __future__ import annotations

from packages.agents.slide_deck_engine.models import AssembledSlideDeckInput, SlideDeckEngineRequest


def assemble_input(request: SlideDeckEngineRequest) -> AssembledSlideDeckInput:
    topic = str(request.lesson_blueprint.get("topic", "Teaching Deck"))
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
