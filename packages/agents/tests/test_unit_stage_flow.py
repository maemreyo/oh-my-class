from __future__ import annotations

from packages.agents.teaching_pack.nodes import route_after_triage, route_after_unit_approval


def test_plan_unit_mode_routes_to_unit_branch() -> None:
    assert route_after_triage({"run_id": "run-1", "contract": {"mode": "plan_unit"}}) == "unit_planning"


def test_single_lesson_mode_routes_to_existing_branch() -> None:
    assert route_after_triage({"run_id": "run-1", "contract": {"mode": "generate_pack"}}) == "preplanning_search"


def test_unit_approval_edit_loops_and_approve_preps() -> None:
    assert route_after_unit_approval({"run_id": "run-1", "teacher_approved": True}) == "unit_prep"
    assert route_after_unit_approval({"run_id": "run-1", "teacher_decision": "edit"}) == "unit_planning"
    assert route_after_unit_approval({"run_id": "run-1", "teacher_decision": "reject"}) == "unit_planning"
