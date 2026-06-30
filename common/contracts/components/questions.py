"""Question components — QuestionCard (MCQ), QuestionList (section wrapper)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QuestionCard(BaseModel):
    type: Literal["question_card"] = "question_card"
    id: int | str
    text: str
    options: dict[str, str]
    answer: str
    explain: str
    group: str = "a"
    wrong_reasons: dict[str, str] | None = None
    essence: str | None = None
    tip: str | None = None
    kc_ids: list[str] = Field(default_factory=list)


class QuestionList(BaseModel):
    type: Literal["question_list"] = "question_list"
    questions: list[QuestionCard]
    section_key: str
    group: str
    title: str
    sub: str | None = None
    instruction: str | None = None
    summary: str | None = None
    range: str | None = None
