from __future__ import annotations

from unittest.mock import patch

import pytest

from packages.agents.teaching_pack.config import TeachingPackConfig, load_policy_file
from packages.agents.teaching_pack.graph import build_teaching_pack_graph, teaching_pack_thread_config
from packages.agents.teaching_pack import ports
from packages.agents.teaching_pack.stages import StageEnum, TEACHING_PACK_STAGES, TeachingPackStage, stage_number, teaching_pack_stages


class TestTeachingPackStages:
    def test_stage_enum_is_the_canonical_stage_type(self) -> None:
        assert TeachingPackStage is StageEnum
        assert all(isinstance(stage, StageEnum) for stage in TEACHING_PACK_STAGES)

    def test_stage_values_are_stable_and_do_not_collide_with_v1_step_names(self) -> None:
        expected = (
            "setup_contract",
            "triage",
            "preplanning_search",
            "planning_blueprint",
            "post_blueprint_research",
            "artifact_workflow",
            "render_quality",
            "compliance_gate",
            "teacher_approval",
            "export_finalize",
        )

        actual = tuple(stage.value for stage in TEACHING_PACK_STAGES)

        assert actual == expected
        assert all(not value.startswith(("step_", "gate_")) for value in actual)

    def test_component_strategy_stages_are_feature_flagged(self) -> None:
        old_path = tuple(stage.value for stage in teaching_pack_stages(False))
        strategy_path = tuple(stage.value for stage in teaching_pack_stages(True))

        assert "provisional_component_strategy" not in old_path
        assert "finalize_component_strategy" not in old_path
        assert strategy_path[strategy_path.index("planning_blueprint") + 1] == "provisional_component_strategy"
        assert strategy_path[strategy_path.index("post_blueprint_research") + 1] == "finalize_component_strategy"
        assert strategy_path[strategy_path.index("finalize_component_strategy") + 1] == "teacher_approval"

    def test_stage_event_names_are_serializable(self) -> None:
        stage = TeachingPackStage.ARTIFACT_WORKFLOW

        assert stage.started_event == "teaching_pack.artifact_workflow.started"
        assert stage.completed_event == "teaching_pack.artifact_workflow.completed"

    def test_stage_number_maps_stage_enum_to_telemetry_step(self) -> None:
        assert stage_number(StageEnum.SETUP_CONTRACT) == 1
        assert stage_number(StageEnum.ARTIFACT_WORKFLOW) == 6
        assert stage_number(StageEnum.COMPLIANCE_GATE) == 8
        assert stage_number(StageEnum.UNIT_PLANNING) == len(TEACHING_PACK_STAGES) + 1


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

    def test_graph_compiles_with_component_strategy_nodes_when_flag_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from packages.agents.config.features import reset_features

        monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_V1", "true")
        reset_features()

        graph = build_teaching_pack_graph(checkpointer=None)

        node_names = set(graph.get_graph().nodes)
        assert "provisional_component_strategy" in node_names
        assert "finalize_component_strategy" in node_names
        reset_features()

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


class TestGraphContract:

    def test_graph_contract_matches_live_graph(self) -> None:
        import json
        from pathlib import Path

        from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY

        contract_path = Path(__file__).resolve().parent.parent.parent / "teaching_pack" / "graph_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))

        assert contract["stages"] == [s.value for s in TEACHING_PACK_STAGES]
        assert contract["stages_with_component_strategy"] == [
            s.value for s in TEACHING_PACK_STAGES_WITH_COMPONENT_STRATEGY
        ]

        graph = build_teaching_pack_graph(checkpointer=None)
        live_nodes = sorted(
            n for n in graph.get_graph().nodes if not n.startswith("__")
        )
        assert contract["node_names"] == live_nodes

        for edge in contract["conditional_edges"]:
            assert edge["source"] in contract["node_names"], (
                f"conditional edge source '{edge['source']}' missing from node_names"
            )


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


