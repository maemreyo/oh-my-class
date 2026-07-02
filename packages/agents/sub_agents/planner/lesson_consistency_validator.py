from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, assert_never

from common.contracts.lesson_sequence import BloomLevel
from common.contracts.lesson_plan import LessonPlan

LessonConsistencyRule = Literal[
    "bloom_coverage",
    "assessment_alignment",
    "prerequisite_ordering",
    "cognitive_load",
    "duration_realism",
    "gagne_coverage",
]


class LessonConsistencySeverity(StrEnum):
    HARD = "hard"
    ADVISORY = "advisory"


@dataclass(frozen=True, slots=True)
class LessonConsistencyIssue:
    rule: LessonConsistencyRule
    severity: LessonConsistencySeverity
    message: str


GAGNE_EVENTS: tuple[str, ...] = (
    "gain_attention",
    "inform_objectives",
    "recall_prior",
    "present_content",
    "provide_guidance",
    "elicit_performance",
    "provide_feedback",
    "assess_performance",
    "enhance_retention",
)


class LessonConsistencyValidator:
    def validate(self, plan: LessonPlan) -> list[LessonConsistencyIssue]:
        return [
            *_bloom_issues(plan),
            *_assessment_issues(plan),
            *_ordering_issues(plan),
            *_load_issues(plan),
            *_duration_issues(plan),
            *_gagne_issues(plan),
        ]

    def repair(self, plan: LessonPlan) -> LessonPlan:
        repaired = _repair_objective_order(plan)
        repaired = _repair_cognitive_load(repaired)
        repaired = _repair_gagne_coverage(repaired)
        return repaired


def _bloom_issues(plan: LessonPlan) -> list[LessonConsistencyIssue]:
    bloom_levels = {objective.bloom_level for objective in plan.learning_objectives}
    has_apply = any(_is_apply_or_higher(level) for level in bloom_levels)
    if len(bloom_levels) >= 2 and has_apply:
        return []
    return [LessonConsistencyIssue(
        rule="bloom_coverage",
        severity=LessonConsistencySeverity.HARD,
        message="Lesson needs at least two Bloom levels and one apply-or-higher objective.",
    )]


def _assessment_issues(plan: LessonPlan) -> list[LessonConsistencyIssue]:
    checkpoint_text = " ".join(checkpoint.description for checkpoint in plan.assessment_checkpoints).casefold()
    issues: list[LessonConsistencyIssue] = []
    for objective in plan.learning_objectives:
        has_method = bool(objective.assessment_method)
        objective_words = [word for word in objective.description.casefold().split() if len(word) > 3]
        has_checkpoint = any(word in checkpoint_text for word in objective_words[:3])
        if not has_method or not has_checkpoint:
            issues.append(LessonConsistencyIssue(
                rule="assessment_alignment",
                severity=LessonConsistencySeverity.HARD,
                message=f"Objective lacks aligned assessment evidence: {objective.description}",
            ))
    return issues


def _ordering_issues(plan: LessonPlan) -> list[LessonConsistencyIssue]:
    ranks = [_bloom_rank(objective.bloom_level) for objective in plan.learning_objectives]
    if ranks == sorted(ranks):
        return []
    return [LessonConsistencyIssue(
        rule="prerequisite_ordering",
        severity=LessonConsistencySeverity.HARD,
        message="Lower-Bloom prerequisite objectives must precede apply-or-higher work.",
    )]


def _load_issues(plan: LessonPlan) -> list[LessonConsistencyIssue]:
    if len(plan.learning_objectives) <= 5 and len(plan.prerequisite_knowledge) <= 8:
        return []
    return [LessonConsistencyIssue(
        rule="cognitive_load",
        severity=LessonConsistencySeverity.HARD,
        message="Lesson introduces too many objectives or prerequisites for one session.",
    )]


def _duration_issues(plan: LessonPlan) -> list[LessonConsistencyIssue]:
    if 10 <= plan.duration_minutes <= 90:
        return []
    return [LessonConsistencyIssue(
        rule="duration_realism",
        severity=LessonConsistencySeverity.HARD,
        message="Single-lesson duration must stay within age-band realistic limits.",
    )]


def _gagne_issues(plan: LessonPlan) -> list[LessonConsistencyIssue]:
    missing = [event for event in GAGNE_EVENTS if event not in plan.learning_plan]
    if not missing:
        return []
    return [LessonConsistencyIssue(
        rule="gagne_coverage",
        severity=LessonConsistencySeverity.HARD,
        message="Missing Gagné event(s): " + ", ".join(missing),
    )]


def _repair_objective_order(plan: LessonPlan) -> LessonPlan:
    objectives = sorted(plan.learning_objectives, key=lambda objective: _bloom_rank(objective.bloom_level))
    return plan.model_copy(update={"learning_objectives": objectives})


def _repair_cognitive_load(plan: LessonPlan) -> LessonPlan:
    return plan.model_copy(update={
        "learning_objectives": plan.learning_objectives[:5],
        "prerequisite_knowledge": plan.prerequisite_knowledge[:8],
    })


def _repair_gagne_coverage(plan: LessonPlan) -> LessonPlan:
    learning_plan = dict(plan.learning_plan)
    for event in GAGNE_EVENTS:
        learning_plan.setdefault(event, f"Complete {event.replace('_', ' ')} for {plan.topic}.")
    return plan.model_copy(update={"learning_plan": learning_plan})


def _is_apply_or_higher(level: BloomLevel) -> bool:
    match level:
        case "remember" | "understand":
            return False
        case "apply" | "analyze" | "evaluate" | "create":
            return True
        case unreachable:
            assert_never(unreachable)


def _bloom_rank(level: BloomLevel) -> int:
    match level:
        case "remember":
            return 0
        case "understand":
            return 1
        case "apply":
            return 2
        case "analyze":
            return 3
        case "evaluate":
            return 4
        case "create":
            return 5
        case unreachable:
            assert_never(unreachable)
