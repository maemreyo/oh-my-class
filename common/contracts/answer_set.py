"""Teacher-only answers linked to stable assessment entity IDs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AnswerAuthority = Literal["generated", "teacher_edit", "ai_assisted_edit"]


class AnswerEntry(BaseModel):
    """One teacher-only answer for a question in an assessment document."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    question_id: str = Field(min_length=1, max_length=80)
    correct_option_ids: list[str] = Field(default_factory=list)
    accepted_answers: list[str] = Field(default_factory=list)
    rationale: str | None = Field(default=None, min_length=1, max_length=2_000)


class AnswerSet(BaseModel):
    """Teacher-only answers for one immutable assessment document version."""

    model_config = ConfigDict(frozen=True)

    answer_set_id: str = Field(min_length=1, max_length=80)
    source_document_id: str = Field(min_length=1, max_length=80)
    source_version: int = Field(ge=1)
    authority: AnswerAuthority = "generated"
    entries: list[AnswerEntry] = Field(min_length=1)


class AnswerSetVerificationError(ValueError):
    pass


def derive_answer_set(
    artifact: dict[str, Any],
    *,
    source_document_id: str,
    source_version: int,
) -> AnswerSet:
    entries: list[AnswerEntry] = []
    for section in artifact.get("sections", []):
        if not isinstance(section, dict):
            continue
        components = section.get("components", [])
        if not isinstance(components, list):
            continue
        for component in components:
            if not isinstance(component, dict) or component.get("type") != "question_card":
                continue
            question_id = component.get("id")
            answer = component.get("answer")
            if not isinstance(question_id, str) or not question_id or not isinstance(answer, str) or not answer:
                continue
            entries.append(AnswerEntry(
                entity_id=f"answer-{question_id}",
                question_id=question_id,
                correct_option_ids=[answer],
                rationale=component.get("explain") if isinstance(component.get("explain"), str) else None,
            ))
    if not entries:
        raise AnswerSetVerificationError("assessment contains no answer-bearing question_card components")
    answer_set = AnswerSet(
        answer_set_id=f"answers-{source_document_id}-v{source_version}",
        source_document_id=source_document_id,
        source_version=source_version,
        entries=entries,
    )
    verify_answer_set(artifact, answer_set)
    return answer_set


def verify_answer_set(artifact: dict[str, Any], answer_set: AnswerSet) -> None:
    answers_by_question = {entry.question_id: entry for entry in answer_set.entries}
    questions: dict[str, dict[str, Any]] = {}
    for section in artifact.get("sections", []):
        if not isinstance(section, dict) or not isinstance(section.get("components"), list):
            continue
        for component in section["components"]:
            if isinstance(component, dict) and component.get("type") == "question_card":
                question_id = component.get("id")
                if isinstance(question_id, str):
                    questions[question_id] = component
    for question_id, entry in answers_by_question.items():
        question = questions.get(question_id)
        if question is None:
            raise AnswerSetVerificationError(f"answer references missing question {question_id}")
        options = question.get("options")
        if not isinstance(options, dict) or any(option_id not in options for option_id in entry.correct_option_ids):
            raise AnswerSetVerificationError(f"answer for {question_id} references an unknown option")


def derive_answer_key_artifact(
    artifact: dict[str, Any],
    answer_set: AnswerSet,
    *,
    theme: str = "default",
    language: str = "vi",
) -> dict[str, Any]:
    questions = {
        str(component.get("id")): component
        for section in artifact.get("sections", [])
        if isinstance(section, dict) and isinstance(section.get("components"), list)
        for component in section["components"]
        if isinstance(component, dict) and component.get("type") == "question_card"
    }
    sections: list[dict[str, Any]] = []
    for entry in answer_set.entries:
        question = questions.get(entry.question_id)
        if question is None:
            raise AnswerSetVerificationError(f"answer key references missing question {entry.question_id}")
        answer = ", ".join(entry.correct_option_ids or entry.accepted_answers)
        sections.append({
            "id": f"answer-key-{entry.question_id}",
            "title": f"Question {entry.question_id}",
            "summary": str(question.get("text") or ""),
            "components": [{
                "type": "paragraph",
                "text": f"Answer: {answer}",
            }],
        })
    return {
        "artifact_type": "answer_key",
        "title": f"Answer Key: {artifact.get('title', 'Assessment')}",
        "theme": theme,
        "sections": sections,
        "metadata": {"total_questions": len(sections)},
        "accessibility": {"language": language},
    }