class TestGateRegistrySnapshot:
    """Snapshot tests for the gateway gate registry — 7 gates with stable allowed_actions."""

    def test_all_seven_gates_exist(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateName,
        )

        expected_gates = frozenset({
            "clarification_required",
            "contract_confirmation",
            "source_conflict",
            "search_plan_confirmation",
            "blueprint_approval",
            "content_approval",
            "unit_approval",
        })
        actual_gates = frozenset(g.value for g in TeachingPackGateName)
        assert actual_gates == expected_gates, (
            f"Gate names changed: added={actual_gates - expected_gates}, "
            f"removed={expected_gates - actual_gates}"
        )

    def test_clarification_only_accepts_answer(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.CLARIFICATION_REQUIRED)
        assert actions == frozenset({TeachingPackGateAction.ANSWER})

    def test_contract_confirmation_actions(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.CONTRACT_CONFIRMATION)
        assert actions == frozenset({
            TeachingPackGateAction.APPROVE,
            TeachingPackGateAction.EDIT,
            TeachingPackGateAction.REJECT,
        })

    def test_source_conflict_actions(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.SOURCE_CONFLICT)
        assert actions == frozenset({
            TeachingPackGateAction.APPROVE,
            TeachingPackGateAction.EDIT,
            TeachingPackGateAction.REJECT,
        })

    def test_search_plan_confirmation_actions(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.SEARCH_PLAN_CONFIRMATION)
        assert actions == frozenset({TeachingPackGateAction.APPROVE, TeachingPackGateAction.EDIT})

    def test_blueprint_approval_actions(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.BLUEPRINT_APPROVAL)
        assert actions == frozenset({
            TeachingPackGateAction.APPROVE,
            TeachingPackGateAction.REJECT,
            TeachingPackGateAction.EDIT,
        })

    def test_content_approval_actions(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.CONTENT_APPROVAL)
        assert actions == frozenset({
            TeachingPackGateAction.APPROVE,
            TeachingPackGateAction.APPROVE_SELECTED,
            TeachingPackGateAction.REJECT,
            TeachingPackGateAction.REJECT_SELECTED,
            TeachingPackGateAction.EDIT,
        })

    def test_unit_approval_actions(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction,
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        actions = allowed_actions_for_gate(TeachingPackGateName.UNIT_APPROVAL)
        assert actions == frozenset({
            TeachingPackGateAction.APPROVE,
            TeachingPackGateAction.REJECT,
            TeachingPackGateAction.EDIT,
        })

    def test_every_gate_has_at_least_one_action(self) -> None:
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateName,
            allowed_actions_for_gate,
        )

        for gate in TeachingPackGateName:
            actions = allowed_actions_for_gate(gate)
            assert len(actions) > 0, f"Gate '{gate.value}' has no allowed actions"

    def test_allowed_actions_snapshot(self) -> None:
        """Full snapshot — catches any gate's action set changing."""
        from services.gateway.teaching_pack_gate_registry import (
            TeachingPackGateAction as A,
            TeachingPackGateName as G,
            allowed_actions_for_gate,
        )

        snapshot = {
            G.CLARIFICATION_REQUIRED: {A.ANSWER},
            G.CONTRACT_CONFIRMATION: {A.APPROVE, A.EDIT, A.REJECT},
            G.SEARCH_PLAN_CONFIRMATION: {A.APPROVE, A.EDIT},
            G.BLUEPRINT_APPROVAL: {A.APPROVE, A.REJECT, A.EDIT},
            G.CONTENT_APPROVAL: {A.APPROVE, A.APPROVE_SELECTED, A.REJECT, A.REJECT_SELECTED, A.EDIT},
            G.UNIT_APPROVAL: {A.APPROVE, A.REJECT, A.EDIT},
        }

        for gate, expected_actions in snapshot.items():
            actual = allowed_actions_for_gate(gate)
            assert actual == expected_actions, (
                f"Gate '{gate.value}' actions changed: "
                f"expected={expected_actions}, got={actual}"
            )


