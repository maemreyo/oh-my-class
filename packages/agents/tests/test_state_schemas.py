"""Tests for F2 per-agent state schemas.

Each sub-agent has its own state — independently instantiable, no OhMyClassState dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TestPlannerState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.sub_agents.planner.state import PlannerState

        state = PlannerState(
            messages=[],
            raw_request="Teach photosynthesis to grade 5",
            class_info={"grade": 5, "subject": "science"},
            run_id="run-001",
            current_step=3,
            lesson_plan=None,
        )
        assert state["raw_request"] == "Teach photosynthesis to grade 5"
        assert state["lesson_plan"] is None

    def test_has_messages_from_messages_state(self):
        from packages.agents.sub_agents.planner.state import PlannerState

        state = PlannerState(
            messages=[],
            raw_request="req",
            class_info={},
            run_id="r",
            current_step=3,
            lesson_plan=None,
        )
        assert "messages" in state
        assert state["messages"] == []

    def test_lesson_plan_can_be_set(self):
        from packages.agents.sub_agents.planner.state import PlannerState

        plan = {"topic": "Photosynthesis", "grade_level": "Grade 5"}
        state = PlannerState(
            messages=[],
            raw_request="req",
            class_info={},
            run_id="r",
            current_step=3,
            lesson_plan=plan,
        )
        assert state["lesson_plan"] == plan

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.planner.state as mod

        # No import of OhMyClassState — graph coupling must stay in adapters
        source = inspect.getsource(mod)
        assert "from packages.agents.state import" not in source
        assert "import OhMyClassState" not in source


class TestResearcherState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.sub_agents.researcher.state import ResearcherState

        state = ResearcherState(
            messages=[],
            lesson_plan={"topic": "Photosynthesis"},
            research_policy="standard",
            run_id="run-001",
            current_step=7,
            research_bundle=None,
        )
        assert state["lesson_plan"]["topic"] == "Photosynthesis"
        assert state["research_policy"] == "standard"
        assert state["research_bundle"] is None

    def test_has_messages_from_messages_state(self):
        from packages.agents.sub_agents.researcher.state import ResearcherState

        state = ResearcherState(
            messages=[],
            lesson_plan={},
            research_policy="basic",
            run_id="r",
            current_step=7,
            research_bundle=None,
        )
        assert "messages" in state

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.researcher.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents.state import" not in source
        assert "import OhMyClassState" not in source


class TestUnitPlannerState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.sub_agents.unit_planner.state import UnitPlannerState

        state = UnitPlannerState(
            messages=[],
            raw_request="Plan a unit about fractions",
            class_info={"grade": 5, "subject": "math"},
            grounding={"grounding_status": "grounded"},
            persona_snapshot=None,
            run_id="run-001",
            current_step=1,
            lesson_sequence=None,
        )
        assert state["grounding"]["grounding_status"] == "grounded"
        assert state["lesson_sequence"] is None

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.unit_planner.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents.state import" not in source
        assert "import OhMyClassState" not in source


class TestContentCreatorState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.sub_agents.content_creator.state import ContentCreatorState

        state = ContentCreatorState(
            messages=[],
            lesson_plan={"topic": "X"},
            research_bundle={"topic": "X", "sources": []},
            artifact_types=["lesson", "quiz"],
            theme="default",
            run_id="run-001",
            current_step=8,
            artifacts=None,
        )
        assert state["artifact_types"] == ["lesson", "quiz"]
        assert state["theme"] == "default"
        assert state["artifacts"] is None

    def test_artifacts_can_be_set(self):
        from packages.agents.sub_agents.content_creator.state import ContentCreatorState

        arts = [{"artifact_type": "lesson", "title": "Lesson 1"}]
        state = ContentCreatorState(
            messages=[],
            lesson_plan={},
            research_bundle={},
            artifact_types=["lesson"],
            theme="default",
            run_id="r",
            current_step=8,
            artifacts=arts,
        )
        assert state["artifacts"] == arts

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.content_creator.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents.state import" not in source
        assert "import OhMyClassState" not in source


class TestReviewerState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.sub_agents.reviewer.state import ReviewerState

        state = ReviewerState(
            messages=[],
            artifacts=[{"artifact_type": "lesson", "title": "L1"}],
            lesson_plan={"topic": "Photosynthesis"},
            quality_scores=None,
            quality_passed=None,
        )
        assert len(state["artifacts"]) == 1
        assert state["quality_scores"] is None
        assert state["quality_passed"] is None

    def test_quality_scores_can_be_set(self):
        from packages.agents.sub_agents.reviewer.state import ReviewerState

        scores = {"overall": 8.5, "passed": True}
        state = ReviewerState(
            messages=[],
            artifacts=[],
            lesson_plan={},
            quality_scores=scores,
            quality_passed=True,
        )
        assert state["quality_scores"] == scores
        assert state["quality_passed"] is True

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.reviewer.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents.state import" not in source
        assert "import OhMyClassState" not in source


class TestLeadAgentState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.lead_agent.state import LeadAgentState

        state = LeadAgentState(  # pyright: ignore[reportCallIssue]
            messages=[],
            task="Generate a lesson on photosynthesis",
            context={"raw_request": "Teach photosynthesis", "run_id": "r1"},
            result=None,
            recovery_guidance=None,
        )
        assert state["task"] == "Generate a lesson on photosynthesis"
        assert state["result"] is None
        assert state["recovery_guidance"] is None

    def test_result_can_be_set(self):
        from packages.agents.lead_agent.state import LeadAgentState

        state = LeadAgentState(  # pyright: ignore[reportCallIssue]
            messages=[],
            task="task",
            context={},
            result={"lesson_plan": {"topic": "X"}},
            recovery_guidance=None,
        )
        assert state["result"]["lesson_plan"]["topic"] == "X"  # pyright: ignore[reportOptionalSubscript]

    def test_recovery_guidance_can_be_set(self):
        from packages.agents.lead_agent.state import LeadAgentState

        state = LeadAgentState(  # pyright: ignore[reportCallIssue]
            messages=[],
            task="task",
            context={},
            result=None,
            recovery_guidance="Try with simpler vocabulary",
        )
        assert state["recovery_guidance"] == "Try with simpler vocabulary"

    def test_has_messages_from_messages_state(self):
        from packages.agents.lead_agent.state import LeadAgentState

        state = LeadAgentState(  # pyright: ignore[reportCallIssue]
            messages=[],
            task="task",
            context={},
            result=None,
            recovery_guidance=None,
        )
        assert "messages" in state

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.lead_agent.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents.state import" not in source
        assert "import OhMyClassState" not in source


class TestOhMyClassStateGateFields:
    """OhMyClassState must have gate/error fields for HITL and error routing."""

    def test_has_teacher_decision_field(self):
        import inspect

        import packages.agents.state as mod

        source = inspect.getsource(mod)
        assert "teacher_decision" in source

    def test_has_gate_payload_field(self):
        import inspect

        import packages.agents.state as mod

        source = inspect.getsource(mod)
        assert "gate_payload" in source

    def test_has_error_field(self):
        import inspect

        import packages.agents.state as mod

        source = inspect.getsource(mod)
        assert "error" in source

    def test_graph_state_instantiates(self):

        state: OhMyClassState = {
            "raw_request": "Teach photosynthesis",
            "teacher_id": "teacher-001",
            "class_info": {"grade": 5},
            "run_id": "run-001",
            "blueprint_approved": False,
            "research_policy": "standard",
            "artifact_types": ["lesson"],
            "theme": "default",
            "artifacts": [],
            "quality_passed": False,
            "teacher_approved": False,
            "revision_count": 0,
            "export_formats": ["html"],
            "exported_files": [],
            "current_step": 1,
            "tokens_used": 0,
            "cost_usd": 0.0,
        }
        assert state["run_id"] == "run-001"
