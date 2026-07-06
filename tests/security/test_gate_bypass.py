from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from packages.agents.teaching_pack.nodes import JsonObject, TeachingPackState


class TestGateBypassInvariant06:
    def test_teacher_approval_stage_calls_interrupt_before_export(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from packages.agents.teaching_pack import nodes

        captured: JsonObject = {}

        def fake_interrupt(payload: JsonObject) -> JsonObject:
            captured.update(payload)
            return {"action": "approve"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

        result = nodes._teacher_approval(TeachingPackState(
            run_id="run-gate-visible",
            rendered_snapshots=[{"snapshot_id": "snap-1"}],
            artifacts=[{"artifact_id": "quiz-1", "artifact_type": "quiz"}],
        ))

        assert captured["gate"] == "content_approval"
        assert captured["snapshot_ids"] == ["snap-1"]
        assert result.get("teacher_approved") is True

    def test_fast_lane_still_calls_interrupt_with_audited_revert_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from packages.agents.teaching_pack import nodes

        captured: JsonObject = {}

        def fake_interrupt(payload: JsonObject) -> JsonObject:
            captured.update(payload)
            return {}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.should_fast_lane", lambda *_args: True)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.record_gate_event", lambda *_args: None)
        monkeypatch.setattr("packages.agents.teaching_pack.teacher_memory.write_gate_approval", lambda *_args: None)
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")

        result = nodes._teacher_approval(
            TeachingPackState(
                run_id="run-fast-lane-visible",
                contract={"teacher_id": "teacher-1"},
                compliance_passed=True,
                rendered_snapshots=[{"snapshot_id": "snap-1"}],
                artifacts=[{"artifact_id": "lesson-1", "artifact_type": "lesson"}],
            ),
            store=InMemoryStore(),
        )

        assert captured["auto_approved"] is True
        assert captured["approval_mode"] == "auto_approved"
        assert captured["revert_window_seconds"] == 900
        assert result.get("teacher_approved") is True

    def test_teaching_pack_stages_order_approval_before_export(self) -> None:
        from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage

        stage_values = [s.value for s in TEACHING_PACK_STAGES]
        assert "teacher_approval" in stage_values, (
            "teacher_approval must be in TEACHING_PACK_STAGES — cannot be bypassed"
        )
        assert TeachingPackStage.TEACHER_APPROVAL.value == "teacher_approval"
        approval_idx = stage_values.index("teacher_approval")
        export_idx = stage_values.index("export_finalize")
        assert approval_idx < export_idx, (
            "INVARIANT-06: teacher_approval must precede export_finalize"
        )

    def test_component_strategy_stages_order_approval_before_export(self) -> None:
        from packages.agents.teaching_pack.stages import teaching_pack_stages

        stage_values = [stage.value for stage in teaching_pack_stages(component_strategy_enabled=True)]
        assert "provisional_component_strategy" in stage_values
        assert "finalize_component_strategy" in stage_values
        assert "teacher_approval" in stage_values, (
            "teacher_approval must be in component-strategy stages — cannot be bypassed"
        )
        approval_idx = stage_values.index("teacher_approval")
        export_idx = stage_values.index("export_finalize")
        assert approval_idx < export_idx, (
            "INVARIANT-06: component-strategy teacher_approval must precede export_finalize"
        )