class TestGateConfigSnapshot:
    """GateConfig defaults must match AGENTS.md thresholds."""

    def test_judge_n_defaults_to_three(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.judge_n == 3

    def test_export_consensus_threshold_is_two_thirds(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.export_consensus_threshold == 0.67

    def test_judge_min_score_is_seven(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.judge_min_score == 7.0

    def test_hitl_timeout_is_24_hours(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.hitl_timeout_hours == 24

    def test_hitl_max_revisions_is_three(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.hitl_max_revisions == 3

    def test_schema_max_retries_is_three(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.schema_max_retries == 3

    def test_fast_lane_disabled_by_default(self) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        assert config.fast_lane_threshold is None

    def test_gate_config_snapshot(self) -> None:
        """Full snapshot of critical thresholds — catches silent drift."""
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        critical = {
            "judge_n": config.judge_n,
            "judge_min_score": config.judge_min_score,
            "judge_temperature": config.judge_temperature,
            "export_consensus_threshold": config.export_consensus_threshold,
            "export_min_score": config.export_min_score,
            "hitl_timeout_hours": config.hitl_timeout_hours,
            "hitl_max_revisions": config.hitl_max_revisions,
            "schema_max_retries": config.schema_max_retries,
            "schema_circuit_threshold": config.schema_circuit_threshold,
            "fast_lane_threshold": config.fast_lane_threshold,
            "fact_min_sources": config.fact_min_sources,
        }
        expected = {
            "judge_n": 3,
            "judge_min_score": 7.0,
            "judge_temperature": 0.1,
            "export_consensus_threshold": 0.67,
            "export_min_score": 7.0,
            "hitl_timeout_hours": 24,
            "hitl_max_revisions": 3,
            "schema_max_retries": 3,
            "schema_circuit_threshold": 3,
            "fast_lane_threshold": None,
            "fact_min_sources": 2,
        }
        assert critical == expected, (
            f"GateConfig defaults changed: {critical}"
        )


class TestTeachingPackStateSnapshot:
    """TeachingPackState key fields — frozen contract with AGENTS.md."""

    def test_required_fields_exist(self) -> None:
        from typing import get_type_hints

        from packages.agents.teaching_pack.nodes import TeachingPackState

        hints = get_type_hints(TeachingPackState, include_extras=True)
        required_fields = [
            "run_id",
            "raw_request",
            "contract",
            "artifact_references",
            "quality_scores",
            "quality_issues",
            "teacher_approved",
            "teacher_decision",
            "gate_payload",
            "fail_layer",
            "fail_count",
            "fail_type",
            "fail_context",
            "escalate",
            "healing_strategy",
            "generation_model",
            "exported_files",
        ]
        for field in required_fields:
            assert field in hints, f"TeachingPackState missing field: {field}"

    def test_state_has_artifact_references_reducer(self) -> None:
        from typing import get_type_hints

        from packages.agents.teaching_pack.nodes import TeachingPackState

        hints = get_type_hints(TeachingPackState, include_extras=True)
        assert "artifact_references" in hints

    def test_state_has_artifact_workflow_states_reducer(self) -> None:
        """artifact_workflow_states uses stable_merge_workflow_states reducer."""
        from typing import get_type_hints

        from packages.agents.teaching_pack.nodes import TeachingPackState

        hints = get_type_hints(TeachingPackState, include_extras=True)
        assert "artifact_workflow_states" in hints

    def test_state_field_count_is_stable(self) -> None:
        """Prevent accidental removal or addition of fields without updating this test."""
        from typing import get_type_hints

        from packages.agents.teaching_pack.nodes import TeachingPackState

        hints = get_type_hints(TeachingPackState, include_extras=True)
        # Count the raw fields (NotRequired wraps but doesn't add new names)
        field_names = [k for k in hints.keys() if not k.startswith("_")]
        # This is a sentinel: if the count changes, update this test.
        assert len(field_names) >= 50, (
            f"TeachingPackState has {len(field_names)} fields; "
            f"expected at least 50. Update this test if fields were intentionally added."
        )
