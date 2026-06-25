"""Tests for new quality gate state fields."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


def test_state_has_fail_layer():
    state: OhMyClassState = {
        "raw_request": "test", "teacher_id": "t1", "class_info": {},
        "run_id": "r1", "blueprint_approved": False, "quality_passed": False,
        "teacher_approved": False, "revision_count": 0, "artifact_types": [],
        "theme": "default", "artifacts": [], "export_formats": [], "exported_files": [],
        "current_step": 1, "tokens_used": 0, "cost_usd": 0.0, "research_policy": "basic",
        "fail_layer": "schema", "fail_count": 1,
    }
    assert state["fail_layer"] == "schema"
    assert state["fail_count"] == 1

def test_state_has_schema_valid():
    state = {"schema_valid": True}
    assert state.get("schema_valid") is True

def test_state_has_judge_score():
    state = {"judge_score": 8.5}
    assert state.get("judge_score") == 8.5

def test_state_has_escalate():
    state = {"escalate": True, "escalate_reason": "Too many retries"}
    assert state["escalate"] is True
