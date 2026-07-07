from __future__ import annotations

import json
from typing import Any

from common.contracts.artifact import ArtifactContent
from common.contracts.methodology_registry import MethodologyTag, methodology_entry_by_tag
from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState


def methodology_components(lesson_plan: dict[str, Any], state: ContentCreatorNodeState) -> list[dict[str, str]]:
    if state.get("disable_methodology_components") is True:
        return []
    components: list[dict[str, str]] = []
    for tag in _methodology_tags(lesson_plan):
        for component in methodology_entry_by_tag(tag).required_components:
            components.append({"type": "paragraph", "text": f"methodology component: {component}"})
    return components


def validate_methodology(artifact: ArtifactContent, lesson_plan: dict[str, Any]) -> None:
    content = json.dumps(artifact.model_dump(), ensure_ascii=False).casefold()
    for tag in _methodology_tags(lesson_plan):
        entry = methodology_entry_by_tag(tag)
        missing = [component for component in entry.required_components if component.casefold() not in content]
        if missing:
            msg = "methodology component missing: " + missing[0]
            raise ValueError(msg)


def _methodology_tags(lesson_plan: dict[str, Any]) -> list[MethodologyTag]:
    methodology = lesson_plan.get("methodology")
    if not isinstance(methodology, dict):
        return []
    tags = methodology.get("tags")
    if not isinstance(tags, list):
        return []
    return [_methodology_tag(str(tag)) for tag in tags]


def _methodology_tag(value: str) -> MethodologyTag:
    match value:
        case "concept_map":
            return "concept_map"
        case "contrastive_pairs":
            return "contrastive_pairs"
        case "film_based":
            return "film_based"
        case "shy_student_1on1":
            return "shy_student_1on1"
        case "active_recall":
            return "active_recall"
        case "why_wrong_reasoning":
            return "why_wrong_reasoning"
        case "timed_quiz":
            return "timed_quiz"
        case "roleplay_script":
            return "roleplay_script"
        case "inverse_thinking":
            return "inverse_thinking"
        case "semantic_anchoring":
            return "semantic_anchoring"
        case _:
            msg = f"unknown methodology tag: {value}"
            raise ValueError(msg)
