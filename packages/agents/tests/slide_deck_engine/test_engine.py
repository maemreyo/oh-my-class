from __future__ import annotations

from common.contracts.slide_deck import SlideDeckData
from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.models import SlideArchitecturePlan, SlideDeckScopedRepairReport
from packages.agents.slide_deck_engine.policies import DensityBudgetPolicy, PageCountPolicy
from packages.agents.slide_deck_engine.quality import (
    build_healing_reports,
    build_scorecard,
    trace_artifacts,
    validate_pacing,
    validate_source_references,
)
from packages.agents.slide_deck_engine.registries import (
    BLOCK_REGISTRY,
    INTERACTION_REGISTRY,
    LAYOUT_REGISTRY,
)


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-slide-engine",
        lesson_blueprint={
            "topic": "Equivalent fractions",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Explain why two fractions are equivalent."},
            ],
        },
        research_brief={
            "sources": [
                {
                    "id": "src-fractions-standard",
                    "title": "Grade 5 Fractions Standard",
                    "citation": "CCSS 5.NF.A",
                },
            ],
        },
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )


def _request_with_feedback(feedback: dict[str, str]) -> SlideDeckEngineRequest:
    request = _request()
    constraints = {**request.teacher_constraints, "slide_deck_feedback": feedback}
    return request.model_copy(update={"teacher_constraints": constraints})


def test_slide_deck_engine_returns_valid_deterministic_deck_without_llm() -> None:
    result = SlideDeckEngine().generate(_request())
    slide_titles = [slide.title for slide in result.deck.slides]

    assert isinstance(result.deck, SlideDeckData)
    assert result.deck.deck_id == "slide-deck-run-slide-engine"
    assert slide_titles == ["Equivalent fractions", "Learning Goal", "Key Vocabulary", "Worked Example", "Guided Practice", "Exit Ticket"]
    assert len(result.deck.slides) == 6
    assert result.deck.slides[4].interactions[0].teacher_only is not None
    assert result.scorecard.overall_score == 1.0
    assert result.trace.llm_calls == 0
    assert result.trace.internal_only is True
    assert result.trace.model_cost_metadata == {"llm_calls": 0, "estimated_cost_usd": 0.0, "provider": "none"}
    assert result.trace.export_readiness_manifest["format"] == "html"
    assert result.trace.export_readiness_manifest["slide_count"] == 6


def test_slide_deck_engine_caps_deck_title_for_long_inferred_topics() -> None:
    request = _request().model_copy(update={
        "lesson_blueprint": {
            "topic": "A" * 200,
            "grade_level": "Grade 5",
        "learning_objectives": [{"description": "Use the long topic in a slide deck."}],
        },
    })

    result = SlideDeckEngine().generate(request)

    assert len(result.deck.title) == 200
    assert result.deck.title.endswith(" Slide Deck")
    assert result.deck.slides[0].title == "A" * 200
    assert result.deck.slides[1].title == "Learning Goal"


def test_slide_deck_engine_cleans_teacher_request_before_materializing_student_slides() -> None:
    raw_request = (
        "LIVE_4OMC_SLIDE_DECK_SMOKE 49e877da-e109-42ac-849c-2a3d6fff3027: "
        "Generate a slide deck for Grade 5 English ESL food vocabulary. "
        "Include teachable slide titles, student-safe interactions, and teacher-only answers."
    )
    request = _request().model_copy(update={
        "lesson_blueprint": {
            "topic": raw_request,
            "grade_level": "Grade 5",
            "learning_objectives": [{"description": "Use food vocabulary in short ESL speaking exchanges."}],
        },
    })

    result = SlideDeckEngine().generate(request)
    student_surface = " ".join([
        result.deck.title,
        *[slide.title for slide in result.deck.slides],
        *[block.body for slide in result.deck.slides for block in slide.blocks],
        *[interaction.prompt for slide in result.deck.slides for interaction in (slide.interactions or [])],
    ]).lower()

    assert result.deck.title == "Grade 5 English ESL food vocabulary Slide Deck"
    assert result.deck.slides[0].title == "Grade 5 English ESL food vocabulary"
    assert len(result.deck.slides) >= 6
    assert "food vocabulary" in student_surface
    assert "live_4omc_slide_deck_smoke" not in student_surface
    assert "49e877da-e109-42ac-849c-2a3d6fff3027" not in student_surface
    assert "generate a slide deck" not in student_surface
    assert "teacher-only answers" not in student_surface


