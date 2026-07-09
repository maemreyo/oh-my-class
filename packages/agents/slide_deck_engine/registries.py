from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SurfaceName = Literal["presentation", "teacher_guide", "print"]
TeacherOnlyBehavior = Literal["none", "teacher_notes", "teacher_only_projection"]
InteractionSchemaKind = Literal["display", "choice", "free_response", "timer"]


class RegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1, max_length=80)
    supported_surfaces: list[SurfaceName]
    density_units: int = Field(ge=0)
    answer_bearing: bool = False
    requires_alt_text: bool = False
    print_behavior: str = Field(min_length=1, max_length=120)
    teacher_only_behavior: TeacherOnlyBehavior = "none"
    fallback_behavior: str = Field(min_length=1, max_length=120)
    schema_kind: InteractionSchemaKind = "display"
    no_js_fallback: str = Field(default="Render as static classroom prompt.", min_length=1, max_length=160)
    accessibility_requirement: str = Field(default="Keyboard-readable prompt text.", min_length=1, max_length=160)
    persists_student_response: bool = False


class Registry(BaseModel):
    model_config = ConfigDict(frozen=True)

    entries: dict[str, RegistryEntry]

    def get(self, key: str) -> RegistryEntry:
        return self.entries[key]


ALL_SURFACES: list[SurfaceName] = ["presentation", "teacher_guide", "print"]

# ADR-041 target layout vocabulary (SDE-02) beyond the 5 production layouts
# below. These are declared now so `SlideLayout` and the registry are honest
# about the full contract immediately; renderer template support ships
# incrementally. Every one of them degrades to the generic content layout
# for registry/healing purposes, but the renderer's own supported-layout
# allowlist fails closed rather than silently using that fallback.
_ADR_041_DECLARED_LAYOUTS: tuple[str, ...] = (
    "cover", "agenda", "objective", "hook", "concept", "definition",
    "comparison", "timeline", "process", "diagram", "worked_example",
    "guided_practice", "independent_practice", "discussion", "poll",
    "quiz_check", "reflection", "exit_ticket", "homework", "appendix",
)


def _declared_layout(key: str) -> RegistryEntry:
    return RegistryEntry(
        key=key,
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        print_behavior="print_as_body_sections",
        fallback_behavior="content_layout",
    )


LAYOUT_REGISTRY = Registry(entries={
    "title": RegistryEntry(
        key="title",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_as_heading",
        teacher_only_behavior="teacher_notes",
        fallback_behavior="content_layout",
    ),
    "question": RegistryEntry(
        key="question",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        print_behavior="print_question_block",
        teacher_only_behavior="teacher_only_projection",
        fallback_behavior="content_layout",
    ),
    # Bug fix (SDE-02): the deterministic v1 generator has always emitted
    # these three layouts (goal/vocabulary -> content, worked example ->
    # activity, exit ticket -> summary) but they were missing from this
    # registry, so `validate_registry_membership` silently failed on every
    # generated deck. `build_scorecard` never wires `invalid_layout` into a
    # scored dimension, so nothing surfaced the failure.
    "content": RegistryEntry(
        key="content",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        print_behavior="print_as_body_sections",
        teacher_only_behavior="teacher_notes",
        fallback_behavior="reduce_to_single_paragraph",
    ),
    "activity": RegistryEntry(
        key="activity",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        print_behavior="print_activity_steps",
        teacher_only_behavior="teacher_notes",
        fallback_behavior="content_layout",
    ),
    "summary": RegistryEntry(
        key="summary",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_summary_recap",
        teacher_only_behavior="teacher_notes",
        fallback_behavior="content_layout",
    ),
    **{key: _declared_layout(key) for key in _ADR_041_DECLARED_LAYOUTS},
})

