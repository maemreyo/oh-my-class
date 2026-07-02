from __future__ import annotations

from unittest.mock import patch

import pytest

from packages.agents.teaching_pack.config import TeachingPackConfig, load_policy_file
from packages.agents.teaching_pack.graph import build_teaching_pack_graph, teaching_pack_thread_config
from packages.agents.teaching_pack import ports
from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES, TeachingPackStage


class TestTeachingPackStages:
    def test_stage_values_are_stable_and_do_not_collide_with_v1_step_names(self) -> None:
        expected = (
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
            "artifact_workflow",
            "render_quality",
            "teacher_approval",
            "export_finalize",
        )

        actual = tuple(stage.value for stage in TEACHING_PACK_STAGES)

        assert actual == expected
        assert all(not value.startswith(("step_", "gate_")) for value in actual)

    def test_stage_event_names_are_serializable(self) -> None:
        stage = TeachingPackStage.ARTIFACT_WORKFLOW

        assert stage.started_event == "teaching_pack.artifact_workflow.started"
        assert stage.completed_event == "teaching_pack.artifact_workflow.completed"


class TestTeachingPackConfig:
    def test_default_config_is_valid(self) -> None:
        config = TeachingPackConfig()

        assert config.require_postgres is True
        assert config.default_artifact_parallelism == 2
        assert config.max_stage_duration_seconds > 0

    def test_rejects_negative_duration(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            TeachingPackConfig(max_stage_duration_seconds=-1)

    def test_rejects_zero_parallelism(self) -> None:
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            TeachingPackConfig(default_artifact_parallelism=0)

    def test_loads_valid_policy_file(self, tmp_path) -> None:
        policy_path = tmp_path / "teaching-packs-policy.yaml"
        policy_path.write_text(
            "version: v2-test\n"
            "research:\n"
            "  default_queries: 3\n"
            "  default_fetches: 4\n"
            "artifacts:\n"
            "  core_types:\n"
            "    - lesson\n"
            "    - worksheet\n"
            "    - quiz\n",
            encoding="utf-8",
        )

        policy = load_policy_file(policy_path)

        assert policy.version == "v2-test"
        assert policy.research.default_queries == 3
        assert policy.artifacts.core_types == ("lesson", "worksheet", "quiz")

    def test_rejects_missing_policy_file(self, tmp_path) -> None:
        missing_path = tmp_path / "missing.yaml"

        with pytest.raises(FileNotFoundError, match="missing.yaml"):
            load_policy_file(missing_path)

    def test_rejects_invalid_policy_yaml(self, tmp_path) -> None:
        policy_path = tmp_path / "invalid.yaml"
        policy_path.write_text("version: [", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid Teaching Pack policy YAML"):
            load_policy_file(policy_path)


class TestTeachingPackGraph:
    def test_graph_compiles_with_all_stage_nodes(self) -> None:
        # Build the real graph (the removed test_graph langgraph-mock helper is gone;
        # langgraph is a real dependency, so build directly). Node completeness is also
        # covered end-to-end by tests/e2e/test_canonical_flow.py.
        graph = build_teaching_pack_graph(checkpointer=None)

        assert graph is not None
        node_names = set(graph.get_graph().nodes)
        for stage in TEACHING_PACK_STAGES:
            assert stage.value in node_names

    def test_graph_instantiation_does_not_initialize_external_clients(self) -> None:
        # Invariant: constructing the graph must not eagerly initialize the LLM client.
        with patch(
            "packages.agents.llm.chat.LLMClient",
            side_effect=AssertionError("LLM client must not initialize during graph construction"),
        ):
            graph = build_teaching_pack_graph(checkpointer=None)

        assert graph is not None

    def test_thread_config_uses_run_id_as_langgraph_thread_id(self) -> None:
        # asf-005 added a top-level max_concurrency alongside the thread id.
        config = teaching_pack_thread_config("run-123")

        assert config["configurable"] == {"thread_id": "run-123"}
        assert config["max_concurrency"] >= 1


class TestTeachingPackPorts:
    def test_production_adapter_protocols_are_package_level(self) -> None:
        expected = {
            "RunStore",
            "EventWriter",
            "ArtifactSnapshotStore",
            "RunExecutor",
            "TeachingPackGraph",
            "LLMTransport",
            "SearchFetchClient",
            "ArtifactRenderer",
            "NotificationChannel",
            "QualityGate",
        }

        assert expected <= set(ports.__dict__)
