from __future__ import annotations

import pytest

from common.contracts.answer_set import derive_answer_set
from packages.agents.teaching_pack.specialists.drill_specialist import (
    NoDrillObjectivesError,
    build_drill_activities,
    generate_drill_artifact,
    score_drill,
)
from packages.quality.layer1_schema.component_gate import validate_component_minimums


def _lesson_plan() -> dict[str, object]:
    return {
        "topic": "Equivalent Fractions",
        "subject": "Math",
        "grade_level": "Grade 5",
        "locale": "en",
        "learning_objectives": [{"description": "Identify equivalent fractions."}],
    }


def test_drill_activities_have_stable_ids_and_governed_progression() -> None:
    first = build_drill_activities(_lesson_plan())
    second = build_drill_activities(_lesson_plan())

    assert [activity["id"] for activity in first] == [activity["id"] for activity in second]
    assert [activity["difficulty_level"] for activity in first] == [1, 2, 3, 4, 5]


def test_drill_fails_closed_without_objectives() -> None:
    with pytest.raises(NoDrillObjectivesError):
        generate_drill_artifact({"topic": "Empty"}, {"sources": []})


def test_drill_passes_gate_and_derives_answer_set() -> None:
    artifact = generate_drill_artifact(_lesson_plan(), {"sources": []})

    assert validate_component_minimums(artifact) == []
    assert len(derive_answer_set(artifact, source_document_id="drill-1", source_version=1).entries) == 5


def test_drill_scorecard_is_complete() -> None:
    scorecard = score_drill(build_drill_activities(_lesson_plan()))

    assert scorecard.progression == 1.0
    assert scorecard.activity_identity == 1.0
    assert scorecard.answer_verifiability == 1.0
    assert scorecard.scoped_repairability == 1.0
