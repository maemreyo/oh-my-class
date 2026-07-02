from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

Confidence = Literal["low", "medium", "high"]


class MasterySnapshot(TypedDict):
    mastery: float
    confidence: Confidence
    source: str


@dataclass(slots=True)
class KnowledgeStateStore:
    _state: dict[str, dict[str, MasterySnapshot]] = field(default_factory=dict)

    def record_diagnostic(self, student_id: str, report: dict[str, object]) -> dict[str, object]:
        gaps = report.get("knowledge_gaps")
        if isinstance(gaps, list):
            for gap in gaps:
                if isinstance(gap, dict):
                    category = str(gap.get("category", "general"))
                    error_rate = _float(gap.get("error_rate"), 0.5)
                    confidence = _confidence(_float(gap.get("confidence"), 0.5))
                    self._upsert(student_id, category, 1.0 - error_rate, confidence, "diagnostic")
        return report

    def record_kt_update(
        self,
        student_id: str,
        knowledge_component: str,
        *,
        mastery: float,
        confidence: Confidence,
    ) -> None:
        self._upsert(student_id, knowledge_component, mastery, confidence, "kt")

    def planner_mastery(self, student_id: str) -> dict[str, MasterySnapshot]:
        return dict(self._state.get(student_id, {}))

    def _upsert(
        self,
        student_id: str,
        knowledge_component: str,
        mastery: float,
        confidence: Confidence,
        source: str,
    ) -> None:
        student_state = self._state.setdefault(student_id, {})
        student_state[knowledge_component] = {
            "mastery": max(0.0, min(1.0, mastery)),
            "confidence": confidence,
            "source": source,
        }


def _float(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _confidence(value: float) -> Confidence:
    if value >= 0.75:
        return "high"
    if value >= 0.45:
        return "medium"
    return "low"
