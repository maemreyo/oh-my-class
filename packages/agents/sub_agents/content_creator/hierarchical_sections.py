from __future__ import annotations

from typing import Any


def flashcards(lesson_plan: dict[str, Any], fact: str) -> list[dict[str, str]]:
    objectives = _objective_texts(lesson_plan) or [fact]
    doubled_objectives = [*objectives, *objectives]
    return [
        {
            "id": f"card-{index}",
            "front": objective,
            "back": f"Key idea: {fact}",
            "hint": "Connect this card to the lesson objective.",
        }
        for index, objective in enumerate(doubled_objectives, start=1)
    ][:8]


def regen_placeholder(section_id: str, title: str) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "title": title,
        "content": "This section needs scoped regeneration before teacher approval.",
        "needs_regen": True,
        "metadata": {"filled_independently": True, "failure_mode": "persistent_section_failure"},
    }


def _objective_texts(lesson_plan: dict[str, Any]) -> list[str]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    return [str(item.get("description")) for item in objectives if isinstance(item, dict) and item.get("description")]
