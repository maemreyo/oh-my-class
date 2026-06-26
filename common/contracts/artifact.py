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


class ArtifactContent(BaseModel):
    """A single artifact within a teaching pack.

    The Content Creator Agent produces JSON conforming to this schema.
    The template renderer consumes it to produce standalone HTML.
    """

    artifact_type: Literal[
        "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
        "answer_key", "roadmap",
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
        ``ContentComponent`` discriminated union.  Missing ``components``,
        non-list values, and non-dict entries are silently skipped.
        """
        for s_idx, section in enumerate(self.sections):
            components = section.get("components")
            if not isinstance(components, list):
                continue
            for c_idx, entry in enumerate(components):
                if not isinstance(entry, dict):
                    continue
                if "type" not in entry:
                    continue
                try:
                    _component_ta.validate_python(entry)
                except ValidationError as exc:
                    raise ValueError(
                        f"sections[{s_idx}].components[{c_idx}] "
                        f"(type={entry.get('type')!r}): {exc}"
                    ) from exc
        return self


class TeachingPack(BaseModel):
    """A complete teaching pack containing one or more artifacts."""

    run_id: str = Field(..., description="Pipeline run identifier")
    artifacts: list[ArtifactContent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
