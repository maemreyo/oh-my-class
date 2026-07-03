from __future__ import annotations

import pytest

from packages.agents.teaching_pack.nodes import (
    TeachingPackState,
    _compliance_gate,
    _export_finalize,
    make_stage_node,
    route_after_compliance_gate,
    route_after_teacher_approval,
)
from packages.agents.teaching_pack.quality_routing import route_after_render_quality
from packages.agents.teaching_pack.stages import StageEnum, TeachingPackStage


class TestTeachingPackPlanningResearch:
    @pytest.mark.anyio
    async def test_completed_stage_is_skipped_when_reclaimed(self, monkeypatch) -> None:
        calls = []

        async def fake_planner_node(state):
            calls.append(state)
            return {"lesson_plan": {"topic": "Should not run"}}

        monkeypatch.setattr(
            "packages.agents.sub_agents.planner.nodes.planner_node",
            fake_planner_node,
        )
        stage_node = make_stage_node(TeachingPackStage.PLANNING_BLUEPRINT)

        result = await stage_node(TeachingPackState(
            run_id="run-reclaim",
            completed_stages=[StageEnum.PLANNING_BLUEPRINT],
            lesson_plan={"topic": "Already done"},
        ))

        assert calls == []
        assert result.get("lesson_plan") == {"topic": "Already done"}

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
                    "learning_objectives": [
                        {"description": "Identify equivalent fractions", "bloom_level": "understand"},
                    ],
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
            "current_step": StageEnum.PLANNING_BLUEPRINT,
            "lesson_plan": None,
            "use_staged_planner": True,
            "persona_snapshot": {},
            "kt_mastery": {},
            "teacher_preferences": {},
        }]
        lesson_plan = result.get("lesson_plan", {})
        assert lesson_plan.get("topic") == "Fractions"

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
            "current_step": StageEnum.POST_BLUEPRINT_RESEARCH,
            "research_bundle": {"sources": []},
        }]
        research_brief = result.get("research_brief", {})
        assert research_brief.get("topic") == "Fractions"


