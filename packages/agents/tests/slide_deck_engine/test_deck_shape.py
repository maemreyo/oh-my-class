from __future__ import annotations

import pytest

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.deck_shape import (
    assign_pedagogical_roles,
    estimate_slide_planned_minutes,
    evaluate_deck_shape,
    evaluate_purpose_density,
)
from packages.agents.sub_agents.content_creator.slide_deck_artifact import build_slide_deck_artifact
from packages.agents.teaching_pack.stages import StageEnum


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-deck-shape",
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


async def test_well_formed_six_slide_deck_passes_shape_and_density() -> None:
    deck = await _deck()

    shape = evaluate_deck_shape(deck, teacher_constraints={"locale": "en-US"}, grade_level="Grade 5")
    density = evaluate_purpose_density(deck)

    assert shape.passed is True
    assert shape.code == "deck_shape_ok"
    assert density.passed is True
    assert density.code == "density_purpose_ok"


async def test_sparse_vocabulary_slide_fails_purpose_density() -> None:
    deck = await _deck()
    vocabulary_slide = next(slide for slide in deck.slides if slide.slide_id == "slide-vocabulary")
    thin_slide = vocabulary_slide.model_copy(update={
        "blocks": [vocabulary_slide.blocks[0].model_copy(update={"body": "OK."})],
    })
    thin_deck = deck.model_copy(update={
        "slides": [thin_slide if slide.slide_id == "slide-vocabulary" else slide for slide in deck.slides],
    })

    density = evaluate_purpose_density(thin_deck)

    assert density.passed is False
    assert density.code == "density_purpose_gap"


async def test_missing_spine_slide_fails_deck_shape() -> None:
    deck = await _deck()
    incomplete_deck = deck.model_copy(update={
        "slides": [slide for slide in deck.slides if slide.slide_id != "slide-practice"],
    })

    shape = evaluate_deck_shape(incomplete_deck, teacher_constraints={}, grade_level="Grade 5")

    assert shape.passed is False
    assert shape.code == "deck_shape_incomplete"
    assert "practice" in shape.message


async def _padded_deck_with_misconception_slide():
    deck = await _deck()
    vocabulary_slide = next(slide for slide in deck.slides if slide.slide_id == "slide-vocabulary")
    extra_slide = vocabulary_slide.model_copy(update={
        "slide_id": "slide-misconception",
        "title": "Common Misconception",
        "progression": vocabulary_slide.progression.model_copy(update={"step_index": 7}),
    })
    return deck.model_copy(update={"slides": [*deck.slides, extra_slide]})


async def test_unjustified_extra_slide_is_rejected() -> None:
    padded_deck = await _padded_deck_with_misconception_slide()

    shape = evaluate_deck_shape(padded_deck, teacher_constraints={}, grade_level="Grade 5")

    assert shape.passed is False
    assert shape.code == "deck_shape_unjustified_slide"


async def test_justified_extra_slide_from_long_duration_is_allowed() -> None:
    padded_deck = await _padded_deck_with_misconception_slide()

    shape = evaluate_deck_shape(padded_deck, teacher_constraints={"duration_minutes": 60}, grade_level="Grade 5")

    assert shape.passed is True
    assert shape.code == "deck_shape_ok"


async def test_justified_extra_slide_from_higher_grade_band_is_allowed() -> None:
    padded_deck = await _padded_deck_with_misconception_slide()

    shape = evaluate_deck_shape(padded_deck, teacher_constraints={}, grade_level="Grade 8")

    assert shape.passed is True
    assert shape.code == "deck_shape_ok"


async def test_build_slide_deck_artifact_raises_when_engine_reports_sparse_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    result = await SlideDeckEngine().generate(_request())
    sparse_report = result.validation_reports[0].model_copy(update={
        "passed": False,
        "code": "density_purpose_gap",
        "message": "Slide 'slide-vocabulary' lacks the content its role requires.",
    })
    sparse_result = result.model_copy(update={"validation_reports": [*result.validation_reports, sparse_report]})

    async def fake_generate(self, request):  # noqa: ANN001, ARG001 - test seam mirrors SlideDeckEngine.generate
        return sparse_result

    monkeypatch.setattr(SlideDeckEngine, "generate", fake_generate)

    with pytest.raises(ValueError, match="density/shape quality"):
        await build_slide_deck_artifact({
            "lesson_plan": {"topic": "Equivalent fractions", "grade_level": "Grade 5", "learning_objectives": []},
            "research_bundle": {"sources": []},
            "artifact_types": ["slide_deck"],
            "theme": "default",
            "run_id": "run-sparse",
            "current_step": StageEnum.ARTIFACT_WORKFLOW,
            "artifacts": [],
        })