def test_slide_deck_engine_scorecard_complements_existing_layer4_judge_gate() -> None:
    result = SlideDeckEngine().generate(_request())

    assert result.scorecard.objective_coverage_score == 1.0
    assert result.scorecard.pacing_fit_score == 1.0
    assert result.scorecard.source_reference_score == 1.0
    assert "layer4_judge_passed" not in result.trace.scorecard_artifact


def test_slide_deck_engine_healing_maps_failures_to_scoped_repairs() -> None:
    deck = SlideDeckEngine().generate(_request()).deck
    crowded_slide = deck.slides[0].model_copy(
        update={"blocks": [*deck.slides[0].blocks, *deck.slides[0].blocks]},
    )
    crowded_deck = deck.model_copy(update={"slides": [crowded_slide, *deck.slides[1:]]})
    validation = DensityBudgetPolicy(max_blocks_per_slide=2, max_interactions_per_slide=1).evaluate(crowded_deck)

    healing = build_healing_reports([validation])
    scorecard = build_scorecard([validation], crowded_deck)

    assert validation.code == "density_budget_exceeded"
    assert healing[0].attempted is True
    assert healing[0].scope == "slide"
    assert healing[0].strategy == "rewrite"
    assert healing[0].outcome == "planned"
    assert scorecard.density_score == 0.0


def test_slide_deck_engine_validators_report_pacing_and_source_failures() -> None:
    deck = SlideDeckEngine().generate(_request()).deck
    shifted_slide = deck.slides[1].model_copy(
        update={"progression": deck.slides[1].progression.model_copy(update={"step_index": 7})},
    )
    missing_source_block = deck.slides[0].blocks[0].model_copy(update={"source_ref_ids": ["missing-source"]})
    missing_source_slide = deck.slides[0].model_copy(update={"blocks": [missing_source_block, deck.slides[0].blocks[1]]})

    pacing = validate_pacing(deck.model_copy(update={"slides": [deck.slides[0], shifted_slide, *deck.slides[2:]]}))
    source_refs = validate_source_references(deck.model_copy(update={"slides": [missing_source_slide, *deck.slides[1:]]}))

    assert pacing.passed is False
    assert pacing.code == "pacing_mismatch"
    assert pacing.scope == "plan"
    assert source_refs.passed is False
    assert source_refs.code == "missing_source_refs"
    assert source_refs.scope == "block"


def test_slide_deck_engine_trace_redacts_internal_artifacts() -> None:
    result = SlideDeckEngine().generate(_request())
    deck = result.deck.model_copy(update={"title": "Student alice@example.com Traceback (most recent call last) correct answer"})

    artifacts = trace_artifacts(
        deck,
        SlideArchitecturePlan(slide_titles=[slide.title for slide in deck.slides], layouts=[slide.layout for slide in deck.slides]),
        result.validation_reports,
        result.healing_reports,
        result.scorecard,
        SlideDeckScopedRepairReport(),
    )

    assert "alice@example.com" not in str(artifacts)
    assert "Traceback" not in str(artifacts)
    assert "correct answer" not in str(artifacts).lower()


def test_slide_deck_engine_scoped_slide_density_feedback_preserves_siblings() -> None:
    result = SlideDeckEngine().generate(_request_with_feedback({
        "scope": "slide",
        "slide_id": "slide-practice",
        "reason": "Slide 4 is too dense; reduce the amount of classroom prompt text.",
    }))

    repair = result.trace.scoped_regeneration_artifact

    assert repair["requested_scope"] == "slide"
    assert repair["applied_scope"] == "slide"
    assert repair["target_id"] == "slide-practice"
    assert repair["preserved_slide_ids"] == ["slide-title", "slide-goal", "slide-vocabulary", "slide-example", "slide-exit"]
    assert result.deck.slides[0].title == "Equivalent fractions"
    assert result.scorecard.density_score == 1.0


