from __future__ import annotations

import pytest

from common.contracts.answer_set import derive_answer_set
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from packages.agents.teaching_pack.generate_one_artifact import generate_one_artifact
from packages.agents.teaching_pack.specialists.quiz_specialist import (
    NoQuizObjectivesError,
    build_quiz_questions,
    generate_quiz_artifact,
    score_quiz,
)
from packages.quality.layer1_schema.component_gate import validate_component_minimums


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent Fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "locale": "en",
        "learning_objectives": [
            {"description": "Identify equivalent fractions."},
            {"description": "Generate equivalent fractions."},
        ],
    }


def test_quiz_questions_are_stable_and_answerable() -> None:
    first = build_quiz_questions(_lesson_plan())
    second = build_quiz_questions(_lesson_plan())

    assert len(first) == 8
    assert [question["id"] for question in first] == [question["id"] for question in second]
    assert all(question["answer"] in question["options"] for question in first)


def test_quiz_fails_closed_without_objectives() -> None:
    with pytest.raises(NoQuizObjectivesError):
        generate_quiz_artifact({"topic": "Empty"}, {"sources": []})


def test_generated_quiz_passes_component_gate_and_derives_answer_set() -> None:
    artifact = generate_quiz_artifact(_lesson_plan(), {"sources": []})

    assert validate_component_minimums(artifact) == []
    answer_set = derive_answer_set(artifact, source_document_id="quiz-1", source_version=1)
    assert len(answer_set.entries) == 8


def test_quiz_scorecard_is_complete() -> None:
    questions = build_quiz_questions(_lesson_plan())
    scorecard = score_quiz(questions, objective_count=2)

    assert scorecard.objective_coverage == 1.0
    assert scorecard.question_identity == 1.0
    assert scorecard.assessment_alignment == 1.0
    assert scorecard.answer_verifiability == 1.0


@pytest.mark.anyio
async def test_quiz_workflow_persists_answer_set_and_derives_teacher_only_answer_key() -> None:
    store = InMemoryArtifactContentStore()
    quiz_result = await generate_one_artifact({
        "run_id": "run-1",
        "artifact_generation_id": "run-1:artifact:1",
        "artifact_type": "quiz",
        "lesson_plan": _lesson_plan(),
        "research_brief": {"sources": []},
        "theme": "ocean",
        "dependency_artifact_references": [],
    }, store)
    quiz_reference = quiz_result["artifact_references"][0]
    quiz = await store.read_projection(quiz_reference["document_id"])

    assert "answer_set" in quiz.metadata
    first_question_answer = quiz.sections[0]["components"][0]["answer"]
    key_result = await generate_one_artifact({
        "run_id": "run-1",
        "artifact_generation_id": "run-1:artifact:1",
        "artifact_type": "answer_key",
        "lesson_plan": _lesson_plan(),
        "research_brief": {"sources": []},
        "theme": "ocean",
        "dependency_artifact_references": [quiz_reference],
    }, store)
    key = await store.read_projection(key_result["artifact_references"][0]["document_id"])

    assert key.artifact_type == "answer_key"
    assert key.theme == "ocean"
    # #447: this lesson plan is math/Grade 5, so quiz_specialist now builds
    # real solver-verified questions whose correct option isn't always "A"
    # (shuffled to avoid a guessable pattern) -- assert against the quiz's
    # own stored answer rather than a hardcoded letter.
    assert key.sections[0]["components"][0]["text"] == f"Answer: {first_question_answer}"
