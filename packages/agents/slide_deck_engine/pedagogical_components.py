"""SDTF-07: typed teaching-component vocabulary for slide decks (ADR-045 #14).

Maps each SDTF-02 `PedagogicalRole` to a small, typed teaching component --
expected student-facing content, teacher-only guidance, a density/
accessibility check, and the SDE-02 registry keys (layout/block/interaction)
it typically renders through. This constrains what a slide *is for* to a
validated shape instead of a freeform LLM slide pattern.

Alignment with the existing component-strategist system (ADR-035/039,
`common/contracts/component_strategy*.py`, gated behind
`FEATURE_COMPONENT_STRATEGIST_V1`): that system is a separate, data-driven
strategy planner for teaching-pack artifacts (quiz/lesson/worksheet). Its
`component_type` vocabulary (e.g. "vocab_cluster", "flow_step",
"question_list" -- see `common/component_strategy_knowledge/knowledge.yaml`)
names *renderer content shapes* for `packages/renderer`'s `ContentComponent`
union, and its `learning_move_id` vocabulary (e.g. "semantic_discrimination",
"concept_model_build") names Gagne-event-based pedagogical moves -- both are
open, data-driven strings validated against a knowledge index, not a closed
enum this module could import and extend.

Slide decks render through a completely different, already-existing registry
(SDE-02's `LAYOUT_REGISTRY`/`BLOCK_REGISTRY`/`INTERACTION_REGISTRY` in
`.registries`, keyed by `SlideLayout`/`SlideBlockType`/`SlideInteractionType`
Literals in `common.contracts.slide_deck`) -- not the renderer's
`ContentComponent` union. So this module cannot literally reuse a
component-strategist `component_type` string as a slide-deck component
without pretending the two renderer contracts are the same thing. Instead it
reuses this *repo's own* existing slide-deck vocabulary wherever one already
names the concept: `worked_example`, `guided_practice`,
`independent_practice`, `exit_ticket`, and `quiz_check` are already declared
`SlideLayout` values (`registries.py` `_ADR_041_DECLARED_LAYOUTS`, ADR-045
decision #14's own wording), and `think_pair_share`/`exit_ticket` are already
`INTERACTION_REGISTRY` entries -- this module keys components to those exact
names rather than inventing synonyms. Only "vocabulary_scaffold" and
"misconception_check" are new strings, for the two ADR-045-named concepts
(vocabulary scaffold, misconception check) that have no existing slide-deck
or component-strategist token. `test_pedagogical_components.py` asserts this
vocabulary is disjoint from the component-strategist knowledge base's
`component_type`/`learning_move_id` strings -- no silent collision, no
competing registry.

LLM generation is already constrained to a validated shape by
`content_materialization_llm.py`'s `SlideDeckWordingResponse` (exactly 10
named fields, schema-bound via pydantic) -- e.g. `vocabulary_body`/
`vocabulary_practice_body` back the `vocabulary_scaffold` component,
`example_body`/`sentence_stem` back `worked_example`, `check_prompt`/
`practice_correct_option`/`practice_distractor_a`/`practice_distractor_b`/
`teacher_rationale` back `guided_practice`, and `exit_prompt` backs
`exit_ticket` (see `content_materialization.py`'s per-slide builders). This
module's component vocabulary maps onto that existing constraint rather
than adding a second LLM-schema mechanism.
"""

from __future__ import annotations

from typing import Final, NamedTuple

from common.contracts.slide_deck import PedagogicalRole, SlideDeckData, SlideDeckSlide
from packages.agents.slide_deck_engine.deck_shape import (
    SPINE_ROLES,
    PurposeDensityRule,
    assign_pedagogical_roles,
    role_density_rule,
)
from packages.agents.slide_deck_engine.models import (
    SlideDeckHealingScope,
    SlideDeckValidationCode,
    SlideDeckValidationReport,
)
from packages.agents.slide_deck_engine.registries import (
    BLOCK_REGISTRY,
    INTERACTION_REGISTRY,
    LAYOUT_REGISTRY,
)


class TeachingComponent(NamedTuple):
    component_id: str
    student_content: str
    teacher_guidance: str
    layout_keys: tuple[str, ...]
    block_keys: tuple[str, ...]
    interaction_keys: tuple[str, ...] = ()


