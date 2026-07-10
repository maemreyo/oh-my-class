"""V2 canonical artifact envelope for typed, versioned teaching content."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ArtifactDocumentType = Literal[
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "infographic",
    "answer_key",
    "roadmap",
    "flashcard_deck",
    "slide_deck",
    "exit_ticket",
    "reading_passage",
]
DocumentAudience = Literal["student", "teacher", "print"]
DocumentAuthority = Literal["generated", "teacher_edit", "ai_assisted_edit", "restored"]
DocumentLanguage = Literal["en", "vi"]


class HeadingBlock(BaseModel):
    """A stable heading in a block document."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    block_kind: Literal["heading"] = "heading"
    level: Literal[1, 2, 3, 4]
    text: str = Field(min_length=1, max_length=2_000)


class ParagraphBlock(BaseModel):
    """A stable paragraph in a block document."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    block_kind: Literal["paragraph"] = "paragraph"
    text: str = Field(min_length=1, max_length=10_000)


DocumentBlock = Annotated[HeadingBlock | ParagraphBlock, Field(discriminator="block_kind")]


class DocumentSection(BaseModel):
    """An ordered stable section of a block document."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    blocks: list[DocumentBlock] = Field(min_length=1)


class BlockDocument(BaseModel):
    """Typed payload for lesson-like and synthesis artifact surfaces."""

    model_config = ConfigDict(frozen=True)

    payload_kind: Literal["block_document"] = "block_document"
    sections: list[DocumentSection] = Field(min_length=1)


class AssessmentOption(BaseModel):
    """A student-safe assessment option with stable identity."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=2_000)


class AssessmentQuestion(BaseModel):
    """A student-safe question that deliberately excludes answer data."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=10_000)
    options: list[AssessmentOption] = Field(default_factory=list)


class AssessmentDocument(BaseModel):
    """Typed student-safe payload for question-bearing artifacts."""

    model_config = ConfigDict(frozen=True)

    payload_kind: Literal["assessment_document"] = "assessment_document"
    questions: list[AssessmentQuestion] = Field(min_length=1)


ArtifactPayload = Annotated[
    BlockDocument | AssessmentDocument,
    Field(discriminator="payload_kind"),
]


class ArtifactDocument(BaseModel):
    """Immutable V2 teaching artifact with an explicitly typed payload."""

    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1, max_length=80)
    artifact_id: str = Field(min_length=1, max_length=80)
    artifact_type: ArtifactDocumentType
    version: int = Field(ge=1)
    language: DocumentLanguage
    audience: DocumentAudience
    authority: DocumentAuthority
    payload: ArtifactPayload
    parent_document_id: str | None = Field(default=None, min_length=1, max_length=80)
    source_document_id: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def _payload_matches_artifact_type(self) -> ArtifactDocument:
        assessment_types = frozenset({"quiz", "drill", "exit_ticket"})
        if self.artifact_type in assessment_types and self.payload.payload_kind != "assessment_document":
            msg = f"{self.artifact_type} requires an assessment_document payload"
            raise ValueError(msg)
        if self.artifact_type not in assessment_types and self.payload.payload_kind != "block_document":
            msg = f"{self.artifact_type} requires a block_document payload"
            raise ValueError(msg)
        return self
