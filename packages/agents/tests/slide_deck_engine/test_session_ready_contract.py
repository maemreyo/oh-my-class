from __future__ import annotations

import pytest

from common.contracts.slide_deck import SlideDeckInteraction, SlideDeckInteractionTeacherOnly
from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.quality import validate_registry_membership
from packages.agents.slide_deck_engine.registries import INTERACTION_REGISTRY

# ADR-045 / SDTF-01: deck, slide, block, and interaction IDs are the join
# points a future TeachingSession binds to, so they must be stable across
# builds, and interactions must be typed (prompt, response intent via
# interaction_type, answer-bearing flag, no-JS fallback, accessibility
# label) without arbitrary HTML/JS. This suite hardens both.


def _request(run_id: str = "run-session-ready") -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id=run_id,
        lesson_blueprint={
            "topic": "Equivalent fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [{"description": "Explain why two fractions are equivalent."}],
        },
        research_brief={
            "sources": [
                {"id": "src-fractions-standard", "title": "Grade 5 Fractions Standard", "citation": "CCSS 5.NF.A"},
            ],
        },
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )


async def test_deck_slide_block_and_interaction_ids_are_stable_across_two_builds() -> None:
    first = (await SlideDeckEngine().generate(_request())).deck
    second = (await SlideDeckEngine().generate(_request())).deck

    assert first.deck_id == second.deck_id
    assert [slide.slide_id for slide in first.slides] == [slide.slide_id for slide in second.slides]
    assert [block.block_id for slide in first.slides for block in slide.blocks] == [
        block.block_id for slide in second.slides for block in slide.blocks
    ]
    assert [interaction.interaction_id for slide in first.slides for interaction in slide.interactions] == [
        interaction.interaction_id for slide in second.slides for interaction in slide.interactions
    ]


async def test_deck_id_is_content_addressed_by_run_id_while_slide_shape_stays_deterministic() -> None:
    deck_a = (await SlideDeckEngine().generate(_request(run_id="run-a"))).deck
    deck_b = (await SlideDeckEngine().generate(_request(run_id="run-b"))).deck

    assert deck_a.deck_id == "slide-deck-run-a"
    assert deck_b.deck_id == "slide-deck-run-b"
    assert deck_a.deck_id != deck_b.deck_id
    assert [slide.slide_id for slide in deck_a.slides] == [slide.slide_id for slide in deck_b.slides]


def test_short_answer_is_a_registry_backed_answer_bearing_free_response_interaction() -> None:
    entry = INTERACTION_REGISTRY.get("short_answer")

    assert entry.answer_bearing is True
    assert entry.schema_kind == "free_response"
    assert entry.teacher_only_behavior == "teacher_only_projection"
    assert entry.persists_student_response is False
    assert entry.no_js_fallback
    assert entry.accessibility_requirement


@pytest.mark.parametrize("interaction_type", ["quick_check", "discussion_prompt", "exit_ticket", "short_answer"])
def test_required_response_intents_construct_with_full_typed_metadata(interaction_type: str) -> None:
    answer_bearing = interaction_type in {"quick_check", "short_answer"}
    teacher_only = (
        SlideDeckInteractionTeacherOnly(
            separation="teacher_only_projection",
            acceptable_answers=["a sample acceptable answer"],
            rationale="Sample teacher-only rationale.",
        )
        if answer_bearing
        else None
    )

    interaction = SlideDeckInteraction(
        interaction_id=f"interaction-{interaction_type}",
        interaction_type=interaction_type,
        prompt=f"Prompt for {interaction_type}",
        answer_bearing=answer_bearing,
        teacher_only=teacher_only,
    )

    assert interaction.interaction_type in INTERACTION_REGISTRY.entries
    assert interaction.prompt
    assert interaction.no_js_fallback
    assert interaction.accessibility_label
    assert interaction.answer_bearing is answer_bearing


async def test_registry_membership_accepts_a_real_deck_with_a_short_answer_interaction() -> None:
    deck = (await SlideDeckEngine().generate(_request())).deck
    practice_slide = deck.slides[4]
    short_answer = SlideDeckInteraction(
        interaction_id="interaction-short-answer-check",
        interaction_type="short_answer",
        prompt="Write one sentence that correctly uses the target vocabulary.",
        answer_bearing=True,
        no_js_fallback="Students write or say a short answer; no response is stored.",
        accessibility_label="Short answer prompt",
        teacher_only=SlideDeckInteractionTeacherOnly(
            separation="teacher_only_projection",
            acceptable_answers=["Any grammatically correct sentence using the target vocabulary."],
            rationale="Accept any correct usage of the target vocabulary.",
        ),
    )
    updated_slide = practice_slide.model_copy(update={"interactions": [short_answer]})
    # SDE-02 closed the once-pre-existing LAYOUT_REGISTRY/BLOCK_REGISTRY gap
    # (they now cover every layout/block type content_materialization.py
    # emits), so this exercises the full deck rather than isolating to one
    # registry-conformant slide.
    updated_deck = deck.model_copy(update={"slides": [*deck.slides[:4], updated_slide, *deck.slides[5:]]})

    reports = validate_registry_membership(updated_deck)

    assert all(report.passed for report in reports)
    assert any(report.code == "registry_membership_ok" for report in reports)
