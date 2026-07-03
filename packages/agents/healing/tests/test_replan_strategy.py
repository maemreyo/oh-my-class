from __future__ import annotations


class TestReplanStrategy:
    def test_clears_all_downstream_state(self):
        from packages.agents.healing.strategies.replan import apply

        result = apply({}, 3)

        assert result["artifact_chunks"] is None
        assert result["quality_scores"] is None
        assert result["quality_recovery_route"] == "artifact_workflow"

    def test_preserves_unaffected_wave_one_artifacts_for_wave_two_failure(self):
        from packages.agents.healing.strategies.replan import apply

        state = {
            "fail_context": {"artifact_id": "quiz-1"},
            "artifact_chunks": [
                {"artifact_id": "lesson-1", "artifact_type": "lesson"},
                {"artifact_id": "worksheet-1", "artifact_type": "worksheet"},
                {"artifact_id": "quiz-1", "artifact_type": "quiz"},
                {"artifact_id": "drill-1", "artifact_type": "drill"},
                {"artifact_id": "recap-1", "artifact_type": "recap"},
            ],
            "artifacts": [
                {"artifact_id": "lesson-1", "artifact_type": "lesson"},
                {"artifact_id": "worksheet-1", "artifact_type": "worksheet"},
                {"artifact_id": "quiz-1", "artifact_type": "quiz"},
                {"artifact_id": "drill-1", "artifact_type": "drill"},
                {"artifact_id": "recap-1", "artifact_type": "recap"},
            ],
            "artifact_workflow_states": [
                {"artifact_id": "lesson-1", "artifact_type": "lesson", "status": "passed"},
                {"artifact_id": "quiz-1", "artifact_type": "quiz", "status": "failed"},
                {"artifact_id": "recap-1", "artifact_type": "recap", "status": "blocked"},
            ],
            "rendered_snapshots": [
                {"artifact_id": "lesson-1", "artifact_type": "lesson"},
                {"artifact_id": "quiz-1", "artifact_type": "quiz"},
                {"artifact_id": "recap-1", "artifact_type": "recap"},
            ],
            "quality_scores": {
                "reports": [
                    {"artifact_id": "lesson-1", "artifact_type": "lesson"},
                    {"artifact_id": "quiz-1", "artifact_type": "quiz"},
                    {"artifact_id": "recap-1", "artifact_type": "recap"},
                ],
            },
        }

        result = apply(state, 3)

        assert [chunk["artifact_id"] for chunk in result["artifact_chunks"]] == [
            "lesson-1",
            "worksheet-1",
            "drill-1",
        ]
        assert [artifact["artifact_id"] for artifact in result["artifacts"]] == [
            "lesson-1",
            "worksheet-1",
            "drill-1",
        ]
        assert [state["artifact_id"] for state in result["artifact_workflow_states"]] == [
            "lesson-1",
        ]
        assert [snapshot["artifact_id"] for snapshot in result["rendered_snapshots"]] == [
            "lesson-1",
        ]
        assert result["quality_scores"] == {
            "reports": [{"artifact_id": "lesson-1", "artifact_type": "lesson"}],
        }
        assert result["quality_recovery_route"] == "artifact_workflow"

    def test_full_replan_is_reserved_for_upstream_failures(self):
        from packages.agents.healing.strategies.replan import apply

        result = apply({"fail_context": {"stage": "planning_blueprint"}}, 3)

        assert result["artifact_chunks"] is None
        assert result["quality_scores"] is None
        assert result["quality_recovery_route"] == "planning_blueprint"

    def test_returns_replan_strategy(self):
        from packages.agents.healing.strategies.replan import apply

        result = apply({}, 3)

        assert result["healing_strategy"] == "replan"
