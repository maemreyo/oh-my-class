from __future__ import annotations

from typing import get_args

import pytest

from common.contracts.component_strategy_knowledge import (
    DEFAULT_KNOWLEDGE_SOURCE_PATH,
    load_knowledge_source,
)
from common.contracts.slide_deck import PedagogicalRole
from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.deck_shape import SPINE_ROLES
from packages.agents.slide_deck_engine.pedagogical_components import (
    SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT,
    component_accessibility_requirements,
    component_density_rule,
    evaluate_component_completeness,
)
from packages.agents.slide_deck_engine.registries import (
    BLOCK_REGISTRY,
    INTERACTION_REGISTRY,
    LAYOUT_REGISTRY,
)


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-pedagogical-components",
        lesson_blueprint={
            "topic": "Equivalent fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [{"description": "Explain why two fractions are equivalent."}],
        },
        research_brief={"sources": [{"id": "src-fractions", "title": "Grade 5 Fractions Standard", "citation": "CCSS 5.NF.A"}]},
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )


async def _deck():
    return (await SlideDeckEngine().generate(_request())).deck


def test_every_pedagogical_role_has_a_component_mapping() -> None:
    assert set(SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT) == set(get_args(PedagogicalRole))


def test_required_spine_roles_are_all_mapped() -> None:
    for role in SPINE_ROLES:
        assert role in SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT


@pytest.mark.parametrize("role", list(SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT))
def test_component_definitions_have_all_four_required_aspects(role: PedagogicalRole) -> None:
    component = SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT[role]

    assert component.student_content.strip()
    assert component.teacher_guidance.strip()
    assert component.layout_keys or component.block_keys  # renderer needs
    assert component_density_rule(role) is not None  # density/accessibility check

    for key in component.layout_keys:
        assert key in LAYOUT_REGISTRY.entries
    for key in component.block_keys:
        assert key in BLOCK_REGISTRY.entries
    for key in component.interaction_keys:
        assert key in INTERACTION_REGISTRY.entries


def test_component_accessibility_requirements_reuse_registry_entries() -> None:
    guided_practice = SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT["guided_practice"]

    requirements = component_accessibility_requirements(guided_practice)

    assert requirements  # quick_check/short_answer both declare accessibility_requirement


async def test_evaluate_component_completeness_passes_for_real_generated_deck() -> None:
    deck = await _deck()

    report = evaluate_component_completeness(deck)

    assert report.passed is True
    assert report.code == "component_coverage_ok"


async def test_evaluate_component_completeness_flags_incomplete_deck() -> None:
    deck = await _deck()
    example_slide = next(slide for slide in deck.slides if slide.slide_id == "slide-example")
    # Swap the worked-example slide's layout/blocks for something that matches
    # no part of the "worked_example" component's renderer needs.
    mismatched_slide = example_slide.model_copy(update={
        "layout": "poll",
        "blocks": [example_slide.blocks[0].model_copy(update={"block_type": "heading"})],
    })
    incomplete_deck = deck.model_copy(update={
        "slides": [mismatched_slide if slide.slide_id == "slide-example" else slide for slide in deck.slides],
    })

    report = evaluate_component_completeness(incomplete_deck)

    assert report.passed is False
    assert report.code == "component_coverage_gap"


def test_slide_deck_component_vocabulary_does_not_collide_with_component_strategist_registry() -> None:
    """SDTF-07 AC: this mapping must not become a parallel/competing registry.

    The component-strategist system (ADR-035/039, gated behind
    FEATURE_COMPONENT_STRATEGIST_V1) owns an open, data-driven vocabulary of
    `component_type` (renderer content shapes) and `learning_move_id`
    (Gagne-event pedagogical moves) strings in
    common/component_strategy_knowledge/knowledge.yaml. This asserts the
    slide-deck component vocabulary added here is a disjoint namespace --
    no silently-duplicated or competing definition for the same name.
    """
    source = load_knowledge_source(DEFAULT_KNOWLEDGE_SOURCE_PATH)
    component_strategist_names = {binding.component_type for binding in source.component_bindings} | {
        binding.learning_move_id for binding in source.component_bindings
    }
    slide_deck_component_ids = {component.component_id for component in SLIDE_PEDAGOGICAL_ROLE_TO_COMPONENT.values()}

    assert slide_deck_component_ids.isdisjoint(component_strategist_names)
