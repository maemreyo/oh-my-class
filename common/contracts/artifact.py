"""Artifact content Pydantic models — output contract for the Content Creator Agent.

Defines the schema for generated teaching pack artifacts (lesson, worksheet, quiz,
drill, recap, infographic). Content Creator returns JSON matching this schema;
the template renderer consumes it.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ArtifactContent(BaseModel):
    """A single artifact within a teaching pack.

    The Content Creator Agent produces JSON conforming to this schema.
    The template renderer consumes it to produce standalone HTML.
    """

    artifact_type: Literal[
        "lesson", "worksheet", "quiz", "drill", "recap", "infographic"
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


class TeachingPack(BaseModel):
    """A complete teaching pack containing one or more artifacts."""

    run_id: str = Field(..., description="Pipeline run identifier")
    artifacts: list[ArtifactContent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
