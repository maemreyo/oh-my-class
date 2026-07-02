"""Artifact content Pydantic models — output contract for the Content Creator Agent.

Defines the schema for generated teaching pack artifacts (lesson, worksheet, quiz,
drill, recap, infographic). Content Creator returns JSON matching this schema;
the template renderer consumes it.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, model_validator

from common.contracts.components import ContentComponent

_component_ta = TypeAdapter(ContentComponent)


class Flashcard(BaseModel):
    """A single flashcard with front, back, and optional hint."""

    id: str = Field(..., min_length=1)
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)
    hint: str | None = None


class FlashcardDeckData(BaseModel):
    """Structured data for a flashcard_deck artifact.

    Mirrors the TypeScript FlashcardDeckData contract in
    packages/renderer/src/contracts/flashcard_deck.ts.
    Cards are stored in ArtifactContent.sections[].cards so that the
    ArtifactContent Pydantic model (which requires ``sections``) stays valid;
    subject/gradeLevel go in ArtifactContent.metadata.
    """

    title: str = Field(..., min_length=3, max_length=200)
    subject: str = Field(..., min_length=1)
    gradeLevel: str = Field(..., min_length=1)
    cards: list[Flashcard] = Field(default_factory=list)
    theme: str | None = None
    lang: str | None = None


class ArtifactContent(BaseModel):
    """A single artifact within a teaching pack.

    The Content Creator Agent produces JSON conforming to this schema.
    The template renderer consumes it to produce standalone HTML.
    """

    artifact_type: Literal[
        "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
        "answer_key", "roadmap", "flashcard_deck",
    ]
    theme: str = Field(default="default", description="Visual theme name")
    title: str = Field(..., min_length=3, max_length=200)
    sections: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of content sections; structure varies by artifact_type",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata (duration, difficulty, etc.)",
    )
    accessibility: dict[str, Any] = Field(
        default_factory=dict,
        description="Language, reading_level, alt_texts, etc.",
    )

    @model_validator(mode="after")
    def _validate_components(self) -> ArtifactContent:
        """Validate typed component dicts inside section ``components`` lists.

        Only dicts with a ``type`` field are validated against the
        ``ContentComponent`` discriminated union. Invalid typed components
        fail closed so unknown LLM-emitted component shapes cannot silently
        pass into renderer templates.
        """
        for s_idx, section in enumerate(self.sections):
            components = section.get("components")
            if not isinstance(components, list):
                continue
            cleaned: list[dict[str, Any]] = []
            for c_idx, entry in enumerate(components):
                if not isinstance(entry, dict):
                    cleaned.append(entry)
                    continue
                if "type" not in entry:
                    cleaned.append(entry)
                    continue
                try:
                    _component_ta.validate_python(entry)
                    cleaned.append(entry)
                except ValidationError as exc:
                    raise ValueError(
                        f"sections[{s_idx}].components[{c_idx}] invalid component: {exc}",
                    ) from exc
            section["components"] = cleaned
        return self


class TeachingPack(BaseModel):
    """A complete teaching pack containing one or more artifacts."""

    run_id: str = Field(..., description="Pipeline run identifier")
    artifacts: list[ArtifactContent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
