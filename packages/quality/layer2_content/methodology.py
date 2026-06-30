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
from typing import Any, assert_never

from common.contracts.methodology_registry import METHODOLOGY_REGISTRY, CompositeProjectionPlan

_STRUCTURAL_REQUIREMENTS = {
    entry.tag: entry
    for entry in METHODOLOGY_REGISTRY
    if entry.required_components and entry.tag not in {"timed_quiz", "why_wrong_reasoning"}
}


@dataclass
class MethodologyViolation:
    tag: str
    message: str


@dataclass
class MethodologyGateResult:
    passed: bool
    violations: list[MethodologyViolation] = field(default_factory=list)


def validate_composite_projection_plan(plan: CompositeProjectionPlan, sections: list[dict[str, Any]]) -> MethodologyGateResult:
    violations: list[MethodologyViolation] = []
    for component, source_tags in plan.source_methodology_tags.items():
        if _component_satisfied(component, sections):
            continue
        violations.append(MethodologyViolation(
            tag="+".join(source_tags),
            message=f"Composite projection missing {component} required by {', '.join(source_tags)}.",
        ))
    return MethodologyGateResult(passed=len(violations) == 0, violations=violations)


def _component_satisfied(component: str, sections: list[dict[str, Any]]) -> bool:
    match component:
        case "wrong_reasons":
            return _count_question_cards(sections) > 0 and not _question_card_wrong_reason_gaps(sections)
        case "time_limit":
            return any(section.get("time_limit") or section.get("duration_minutes") for section in sections)
        case "case_flow":
            return _has_component_type(sections, "case_flow")
        case "summary_table":
            return _has_component_type(sections, "table") or _has_component_type(sections, "summary_table")
        case _:
            return _has_component_type(sections, component)


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


def _question_card_wrong_reason_gaps(sections: list[dict[str, Any]]) -> list[str]:
    gaps: list[str] = []
    for section in sections:
        for comp in section.get("components", []):
            if not isinstance(comp, dict) or comp.get("type") != "question_card":
                continue

            question_id = str(comp.get("id", "unknown"))
            anchor = f"#question-card-{question_id}-wrong-reasons"
            wrong_reasons = comp.get("wrong_reasons")
            if not isinstance(wrong_reasons, dict) or len(wrong_reasons) == 0:
                gaps.append(f"question_card {question_id}: wrong_reasons empty ({anchor})")
                continue

            options = comp.get("options")
            if not isinstance(options, dict):
                continue

            answer = str(comp.get("answer", ""))
            missing_options = [
                str(option_key)
                for option_key in options
                if str(option_key) != answer and not str(wrong_reasons.get(option_key, "")).strip()
            ]
            if missing_options:
                gaps.append(
                    f"question_card {question_id}: missing wrong_reasons for "
                    f"options {', '.join(missing_options)} ({anchor})"
                )
    return gaps


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
        entry = _STRUCTURAL_REQUIREMENTS.get(tag)
        if entry is None:
            continue

        required_types = entry.required_components
        match entry.requirement_mode:
            case "any":
                satisfied = any(_has_component_type(sections, comp_type) for comp_type in required_types)
            case "all":
                satisfied = all(_has_component_type(sections, comp_type) for comp_type in required_types)
            case unreachable:
                assert_never(unreachable)
        if not satisfied:
            alternatives = " or ".join(required_types)
            violations.append(MethodologyViolation(
                tag=tag,
                message=(
                    f"{entry.label_en} methodology tag '{tag}' requires {alternatives} "
                    "so students can see relationships and grouping, but none "
                    "were found in lesson sections."
                ),
            ))

    if "why_wrong_reasoning" in methodology_tags and _count_question_cards(sections) > 0:
        wrong_reason_gaps = _question_card_wrong_reason_gaps(sections)
        if wrong_reason_gaps:
            violations.append(MethodologyViolation(
                    tag="why_wrong_reasoning",
                    message=(
                        "Methodology tag 'why_wrong_reasoning' requires every question_card "
                        "to have wrong_reasons for each distractor/choice: "
                        + "; ".join(wrong_reason_gaps)
                    ),
                ))

    return MethodologyGateResult(passed=len(violations) == 0, violations=violations)