BLOCK_REGISTRY = Registry(entries={
    "heading": RegistryEntry(
        key="heading",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_text",
        fallback_behavior="paragraph",
    ),
    "image": RegistryEntry(
        key="image",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        requires_alt_text=True,
        print_behavior="print_image_with_caption",
        fallback_behavior="alt_text_callout",
    ),
    "interaction_prompt": RegistryEntry(
        key="interaction_prompt",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_prompt",
        fallback_behavior="paragraph",
    ),
    # Bug fix (SDE-02): the deterministic v1 generator has always emitted
    # these three block types but they were missing from this registry —
    # same silent `validate_registry_membership` gap as the layouts above.
    "paragraph": RegistryEntry(
        key="paragraph",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_text",
        fallback_behavior="heading",
    ),
    "callout": RegistryEntry(
        key="callout",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_callout_box",
        fallback_behavior="paragraph",
    ),
    "diagram": RegistryEntry(
        key="diagram",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        requires_alt_text=True,
        print_behavior="print_diagram_with_caption",
        fallback_behavior="alt_text_callout",
    ),
})

INTERACTION_REGISTRY = Registry(entries={
    "reveal": RegistryEntry(
        key="reveal",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_revealed_content",
        fallback_behavior="show_all_content",
        schema_kind="display",
        no_js_fallback="Show all reveal content inline.",
        accessibility_requirement="Reveal state must be readable without motion.",
    ),
    "quick_check": RegistryEntry(
        key="quick_check",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        answer_bearing=True,
        print_behavior="print_options_without_answers",
        teacher_only_behavior="teacher_only_projection",
        fallback_behavior="short_answer_prompt",
        schema_kind="choice",
        no_js_fallback="Students answer verbally or on paper; no response is stored.",
        accessibility_requirement="Options must be visible text with teacher-only answer projection.",
    ),
    "multiple_choice_single": RegistryEntry(
        key="multiple_choice_single",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        answer_bearing=True,
        print_behavior="print_options_without_answers",
        teacher_only_behavior="teacher_only_projection",
        fallback_behavior="short_answer_prompt",
        schema_kind="choice",
        no_js_fallback="Students answer verbally or on paper; no response is stored.",
        accessibility_requirement="Options must be visible text with teacher-only answer projection.",
    ),
    "poll_prompt": RegistryEntry(
        key="poll_prompt",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_poll_prompt",
        fallback_behavior="show_of_hands_prompt",
        schema_kind="choice",
        no_js_fallback="Run as a show-of-hands poll; no response is stored.",
        accessibility_requirement="Poll choices must be readable aloud and on screen.",
    ),
    "timer": RegistryEntry(
        key="timer",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_duration_instruction",
        fallback_behavior="static_duration_label",
        schema_kind="timer",
        no_js_fallback="Display the timer duration as text.",
        accessibility_requirement="Timer duration must be present as text.",
    ),
    "discussion_prompt": RegistryEntry(
        key="discussion_prompt",
        supported_surfaces=ALL_SURFACES,
        density_units=1,
        print_behavior="print_discussion_prompt",
        fallback_behavior="static_discussion_prompt",
        schema_kind="free_response",
        no_js_fallback="Use as a whole-class discussion prompt.",
        accessibility_requirement="Prompt must not rely on color or timing alone.",
    ),
    "short_answer": RegistryEntry(
        key="short_answer",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        answer_bearing=True,
        print_behavior="print_short_answer_prompt",
        teacher_only_behavior="teacher_only_projection",
        fallback_behavior="paper_short_answer",
        schema_kind="free_response",
        no_js_fallback="Students write or say a short answer; no response is stored.",
        accessibility_requirement="Prompt must support a short written or spoken response with teacher-only acceptable answers.",
    ),
    "exit_ticket": RegistryEntry(
        key="exit_ticket",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        print_behavior="print_exit_ticket_lines",
        fallback_behavior="paper_exit_ticket",
        schema_kind="free_response",
        no_js_fallback="Students answer on paper; no response is stored.",
        accessibility_requirement="Prompt must support written response outside the browser.",
    ),
    "think_pair_share": RegistryEntry(
        key="think_pair_share",
        supported_surfaces=ALL_SURFACES,
        density_units=2,
        print_behavior="print_tps_steps",
        fallback_behavior="static_tps_steps",
        schema_kind="free_response",
        no_js_fallback="Run think, pair, and share as classroom steps.",
        accessibility_requirement="Each step must be visible as text.",
    ),
})
