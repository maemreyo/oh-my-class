from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from common.contracts.outcome import StudentAttempt, StudentKCState

MIN_SUFFICIENT_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class KTUpdate:
    state: StudentKCState
    confidence: str


def update_knowledge_tracing(attempts: list[StudentAttempt]) -> list[KTUpdate]:
    grouped: dict[tuple[str, str], list[StudentAttempt]] = {}
    for attempt in attempts:
        for kc_id in attempt.kc_ids:
            grouped.setdefault((attempt.student_pseudonym, kc_id), []).append(attempt)
    return [_update_one(student, kc_id, rows) for (student, kc_id), rows in sorted(grouped.items())]


def _update_one(student: str, kc_id: str, attempts: list[StudentAttempt]) -> KTUpdate:
    mastery = 0.35
    for attempt in sorted(attempts, key=lambda row: row.timestamp):
        if attempt.correct:
            mastery = mastery + (1.0 - mastery) * 0.28
        else:
            mastery = mastery * 0.72
    confidence = "high" if len(attempts) >= MIN_SUFFICIENT_ATTEMPTS else "low"
    return KTUpdate(
        state=StudentKCState(
            state_id=f"state-{uuid4()}",
            student_pseudonym=student,
            kc_id=kc_id,
            mastery=max(0.0, min(1.0, mastery)),
            params={
                "prior": 0.35,
                "learn": 0.28,
                "slip": 0.28,
                "guess": 0.28,
                "attempts": float(len(attempts)),
            },
            updated_at=datetime.now(UTC),
        ),
        confidence=confidence,
    )
