from __future__ import annotations

import pytest

from packages.agents.teaching_pack.nodes import (
    TeachingPackState,
    _export_finalize,
    route_after_teacher_approval,
)


class TestTeachingPackPlanningResearch:
    @pytest.mark.anyio
    async def test_planning_blueprint_delegates_to_planner_node(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        calls = []

        async def fake_planner_node(state):
            calls.append(state)
            return {
                "lesson_plan": {
                    "topic": "Fractions",
                    "grade_level": "Grade 5",
                    "subject": "math",
                    "learning_objectives": [],
                },
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.planner.nodes.planner_node",
            fake_planner_node,
        )

        result = await nodes._planning_blueprint(TeachingPackState(
            run_id="run-plan",
            contract={
                "topic": "Fractions",
                "raw_request": "Teach equivalent fractions",
                "grade_band": "Grade 5",
                "subject": "math",
                "instruction_language": "vi",
                "student_count": 30,
            },
        ))

        assert calls == [{
            "raw_request": "Teach equivalent fractions",
            "class_info": {
                "topic": "Fractions",
                "grade": 5,
                "grade_band": "Grade 5",
                "subject": "math",
                "language": "vi",
                "student_count": 30,
            },
            "run_id": "run-plan",
            "current_step": 3,
            "lesson_plan": None,
        }]
        assert result["lesson_plan"]["topic"] == "Fractions"

    @pytest.mark.anyio
    async def test_post_blueprint_research_delegates_to_researcher_node(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        calls = []

        async def fake_researcher_node(state):
            calls.append(state)
            return {
                "research_bundle": {
                    "topic": "Fractions",
                    "sources": [{"title": "Source", "url": "https://example.test"}],
                },
            }

        monkeypatch.setattr(
            "packages.agents.sub_agents.researcher.nodes.researcher_node",
            fake_researcher_node,
        )

        result = await nodes._post_blueprint_research(TeachingPackState(
            run_id="run-research",
            contract={"research_policy": "standard"},
            lesson_plan={"topic": "Fractions", "learning_objectives": []},
            research_brief={"sources": []},
        ))

        assert calls == [{
            "lesson_plan": {"topic": "Fractions", "learning_objectives": []},
            "research_policy": "standard",
            "run_id": "run-research",
            "current_step": 7,
            "research_bundle": {"sources": []},
        }]
        assert result["research_brief"]["topic"] == "Fractions"


class TestTeachingPackApprovalExport:
    def test_export_uses_teacher_approved_snapshot_ids_only(self) -> None:
        state = TeachingPackState(
            run_id="run-approval",
            teacher_approved=True,
            approved_snapshot_ids=["snap-approved"],
            rendered_snapshots=[
                {"snapshot_id": "snap-approved"},
                {"snapshot_id": "snap-rejected"},
            ],
        )

        result = _export_finalize(state)

        assert result["exported_files"] == ["exports/run-approval/snap-approved.html"]

    def test_export_blocks_when_teacher_rejects_content(self) -> None:
        state = TeachingPackState(
            run_id="run-rejected",
            teacher_approved=False,
            approved_snapshot_ids=["snap-ignored"],
        )

        result = _export_finalize(state)

        assert result["exported_files"] == []

    def test_scoped_rejection_routes_back_to_artifact_workflow(self) -> None:
        state = TeachingPackState(
            run_id="run-scoped",
            teacher_approved=False,
            artifacts=[{"artifact_id": "quiz-1", "artifact_type": "quiz"}],
            gate_payload={
                "action": "reject",
                "rejection_type": "scoped",
                "artifact_rejections": [{"artifact_id": "quiz-1", "reason": "Simplify."}],
            },
        )

        assert route_after_teacher_approval(state) == "artifact_workflow"

    def test_unscoped_rejection_routes_to_export_finalize_without_exports(self) -> None:
        state = TeachingPackState(
            run_id="run-unscoped",
            teacher_approved=False,
            gate_payload={"action": "reject", "feedback": "Rework all."},
        )

        assert route_after_teacher_approval(state) == "export_finalize"
