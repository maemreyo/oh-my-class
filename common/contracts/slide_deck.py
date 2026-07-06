"""Canonical slide deck contract for native slide_deck artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SlideLayout = Literal["title", "content", "question", "activity", "summary"]
SlideBlockType = Literal[
    "heading",
    "paragraph",
    "image",
    "diagram",
    "callout",
    "interaction_prompt",
]
SlideInteractionType = Literal[
    "reveal",
    "quick_check",
    "multiple_choice_single",
    "multiple_choice_multiple",
    "true_false",
    "short_answer",
    "poll",
    "poll_prompt",
    "timer",
    "discussion_prompt",
    "exit_ticket",
    "think_pair_share",
]
SlideRevealPolicy = Literal["all_at_once", "progressive", "teacher_controlled"]
SlideSurfaceMode = Literal["presentation", "teacher_guide", "print"]
SlideExportFormat = Literal["html"]
SourceConfidence = Literal["verified", "modified", "uncertain"]
MediaType = Literal["image", "audio", "video", "diagram"]
MediaTier = Literal["packaged", "online_optional"]
TeacherOnlySeparation = Literal["teacher_only_projection"]


class SlideDeckSourceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    citation: str = Field(min_length=1, max_length=500)
    confidence: SourceConfidence


class SlideDeckSurface(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: SlideSurfaceMode
    export_format: SlideExportFormat


class SlideDeckSurfaces(BaseModel):
    model_config = ConfigDict(frozen=True)

    student: SlideDeckSurface
    teacher: SlideDeckSurface
    print: SlideDeckSurface


class SlideDeckProgression(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_index: int = Field(ge=1)
    reveal_policy: SlideRevealPolicy


class SlideDeckMedia(BaseModel):
    model_config = ConfigDict(frozen=True)

    media_id: str = Field(min_length=1, max_length=80)
    media_type: MediaType
    source: str = Field(min_length=1, max_length=500)
    tier: MediaTier
    alt_text: str = Field(min_length=1, max_length=500)
    fallback_text: str | None = Field(default=None, max_length=500)
    requires_network: bool = False

    @model_validator(mode="after")
    def _media_policy_fields_are_consistent(self) -> SlideDeckMedia:
        if self.tier == "packaged" and self.source.startswith(("http://", "https://")):
            msg = "packaged media must not use unmanaged external URLs"
            raise ValueError(msg)
        if self.tier == "online_optional" and not self.requires_network:
            msg = "online_optional media must set requires_network"
            raise ValueError(msg)
        if self.tier == "online_optional" and not self.fallback_text:
            msg = "online_optional media requires fallback_text"
            raise ValueError(msg)
        return self


class SlideDeckBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    block_id: str = Field(min_length=1, max_length=80)
    block_type: SlideBlockType
    body: str = Field(min_length=1, max_length=2000)
    source_ref_ids: list[str] = Field(default_factory=list)
    media: SlideDeckMedia | None = None


class SlideDeckTeacherOnly(BaseModel):
    model_config = ConfigDict(frozen=True)

    facilitation_notes: list[str] = Field(default_factory=list)
    answer_key_notes: list[str] = Field(default_factory=list)


class SlideDeckInteractionOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    option_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=500)


class SlideDeckInteractionTeacherOnly(BaseModel):
    model_config = ConfigDict(frozen=True)

    separation: TeacherOnlySeparation
    correct_option_ids: list[str] = Field(default_factory=list)
    acceptable_answers: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=1000)


class SlideDeckInteraction(BaseModel):
    model_config = ConfigDict(frozen=True)

    interaction_id: str = Field(min_length=1, max_length=80)
    interaction_type: SlideInteractionType
    prompt: str = Field(min_length=1, max_length=1000)
    answer_bearing: bool = False
    options: list[SlideDeckInteractionOption] = Field(default_factory=list)
    teacher_only: SlideDeckInteractionTeacherOnly | None = None
    no_js_fallback: str = Field(default="Use this prompt as an offline classroom discussion.", min_length=1, max_length=500)
    accessibility_label: str = Field(default="Slide interaction", min_length=1, max_length=200)

    @model_validator(mode="after")
    def _answer_bearing_interactions_use_teacher_projection(self) -> SlideDeckInteraction:
        if self.answer_bearing and self.teacher_only is None:
            msg = "answer-bearing interactions require teacher_only_projection metadata"
            raise ValueError(msg)
        return self


class SlideDeckSlide(BaseModel):
    model_config = ConfigDict(frozen=True)

    slide_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    layout: SlideLayout
    progression: SlideDeckProgression
    blocks: list[SlideDeckBlock] = Field(min_length=1)
    interactions: list[SlideDeckInteraction] = Field(default_factory=list)
    teacher_notes: SlideDeckTeacherOnly | None = None

    @model_validator(mode="after")
    def _block_ids_are_unique_within_slide(self) -> SlideDeckSlide:
        block_ids = [block.block_id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            msg = f"duplicate block_id in slide {self.slide_id}"
            raise ValueError(msg)
        return self


class SlideDeckAccessibility(BaseModel):
    model_config = ConfigDict(frozen=True)

    reading_level: str = Field(min_length=1, max_length=80)
    language: str = Field(min_length=2, max_length=32)
    alt_text_required: bool = True
    keyboard_navigation: bool = True


class SlideDeckMediaPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    default_tier: MediaTier
    online_optional_allowed: bool
    fallback_required: bool


class SlideDeckData(BaseModel):
    """Canonical data model for one native slide deck artifact."""

    model_config = ConfigDict(frozen=True)

    deck_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=3, max_length=200)
    locale: str = Field(min_length=2, max_length=16)
    theme: str = Field(default="default", min_length=1, max_length=80)
    surfaces: SlideDeckSurfaces
    source_refs: list[SlideDeckSourceRef] = Field(default_factory=list)
    slides: list[SlideDeckSlide] = Field(min_length=1)
    accessibility: SlideDeckAccessibility
    media_policy: SlideDeckMediaPolicy

    @model_validator(mode="after")
    def _slide_ids_are_unique(self) -> SlideDeckData:
        slide_ids = [slide.slide_id for slide in self.slides]
        if len(slide_ids) != len(set(slide_ids)):
            msg = "duplicate slide_id in slide deck"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _media_policy_matches_blocks(self) -> SlideDeckData:
        for slide in self.slides:
            for block in slide.blocks:
                media = block.media
                if media is None:
                    continue
                if self.media_policy.fallback_required and not media.fallback_text and media.tier == "online_optional":
                    msg = f"online media {media.media_id} requires fallback_text"
                    raise ValueError(msg)
                if media.tier == "online_optional" and not self.media_policy.online_optional_allowed:
                    msg = f"online media {media.media_id} is not allowed by media_policy"
                    raise ValueError(msg)
        return self
