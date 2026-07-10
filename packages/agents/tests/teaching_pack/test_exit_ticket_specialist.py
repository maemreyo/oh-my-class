from __future__ import annotations

import pytest

from common.contracts.answer_set import derive_answer_set
from packages.agents.teaching_pack.specialists.exit_ticket_specialist import (
    NoExitTicketObjectivesError,
    build_exit_ticket_questions,
    generate_exit_ticket_artifact,
    score_exit_ticket,
)


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "locale": "en",
        "learning_objectives": [{"description": "Identify equivalent fractions."}],
    }


def test_exit_ticket_has_three_stable_objective_sampling_questions() -> None:
    first = build_exit_ticket_questions(_lesson_plan())
    second = build_exit_ticket_questions(_lesson_plan())

    assert len(first) == 3
    assert [question["id"] for question in first] == [question["id"] for question in second]


def test_exit_ticket_fails_closed_without_objectives() -> None:
    with pytest.raises(NoExitTicketObjectivesError):
        generate_exit_ticket_artifact({"topic": "Empty"}, {"sources": []})


def test_exit_ticket_derives_teacher_only_answer_set() -> None:
    artifact = generate_exit_ticket_artifact(_lesson_plan(), {"sources": []})
    answer_set = derive_answer_set(artifact, source_document_id="exit-1", source_version=1)

    assert len(answer_set.entries) == 3
    assert answer_set.entries[0].correct_option_ids == ["A"]


def test_exit_ticket_scorecard_is_complete() -> None:
    scorecard = score_exit_ticket(build_exit_ticket_questions(_lesson_plan()), objective_count=1)

    assert scorecard.brevity == 1.0
    assert scorecard.objective_sampling == 1.0
    assert scorecard.scoring == 1.0
    assert scorecard.identity_stability == 1.0
