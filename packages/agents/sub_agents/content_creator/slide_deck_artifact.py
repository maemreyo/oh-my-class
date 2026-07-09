from __future__ import annotations

from typing import Any

from common.contracts.artifact import ArtifactContent
from packages.agents.slide_deck_engine import SlideDeckEngine, SlideDeckEngineRequest
from packages.agents.slide_deck_engine.models import SlideDeckValidationReport
from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState

# SDH-06: deterministic deck-shape/density failures are sparse-deck signals,
# not incidental validator noise — fail the artifact before it can reach
# teacher approval/export instead of shipping a thin deck silently.
_SPARSE_DECK_CODES = frozenset({"deck_shape_incomplete", "deck_shape_unjustified_slide", "density_purpose_gap"})


async def build_slide_deck_artifact(state: ContentCreatorNodeState) -> dict[str, Any]:
    lesson_plan = state["lesson_plan"]
    deck_result = await SlideDeckEngine().generate(SlideDeckEngineRequest(
        run_id=state["run_id"],
        lesson_blueprint=lesson_plan,
        research_brief=state["research_bundle"],
        dependency_artifacts=state.get("artifacts") or [],
        teacher_constraints={
            "locale": _locale(lesson_plan),
            "theme": state.get("theme", "default"),
            "duration_minutes": lesson_plan.get("duration_minutes"),
        },
        revision_feedback=state.get("revision_feedback", ""),
        structure_preset=state.get("structure_preset"),
    ))
    _raise_if_sparse(deck_result.validation_reports)
    deck_data = deck_result.deck.model_dump(mode="json")
    artifact = ArtifactContent(
        artifact_type="slide_deck",
        theme=state.get("theme", "default"),
        title=deck_result.deck.title,
        sections=[{"title": deck_result.deck.title, "slide_deck": deck_data}],
        metadata={
            "generation_mode": "slide_deck_engine_llm_assisted",
            "artifact_type": "slide_deck",
            "covered_objectives": _objective_texts(lesson_plan),
            "covered_bloom_levels": _bloom_levels(lesson_plan),
            "slide_deck_data": deck_data,
            "slide_deck_scorecard": deck_result.scorecard.model_dump(mode="json"),
            "slide_deck_trace": deck_result.trace.model_dump(mode="json"),
        },
        accessibility={"language": deck_result.deck.accessibility.language},
    )
    return artifact.model_dump()


def _objective_texts(lesson_plan: dict[str, Any]) -> list[str]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    return [str(item.get("description")) for item in objectives if isinstance(item, dict) and item.get("description")]


def _bloom_levels(lesson_plan: dict[str, Any]) -> list[str]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list):
        return []
    levels: list[str] = []
    for item in objectives:
        if not isinstance(item, dict):
            continue
        level = item.get("bloom_level")
        if isinstance(level, str) and level not in levels:
            levels.append(level)
    return levels


def _locale(lesson_plan: dict[str, Any]) -> str:
    return str(lesson_plan.get("locale", lesson_plan.get("citation_locale", "en-US")))


def _raise_if_sparse(validation_reports: list[SlideDeckValidationReport]) -> None:
    failures = [report.message for report in validation_reports if not report.passed and report.code in _SPARSE_DECK_CODES]
    if failures:
        msg = f"slide deck failed deterministic density/shape quality: {'; '.join(failures)}"
        raise ValueError(msg)
