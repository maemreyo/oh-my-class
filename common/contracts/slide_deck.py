"""Canonical slide deck contract for native slide_deck artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator

from common.contracts.artifact_workflow import CoreArtifactType
from common.contracts.media_asset import is_remote_source

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping


SlideLayout = Literal[
    # Existing production layouts (SDE-01 deterministic generator).
    "title", "content", "question", "activity", "summary",
    # ADR-041 target vocabulary (SDE-02): declared now so the schema is
    # honest immediately; renderer template support ships incrementally.
    # Any layout without a renderer template fails closed at render time
    # instead of silently falling back to a different layout — see
    # `RENDERER_SUPPORTED_SLIDE_LAYOUTS` in packages/renderer.
    "cover", "agenda", "objective", "hook", "concept", "definition",
    "comparison", "timeline", "process", "diagram", "worked_example",
    "guided_practice", "independent_practice", "discussion", "poll",
    "quiz_check", "reflection", "exit_ticket", "homework", "appendix",
]
# ADR-045: pedagogical role is a slide's teaching purpose (hook, explain,
# practice, ...), kept separate from `SlideLayout` (its visual shape). The
# first six values are the required deck-spine roles; the rest cover
# optional extensions beyond the spine. See
# `packages.agents.slide_deck_engine.deck_shape.assign_pedagogical_roles` for
# how a slide's role is derived from its `slide_id` convention, reusing the
# same spine classification SDH-06 built for deck-shape/budget checks.
PedagogicalRole = Literal[
    "hook", "objective", "explain", "model", "guided_practice",
    "check_understanding", "independent_practice", "recap", "exit_ticket",
]
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

# ADR-043: display preferences are slide-deck-specific and never LLM-authored.
SlideDeckDisplaySurface = Literal["presentation", "student", "teacher", "print", "review"]
SlideDeckPrintLayout = Literal["paged", "continuous"]
SlideDeckSlidesPerPage = Literal[1, 2, 4, 6]
SlideDeckChromeVisibility = Literal["hidden", "minimal", "branded"]


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
        if self.tier == "packaged" and is_remote_source(self.source):
            msg = "packaged media must not use unmanaged external URLs"
            raise ValueError(msg)
        if self.tier == "online_optional" and not self.requires_network:
            msg = "online_optional media must set requires_network"
            raise ValueError(msg)
        if self.tier == "online_optional" and not self.fallback_text:
            msg = "online_optional media requires fallback_text"
            raise ValueError(msg)
        return self


# ADR-045 (SDTF-03): related-artifact references are pointers, not embedded
# content. This reuses the CoreArtifactType/artifact_id join-key convention
# from common.contracts.artifact_workflow (the same vocabulary the artifact
# generation pipeline already uses) rather than inventing a new ID scheme,
# extended with "objective"/"checkpoint" for semantic targets that don't
# have their own generated-artifact workflow entry.
SlideDeckRelatedArtifactType = Literal[CoreArtifactType, "objective", "checkpoint"]


class SlideDeckRelatedArtifactRef(BaseModel):
    """A slide/block pointer to another teaching-pack artifact or objective
    generated in the same run -- never the artifact's content or answer key.

    ``relationship_label`` is the only field safe to show students (e.g.
    "See Worksheet 2"); ``artifact_type``/``artifact_id`` are teacher-preview
    planning context only. Existence of the referenced ``artifact_id`` is
    deliberately NOT validated here -- a deck must construct and export
    standalone even when the referenced artifact hasn't been generated (yet)
    or belongs to a run assembled independently. Use
    ``resolve_slide_deck_related_refs`` to check resolution for teacher
    preview without ever blocking export.
    """

    model_config = ConfigDict(frozen=True)

    artifact_type: SlideDeckRelatedArtifactType
    artifact_id: str = Field(min_length=1, max_length=80)
    relationship_label: str = Field(min_length=1, max_length=200)


class SlideDeckRelatedArtifactStatus(BaseModel):
    """Teacher-preview resolution of one related ref against a run's known
    artifact IDs. ``resolved=False`` never blocks deck export or standalone
    rendering -- it only tells teacher preview the target isn't available."""

    model_config = ConfigDict(frozen=True)

    ref: SlideDeckRelatedArtifactRef
    resolved: bool


def resolve_slide_deck_related_refs(
    refs: list[SlideDeckRelatedArtifactRef],
    known_artifact_ids: Collection[str],
) -> list[SlideDeckRelatedArtifactStatus]:
    """Resolve related refs against a run's artifact list for teacher
    preview context. Never raises: an unresolvable ``artifact_id`` degrades
    to ``resolved=False`` so a standalone or partial export is unaffected.
    """
    known = set(known_artifact_ids)
    return [SlideDeckRelatedArtifactStatus(ref=ref, resolved=ref.artifact_id in known) for ref in refs]


class SlideDeckBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    block_id: str = Field(min_length=1, max_length=80)
    block_type: SlideBlockType
    body: str = Field(min_length=1, max_length=2000)
    source_ref_ids: list[str] = Field(default_factory=list)
    media: SlideDeckMedia | None = None
    related_refs: list[SlideDeckRelatedArtifactRef] = Field(default_factory=list)


class SlideDeckTeacherOnly(BaseModel):
    model_config = ConfigDict(frozen=True)

    facilitation_notes: list[str] = Field(default_factory=list)
    answer_key_notes: list[str] = Field(default_factory=list)


# ADR-045 (SDTF-05): a scaffold/stretch suggestion for mixed-ability
# classrooms -- teacher-only planning guidance, deliberately separate from
# `SlideDeckTeacherOnly.answer_key_notes` (this is "how to adapt the
# activity", not "what the correct answer is"). `level` is a free string
# rather than a `Literal["scaffold", "stretch"]` so a future group/level
# variant (e.g. "esl_support", "advanced_group_a") is just another list item,
# never a breaking schema change. This slice only ever populates "scaffold"
# and "stretch" -- see `SLIDE_DECK_DIFFERENTIATION_LEVELS`.
class SlideDeckDifferentiationNote(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: str = Field(min_length=1, max_length=40)
    guidance: str = Field(min_length=1, max_length=1000)


# Known levels this slice produces -- documentation/test convenience only,
# not a validation constraint (see `SlideDeckDifferentiationNote.level`).
SLIDE_DECK_DIFFERENTIATION_LEVELS = ("scaffold", "stretch")


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
    # ADR-045: engine-assigned teaching purpose and planned pacing, both
    # optional so decks generated before this landed keep validating.
    pedagogical_role: PedagogicalRole | None = None
    planned_duration_minutes: float | None = Field(default=None, ge=0, le=180)
    related_refs: list[SlideDeckRelatedArtifactRef] = Field(default_factory=list)
    # ADR-045 (SDTF-05): teacher-only scaffold/stretch guidance for mixed-
    # ability classrooms. Never a source of student-path branching in this
    # slice -- see `SlideDeckDifferentiationNote` and the renderer
    # projection, which strips this list on every student-safe surface.
    differentiation_guidance: list[SlideDeckDifferentiationNote] = Field(default_factory=list)

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


class SlideDeckDisplayPreferences(BaseModel):
    """Typed, slide-deck-specific display preferences (ADR-043).

    Covers surface, print layout, slides-per-page, and chrome visibility.
    Strict Literal fields reject invalid values at construction time. The
    LLM never populates this model — it is owned by the app, gateway
    preview/export routes, and standalone HTML. Use
    ``resolve_slide_deck_display_preferences`` to safely coerce
    untrusted/partial input (old artifacts, query/hash/localStorage
    overrides) instead of raising.
    """

    model_config = ConfigDict(frozen=True)

    surface: SlideDeckDisplaySurface = "presentation"
    print_layout: SlideDeckPrintLayout = "paged"
    slides_per_page: SlideDeckSlidesPerPage = 1
    chrome: SlideDeckChromeVisibility = "hidden"


_DEFAULT_SLIDE_DECK_DISPLAY_PREFERENCES = SlideDeckDisplayPreferences()
_SLIDE_DECK_DISPLAY_PREFERENCE_FIELD_ADAPTERS: dict[str, TypeAdapter[object]] = {
    "surface": TypeAdapter(SlideDeckDisplaySurface),
    "print_layout": TypeAdapter(SlideDeckPrintLayout),
    "slides_per_page": TypeAdapter(SlideDeckSlidesPerPage),
    "chrome": TypeAdapter(SlideDeckChromeVisibility),
}


def resolve_slide_deck_display_preferences(
    raw: Mapping[str, object] | None,
) -> SlideDeckDisplayPreferences:
    """Resolve effective display preferences from untrusted/partial input.

    Missing fields and invalid values fall back to the production-safe
    default *for that field only*, so one bad value (or an old artifact
    with no preference fields at all) never breaks rendering.
    """
    if not raw:
        return _DEFAULT_SLIDE_DECK_DISPLAY_PREFERENCES

    resolved: dict[str, object] = {}
    for field_name, adapter in _SLIDE_DECK_DISPLAY_PREFERENCE_FIELD_ADAPTERS.items():
        default = getattr(_DEFAULT_SLIDE_DECK_DISPLAY_PREFERENCES, field_name)
        if field_name not in raw:
            resolved[field_name] = default
            continue
        try:
            resolved[field_name] = adapter.validate_python(raw[field_name])
        except ValidationError:
            resolved[field_name] = default
    return SlideDeckDisplayPreferences(**resolved)


# ADR-045 decision 10: future manual edits are structured patches or
# regeneration targets -- never arbitrary HTML/CSS/JS. Any future edit
# request model (SDE-04..06) should type its authority field against this
# Literal instead of accepting freeform markup.
SlideDeckManualEditAuthority = Literal["structured_patch", "regeneration_target"]


class SlideDeckAnnotationOverlay(BaseModel):
    """ADR-045 decision 9: a teacher annotation over an immutable snapshot.

    Overlays attach to a generated snapshot by ID plus stable slide/block
    IDs -- they never mutate the snapshot's ``content_json``/rendered HTML.
    ``teacher_only`` defaults ``True``; showing an annotation to students
    requires an explicit future live-session action, not a change to this
    default. This is a foundation-level type only -- there is no overlay
    storage, live annotation UI, or student-visibility toggle yet
    (SDE-04..06 build that runtime).
    """

    model_config = ConfigDict(frozen=True)

    target_slide_id: str = Field(min_length=1, max_length=80)
    target_block_id: str | None = Field(default=None, min_length=1, max_length=80)
    created_from_snapshot_id: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=2000)
    teacher_only: bool = True


