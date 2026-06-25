"""AnswerKeyContent model — typed artifact for detailed answer keys.

Produced by the Content Creator Agent when artifact_type == "answer_key".
Consumed by the renderer's answer_key.eta template.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from common.contracts.components import ContentComponent  # noqa: TC001


class AnswerKeyMetadata(BaseModel):
    total_questions: int = 0
    groups: dict[str, dict[str, str]] = Field(default_factory=dict)


class AnswerKeySection(BaseModel):
    id: str
    title: str
    sub: str | None = None
    range: str | None = None
    group: str = "a"
    instruction: str | None = None
    summary: str | None = None
    components: list[ContentComponent] = Field(default_factory=list)


class AnswerKeyContent(BaseModel):
    artifact_type: Literal["answer_key"] = "answer_key"
    title: str
    theme: str = "default"
    sections: list[AnswerKeySection] = Field(default_factory=list)
    metadata: AnswerKeyMetadata = Field(default_factory=AnswerKeyMetadata)
    accessibility: dict[str, Any] = Field(default_factory=lambda: {"language": "vi"})
