"""V2 canonical artifact envelope for typed, versioned teaching content."""

from __future__ import annotations

from typing import Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError


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
DocumentAuthority = Literal[
    "generated", "teacher_edit", "ai_assisted_edit", "restored", "translated", "variant_generated",
]
DocumentLanguage = Literal["en", "vi"]


class DocumentBlock(BaseModel):
    """A stable block with a validated heading or paragraph shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entity_id: str = Field(min_length=1, max_length=80)
    block_kind: Literal["heading", "paragraph"]
    text: str = Field(min_length=1, max_length=10_000)
    level: Literal[1, 2, 3, 4] | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> DocumentBlock:
        match self.block_kind:
            case "heading":
                if self.level is None:
                    raise PydanticCustomError(
                        "heading_level_required",
                        "heading blocks require level",
                    )
            case "paragraph":
                if self.level is not None:
                    raise PydanticCustomError(
                        "paragraph_level_forbidden",
                        "paragraph blocks must not set level",
                    )
            case unreachable:
                assert_never(unreachable)
        return self


class DocumentSection(BaseModel):
    """An ordered stable section of a block document."""

    model_config = ConfigDict(frozen=True)

    entity_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    blocks: list[DocumentBlock] = Field(min_length=1)


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


class ArtifactPayload(BaseModel):
    """A strict block or assessment payload selected by payload_kind."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    payload_kind: Literal["block_document", "assessment_document"]
    sections: list[DocumentSection] | None = None
    questions: list[AssessmentQuestion] | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> ArtifactPayload:
        match self.payload_kind:
            case "block_document":
                if not self.sections or self.questions is not None:
                    raise PydanticCustomError(
                        "block_document_shape_invalid",
                        "block_document requires sections and forbids questions",
                    )
            case "assessment_document":
                if not self.questions or self.sections is not None:
                    raise PydanticCustomError(
                        "assessment_document_shape_invalid",
                        "assessment_document requires questions and forbids sections",
                    )
            case unreachable:
                assert_never(unreachable)
        return self


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
            raise PydanticCustomError("artifact_payload_mismatch", msg)
        if self.artifact_type not in assessment_types and self.payload.payload_kind != "block_document":
            msg = f"{self.artifact_type} requires a block_document payload"
            raise PydanticCustomError("artifact_payload_mismatch", msg)
        return self
