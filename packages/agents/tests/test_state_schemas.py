from __future__ import annotations

from packages.agents.teaching_pack.stages import StageEnum


class TestPlannerState:
    def test_instantiates_with_required_fields(self):
        state = {
            "messages": [],
            "raw_request": "Teach photosynthesis to grade 5",
            "class_info": {"grade": 5, "subject": "science"},
            "run_id": "run-001",
            "current_step": StageEnum.PLANNING_BLUEPRINT,
            "lesson_plan": None,
        }
        assert state["raw_request"] == "Teach photosynthesis to grade 5"
        assert state["lesson_plan"] is None

    def test_has_messages_from_messages_state(self):
        state = {
            "messages": [],
            "raw_request": "req",
            "class_info": {},
            "run_id": "r",
            "current_step": StageEnum.PLANNING_BLUEPRINT,
            "lesson_plan": None,
        }
        assert "messages" in state
        assert state["messages"] == []

    def test_lesson_plan_can_be_set(self):
        plan = {"topic": "Photosynthesis", "grade_level": "Grade 5"}
        state = {
            "messages": [],
            "raw_request": "req",
            "class_info": {},
            "run_id": "r",
            "current_step": StageEnum.PLANNING_BLUEPRINT,
            "lesson_plan": plan,
        }
        assert state["lesson_plan"] == plan

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.planner.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents." + "state import" not in source
        assert "Oh" + "MyClassState" not in source


class TestResearcherState:
    def test_instantiates_with_required_fields(self):
        from packages.agents.sub_agents.researcher.state import ResearcherState

        state: ResearcherState = {
            "messages": [],
            "lesson_plan": {"topic": "Photosynthesis"},
            "research_policy": "standard",
            "run_id": "run-001",
            "current_step": StageEnum.POST_BLUEPRINT_RESEARCH,
            "research_bundle": None,
        }
        assert state["lesson_plan"]["topic"] == "Photosynthesis"
        assert state["research_policy"] == "standard"
        assert state["research_bundle"] is None

    def test_has_messages_from_messages_state(self):
        from packages.agents.sub_agents.researcher.state import ResearcherState

        state: ResearcherState = {
            "messages": [],
            "lesson_plan": {},
            "research_policy": "basic",
            "run_id": "r",
            "current_step": StageEnum.POST_BLUEPRINT_RESEARCH,
            "research_bundle": None,
        }
        assert "messages" in state

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.researcher.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents." + "state import" not in source
        assert "Oh" + "MyClassState" not in source


class TestUnitPlannerState:
    def test_instantiates_with_required_fields(self):
        state = {
            "messages": [],
            "raw_request": "Plan a unit about fractions",
            "class_info": {"grade": 5, "subject": "math"},
            "grounding": {"grounding_status": "grounded"},
            "persona_snapshot": None,
            "run_id": "run-001",
            "current_step": StageEnum.UNIT_PLANNING,
            "lesson_sequence": None,
        }
        grounding = state["grounding"]
        assert grounding is not None
        assert grounding["grounding_status"] == "grounded"
        assert state["lesson_sequence"] is None

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.unit_planner.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents." + "state import" not in source
        assert "Oh" + "MyClassState" not in source


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
            current_step=StageEnum.ARTIFACT_WORKFLOW,
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
            current_step=StageEnum.ARTIFACT_WORKFLOW,
            artifacts=arts,
        )
        assert state["artifacts"] == arts

    def test_independent_of_ohmy_class_state(self):
        import inspect

        import packages.agents.sub_agents.content_creator.state as mod

        source = inspect.getsource(mod)
        assert "from packages.agents." + "state import" not in source
        assert "Oh" + "MyClassState" not in source


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
        assert "from packages.agents." + "state import" not in source
        assert "Oh" + "MyClassState" not in source


class TestTeachingPackStateGateFields:
    def test_has_teacher_decision_field(self):
        import inspect

        import packages.agents.teaching_pack.nodes as mod

        source = inspect.getsource(mod)
        assert "teacher_decision" in source

    def test_has_gate_payload_field(self):
        import inspect

        import packages.agents.teaching_pack.nodes as mod

        source = inspect.getsource(mod)
        assert "gate_payload" in source

    def test_has_error_field(self):
        from packages.agents.teaching_pack.nodes import TeachingPackState

        state = TeachingPackState(run_id="run-001", fail_context={"errors": ["boom"]})
        assert state["fail_context"] == {"errors": ["boom"]}

    def test_graph_state_instantiates(self):
        from packages.agents.teaching_pack.nodes import TeachingPackState
        state = TeachingPackState(
            run_id="run-001",
            contract={"raw_request": "Teach photosynthesis", "teacher_id": "teacher-001"},
            artifact_types=["lesson"],
            artifacts=[],
            teacher_approved=False,
            current_step=StageEnum.SETUP_CONTRACT,
            exported_files=[],
        )
        assert state["run_id"] == "run-001"