# One entry per SDTF-02 `PedagogicalRole` value -- deliberately small (9
# entries) rather than a second, larger taxonomy. `layout_keys`/`block_keys`/
# `interaction_keys` list every SDE-02 registry key the deterministic v1
# generator (`content_materialization.py`) actually emits for that role,
# plus the matching ADR-041-declared key so a future generator that adopts
# the fuller layout vocabulary still passes `evaluate_component_completeness`.
SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT: Final[dict[PedagogicalRole, TeachingComponent]] = {
    "hook": TeachingComponent(
        component_id="hook",
        student_content="An engaging question, scenario, or image that introduces the topic -- no answer key.",
        teacher_guidance="Suggested delivery: invite students to share what they already know before revealing the goal.",
        layout_keys=("title", "hook"),
        block_keys=("heading", "image", "paragraph"),
    ),
    "objective": TeachingComponent(
        component_id="objective",
        student_content="An explicit, student-facing 'I can...' learning goal statement.",
        teacher_guidance="Note curriculum/standard alignment for this goal; read it aloud and have students paraphrase it.",
        layout_keys=("content", "objective"),
        block_keys=("callout", "paragraph", "heading"),
    ),
    "explain": TeachingComponent(
        component_id="vocabulary_scaffold",
        student_content="Key term(s), a plain-language definition, and a concrete example each.",
        teacher_guidance="Flag common student mis-readings of the term(s) and model pronunciation/usage.",
        layout_keys=("content", "concept", "definition"),
        block_keys=("paragraph", "callout", "heading"),
    ),
    "model": TeachingComponent(
        component_id="worked_example",
        student_content="A fully worked, step-by-step example of the skill, plus a sentence stem or scaffold to imitate it.",
        teacher_guidance="Think-aloud script: narrate the reasoning while filling the stem, don't just show the result.",
        layout_keys=("activity", "worked_example"),
        block_keys=("paragraph", "callout", "diagram"),
    ),
    "guided_practice": TeachingComponent(
        component_id="guided_practice",
        student_content="A practice prompt structurally similar to the worked example, with visible hint/options.",
        teacher_guidance="Expected answer plus common wrong answers, kept teacher-only; ask students to justify before revealing.",
        layout_keys=("question", "guided_practice"),
        block_keys=("interaction_prompt", "paragraph"),
        interaction_keys=("quick_check", "short_answer", "think_pair_share"),
    ),
    "check_understanding": TeachingComponent(
        component_id="misconception_check",
        student_content="A diagnostic question with distractors that each target a specific, named misconception.",
        teacher_guidance="Teacher-only map of each wrong option to the misconception it reveals, plus a remediation prompt.",
        layout_keys=("quiz_check", "question"),
        block_keys=("interaction_prompt",),
        interaction_keys=("quick_check", "multiple_choice_single"),
    ),
    "independent_practice": TeachingComponent(
        component_id="independent_practice",
        student_content="A practice prompt without embedded hints/scaffolds, for students to attempt solo.",
        teacher_guidance="Answer key plus an extension task for early finishers, kept teacher-only.",
        layout_keys=("independent_practice", "activity"),
        block_keys=("interaction_prompt", "paragraph"),
        interaction_keys=("short_answer", "discussion_prompt"),
    ),
    "recap": TeachingComponent(
        component_id="recap",
        student_content="2-3 key takeaway bullets or a self-check question covering the lesson.",
        teacher_guidance="Elicit the recap from the class with questions rather than restating it yourself.",
        layout_keys=("reflection", "summary"),
        block_keys=("heading", "paragraph", "callout"),
        interaction_keys=("discussion_prompt",),
    ),
    "exit_ticket": TeachingComponent(
        component_id="exit_ticket",
        student_content="A short reflective or assessment prompt students respond to at lesson end.",
        teacher_guidance="How to collect/review responses before next class; v1 does not persist student responses (ADR-045 #3/#11).",
        layout_keys=("summary", "exit_ticket"),
        block_keys=("interaction_prompt", "paragraph"),
        interaction_keys=("exit_ticket", "short_answer"),
    ),
}


def component_density_rule(role: PedagogicalRole) -> PurposeDensityRule:
    """A component's density/accessibility budget -- reuses SDH-06's
    per-role thresholds (`deck_shape.role_density_rule`) rather than
    duplicating the numbers here."""
    return role_density_rule(role)


def component_accessibility_requirements(component: TeachingComponent) -> tuple[str, ...]:
    """Accessibility requirements for a component, pulled from the SDE-02
    registry entries its renderer needs point at (already-declared
    `accessibility_requirement`/`requires_alt_text` fields) -- not a second
    set of accessibility rules."""
    requirements: list[str] = []
    for key in component.layout_keys:
        entry = LAYOUT_REGISTRY.entries.get(key)
        if entry is not None and entry.requires_alt_text:
            requirements.append(f"layout '{key}' requires alt text")
    for key in component.block_keys:
        entry = BLOCK_REGISTRY.entries.get(key)
        if entry is not None and entry.requires_alt_text:
            requirements.append(f"block '{key}' requires alt text")
    for key in component.interaction_keys:
        entry = INTERACTION_REGISTRY.entries.get(key)
        if entry is not None:
            requirements.append(entry.accessibility_requirement)
    return tuple(dict.fromkeys(requirements))


def evaluate_component_completeness(deck: SlideDeckData) -> SlideDeckValidationReport:
    """Quality gate: every required-spine role has a validated component,
    and each spine/optional slide actually uses its component's renderer
    needs (layout, block type, or -- when the role's density rule requires
    it -- interaction type)."""
    roles = assign_pedagogical_roles(deck)
    assigned = {role for role in roles if role is not None}
    missing = [role for role in SPINE_ROLES if role not in assigned]
    if missing:
        return _failed(
            "component_coverage_gap",
            f"Deck is missing a mapped teaching component for required role(s): {', '.join(missing)}.",
            "deck",
        )
    for slide, role in zip(deck.slides, roles, strict=True):
        if role is None:
            continue
        component = SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT[role]
        if not _slide_matches_component(slide, component):
            return _failed(
                "component_coverage_gap",
                f"Slide '{slide.slide_id}' does not use its '{component.component_id}' component's renderer needs (role={role}).",
                "slide",
            )
    return _passed("component_coverage_ok", "Every assigned slide uses its pedagogical component's renderer needs.", "deck")


def _slide_matches_component(slide: SlideDeckSlide, component: TeachingComponent) -> bool:
    if slide.layout in component.layout_keys:
        return True
    if any(block.block_type in component.block_keys for block in slide.blocks):
        return True
    return bool(component.interaction_keys) and any(
        interaction.interaction_type in component.interaction_keys for interaction in slide.interactions
    )


def _failed(code: SlideDeckValidationCode, message: str, scope: SlideDeckHealingScope) -> SlideDeckValidationReport:
    return SlideDeckValidationReport(phase="pedagogical_components", passed=False, code=code, message=message, scope=scope)


def _passed(code: SlideDeckValidationCode, message: str, scope: SlideDeckHealingScope) -> SlideDeckValidationReport:
    return SlideDeckValidationReport(phase="pedagogical_components", passed=True, code=code, message=message, scope=scope)
