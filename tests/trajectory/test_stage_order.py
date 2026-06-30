"""Deterministic stage-order trajectory tests for the teaching-pack runtime.

No LLM required — asserts the TEACHING_PACK_STAGES tuple is correct and
complete at import time. Runs in the fast (non-real_llm) tier.
"""
from __future__ import annotations

from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage


def test_single_lesson_stage_order():
    """TEACHING_PACK_STAGES must match the canonical single-lesson traversal order."""
    expected = [
        "setup_contract",
        "triage",
        "preplanning_search",
        "planning_blueprint",
        "post_blueprint_research",
        "artifact_workflow",
        "render_quality",
        "teacher_approval",
        "export_finalize",
    ]
    assert [s.value for s in TEACHING_PACK_STAGES] == expected


def test_all_stages_in_enum():
    """Every entry in TEACHING_PACK_STAGES must be a valid TeachingPackStage member."""
    for stage in TEACHING_PACK_STAGES:
        assert isinstance(stage, TeachingPackStage), (
            f"{stage!r} is not a TeachingPackStage instance"
        )


def test_no_duplicate_stages():
    """Stage list must have no duplicates."""
    values = [s.value for s in TEACHING_PACK_STAGES]
    assert len(values) == len(set(values)), "TEACHING_PACK_STAGES contains duplicate entries"


def test_stage_count():
    """Exactly 9 stages in the single-lesson pipeline (includes TRIAGE)."""
    assert len(TEACHING_PACK_STAGES) == 9


def test_stage_event_names_are_consistent():
    """started_event and completed_event must use the stage value as the middle segment."""
    for stage in TEACHING_PACK_STAGES:
        assert stage.started_event == f"teaching_pack.{stage.value}.started"
        assert stage.completed_event == f"teaching_pack.{stage.value}.completed"
