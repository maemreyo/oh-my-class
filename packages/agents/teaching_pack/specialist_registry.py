"""Registry-driven specialist dispatch (ADR-053).

An artifact type with a registered specialist here bypasses the universal
`content_creator_node` generic-LLM-prompt loop entirely -- `generate_one_artifact`
checks this registry first. Artifact types with no entry keep using the
existing generic path unchanged; adding a specialist is additive, never a
prerequisite for an artifact type to keep working.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from common.contracts.grade_band import FlashcardGradeBand

# #464: ADR-053 names the (lesson_plan, research_brief) argument pair every
# registered specialist takes "SpecialistRequest" -- kept as two positional
# dicts (not wrapped in one object) since that's the real signature every
# specialist below and its tests already implement; wrapping it would be a
# parallel type with no behavior of its own.
ArtifactSpecialist = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def _recap_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.recap_specialist import generate_recap_artifact

    return generate_recap_artifact(lesson_plan, research_brief)


def _flashcard_deck_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.flashcard_deck_specialist import (
        generate_flashcard_deck_artifact,
    )

    subject = str(lesson_plan.get("subject") or "General")
    grade_level = str(lesson_plan.get("grade_level") or lesson_plan.get("grade") or "").strip()
    return generate_flashcard_deck_artifact(
        lesson_plan, research_brief, subject=subject, grade_band=_grade_band(grade_level),
    )


def _lesson_design_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.lesson_design_specialist import (
        generate_lesson_design_artifact,
    )

    return generate_lesson_design_artifact(lesson_plan, research_brief)


def _worksheet_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.worksheet_specialist import generate_worksheet_artifact

    return generate_worksheet_artifact(lesson_plan, research_brief)


def _quiz_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.quiz_specialist import generate_quiz_artifact

    return generate_quiz_artifact(lesson_plan, research_brief)


def _drill_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.drill_specialist import generate_drill_artifact

    return generate_drill_artifact(lesson_plan, research_brief)


def _roadmap_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.roadmap_specialist import generate_roadmap_artifact

    return generate_roadmap_artifact(lesson_plan, research_brief)


def _reading_passage_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.reading_passage_specialist import (
        generate_reading_passage_artifact,
    )

    return generate_reading_passage_artifact(lesson_plan, research_brief)


def _infographic_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.infographic_specialist import generate_infographic_artifact

    return generate_infographic_artifact(lesson_plan, research_brief)


def _exit_ticket_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.exit_ticket_specialist import generate_exit_ticket_artifact

    return generate_exit_ticket_artifact(lesson_plan, research_brief)


def _grade_band(grade_level: str) -> FlashcardGradeBand | None:
    from common.contracts.grade_band import (
        flashcard_grade_band,
        grade_band_for_label,
    )

    grade_band = grade_band_for_label(grade_level)
    return flashcard_grade_band(grade_band) if grade_band is not None else None


SPECIALIST_REGISTRY: dict[str, ArtifactSpecialist] = {
    "lesson": _lesson_design_specialist,
    "worksheet": _worksheet_specialist,
    "quiz": _quiz_specialist,
    "drill": _drill_specialist,
    "roadmap": _roadmap_specialist,
    "reading_passage": _reading_passage_specialist,
    "infographic": _infographic_specialist,
    "exit_ticket": _exit_ticket_specialist,
    "recap": _recap_specialist,
    "flashcard_deck": _flashcard_deck_specialist,
}


def get_specialist(artifact_type: str) -> ArtifactSpecialist | None:
    return SPECIALIST_REGISTRY.get(artifact_type)
