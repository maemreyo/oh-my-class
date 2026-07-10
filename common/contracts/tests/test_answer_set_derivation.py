from __future__ import annotations

from typing import Any

import pytest

from common.contracts.answer_set import (
    AnswerSetVerificationError,
    derive_answer_key_artifact,
    derive_answer_set,
    verify_answer_set,
)


def _quiz() -> dict[str, Any]:
    return {
        "artifact_type": "quiz",
        "title": "Quiz: Fractions",
        "sections": [{
            "components": [{
                "type": "question_card",
                "id": "quiz-objective-1-1",
                "text": "Which fraction is one half?",
                "options": {"A": "2/4", "B": "1/3", "C": "3/4", "D": "1/4"},
                "answer": "A",
                "explain": "Two fourths equals one half.",
            }],
        }],
    }


def test_derive_answer_set_keeps_answers_outside_student_artifact_sections() -> None:
    quiz = _quiz()
    answer_set = derive_answer_set(quiz, source_document_id="quiz-1", source_version=1)

    assert answer_set.answer_set_id == "answers-quiz-1-v1"
    assert answer_set.entries[0].question_id == "quiz-objective-1-1"
    assert answer_set.entries[0].correct_option_ids == ["A"]
    assert quiz["sections"][0]["components"][0]["answer"] == "A"


def test_verify_answer_set_rejects_an_answer_not_in_question_options() -> None:
    answer_set = derive_answer_set(_quiz(), source_document_id="quiz-1", source_version=1)
    bad = answer_set.model_copy(update={
        "entries": [answer_set.entries[0].model_copy(update={"correct_option_ids": ["Z"]})],
    })

    with pytest.raises(AnswerSetVerificationError, match="unknown option"):
        verify_answer_set(_quiz(), bad)


def test_derived_answer_key_is_teacher_only_and_uses_stable_question_ids() -> None:
    quiz = _quiz()
    answer_set = derive_answer_set(quiz, source_document_id="quiz-1", source_version=1)
    key = derive_answer_key_artifact(quiz, answer_set, language="en")

    assert key["artifact_type"] == "answer_key"
    assert key["sections"][0]["id"] == "answer-key-quiz-objective-1-1"
    assert key["sections"][0]["components"][0]["text"] == "Answer: A"
