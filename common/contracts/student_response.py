"""StudentResponse Pydantic models — input contract for diagnostic pipeline.

Captures the student's test submission: which questions were wrong (teacher input)
and a per-question answer breakdown built during analysis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StudentAnswerItem(BaseModel):
    """A single question's answer record within a student's response."""

    question_id: int | str
    student_answer: str | None = None    # None = unanswered
    correct_answer: str
    is_correct: bool
    section: str | None = None
    bloom_level: str | None = None       # populated during analysis


class StudentResponse(BaseModel):
    """The full response submitted by a student for a given test."""

    student_id: str
    test_id: str = "unknown"
    wrong_question_ids: list[int | str]  # teacher input
    answers: list[StudentAnswerItem] = []
    total_questions: int = 0
    context: dict = Field(default_factory=dict)