class TestTeachingPackApprovalExport:
    def test_compliance_pass_routes_to_teacher_approval(self) -> None:
        state = TeachingPackState(run_id="run-compliance", compliance_passed=True)

        assert route_after_compliance_gate(state) == "teacher_approval"

    def test_compliance_failure_routes_to_artifact_workflow(self) -> None:
        state = TeachingPackState(run_id="run-compliance", compliance_passed=False)

        assert route_after_compliance_gate(state) == "artifact_workflow"

    def test_teacher_fast_lane_requires_compliance_passed(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        def fake_interrupt(payload):
            assert "auto_approved" not in payload
            return {"action": "approve"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.should_fast_lane", lambda *_args: True)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.record_gate_event", lambda *_args: None)
        monkeypatch.setattr("packages.agents.teaching_pack.teacher_memory.write_gate_approval", lambda *_args: None)
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")

        class StoreItem:
            value = {"events": [{"action": "approve", "artifact_types": ["lesson"]}]}

        class TrustStore:
            def get(self, _namespace, _key):
                return StoreItem()

        result = nodes._teacher_approval(
            TeachingPackState(
                run_id="run-fast-lane",
                contract={"teacher_id": "teacher-1"},
                compliance_passed=False,
                rendered_snapshots=[{"snapshot_id": "snap-1"}],
            ),
            store=TrustStore(),
        )

        assert result["teacher_approved"] is True
        assert result["approval_gate"].get("auto_approved") is None

    def test_teacher_fast_lane_still_opens_visible_gate(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        captured = {}

        def fake_interrupt(payload):
            captured.update(payload)
            return {}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.should_fast_lane", lambda *_args: True)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.record_gate_event", lambda *_args: None)
        monkeypatch.setattr("packages.agents.teaching_pack.teacher_memory.write_gate_approval", lambda *_args: None)
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")

        class StoreItem:
            value = {"events": [{"action": "approve", "artifact_types": ["lesson"]}]}

        class TrustStore:
            def get(self, _namespace, _key):
                return StoreItem()

        result = nodes._teacher_approval(
            TeachingPackState(
                run_id="run-fast-lane-visible",
                contract={"teacher_id": "teacher-1"},
                compliance_passed=True,
                rendered_snapshots=[{"snapshot_id": "snap-1"}],
                artifacts=[{"artifact_id": "lesson-1", "artifact_type": "lesson"}],
            ),
            store=TrustStore(),
        )

        assert captured["auto_approved"] is True
        assert captured["approval_mode"] == "auto_approved"
        assert captured["revert_window_seconds"] == 900
        assert captured["artifact_explanations"][0]["approval_mode"] == "auto_approved"
        assert result["teacher_approved"] is True
        assert result["gate_payload"] == {"action": "approve"}

    def test_escalated_teacher_gate_is_manual_required(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        captured = {}

        def fake_interrupt(payload):
            captured.update(payload)
            return {"action": "reject"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.should_fast_lane", lambda *_args: True)
        monkeypatch.setattr("packages.agents.teaching_pack.gate_trust.record_gate_event", lambda *_args: None)
        monkeypatch.setattr("packages.agents.teaching_pack.teacher_memory.write_gate_approval", lambda *_args: None)
        monkeypatch.setenv("GATE_FAST_LANE_THRESHOLD", "0.8")

        class StoreItem:
            value = {"events": [{"action": "approve", "artifact_types": ["lesson"]}]}

        class TrustStore:
            def get(self, _namespace, _key):
                return StoreItem()

        result = nodes._teacher_approval(
            TeachingPackState(
                run_id="run-escalated",
                contract={"teacher_id": "teacher-1"},
                compliance_passed=True,
                escalate=True,
                escalate_reason="Quality checks did not pass after 4 attempts.",
                healing_strategy="escalate",
                fail_count=4,
                rendered_snapshots=[{"snapshot_id": "snap-1"}],
                artifacts=[{"artifact_id": "lesson-1", "artifact_type": "lesson"}],
            ),
            store=TrustStore(),
        )

        assert captured["escalated"] is True
        assert captured["needs_review"] is True
        assert captured["approval_mode"] == "manual_required"
        assert "auto_approved" not in captured
        assert captured["healing_history"] == [{"strategy": "escalate", "fail_count": 4}]
        assert result["teacher_approved"] is False

    def test_render_quality_escalate_routes_to_teacher_approval(self) -> None:
        assert route_after_render_quality({"quality_recovery_route": "teacher_approval"}) == "teacher_approval"

    def test_teacher_gate_payload_explains_artifacts(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        captured = {}

        def fake_interrupt(payload):
            captured.update(payload)
            return {"action": "approve"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

        nodes._teacher_approval(TeachingPackState(
            run_id="run-explain",
            rendered_snapshots=[{"snapshot_id": "snap-quiz", "artifact_id": "quiz-1"}],
            artifacts=[{"artifact_id": "quiz-1", "artifact_type": "quiz"}],
            artifact_workflow_states=[{"artifact_id": "quiz-1", "artifact_type": "quiz", "status": "passed"}],
            quality_scores={
                "reports": [{
                    "artifact_id": "quiz-1",
                    "artifact_type": "quiz",
                    "passed": True,
                    "rationale": "Quiz aligns to the lesson objectives.",
                }],
            },
            healing_context={"history": [{"artifact_id": "quiz-1", "strategy": "rewrite"}]},
            artifact_generation_revision=2,
        ))

        explainable = captured["artifact_explanations"][0]
        assert explainable["artifact_id"] == "quiz-1"
        assert explainable["judge_rationale"] == "Quiz aligns to the lesson objectives."
        assert explainable["revision_count"] == 2
        assert explainable["healing_history"] == [{"artifact_id": "quiz-1", "strategy": "rewrite"}]
        assert explainable["approval_mode"] == "manual"

    def test_teacher_gate_payload_uses_per_artifact_revision_counts(self, monkeypatch) -> None:
        from packages.agents.teaching_pack import nodes

        captured = {}

        def fake_interrupt(payload):
            captured.update(payload)
            return {"action": "approve"}

        monkeypatch.setattr("langgraph.types.interrupt", fake_interrupt)

        nodes._teacher_approval(TeachingPackState(
            run_id="run-explain-revisions",
            artifacts=[
                {"artifact_id": "quiz-1", "artifact_type": "quiz", "revision_count": 3},
                {"artifact_id": "worksheet-1", "artifact_type": "worksheet"},
            ],
            artifact_revision_counts={"worksheet-1": 5},
            artifact_generation_revision=1,
        ))

        revisions = {
            item["artifact_id"]: item["revision_count"]
            for item in captured["artifact_explanations"]
        }
        assert revisions == {"quiz-1": 3, "worksheet-1": 5}

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

        assert result.get("exported_files") == ["exports/run-approval/snap-approved.html"]

    def test_export_blocks_when_teacher_rejects_content(self) -> None:
        state = TeachingPackState(
            run_id="run-rejected",
            teacher_approved=False,
            approved_snapshot_ids=["snap-ignored"],
        )

        result = _export_finalize(state)

        assert result.get("exported_files") == []

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

    def test_scoped_action_aliases_route_back_to_artifact_workflow(self) -> None:
        state = TeachingPackState(
            run_id="run-scoped-alias",
            teacher_approved=False,
            artifacts=[{"artifact_id": "quiz-1", "artifact_type": "quiz"}],
            gate_payload={
                "action": "reject_selected",
                "artifact_rejections": [{"artifact_id": "quiz-1", "reason": "Simplify."}],
            },
        )

        assert route_after_teacher_approval(state) == "artifact_workflow"

    def test_scoped_section_edit_routes_back_to_artifact_workflow(self) -> None:
        state = TeachingPackState(
            run_id="run-section-edit",
            teacher_approved=False,
            artifacts=[{"artifact_id": "lesson-1", "artifact_type": "lesson"}],
            gate_payload={
                "action": "edit",
                "edit_type": "scoped_section",
                "section_edit": {
                    "artifact_id": "lesson-1",
                    "section_id": "intro",
                    "replacement_content": "Revised intro.",
                    "rationale": "Align with objective.",
                },
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


def _valid_artifact(content: str = "Practice equivalent fractions with models.") -> dict[str, object]:
    return {
        "artifact_id": "worksheet-1",
        "artifact_type": "worksheet",
        "theme": "default",
        "title": "Equivalent Fractions Worksheet",
        "sections": [{"title": "Practice", "content": content}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


def _valid_snapshot(*, student_html: str | None = None, teacher_html: str | None = None) -> dict[str, object]:
    return {
        "snapshot_id": "snap-1",
        "student_rendered_html": student_html or _student_html("Practice equivalent fractions."),
        "rendered_html": teacher_html or _teacher_html("Teacher notes."),
    }


def _student_html(body: str) -> str:
    return f"<!DOCTYPE html><html lang='en'><head><meta name='viewport' content='width=device-width'></head><body>oh-my-class {body}</body></html>"


def _teacher_html(body: str) -> str:
    return f"<!DOCTYPE html><html lang='en'><head><meta name='viewport' content='width=device-width'></head><body>oh-my-class {body}</body></html>"


class TestComplianceGateNode:
    @pytest.mark.anyio
    async def test_valid_content_passes_through_stage_node(self) -> None:
        stage_node = make_stage_node(StageEnum.COMPLIANCE_GATE)

        result = await stage_node(TeachingPackState(
            run_id="run-compliance-pass",
            artifacts=[_valid_artifact()],
            rendered_snapshots=[_valid_snapshot()],
        ))

        assert result["compliance_passed"] is True
        assert route_after_compliance_gate(result) == "teacher_approval"
        assert result["current_stage"] is StageEnum.COMPLIANCE_GATE

    @pytest.mark.parametrize(
        ("html", "expected_code"),
        [
            ("<html lang='en'><body>oh-my-class</body></html>", "missing_doctype"),
            (_student_html("<link href='https://cdn.example.test/a.css'>"), "external_assets"),
            ("<!DOCTYPE html><html lang='en'><body>No brand</body></html>", "missing_brand_string"),
            (_student_html("<input type='radio' name='q'>"), "native_radio_inputs"),
            (_student_html("<script src='https://cdn.example.test/app.js'></script>"), "unmanaged_js_runtime"),
            (_student_html("<img src='data:image/png;base64,abc'>"), "missing_alt_text"),
            ("<!DOCTYPE html><html><body>oh-my-class</body></html>", "missing_lang"),
            (_student_html("<h1>Title</h1><h3>Skipped</h3>"), "broken_heading_order"),
            (_student_html("<input id='name' type='text'>"), "missing_form_label"),
            (_student_html("<p style='color:#777777;background-color:#777777'>Low</p>"), "contrast_below_aa"),
            (_student_html("<svg aria-label='Chart'></svg>"), "missing_long_description"),
            (_student_html("Answer: A"), "answer_key_leakage"),
        ],
    )
    @pytest.mark.anyio
    async def test_html_hard_block_fails_through_stage_node(self, html: str, expected_code: str) -> None:
        result = await make_stage_node(StageEnum.COMPLIANCE_GATE)(TeachingPackState(
            run_id=f"run-{expected_code}",
            artifacts=[_valid_artifact()],
            rendered_snapshots=[_valid_snapshot(student_html=html)],
        ))

        assert result["compliance_passed"] is False
        assert expected_code in result["compliance_result"]["violations"]
        assert route_after_compliance_gate(result) == "artifact_workflow"

    @pytest.mark.anyio
    async def test_pii_fails_and_emits_observability_event(self) -> None:
        from packages.agents.events import clear_run, get_run_events

        clear_run("run-pii")

        result = await make_stage_node(StageEnum.COMPLIANCE_GATE)(TeachingPackState(
            run_id="run-pii",
            artifacts=[_valid_artifact(content="Contact student at jane@example.test before class.")],
            rendered_snapshots=[_valid_snapshot()],
        ))

        events = get_run_events("run-pii")

        assert result["compliance_passed"] is False
        assert "pii_leakage" in result["compliance_result"]["violations"]
        assert any(event["event_type"] == "hard_block_violation" and event["code"] == "pii_leakage" for event in events)

    def test_teacher_only_answer_key_html_is_allowed(self) -> None:
        result = _compliance_gate(TeachingPackState(
            run_id="run-teacher-only",
            artifacts=[_valid_artifact()],
            rendered_snapshots=[_valid_snapshot(teacher_html=_teacher_html("Answer key: A"))],
        ))

        assert result["compliance_passed"] is True
