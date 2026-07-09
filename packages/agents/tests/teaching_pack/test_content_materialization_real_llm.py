"""Real-LLM (9router) proof for SDE-01's ContentMaterializer wording call.

Marked real_llm — excluded from the per-commit merge gate (`-m "not real_llm"`),
run only on the nightly/pre-deploy release gate against a live 9router (`:20228`,
model `4omc`), per ADR-032 / `.scratch/ROADMAP.md`'s testing policy. No stub, no
mock, no fake transport — this calls the real `llm_client` the same way
production does. Not executed in this session (no live 9router access); written
now so it runs unmodified once wired into the release gate.

The ADR-044 3-scenario real-LLM harness (Grade5 ESL, Grade5 math/science,
Vietnamese localization) this issue's acceptance criteria ultimately wants is a
later issue (SDH-07) — this test proves the call site works end-to-end against a
real model today, without waiting on that harness.
"""

from __future__ import annotations

import pytest

from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest

pytestmark = pytest.mark.real_llm


def _request() -> SlideDeckEngineRequest:
    return SlideDeckEngineRequest(
        run_id="run-content-materialization-real-llm",
        lesson_blueprint={
            "topic": "Grade 5 English ESL food vocabulary",
            "grade_level": "Grade 5",
            "learning_objectives": [
                {"description": "Use food vocabulary in short ESL speaking exchanges."},
            ],
        },
        research_brief={
            "sources": [
                {
                    "id": "src-food-vocab",
                    "title": "Teacher supplied ESL food vocabulary context",
                    "citation": "Teacher supplied lesson context",
                },
            ],
        },
        dependency_artifacts=[],
        teacher_constraints={"locale": "en-US", "theme": "default"},
        revision_feedback="",
    )


async def test_content_materialization_calls_real_9router_and_produces_a_valid_deck() -> None:
    result = await SlideDeckEngine().generate(_request())

    # A real call was made and its (real, non-stubbed) output was usable.
    assert result.trace.llm_calls == 1
    assert result.trace.model_cost_metadata["provider"] == "llm_client"
    # The deck is still a fully valid, schema-checked SlideDeckData with the
    # engine's standard shape — real LLM prose flows through the same
    # registry/density/accessibility/teacher-only validators as deterministic
    # content, per this issue's acceptance criteria.
    assert len(result.deck.slides) == 6
    assert result.scorecard.objective_coverage_score == 1.0
    assert result.scorecard.teacher_only_separation_score == 1.0
