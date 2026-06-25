"""Methodology compliance gate — Layer 2 check for vocab lesson methodology.

Enforces that lesson artifacts tagged with specific methodology flags contain
the required component types. Only runs when the lesson plan declares tags;
skips silently when no tags are declared (backwards-compatible).

Report 09 requirements enforced:
  R1 concept_map / contrastive_pairs → vocab_cluster or contrastive_pairs
  R2 film_based                      → film_clip_activity
  R3 shy_student_1on1                → roleplay_script
  R4 active_recall                   → active_recall_prompt
  R5 why_wrong_reasoning             → question_card with wrong_reasons on every card
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Maps a methodology tag to the component type(s) that satisfy it.
# Any ONE of the listed types satisfies the requirement.
_TAG_REQUIRED_TYPES: dict[str, list[str]] = {
    "concept_map":       ["vocab_cluster", "contrastive_pairs"],
    "contrastive_pairs": ["contrastive_pairs"],
    "film_based":        ["film_clip_activity"],
    "shy_student_1on1":  ["roleplay_script"],
    "active_recall":     ["active_recall_prompt"],
    # why_wrong_reasoning is checked separately (quality of each question_card)
}


@dataclass
class MethodologyViolation:
    tag: str
    message: str


@dataclass
class MethodologyGateResult:
    passed: bool
    violations: list[MethodologyViolation] = field(default_factory=list)


def _has_component_type(sections: list[dict[str, Any]], comp_type: str) -> bool:
    """Return True if any section contains a component of the given type."""
    for section in sections:
        for comp in section.get("components", []):
            if isinstance(comp, dict) and comp.get("type") == comp_type:
                return True
    return False


def _count_question_cards(sections: list[dict[str, Any]]) -> int:
    count = 0
    for section in sections:
        for comp in section.get("components", []):
            if isinstance(comp, dict) and comp.get("type") == "question_card":
                count += 1
    return count


def _questions_have_wrong_reasons(sections: list[dict[str, Any]]) -> bool:
    """Return True if every question_card has a non-empty wrong_reasons dict."""
    for section in sections:
        for comp in section.get("components", []):
            if isinstance(comp, dict) and comp.get("type") == "question_card" and not comp.get("wrong_reasons"):  # noqa: E501
                return False
    return True


def check_methodology_compliance(
    sections: list[dict[str, Any]],
    methodology_tags: list[str],
) -> MethodologyGateResult:
    """Check that lesson sections satisfy all declared methodology requirements.

    Args:
        sections: Artifact sections from the lesson content.
        methodology_tags: Tags declared in LessonPlan.methodology.tags.

    Returns:
        MethodologyGateResult with passed=True when all tag requirements are met.
        Returns passed=True immediately when methodology_tags is empty (no-op).
    """
    if not methodology_tags:
        return MethodologyGateResult(passed=True)

    violations: list[MethodologyViolation] = []

    for tag in methodology_tags:
        required_types = _TAG_REQUIRED_TYPES.get(tag)
        if required_types is None:
            continue  # tag has no structural requirement (e.g. timed_quiz handled by time badges)

        satisfied = any(_has_component_type(sections, t) for t in required_types)
        if not satisfied:
            violations.append(MethodologyViolation(
                tag=tag,
                message=(
                    f"Methodology tag '{tag}' requires one of {required_types} "
                    f"but none found in lesson sections."
                ),
            ))

    # R5: why_wrong_reasoning — every question_card must carry wrong_reasons
    if "why_wrong_reasoning" in methodology_tags and _count_question_cards(sections) > 0 and not _questions_have_wrong_reasons(sections):  # noqa: E501
        violations.append(MethodologyViolation(
                tag="why_wrong_reasoning",
                message=(
                    "Methodology tag 'why_wrong_reasoning' requires every question_card "
                    "to have a non-empty 'wrong_reasons' dict."
                ),
            ))

    return MethodologyGateResult(passed=len(violations) == 0, violations=violations)