class SlideDeckSnapshotLineage(BaseModel):
    """ADR-045 decisions 2 & 15: remix derives a new snapshot, it never
    rewrites an existing one.

    ``remix_of_snapshot_id`` is ``None`` for an original generation and set
    to the parent snapshot's ID for a remix ("make easier", "reuse slides
    3-5", ...). This is deliberately a separate model/namespace from
    ``SlideDeckDisplayPreferences``: a display/export choice (surface,
    print layout, slides-per-page, chrome) never creates a content version
    and must never be read as lineage, and lineage must never be read as a
    display preference. There is no remix API or patch-application engine
    yet -- SDE-04..06 build that runtime.
    """

    model_config = ConfigDict(frozen=True)

    remix_of_snapshot_id: str | None = Field(default=None, min_length=1, max_length=120)

    @property
    def requires_revalidation(self) -> bool:
        """ADR-045 decision 16: a remixed snapshot must re-run quality and
        projection gates before export/share. Documents the requirement for
        the future SDE-04+ implementation; nothing calls this yet."""
        return self.remix_of_snapshot_id is not None


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
    display_preferences: SlideDeckDisplayPreferences | None = None
    # SDX-01: a translated deck is a remix (1:1 text substitution, no
    # structural change) of its source deck's snapshot -- reuses SDTF-06's
    # lineage model instead of inventing a parallel "translated_from" field.
    # None for an original (non-derived) deck.
    lineage: SlideDeckSnapshotLineage | None = None

    @property
    def total_planned_duration_minutes(self) -> float | None:
        """ADR-045: rollup of `SlideDeckSlide.planned_duration_minutes`.

        `None` when no slide carries a planned duration yet (older decks, or
        one the engine hasn't pacing-annotated) rather than a misleading 0.
        """
        minutes = [slide.planned_duration_minutes for slide in self.slides if slide.planned_duration_minutes is not None]
        return round(sum(minutes), 1) if minutes else None

    @model_validator(mode="after")
    def _slide_ids_are_unique(self) -> SlideDeckData:
        slide_ids = [slide.slide_id for slide in self.slides]
        if len(slide_ids) != len(set(slide_ids)):
            msg = "duplicate slide_id in slide deck"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _block_ids_are_unique_across_deck(self) -> SlideDeckData:
        # ADR-045: block IDs are future teaching-session join points, so they
        # must be unique deck-wide, not just within their own slide.
        block_ids = [block.block_id for slide in self.slides for block in slide.blocks]
        if len(block_ids) != len(set(block_ids)):
            msg = "duplicate block_id across slide deck"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _interaction_ids_are_unique_across_deck(self) -> SlideDeckData:
        # ADR-045: interaction IDs are future teaching-session join points, so
        # a session can address one interaction unambiguously by ID alone.
        interaction_ids = [interaction.interaction_id for slide in self.slides for interaction in slide.interactions]
        if len(interaction_ids) != len(set(interaction_ids)):
            msg = "duplicate interaction_id across slide deck"
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
