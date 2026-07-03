"""Tests for HITL gate wrapper nodes — E3 pattern."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from packages.agents.gates.state import GateState


def make_base_state(**overrides: Any) -> GateState:
    base: dict[str, Any] = {
        "raw_request": "Teach photosynthesis",
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-001",
        "blueprint_approved": False,
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "export_formats": [],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "research_policy": "basic",
    }
    return GateState(**{**base, **overrides})


# ── gate_01_blueprint_approval ────────────────────────────────────────────────

class TestGate01BlueprintApproval:
    def test_raises_without_lesson_plan(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state()
        with pytest.raises(ValueError, match="lesson_plan must be set"):
            gate_01_blueprint_approval(state)

    def test_calls_interrupt_with_gate_info(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            gate_01_blueprint_approval(state)
        call_payload = mock_interrupt.call_args[0][0]
        assert call_payload["gate"] == "blueprint_approval"
        assert call_payload["lesson_plan"] == {"topic": "Photosynthesis"}
        assert call_payload["run_id"] == "run-001"

    def test_approve_sets_teacher_decision(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            result = gate_01_blueprint_approval(state)
        assert result["teacher_decision"] == "approve"
        assert result["blueprint_approved"] is True

    def test_approve_returns_gate_payload(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            result = gate_01_blueprint_approval(state)
        assert "gate_payload" in result

    def test_reject_sets_teacher_decision(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "reject", "feedback": "Too complex"}
            result = gate_01_blueprint_approval(state)
        assert result["teacher_decision"] == "reject"
        assert result["blueprint_approved"] is False

    def test_edit_updates_lesson_plan(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        edited_plan = {"topic": "Photosynthesis (simplified)", "grade_level": "Grade 3"}
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {
                "action": "edit",
                "feedback": "Simplify for Grade 3",
                "edited_lesson_plan": edited_plan,
            }
            result = gate_01_blueprint_approval(state)
        assert result["teacher_decision"] == "edit"
        assert result["lesson_plan"] == edited_plan

    def test_edit_without_edited_plan_does_not_update_plan(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "edit", "feedback": "Minor tweaks"}
            result = gate_01_blueprint_approval(state)
        assert "lesson_plan" not in result

    def test_approve_stores_feedback_in_revision_feedback(self):
        from packages.agents.gates.gate_01_blueprint import gate_01_blueprint_approval
        state = make_base_state(lesson_plan={"topic": "Photosynthesis"})
        with patch("packages.agents.gates.gate_01_blueprint.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": "Great plan!"}
            result = gate_01_blueprint_approval(state)
        assert result.get("revision_feedback") == "Great plan!"


# ── gate_02_content_approval ──────────────────────────────────────────────────

class TestGate02ContentApproval:
    def test_raises_without_artifacts(self):
        from packages.agents.gates.gate_02_content_approval import gate_02_content_approval
        state = make_base_state()
        with pytest.raises(ValueError, match="artifacts must be set"):
            gate_02_content_approval(state)

    def test_calls_interrupt_with_gate_info(self):
        from packages.agents.gates.gate_02_content_approval import gate_02_content_approval
        state = make_base_state(artifacts=[{"type": "lesson"}])
        with patch("packages.agents.gates.gate_02_content_approval.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            gate_02_content_approval(state)
        call_payload = mock_interrupt.call_args[0][0]
        assert call_payload["gate"] == "content_approval"
        assert call_payload["artifacts"] == [{"type": "lesson"}]
        assert call_payload["run_id"] == "run-001"

    def test_approve_sets_teacher_decision(self):
        from packages.agents.gates.gate_02_content_approval import gate_02_content_approval
        state = make_base_state(artifacts=[{"type": "lesson"}])
        with patch("packages.agents.gates.gate_02_content_approval.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            result = gate_02_content_approval(state)
        assert result["teacher_decision"] == "approve"
        assert result["teacher_approved"] is True

    def test_reject_sets_teacher_decision(self):
        from packages.agents.gates.gate_02_content_approval import gate_02_content_approval
        state = make_base_state(artifacts=[{"type": "lesson"}])
        with patch("packages.agents.gates.gate_02_content_approval.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "reject", "feedback": "Redo this"}
            result = gate_02_content_approval(state)
        assert result["teacher_decision"] == "reject"
        assert result["teacher_approved"] is False

    def test_returns_gate_payload(self):
        from packages.agents.gates.gate_02_content_approval import gate_02_content_approval
        state = make_base_state(artifacts=[{"type": "lesson"}])
        with patch("packages.agents.gates.gate_02_content_approval.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            result = gate_02_content_approval(state)
        assert "gate_payload" in result

    def test_includes_review_results_in_interrupt_payload(self):
        from packages.agents.gates.gate_02_content_approval import gate_02_content_approval
        state = make_base_state(
            artifacts=[{"type": "lesson"}],
            quality_scores={"overall": 8.0},
        )
        with patch("packages.agents.gates.gate_02_content_approval.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"action": "approve", "feedback": ""}
            gate_02_content_approval(state)
        call_payload = mock_interrupt.call_args[0][0]
        assert "review_results" in call_payload


def test_gates_module_is_importable():
    from packages.agents.gates import (  # noqa: F401
        gate_01_blueprint_approval,  # pyright: ignore[reportUnusedImport]
        gate_02_content_approval,  # pyright: ignore[reportUnusedImport]
    )


def test_gates_are_callable():
    from packages.agents.gates import gate_01_blueprint_approval, gate_02_content_approval
    assert callable(gate_01_blueprint_approval)
    assert callable(gate_02_content_approval)
