from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from common.contracts.lesson_plan import LessonPlan


class CritiqueSeverity(StrEnum):
    SOFT = "soft"
    HARD = "hard"


class LessonCritiqueType(StrEnum):
    OBJECTIVE_COVERAGE = "objective_coverage"
    MISCONCEPTION_GAP = "misconception_gap"
    PREREQUISITE_GAP = "prerequisite_gap"


@dataclass(frozen=True, slots=True)
class LessonCritique:
    critique_type: LessonCritiqueType
    severity: CritiqueSeverity
    suggested_fix: str
    evidence: str

    def as_dict(self) -> dict[str, str]:
        return {
            "type": self.critique_type.value,
            "severity": self.severity.value,
            "suggested_fix": self.suggested_fix,
            "evidence": self.evidence,
        }


def critique_lesson(plan: LessonPlan) -> list[LessonCritique]:
    return [
        *_objective_coverage_critiques(plan),
        *_prerequisite_critiques(plan),
        *_misconception_critiques(plan),
    ]


def _objective_coverage_critiques(plan: LessonPlan) -> list[LessonCritique]:
    assessment_text = " ".join(checkpoint.description for checkpoint in plan.assessment_checkpoints).casefold()
    critiques: list[LessonCritique] = []
    for objective in plan.learning_objectives:
        key_terms = [word for word in objective.description.casefold().split() if len(word) > 3]
        if key_terms and not any(term in assessment_text for term in key_terms[:3]):
            critiques.append(LessonCritique(
                critique_type=LessonCritiqueType.OBJECTIVE_COVERAGE,
                severity=CritiqueSeverity.HARD,
                suggested_fix="Add assessment evidence that directly samples this objective.",
                evidence=objective.description,
            ))
    return critiques


def _prerequisite_critiques(plan: LessonPlan) -> list[LessonCritique]:
    if plan.prerequisite_knowledge:
        return []
    return [LessonCritique(
        critique_type=LessonCritiqueType.PREREQUISITE_GAP,
        severity=CritiqueSeverity.HARD,
        suggested_fix="Name the prerequisite knowledge before planning new content.",
        evidence=plan.topic,
    )]


def _misconception_critiques(plan: LessonPlan) -> list[LessonCritique]:
    plan_text = " ".join(str(value) for value in plan.learning_plan.values()).casefold()
    if "misconception" in plan_text or "hiểu lầm" in plan_text:
        return []
    return [LessonCritique(
        critique_type=LessonCritiqueType.MISCONCEPTION_GAP,
        severity=CritiqueSeverity.SOFT,
        suggested_fix="Surface at least one likely misconception before guided practice.",
        evidence=plan.topic,
    )]
