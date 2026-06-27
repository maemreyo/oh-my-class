from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from packages.agents.pipeline_v2.config import PipelineV2Config, load_policy_file
from packages.agents.pipeline_v2.graph import build_pipeline_v2_graph, pipeline_v2_thread_config
from packages.agents.pipeline_v2 import ports
from packages.agents.pipeline_v2.stages import PIPELINE_V2_STAGES, PipelineV2Stage


class TestPipelineV2Stages:
    def test_stage_values_are_stable_and_do_not_collide_with_v1_step_names(self) -> None:
        expected = (
            "setup_contract",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
            "artifact_workflow",
            "render_quality",
            "teacher_approval",
            "export_finalize",
        )

        actual = tuple(stage.value for stage in PIPELINE_V2_STAGES)

        assert actual == expected
        assert all(not value.startswith(("step_", "gate_")) for value in actual)

    def test_stage_event_names_are_serializable(self) -> None:
        stage = PipelineV2Stage.ARTIFACT_WORKFLOW

        assert stage.started_event == "pipeline_v2.artifact_workflow.started"
        assert stage.completed_event == "pipeline_v2.artifact_workflow.completed"


class TestPipelineV2Config:
    def test_default_config_is_valid(self) -> None:
        config = PipelineV2Config()

        assert config.require_postgres is True
        assert config.default_artifact_parallelism == 2
        assert config.max_stage_duration_seconds > 0

    def test_rejects_negative_duration(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            PipelineV2Config(max_stage_duration_seconds=-1)

    def test_rejects_zero_parallelism(self) -> None:
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            PipelineV2Config(default_artifact_parallelism=0)

    def test_loads_valid_policy_file(self, tmp_path) -> None:
        policy_path = tmp_path / "pipeline-v2-policy.yaml"
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

        with pytest.raises(ValueError, match="Invalid Pipeline V2 policy YAML"):
            load_policy_file(policy_path)


class TestPipelineV2Graph:
    def test_graph_compiles_with_all_stage_nodes(self) -> None:
        from packages.agents.tests.test_graph import _make_langgraph_mocks

        mocks, _, nodes = _make_langgraph_mocks()

        with patch.dict("sys.modules", mocks):
            graph = build_pipeline_v2_graph(checkpointer=MagicMock())

        assert graph is not None
        assert tuple(nodes) == tuple(stage.value for stage in PIPELINE_V2_STAGES)

    def test_graph_instantiation_does_not_initialize_external_clients(self) -> None:
        from packages.agents.tests.test_graph import _make_langgraph_mocks

        mocks, _, _ = _make_langgraph_mocks()

        with patch.dict("sys.modules", mocks), patch(
            "packages.agents.llm.chat.AsyncOpenAI",
            side_effect=AssertionError("LLM client must not initialize during graph construction"),
        ):
            graph = build_pipeline_v2_graph(checkpointer=MagicMock())

        assert graph is not None

    def test_thread_config_uses_run_id_as_langgraph_thread_id(self) -> None:
        config = pipeline_v2_thread_config("run-123")

        assert config == {"configurable": {"thread_id": "run-123"}}


class TestPipelineV2Ports:
    def test_production_adapter_protocols_are_package_level(self) -> None:
        expected = {
            "RunStore",
            "EventWriter",
            "ArtifactSnapshotStore",
            "RunExecutor",
            "PipelineV2Graph",
            "LLMTransport",
            "SearchFetchClient",
            "ArtifactRenderer",
            "NotificationChannel",
            "QualityGate",
        }

        assert expected <= set(ports.__dict__)
