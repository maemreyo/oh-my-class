from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MasteryDecision(StrEnum):
    RETEACH = "reteach"
    PRACTICE = "practice"
    ASSUME = "assume"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class MasterySignal:
    kc_id: str
    mastery: float
    confidence: str


def decide_mastery_action(signal: MasterySignal | None) -> MasteryDecision:
    if signal is None or signal.confidence == "low":
        return MasteryDecision.FALLBACK
    if signal.mastery < 0.45:
        return MasteryDecision.RETEACH
    if signal.mastery < 0.75:
        return MasteryDecision.PRACTICE
    return MasteryDecision.ASSUME