def test_slide_deck_engine_scoped_interaction_answer_leak_feedback_preserves_slide_content() -> None:
    result = SlideDeckEngine().generate(_request_with_feedback({
        "scope": "interaction",
        "slide_id": "slide-check",
        "interaction_id": "interaction-check",
        "reason": "Answer leak risk: keep the answer out of the student surface.",
    }))

    interaction = result.deck.slides[4].interactions[0]
    repair = result.trace.scoped_regeneration_artifact

    assert repair["requested_scope"] == "interaction"
    assert repair["applied_scope"] == "block"
    assert repair["target_id"] == "interaction-check"
    assert repair["preserved_slide_ids"] == ["slide-title", "slide-goal", "slide-vocabulary", "slide-example", "slide-exit"]
    assert interaction.teacher_only is not None
    assert interaction.teacher_only.rationale == "Answer remains in teacher-only projection after scoped feedback."
    assert result.scorecard.teacher_only_separation_score == 1.0


def test_slide_deck_engine_deck_level_style_feedback_preserves_artifacts_and_slides() -> None:
    result = SlideDeckEngine().generate(_request_with_feedback({
        "scope": "deck",
        "deck_id": "slide-deck-run-slide-engine",
        "theme": "forest",
        "reason": "Use a calmer visual tone for the deck.",
    }))

    repair = result.trace.scoped_regeneration_artifact

    assert result.deck.theme == "forest"
    assert repair["requested_scope"] == "deck"
    assert repair["applied_scope"] == "deck"
    assert repair["preserved_non_slide_artifacts"] is True
    assert repair["preserved_slide_ids"] == ["slide-title", "slide-goal", "slide-vocabulary", "slide-example", "slide-practice", "slide-exit"]


def test_slide_deck_engine_escalates_scoped_feedback_when_plan_dependencies_change() -> None:
    result = SlideDeckEngine().generate(_request_with_feedback({
        "scope": "slide",
        "slide_id": "slide-check",
        "reason": "Change the learning objective and pacing sequence for this slide.",
    }))

    repair = result.trace.scoped_regeneration_artifact

    assert repair["requested_scope"] == "slide"
    assert repair["applied_scope"] == "plan"
    assert repair["escalated"] is True
    assert repair["escalation_reason"] == "feedback affects objective coverage or pacing"


def test_slide_deck_registries_expose_complete_fixture_path() -> None:
    layout = LAYOUT_REGISTRY.get("question")
    block = BLOCK_REGISTRY.get("interaction_prompt")
    interaction = INTERACTION_REGISTRY.get("multiple_choice_single")

    assert layout.supported_surfaces == ["presentation", "teacher_guide", "print"]
    assert block.requires_alt_text is False
    assert interaction.answer_bearing is True
    assert interaction.teacher_only_behavior == "teacher_only_projection"


def test_slide_deck_interaction_registry_exposes_v1_modules() -> None:
    expected = {
        "reveal",
        "quick_check",
        "poll_prompt",
        "timer",
        "discussion_prompt",
        "exit_ticket",
        "think_pair_share",
    }

    assert expected.issubset(INTERACTION_REGISTRY.entries)
    assert all(INTERACTION_REGISTRY.get(key).persists_student_response is False for key in expected)
    assert INTERACTION_REGISTRY.get("quick_check").teacher_only_behavior == "teacher_only_projection"


def test_page_count_policy_accepts_fixture_size_and_rejects_overflow() -> None:
    policy = PageCountPolicy(min_slides=6, max_slides=6)
    deck = SlideDeckEngine().generate(_request()).deck

    accepted = policy.evaluate(deck)
    overflow = policy.evaluate(deck.model_copy(update={"slides": [*deck.slides, deck.slides[0]]}))

    assert accepted.passed is True
    assert overflow.passed is False
    assert overflow.code == "page_count_exceeded"


def test_density_budget_policy_rejects_too_many_blocks_on_one_slide() -> None:
    deck = SlideDeckEngine().generate(_request()).deck
    crowded_slide = deck.slides[0].model_copy(
        update={"blocks": [*deck.slides[0].blocks, *deck.slides[0].blocks]},
    )
    crowded_deck = deck.model_copy(update={"slides": [crowded_slide, deck.slides[1]]})

    result = DensityBudgetPolicy(max_blocks_per_slide=2, max_interactions_per_slide=1).evaluate(crowded_deck)

    assert result.passed is False
    assert result.code == "density_budget_exceeded"
