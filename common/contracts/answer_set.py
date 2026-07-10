"""Teacher-only answers linked to stable assessment entity IDs."""

from __future__ import annotations

from typing import Literal

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
