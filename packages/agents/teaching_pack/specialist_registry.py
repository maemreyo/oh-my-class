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

ArtifactSpecialist = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def _recap_specialist(
    lesson_plan: dict[str, Any], research_brief: dict[str, Any],
) -> dict[str, Any]:
    from packages.agents.teaching_pack.specialists.recap_specialist import generate_recap_artifact

    return generate_recap_artifact(lesson_plan, research_brief)


SPECIALIST_REGISTRY: dict[str, ArtifactSpecialist] = {
    "recap": _recap_specialist,
}


def get_specialist(artifact_type: str) -> ArtifactSpecialist | None:
    return SPECIALIST_REGISTRY.get(artifact_type)