# --- SDTF-02: pedagogical role + planned pacing -----------------------------


async def test_engine_assigns_adr045_roles_to_the_spine_and_stamps_them_on_slides() -> None:
    deck = await _deck()

    roles = dict(zip((slide.slide_id for slide in deck.slides), assign_pedagogical_roles(deck), strict=True))

    assert roles == {
        "slide-title": "hook",
        "slide-goal": "objective",
        "slide-vocabulary": "explain",
        "slide-example": "model",
        "slide-practice": "guided_practice",
        "slide-exit": "exit_ticket",
    }
    # The engine (`annotate_pedagogical_pacing`) stamps the same classification
    # onto the persisted slide, not just the on-demand derived one.
    assert [slide.pedagogical_role for slide in deck.slides] == list(roles.values())


async def test_optional_extension_slide_gets_a_named_role_beyond_the_spine() -> None:
    deck = await _deck()
    practice_slide = next(slide for slide in deck.slides if slide.slide_id == "slide-practice")
    padded = deck.model_copy(update={
        "slides": [*deck.slides, practice_slide.model_copy(update={
            "slide_id": "slide-independent-drill",
            "title": "Independent Drill",
            "progression": practice_slide.progression.model_copy(update={"step_index": 7}),
            "interactions": [interaction.model_copy(update={"interaction_id": "interaction-independent-check"}) for interaction in practice_slide.interactions],
        })],
    })

    roles = assign_pedagogical_roles(padded)

    assert roles[-1] == "independent_practice"


async def test_unrecognized_optional_slide_has_no_assigned_role() -> None:
    padded_deck = await _padded_deck_with_misconception_slide()

    roles = assign_pedagogical_roles(padded_deck)

    assert roles[-1] is None


async def test_role_specific_density_requires_interaction_for_check_understanding_extension() -> None:
    deck = await _deck()
    practice_slide = next(slide for slide in deck.slides if slide.slide_id == "slide-practice")
    padded = deck.model_copy(update={
        "slides": [*deck.slides, practice_slide.model_copy(update={
            "slide_id": "slide-check-in",
            "title": "Check In",
            "progression": practice_slide.progression.model_copy(update={"step_index": 7}),
            "interactions": [],  # check_understanding still requires one, unlike a plain "optional" slide.
        })],
    })

    density = evaluate_purpose_density(padded)

    assert density.passed is False
    assert density.code == "density_purpose_gap"
    assert "role=check_understanding" in density.message


async def test_engine_stamps_planned_duration_per_slide_and_deck_total_pacing() -> None:
    request = _request().model_copy(update={
        "teacher_constraints": {"locale": "en-US", "theme": "default", "duration_minutes": 30},
    })

    deck = (await SlideDeckEngine().generate(request)).deck

    minutes_by_slide_id = {slide.slide_id: slide.planned_duration_minutes for slide in deck.slides}
    # Role pacing weights (hook/objective/exit=0.5, explain/model=1.0,
    # guided_practice=1.5) split 30 available minutes proportionally.
    assert minutes_by_slide_id == {
        "slide-title": 3.0,
        "slide-goal": 3.0,
        "slide-vocabulary": 6.0,
        "slide-example": 6.0,
        "slide-practice": 9.0,
        "slide-exit": 3.0,
    }
    assert deck.total_planned_duration_minutes == 30.0


async def test_estimate_slide_planned_minutes_falls_back_to_flat_default_without_teacher_duration() -> None:
    deck = await _deck()

    minutes = estimate_slide_planned_minutes(deck, teacher_constraints={})

    # No `duration_minutes` set -- flat 5-minutes-per-slide planning default.
    assert sum(minutes) == len(deck.slides) * 5.0
