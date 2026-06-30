"""Tests for outcome contracts: StudentAttempt, StudentKCState, DeliveryRecord.

Also verifies that QuestionCard.kc_ids is backward-compatible.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from common.contracts.components.questions import QuestionCard
from common.contracts.outcome import DeliveryRecord, StudentAttempt, StudentKCState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


def _attempt(**overrides) -> dict:
    base = {
        "attempt_id": "a1b2c3d4-0000-0000-0000-000000000001",
        "student_pseudonym": "sha256:abc123",
        "question_id": "q-001",
        "kc_ids": ["KC-fractions", "KC-division"],
        "correct": True,
        "score": 1.0,
        "timestamp": _NOW,
        "delivery_id": "del-001",
    }
    return {**base, **overrides}


def _kc_state(**overrides) -> dict:
    base = {
        "state_id": "state-001",
        "student_pseudonym": "sha256:abc123",
        "kc_id": "KC-fractions",
        "mastery": 0.75,
        "params": {"p_L0": 0.25, "p_T": 0.3, "p_G": 0.2, "p_S": 0.1},
        "updated_at": _NOW,
    }
    return {**base, **overrides}


def _delivery(**overrides) -> dict:
    base = {
        "delivery_id": "del-001",
        "run_id": "run-001",
        "teacher_id": "teacher-001",
        "kc_ids": ["KC-fractions"],
        "delivered_at": _NOW,
        "class_id": "class-5A",
    }
    return {**base, **overrides}


# ---------------------------------------------------------------------------
# StudentAttempt
# ---------------------------------------------------------------------------


class TestStudentAttempt:
    def test_parses_valid_attempt(self) -> None:
        attempt = StudentAttempt.model_validate(_attempt())
        assert attempt.attempt_id == "a1b2c3d4-0000-0000-0000-000000000001"
        assert attempt.student_pseudonym == "sha256:abc123"
        assert attempt.kc_ids == ["KC-fractions", "KC-division"]
        assert attempt.correct is True
        assert attempt.score == 1.0

    def test_schema_version_is_fixed(self) -> None:
        attempt = StudentAttempt.model_validate(_attempt())
        assert attempt.schema_version == "student_attempt.v1"

    def test_round_trips_through_model_dump(self) -> None:
        original = StudentAttempt.model_validate(_attempt())
        reparsed = StudentAttempt.model_validate(original.model_dump())
        assert reparsed == original

    def test_score_must_be_within_bounds(self) -> None:
        with pytest.raises(ValidationError):
            StudentAttempt.model_validate(_attempt(score=1.5))
        with pytest.raises(ValidationError):
            StudentAttempt.model_validate(_attempt(score=-0.1))

    def test_empty_kc_ids_is_valid(self) -> None:
        attempt = StudentAttempt.model_validate(_attempt(kc_ids=[]))
        assert attempt.kc_ids == []

    def test_schema_version_cannot_be_overridden(self) -> None:
        # Providing a wrong literal should fail validation
        with pytest.raises(ValidationError):
            StudentAttempt.model_validate({**_attempt(), "schema_version": "student_attempt.v2"})


# ---------------------------------------------------------------------------
# StudentKCState
# ---------------------------------------------------------------------------


class TestStudentKCState:
    def test_parses_valid_state(self) -> None:
        state = StudentKCState.model_validate(_kc_state())
        assert state.kc_id == "KC-fractions"
        assert state.mastery == 0.75
        assert state.params["p_L0"] == 0.25

    def test_schema_version_is_fixed(self) -> None:
        state = StudentKCState.model_validate(_kc_state())
        assert state.schema_version == "student_kc_state.v1"

    def test_round_trips_through_model_dump(self) -> None:
        original = StudentKCState.model_validate(_kc_state())
        reparsed = StudentKCState.model_validate(original.model_dump())
        assert reparsed == original

    def test_mastery_must_be_within_bounds(self) -> None:
        with pytest.raises(ValidationError):
            StudentKCState.model_validate(_kc_state(mastery=1.01))
        with pytest.raises(ValidationError):
            StudentKCState.model_validate(_kc_state(mastery=-0.01))

    def test_empty_params_is_valid(self) -> None:
        state = StudentKCState.model_validate(_kc_state(params={}))
        assert state.params == {}


# ---------------------------------------------------------------------------
# DeliveryRecord
# ---------------------------------------------------------------------------


class TestDeliveryRecord:
    def test_parses_valid_record(self) -> None:
        record = DeliveryRecord.model_validate(_delivery())
        assert record.delivery_id == "del-001"
        assert record.run_id == "run-001"
        assert record.kc_ids == ["KC-fractions"]
        assert record.class_id == "class-5A"

    def test_schema_version_is_fixed(self) -> None:
        record = DeliveryRecord.model_validate(_delivery())
        assert record.schema_version == "delivery_record.v1"

    def test_class_id_is_optional(self) -> None:
        record = DeliveryRecord.model_validate(_delivery(class_id=None))
        assert record.class_id is None

    def test_round_trips_through_model_dump(self) -> None:
        original = DeliveryRecord.model_validate(_delivery())
        reparsed = DeliveryRecord.model_validate(original.model_dump())
        assert reparsed == original


# ---------------------------------------------------------------------------
# QuestionCard — kc_ids backward compatibility
# ---------------------------------------------------------------------------


class TestQuestionCardKcIds:
    def test_question_card_with_kc_ids_parses(self) -> None:
        card = QuestionCard(
            id="q-001",
            text="What is 1/2 + 1/3?",
            options={"A": "5/6", "B": "2/6", "C": "2/5", "D": "1/5"},
            answer="A",
            explain="Common denominator is 6.",
            kc_ids=["KC-fractions", "KC-addition"],
        )
        assert card.kc_ids == ["KC-fractions", "KC-addition"]

    def test_question_card_without_kc_ids_defaults_to_empty_list(self) -> None:
        card = QuestionCard(
            id="q-002",
            text="What is 2+2?",
            options={"A": "3", "B": "4", "C": "5", "D": "6"},
            answer="B",
            explain="Basic addition.",
        )
        assert card.kc_ids == []

    def test_existing_dict_without_kc_ids_parses_for_backward_compat(self) -> None:
        """Simulate deserialising a pre-existing QuestionCard that has no kc_ids key."""
        raw = {
            "type": "question_card",
            "id": "legacy-001",
            "text": "Legacy question",
            "options": {"A": "yes", "B": "no"},
            "answer": "A",
            "explain": "Always yes.",
            "group": "a",
        }
        card = QuestionCard.model_validate(raw)
        assert card.kc_ids == []
