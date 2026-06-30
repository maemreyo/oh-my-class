from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never

from common.contracts.lesson_sequence import LessonSequence, SessionPlan


class CritiqueSeverity(StrEnum):
    SOFT = "soft"
    HARD = "hard"


class CritiqueType(StrEnum):
    ORDERING = "ordering"
    FRAGMENTATION = "fragmentation"


@dataclass(frozen=True, slots=True)
class SequenceCritique:
    critique_type: CritiqueType
    involved_sessions: tuple[str, ...]
    severity: CritiqueSeverity
    suggested_fix: str

    def as_dict(self) -> dict[str, str | list[str]]:
        return {
            "type": self.critique_type.value,
            "involved_sessions": [*self.involved_sessions],
            "severity": self.severity.value,
            "suggested_fix": self.suggested_fix,
        }


def critique_sequence(sequence: LessonSequence) -> list[SequenceCritique]:
    critiques: list[SequenceCritique] = []
    critiques.extend(_ordering_critiques(sequence.sessions))
    critiques.extend(_fragmentation_critiques(sequence.sessions))
    return critiques


def repair_hard_critiques(sequence: LessonSequence) -> LessonSequence:
    critiques = [c for c in critique_sequence(sequence) if c.severity is CritiqueSeverity.HARD]
    if not critiques:
        return sequence
    sessions = sorted(sequence.sessions, key=_bloom_rank)
    repaired = [session.model_copy(update={"order_index": index + 1}) for index, session in enumerate(sessions)]
    return sequence.model_copy(update={"sessions": repaired})


def _ordering_critiques(sessions: list[SessionPlan]) -> list[SequenceCritique]:
    critiques: list[SequenceCritique] = []
    highest_rank = -1
    highest_session = ""
    for session in sessions:
        rank = _bloom_rank(session)
        if rank < highest_rank:
            critiques.append(SequenceCritique(
                critique_type=CritiqueType.ORDERING,
                involved_sessions=(highest_session, session.session_id),
                severity=CritiqueSeverity.HARD,
                suggested_fix="Move lower-Bloom prerequisite work before higher-Bloom application work.",
            ))
        if rank > highest_rank:
            highest_rank = rank
            highest_session = session.session_id
    return critiques


def _fragmentation_critiques(sessions: list[SessionPlan]) -> list[SequenceCritique]:
    seen: dict[str, str] = {}
    critiques: list[SequenceCritique] = []
    for session in sessions:
        normalized = session.sub_topic.casefold().strip()
        if normalized in seen:
            critiques.append(SequenceCritique(
                critique_type=CritiqueType.FRAGMENTATION,
                involved_sessions=(seen[normalized], session.session_id),
                severity=CritiqueSeverity.SOFT,
                suggested_fix="Merge duplicated atomic concept coverage or make the second session a deliberate spiral review.",
            ))
        else:
            seen[normalized] = session.session_id
    return critiques


def _bloom_rank(session: SessionPlan) -> int:
    match session.bloom_level_primary:
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
