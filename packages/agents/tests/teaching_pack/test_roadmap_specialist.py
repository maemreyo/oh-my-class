from __future__ import annotations

import pytest

from packages.agents.teaching_pack.specialists.roadmap_specialist import (
    NoRoadmapObjectivesError,
    build_roadmap_sections,
    generate_roadmap_artifact,
    score_roadmap,
)


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Fractions",
        "subject": "Math",
        "locale": "en",
        "learning_objectives": [
            {"description": "Identify equivalent fractions."},
            {"description": "Generate equivalent fractions."},
        ],
    }


def test_roadmap_milestones_are_stable_and_objective_linked() -> None:
    first = build_roadmap_sections(_lesson_plan())
    second = build_roadmap_sections(_lesson_plan())

    assert [section["id"] for section in first] == ["milestone-1", "milestone-2"]
    assert first == second
    assert first[0]["subtitle"] == "Identify equivalent fractions."


def test_roadmap_fails_closed_without_objectives() -> None:
    with pytest.raises(NoRoadmapObjectivesError):
        generate_roadmap_artifact({"topic": "Empty"}, {"sources": []})


def test_roadmap_scorecard_covers_milestones_and_scoped_edits() -> None:
    sections = build_roadmap_sections(_lesson_plan())
    scorecard = score_roadmap(sections, objective_count=2)

    assert scorecard.milestone_count == 1.0
    assert scorecard.objective_coverage == 1.0
    assert scorecard.dependency_order == 1.0
    assert scorecard.scoped_editability == 1.0


def test_generated_roadmap_has_renderer_metadata() -> None:
    artifact = generate_roadmap_artifact(_lesson_plan(), {"sources": []})

    assert artifact["metadata"]["hero"]["title"] == "Roadmap: Fractions"
    assert artifact["metadata"]["sidebar"]["nav"][0]["href"] == "#milestone-1"
