from __future__ import annotations

from common.contracts.teaching_brief import DEFAULT_ARTIFACT_TYPES, TeachingBrief
from packages.agents.teaching_pack.artifact_fanout import coordinate_artifact_fanout


def test_default_brief_matches_core_four_plus_slide_recipe() -> None:
    brief = TeachingBrief(
        raw_request="Teach equivalent fractions.",
        topic="Equivalent fractions",
        grade=5,
        subject="Math",
    )

    assert DEFAULT_ARTIFACT_TYPES == ["lesson", "worksheet", "quiz", "drill", "slide_deck"]
    assert brief.artifact_types == DEFAULT_ARTIFACT_TYPES


def test_default_pack_fanout_starts_with_lesson_then_releases_core_wave() -> None:
    initial = {
        "run_id": "run-default-pack",
        "contract": {"artifact_types": DEFAULT_ARTIFACT_TYPES, "theme": "default"},
        "artifact_types": DEFAULT_ARTIFACT_TYPES,
        "artifact_workflow_states": [],
        "artifact_references": [],
    }
    first = coordinate_artifact_fanout(initial)
    after_lesson = coordinate_artifact_fanout({
        **initial,
        **first,
        "artifact_workflow_states": [{
            "artifact_generation_id": first["artifact_generation_id"],
            "artifact_type": "lesson",
            "status": "passed",
        }],
    })

    assert first["artifact_wave_index"] == 0
    assert after_lesson["artifact_wave_index"] == 1
