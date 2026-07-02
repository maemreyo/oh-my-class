from __future__ import annotations

from datetime import UTC, datetime, timedelta

from common.contracts.outcome import StudentAttempt
from packages.agents.kt_engine import update_knowledge_tracing


def test_correct_attempts_raise_mastery_and_params_stay_bounded() -> None:
    attempts = [_attempt(index, correct=True) for index in range(3)]

    updates = update_knowledge_tracing(attempts)

    assert len(updates) == 1
    assert updates[0].confidence == "high"
    assert updates[0].state.mastery > 0.35
    assert updates[0].state.params["local_bayesian_ema_used"] == 1.0
    assert "pybkt_used" not in updates[0].state.params
    assert all(0.0 <= value <= 3.0 for value in updates[0].state.params.values())


def test_cold_start_is_low_confidence() -> None:
    updates = update_knowledge_tracing([_attempt(0, correct=True)])

    assert updates[0].confidence == "low"


def test_incorrect_attempt_decreases_bkt_mastery() -> None:
    correct_update = update_knowledge_tracing([_attempt(0, correct=True)])[0]
    incorrect_update = update_knowledge_tracing([_attempt(0, correct=False)])[0]

    assert incorrect_update.state.mastery < correct_update.state.mastery
    assert incorrect_update.state.params["local_bayesian_ema_used"] == 1.0


def test_unverified_alignment_flags_low_trust_mastery() -> None:
    attempts = [_attempt(index, correct=True, alignment_verified=index != 1) for index in range(3)]

    update = update_knowledge_tracing(attempts)[0]

    assert update.confidence == "low"
    assert update.state.params["alignment_verified"] == 0.0


def _attempt(index: int, *, correct: bool, alignment_verified: bool = True) -> StudentAttempt:
    return StudentAttempt(
        attempt_id=f"attempt-{index}",
        student_pseudonym="student-a",
        question_id=f"q-{index}",
        kc_ids=["KC-FRACTION"],
        correct=correct,
        score=1.0 if correct else 0.0,
        alignment_verified=alignment_verified,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
        delivery_id="delivery-1",
    )
