from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CreativeFrame = Literal[
    "auto",
    "detective_case",
    "courtroom_trial",
    "mythbusters_lab",
    "survival_guide",
    "disaster_report",
    "custom",
]

_STUDENT_FIELD_MARKERS: tuple[str, ...] = (
    "answer key",
    "correct answer",
    "teacher rationale",
    "rationale:",
)


def _reject_teacher_only_markers(value: str) -> str:
    lowered = value.lower()
    if any(marker in lowered for marker in _STUDENT_FIELD_MARKERS):
        msg = "student-facing inverse-thinking fields must not contain teacher-only answer data"
        raise ValueError(msg)
    return value


class InverseThinkingTeacherOnly(BaseModel):
    model_config = ConfigDict(frozen=True)

    rationale: str = Field(..., min_length=1, max_length=1000)
    answer_key: str = Field(..., min_length=1, max_length=1000)


class InverseThinkingCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=3, max_length=200)
    alias: str | None = Field(default=None, max_length=120)
    target_concept: str = Field(..., min_length=1, max_length=300)
    foil: str = Field(..., min_length=1, max_length=300)
    disaster: str = Field(..., min_length=1, max_length=1000)
    key_clues: list[str] = Field(..., min_length=1, max_length=8)
    safe_zone: str = Field(..., min_length=1, max_length=1000)
    filing_note: str = Field(..., min_length=1, max_length=1000)
    student_task: str = Field(..., min_length=1, max_length=1000)
    teacher_only: InverseThinkingTeacherOnly

    @field_validator(
        "title",
        "alias",
        "target_concept",
        "foil",
        "disaster",
        "safe_zone",
        "filing_note",
        "student_task",
    )
    @classmethod
    def _student_text_has_no_teacher_only_markers(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _reject_teacher_only_markers(value)

    @field_validator("key_clues")
    @classmethod
    def _clues_have_no_teacher_only_markers(cls, value: list[str]) -> list[str]:
        return [_reject_teacher_only_markers(clue) for clue in value]


class InverseThinkingSummaryRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str = Field(..., min_length=1, max_length=120)
    trap: str = Field(..., min_length=1, max_length=300)
    clue: str = Field(..., min_length=1, max_length=300)
    safe_rule: str = Field(..., min_length=1, max_length=500)


class InverseThinkingStudentChallenge(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, max_length=120)
    prompt: str = Field(..., min_length=1, max_length=1000)
    case_id: str = Field(..., min_length=1, max_length=120)

    @field_validator("prompt")
    @classmethod
    def _prompt_has_no_teacher_only_markers(cls, value: str) -> str:
        return _reject_teacher_only_markers(value)


class InverseThinkingPack(BaseModel):
    model_config = ConfigDict(frozen=True)

    methodology: Literal["inverse_thinking"]
    creative_frame: CreativeFrame
    cases: list[InverseThinkingCase] = Field(..., min_length=1)
    summary_table: list[InverseThinkingSummaryRow] = Field(..., min_length=1)
    student_challenges: list[InverseThinkingStudentChallenge] = Field(..., min_length=1)
    teacher_only: InverseThinkingTeacherOnly
    projection_hints: dict[str, list[str]] = Field(default_factory=dict)
