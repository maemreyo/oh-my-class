from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, NotRequired, TypedDict, assert_never

from packages.agents.sub_agents.planner.state import PlannerNodeState
from packages.agents.sub_agents.researcher.state import ResearcherNodeState

from packages.agents.teaching_pack.artifact_fanout import coordinate_artifact_fanout
from packages.agents.teaching_pack.artifact_status import (
    artifact_statuses_for_teacher,
    export_block_reason,
    unavailable_required_artifact_statuses,
)
from packages.agents.teaching_pack.exporters import ExportRequest, ExporterRegistry, requested_export_formats
from packages.agents.teaching_pack.features import artifact_send_fanout_v1_enabled
from packages.agents.teaching_pack.middleware_runtime import (
    run_entry_middleware as _run_entry_middleware,
    run_gate_middleware as _run_gate_middleware,
    run_generation_context_middleware as _run_generation_context_middleware,
)
from packages.agents.teaching_pack.quality_runtime import render_quality
from packages.agents.teaching_pack.reducers import stable_merge_artifacts, stable_merge_workflow_states
from packages.agents.teaching_pack.scoped_regeneration import (
    apply_scoped_section_edit,
    has_scoped_section_edit,
    rejected_artifact_types,
    scoped_rejections,
)
from packages.agents.teaching_pack.stages import StageEnum
from packages.agents.teaching_pack.teacher_gate_payload import (
    artifact_explanations_for_teacher,
    is_scoped_teacher_action,
    normalized_teacher_action,
)

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

    from packages.agents.teaching_pack.ports import QualityGate

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class TeachingPackState(TypedDict):
    run_id: str
    raw_request: NotRequired[str]
    contract: NotRequired[JsonObject]
    current_stage: NotRequired[StageEnum]
    current_step: NotRequired[StageEnum]
    completed_stages: NotRequired[list[StageEnum]]
    research_brief: NotRequired[JsonObject]
    lesson_plan: NotRequired[JsonObject]
    lesson_sequence: NotRequired[JsonObject]
    sequence_critiques: NotRequired[list[JsonObject]]
    seq_revision: NotRequired[int]
    unit_context: NotRequired[JsonObject]
    artifact_types: NotRequired[list[str]]
    artifact_generation_id: NotRequired[str]
    artifact_generation_revision: NotRequired[int]
    artifact_wave_index: NotRequired[int]
    artifact_fanout_complete: NotRequired[bool]
    artifact_fanout_blocked: NotRequired[bool]
    artifact_regeneration_scope: NotRequired[JsonObject]
    # Sequential pipeline writes complete list; no reducer (replace semantics).
    artifacts: NotRequired[list[JsonObject]]
    # Branch staging only: Send workers write generated content chunks here.
    # Fan-in materializes current-generation chunks into canonical artifacts.
    artifact_chunks: NotRequired[Annotated[list[JsonObject], stable_merge_artifacts]]
    # Branch status only: Send workers write per-artifact workflow states here.
    # Fan-in reads current-generation statuses; downstream stages read artifacts.
    artifact_workflow_states: NotRequired[Annotated[list[JsonObject], stable_merge_workflow_states]]
    rendered_snapshots: NotRequired[list[JsonObject]]
    quality_scores: NotRequired[JsonObject]
    quality_issues: NotRequired[list[str]]
    quality_recovery_route: NotRequired[str]
    compliance_passed: NotRequired[bool]
    compliance_result: NotRequired[JsonObject]
    fail_layer: NotRequired[str | None]
    fail_count: NotRequired[int]
    fail_type: NotRequired[str | None]
    fail_context: NotRequired[JsonObject | None]
    escalate: NotRequired[bool]
    escalate_reason: NotRequired[str | None]
    healing_strategy: NotRequired[str | None]
    healing_note: NotRequired[str | None]
    healing_context: NotRequired[JsonObject | None]
    generation_model: NotRequired[str | None]
    content_update_event: NotRequired[JsonObject]
    approval_gate: NotRequired[JsonObject]
    teacher_approved: NotRequired[bool]
    teacher_decision: NotRequired[str]
    gate_payload: NotRequired[JsonObject]
    revision_feedback: NotRequired[str]
    approved_snapshot_ids: NotRequired[list[str]]
    exported_files: NotRequired[list[str]]
    export_blocked: NotRequired[bool]
    export_block_reason: NotRequired[str]
    artifact_statuses: NotRequired[list[JsonObject]]
    vocabulary_cluster_workflows: NotRequired[list[JsonObject]]
    vocabulary_batch_progress: NotRequired[JsonObject]
    vocabulary_batch_events: NotRequired[list[JsonObject]]
    input_normalization_report: NotRequired[JsonObject]
    diagnostic_report: NotRequired[JsonObject]
    kt_mastery: NotRequired[JsonObject]
    diagnostic_stage: NotRequired[JsonObject]
    teacher_preferences: NotRequired[JsonObject]
    component_effectiveness: NotRequired[JsonObject]
    component_strategy_result: NotRequired[JsonObject]
    component_strategy_plan: NotRequired[JsonObject]
    component_strategy_summary: NotRequired[JsonObject]
    component_strategy_hypotheses: NotRequired[list[str]]
    component_strategy_research_questions: NotRequired[list[str]]
    component_strategy_rollout: NotRequired[JsonObject]


def make_stage_node(
    stage: StageEnum,
    quality_gate: QualityGate | None = None,
    store: BaseStore | None = None,
):
    async def stage_node(state: TeachingPackState) -> TeachingPackState:
        if stage in state.get("completed_stages", []) and not _can_reenter_stage(state, stage):
            return state
        from packages.agents.events import emit_run_event

        emit_run_event(state["run_id"], "stage_transition", {
            "stage": stage.value,
            "status": "started",
        })
        completed_successfully = False
        try:
            match stage.value:
                case "setup_contract":
                    state = await _run_entry_middleware(state)
                    update = _setup_contract(state)
                case "triage":
                    update = await _triage(state)
                case "unit_planning":
                    update = await _unit_planning(state)
                case "unit_approval":
                    update = _unit_approval(state)
                case "unit_prep":
                    update = _unit_prep(state)
                case "preplanning_search":
                    update = _preplanning_search(state)
                case "planning_blueprint":
                    update = await _planning_blueprint(state, store=store)
                case "provisional_component_strategy":
                    update = _provisional_component_strategy(state)
                case "post_blueprint_research":
                    update = await _post_blueprint_research(state)
                case "finalize_component_strategy":
                    update = _finalize_component_strategy(state)
                case "artifact_workflow":
                    update = await _artifact_workflow(state)
                case "render_quality":
                    update = await _render_quality(state, quality_gate=quality_gate)
                case "compliance_gate":
                    update = _compliance_gate(state)
                case "teacher_approval":
                    update = await _teacher_approval_with_middleware(state, store=store)
                case "export_finalize":
                    update = _export_finalize(state, store=store)
                case unreachable:
                    assert_never(unreachable)
            merged_state = state.copy()
            merged_state.update(update)
            if stage.value == "artifact_workflow" and artifact_send_fanout_v1_enabled():
                if not merged_state.get("artifact_fanout_complete", False):
                    completed_successfully = True
                    return merged_state
            completed = _complete_stage(merged_state, stage)
            emit_run_event(state["run_id"], "stage_transition", {
                "stage": stage.value,
                "status": "completed",
            })
            completed_successfully = True
            return completed
        finally:
            if not completed_successfully:
                emit_run_event(state["run_id"], "stage_transition", {
                    "stage": stage.value,
                    "status": "failed",
                })

    stage_node.__name__ = stage.value
    return stage_node


def _setup_contract(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    artifact_types = _artifact_types(contract)
    return {
        "run_id": state["run_id"],
        "contract": contract,
        "artifact_types": artifact_types,
    }


async def _triage(state: TeachingPackState) -> TeachingPackState:
    from packages.agents.teaching_pack.triage import run_triage
    return TeachingPackState(**await run_triage(state))


async def _unit_planning(state: TeachingPackState) -> TeachingPackState:
    from common.contracts.lesson_sequence import LessonSequence
    from packages.agents.sub_agents.unit_planner.nodes import unit_planner_node
    from packages.agents.sub_agents.unit_planner.sequence_critic import (
        CritiqueSeverity,
        critique_sequence,
        repair_hard_critiques,
    )

    contract = state.get("contract", {})
    result = await unit_planner_node({
        "raw_request": _string_field(contract, "raw_request", _topic(contract)),
        "class_info": _class_info(contract),
        "grounding": _json_object(contract.get("grounding")),
        "persona_snapshot": _json_object(contract.get("persona_snapshot")),
        "run_id": state["run_id"],
        "current_step": StageEnum.UNIT_PLANNING,
    })
    sequence = LessonSequence.model_validate(result["lesson_sequence"])
    critiques = critique_sequence(sequence)
    if any(critique.severity is CritiqueSeverity.HARD for critique in critiques):
        sequence = repair_hard_critiques(sequence)
        critiques = critique_sequence(sequence)
    return {
        "run_id": state["run_id"],
        "lesson_sequence": sequence.model_dump(mode="json"),
        "sequence_critiques": [critique.as_dict() for critique in critiques],
        "seq_revision": int(state.get("seq_revision", 0)) + 1,
    }


def _unit_approval(state: TeachingPackState) -> TeachingPackState:
    from langgraph.types import interrupt

    gate_payload: JsonObject = {
        "gate": "unit_approval",
        "gate_name": "unit_approval",
        "run_id": state["run_id"],
        "lesson_sequence": state.get("lesson_sequence", {}),
        "grounding_status": _string_field(state.get("lesson_sequence", {}), "grounding_status", "ungrounded"),
        "sequence_critiques": [*state.get("sequence_critiques", [])],
        "seq_revision": state.get("seq_revision", 1),
    }
    response = interrupt(gate_payload)
    action = _string_field(response, "action", "reject")
    feedback = _string_field(response, "feedback", "")
    return {
        "run_id": state["run_id"],
        "approval_gate": gate_payload,
        "gate_payload": response,
        "teacher_approved": action == "approve",
        "teacher_decision": action,
        "revision_feedback": feedback,
        "seq_revision": int(state.get("seq_revision", 1)) + (1 if action == "edit" else 0),
    }


def _unit_prep(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    unit_context: JsonObject = {
        "locked_theme": _string_field(contract, "theme", "default"),
        "shared_research": state.get("research_brief", {"sources": []}),
        "persona_snapshot": _json_object(contract.get("persona_snapshot")),
    }
    return {"run_id": state["run_id"], "unit_context": unit_context}


def _preplanning_search(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    return {
        "run_id": state["run_id"],
        "research_brief": {
            "policy": _string_field(contract, "research_policy", "standard"),
            "topic": _topic(contract),
            "sources": [
                {
                    "title": "Teacher-provided lesson context",
                    "summary": _topic(contract),
                    "source_type": "contract",
                },
            ],
        },
    }


async def _planning_blueprint(
    state: TeachingPackState,
    *,
    store: BaseStore | None = None,
) -> TeachingPackState:
    state = await _run_generation_context_middleware("planner", state, 3)
    contract = state.get("contract", {})
    diagnostic_update = await _diagnostic_preplanning(state)
    if diagnostic_update:
        state = TeachingPackState(**{**state, **diagnostic_update})
    from packages.agents.sub_agents.planner.nodes import planner_node
    from common.contracts.seam_contracts import PlannerHandoff

    class_info = _class_info(contract)
    if store is not None:
        teacher_id = _string_field(contract, "teacher_id", "")
        if teacher_id:
            from packages.agents.teaching_pack.teacher_memory import read_class_vocabulary
            vocab_ctx = read_class_vocabulary(
                store, teacher_id,
                _string_field(contract, "subject", "general"),
                _string_field(contract, "grade_band", "Grade 5"),
            )
            if vocab_ctx["vocabulary"] or vocab_ctx["topics"]:
                class_info = {
                    **class_info,
                    "prior_vocabulary": vocab_ctx["vocabulary"],
                    "prior_topics": vocab_ctx["topics"],
                }

    planner_state: PlannerNodeState = {
        "raw_request": _string_field(contract, "raw_request", _topic(contract)),
        "class_info": class_info,
        "run_id": state["run_id"],
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "lesson_plan": None,
        "use_staged_planner": True,
        "persona_snapshot": _json_object(state.get("persona_snapshot")),
        "kt_mastery": _json_object(state.get("kt_mastery")),
        "teacher_preferences": _json_object(state.get("teacher_preferences")),
    }
    result = await planner_node(planner_state)
    lesson_plan = _json_object(result.get("lesson_plan"))
    PlannerHandoff(lesson_plan=lesson_plan)  # fail-closed seam contract
    update: TeachingPackState = {
        "run_id": state["run_id"],
        "lesson_plan": lesson_plan,
        # Signal downstream to re-run: allows artifact_workflow and render_quality to
        # re-enter completed_stages. coordinate_artifact_fanout's _needs_new_generation_cycle
        # detects artifact_fanout_complete=True + quality_recovery_route="artifact_workflow"
        # and starts a fresh generation revision automatically. render_quality clears this
        # to None on success, routing to compliance_gate.
        "quality_recovery_route": "artifact_workflow",
    }
    if "diagnostic_report" in diagnostic_update:
        update["diagnostic_report"] = _json_object(diagnostic_update.get("diagnostic_report"))
    if "kt_mastery" in diagnostic_update:
        update["kt_mastery"] = _json_object(diagnostic_update.get("kt_mastery"))
    if "diagnostic_stage" in diagnostic_update:
        update["diagnostic_stage"] = _json_object(diagnostic_update.get("diagnostic_stage"))
    return update


async def _diagnostic_preplanning(state: TeachingPackState) -> dict[str, Any]:
    contract = state.get("contract", {})
    if _string_field(contract, "mode", "generate_pack") != "diagnose_then_generate":
        return {}
    evidence = _json_object(contract.get("student_evidence"))
    if not evidence:
        return {}
    from packages.agents.sub_agents.diagnostician.knowledge_state import KnowledgeStateStore
    from packages.agents.sub_agents.diagnostician.nodes import diagnostician_node

    result = await diagnostician_node({
        "student_responses": evidence,
        "run_id": state["run_id"],
        "current_step": StageEnum.PLANNING_BLUEPRINT,
        "diagnostic_report": None,
        "use_structured_diagnostic": True,
    })
    report = _json_object(result.get("diagnostic_report"))
    student_id = _string_field(report, "student_id", "unknown")
    knowledge_state = KnowledgeStateStore()
    knowledge_state.record_diagnostic(student_id, report)
    return {
        "run_id": state["run_id"],
        "diagnostic_report": report,
        "kt_mastery": knowledge_state.planner_mastery(student_id),
        "diagnostic_stage": {"status": "passed", "student_id": student_id},
    }


async def _post_blueprint_research(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    from packages.agents.sub_agents.researcher.nodes import researcher_node
    from common.contracts.seam_contracts import ResearcherHandoff

    researcher_state: ResearcherNodeState = {
        "lesson_plan": state.get("lesson_plan", {}),
        "research_policy": _string_field(contract, "research_policy", "standard"),
        "run_id": state["run_id"],
        "current_step": StageEnum.POST_BLUEPRINT_RESEARCH,
        "research_bundle": _research_bundle_with_strategy_questions(state),
    }
    result = await researcher_node(researcher_state)
    research_brief = _json_object(result.get("research_bundle"))
    ResearcherHandoff(lesson_plan=state.get("lesson_plan", {}), research_brief=research_brief)
    return {"run_id": state["run_id"], "research_brief": research_brief}

def _provisional_component_strategy(state: TeachingPackState) -> TeachingPackState:
    from packages.agents.teaching_pack.component_strategy_rollout import (
        component_strategy_enabled_for_state,
        component_strategy_rollout_state,
        emit_safe_prose_fallback_event,
    )

    if not component_strategy_enabled_for_state(state):
        rollout = component_strategy_rollout_state(state)
        emit_safe_prose_fallback_event(state, rollout)
        return {"run_id": state["run_id"], "component_strategy_rollout": rollout}
    from packages.agents.teaching_pack.component_strategy_stage import run_provisional_component_strategy

    update = TeachingPackState(**run_provisional_component_strategy(state))
    update["component_strategy_rollout"] = component_strategy_rollout_state(state)
    return update

def _finalize_component_strategy(state: TeachingPackState) -> TeachingPackState:
    from packages.agents.teaching_pack.component_strategy_rollout import (
        component_strategy_enabled_for_state,
        component_strategy_rollout_state,
        emit_safe_prose_fallback_event,
    )

    if not component_strategy_enabled_for_state(state):
        rollout = component_strategy_rollout_state(state)
        emit_safe_prose_fallback_event(state, rollout)
        return {"run_id": state["run_id"], "component_strategy_rollout": rollout}
    from packages.agents.teaching_pack.component_strategy_stage import run_final_component_strategy

    update = TeachingPackState(**run_final_component_strategy(state))
    update["component_strategy_rollout"] = component_strategy_rollout_state(state)
    return update

def _research_bundle_with_strategy_questions(state: TeachingPackState) -> JsonObject:
    bundle = _json_object(state.get("research_brief"))
    questions = state.get("component_strategy_research_questions", [])
    if questions:
        return {**bundle, "component_strategy_research_questions": [*questions]}
    return bundle


async def _artifact_workflow(state: TeachingPackState) -> TeachingPackState:
    from packages.agents.teaching_pack.vocabulary_batch_orchestrator import (
        is_vocabulary_batch_mode,
        run_vocabulary_batch_orchestrator,
    )

    if is_vocabulary_batch_mode(state):
        from packages.agents.config.features import features
        if not features().vocabulary_batch_v1:
            msg = "vocabulary_batch mode requires FEATURE_VOCABULARY_BATCH_V1=true"
            raise RuntimeError(msg)
        return TeachingPackState(**await run_vocabulary_batch_orchestrator(state))
    if artifact_send_fanout_v1_enabled():
        return TeachingPackState(**coordinate_artifact_fanout(state))
    return await _rollback_artifact_workflow(state)


async def _rollback_artifact_workflow(state: TeachingPackState) -> TeachingPackState:
    from common.contracts.seam_contracts import ArtifactWorkflowHandoff
    from packages.agents.sub_agents.content_creator.nodes import content_creator_node
    from packages.agents.sub_agents.content_creator.state import ContentCreatorNodeState
    from packages.agents.teaching_pack.artifacts import normalize_generated_artifacts
    from packages.agents.teaching_pack.scoped_regeneration import merge_regenerated_artifacts

    mediated_state = await _run_generation_context_middleware("content_creator", state, 8)
    if has_scoped_section_edit(mediated_state.get("gate_payload", {})):
        return TeachingPackState(**{
            "run_id": mediated_state["run_id"],
            **apply_scoped_section_edit(
                mediated_state.get("artifacts", []),
                mediated_state.get("gate_payload", {}),
            ),
        })
    contract = mediated_state.get("contract", {})
    artifact_types = _artifact_types_for_generation(mediated_state, contract)
    creator_state: ContentCreatorNodeState = {
        "lesson_plan": mediated_state.get("lesson_plan", {}),
        "research_bundle": mediated_state.get("research_brief", {}),
        "artifact_types": artifact_types,
        "theme": _string_field(contract, "theme", "default"),
        "run_id": mediated_state["run_id"],
        "current_step": StageEnum.ARTIFACT_WORKFLOW,
        "artifacts": None,
        "revision_feedback": mediated_state.get("revision_feedback", ""),
        "use_hierarchical_creator": True,
        "component_effectiveness": _json_object(mediated_state.get("component_effectiveness")),
        "component_strategy_plan": _json_object(mediated_state.get("component_strategy_plan")),
    }
    result = await content_creator_node(creator_state)
    generated = normalize_generated_artifacts(result.get("artifacts", []), artifact_types)
    artifacts = merge_regenerated_artifacts(
        mediated_state.get("artifacts", []),
        mediated_state.get("gate_payload", {}),
        generated,
    )
    ArtifactWorkflowHandoff(artifacts=artifacts)
    return {"run_id": mediated_state["run_id"], "artifacts": artifacts}


async def _render_quality(
    state: TeachingPackState,
    quality_gate: QualityGate | None = None,
) -> TeachingPackState:
    return TeachingPackState(**await render_quality(state, quality_gate))


def _compliance_gate(state: TeachingPackState) -> TeachingPackState:
    from packages.agents.teaching_pack.compliance import compliance_gate_state

    return TeachingPackState(**compliance_gate_state(state))


def _teacher_approval(
    state: TeachingPackState,
    *,
    store: BaseStore | None = None,
) -> TeachingPackState:
    from langgraph.types import interrupt

    rendered_snapshots = state.get("rendered_snapshots") or _preview_snapshots_from_artifacts(state)
    snapshot_ids = [str(snapshot["snapshot_id"]) for snapshot in rendered_snapshots]
    artifact_statuses = artifact_statuses_for_teacher(state)
    artifacts = artifact_statuses or state.get("artifacts") or []
    artifact_types = [
        str(a.get("artifact_type", ""))
        for a in artifacts
        if isinstance(a, dict)
    ]
    gate_payload: JsonObject = {
        "gate": "content_approval",
        "gate_name": "content_approval",
        "snapshot_ids": [*snapshot_ids],
        "rendered_snapshots": [*rendered_snapshots],
        "artifacts": [*artifacts],
        "artifact_statuses": [*artifact_statuses],
        "content_artifacts": [*(state.get("artifacts") or [])],
        "quality_scores": state.get("quality_scores", {}),
        "run_id": state["run_id"],
        "artifact_explanations": artifact_explanations_for_teacher(state, "manual"),
    }
    strategy_summary = _component_strategy_gate_summary(state)
    if strategy_summary:
        gate_payload["component_strategy"] = strategy_summary
    if state.get("escalate") is True:
        gate_payload["escalated"] = True
        gate_payload["needs_review"] = True
        gate_payload["approval_mode"] = "manual_required"
        gate_payload["escalate_reason"] = _state_string_field(
            state,
            "escalate_reason",
            "Quality checks did not pass after repeated attempts.",
        )
        gate_payload["healing_history"] = _healing_history(state)

    contract = state.get("contract", {})
    teacher_id = _string_field(contract, "teacher_id", "")
    auto_approved = False

    if store is not None and teacher_id and state.get("compliance_passed") is True and state.get("escalate") is not True:
        from packages.agents.config.gate_config import GateConfig
        from packages.agents.teaching_pack.gate_trust import compute_trust_score, should_fast_lane
        threshold = GateConfig().fast_lane_threshold
        gate_payload["trust_score"] = compute_trust_score(store, teacher_id, "content_approval")
        if threshold is not None and should_fast_lane(store, teacher_id, "content_approval", threshold):
            auto_approved = True
            gate_payload["auto_approved"] = True
            gate_payload["approval_mode"] = "auto_approved"
            gate_payload["revert_window_seconds"] = 900
            gate_payload["artifact_explanations"] = artifact_explanations_for_teacher(state, "auto_approved")

    gate_response = interrupt(gate_payload)
    action = _string_field(gate_response, "action", "approve" if auto_approved else "reject")
    feedback = _string_field(gate_response, "feedback", "")
    normalized_action = normalized_teacher_action(action)
    from packages.agents.events import emit_run_event

    emit_run_event(state["run_id"], "gate_decision", {
        "gate": "content_approval",
        "decision": "auto_approved" if auto_approved else normalized_action,
        "raw_action": action,
        "via": "fast_lane" if auto_approved else "teacher",
    })

    if store is not None and teacher_id:
        from packages.agents.teaching_pack.gate_trust import record_gate_event
        from packages.agents.teaching_pack.teacher_memory import write_gate_approval
        record_gate_event(store, teacher_id, "content_approval", normalized_action, artifact_types)
        write_gate_approval(store, teacher_id, "content_approval", normalized_action, artifact_types)

    return {
        "run_id": state["run_id"],
        "approval_gate": gate_payload,
        "gate_payload": {"action": action, **gate_response},
        "teacher_approved": normalized_action == "approve",
        "teacher_decision": action,
        "revision_feedback": feedback,
        "approved_snapshot_ids": snapshot_ids if normalized_action == "approve" else [],
    }


def _preview_snapshots_from_artifacts(state: TeachingPackState) -> list[JsonObject]:
    artifacts = state.get("artifacts") or []
    if not artifacts:
        return []
    from packages.agents.teaching_pack.snapshots import build_snapshot

    return [build_snapshot(state["run_id"], artifact) for artifact in artifacts]


def _healing_history(state: TeachingPackState) -> list[JsonValue]:
    context = state.get("healing_context")
    if isinstance(context, dict):
        history = context.get("history")
        if isinstance(history, list):
            return [_json_object(item) for item in history if isinstance(item, dict)]
    strategy = state.get("healing_strategy")
    if isinstance(strategy, str) and strategy:
        return [{"strategy": strategy, "fail_count": state.get("fail_count", 0)}]
    return []


def _state_string_field(state: TeachingPackState, key: str, default: str) -> str:
    value = state.get(key)
    if isinstance(value, str) and value:
        return value
    return default


async def _teacher_approval_with_middleware(
    state: TeachingPackState,
    *,
    store: BaseStore | None = None,
) -> TeachingPackState:
    return await _run_gate_middleware(_teacher_approval(state, store=store), 10)


def _export_finalize(
    state: TeachingPackState,
    *,
    store: BaseStore | None = None,
) -> TeachingPackState:
    if not state.get("teacher_approved", False):
        return {"run_id": state["run_id"], "exported_files": []}
    unavailable = unavailable_required_artifact_statuses(state)
    if unavailable:
        return {
            "run_id": state["run_id"],
            "exported_files": [],
            "export_blocked": True,
            "export_block_reason": export_block_reason(unavailable),
            "artifact_statuses": unavailable,
        }
    # NOTE: Layer-6 deterministic format-requirement enforcement (check_export_readiness)
    # is intentionally NOT wired as a blocker here: the current export contract produces
    # a file per requested format regardless of artifact-type coverage (see
    # test_export_format_wiring). Turning format-requirements into a hard gate is a policy
    # change requiring owner sign-off; the de-stubbed check is available for that.
    if store is not None:
        contract = state.get("contract", {})
        teacher_id = _string_field(contract, "teacher_id", "")
        topic = _topic(contract)
        if teacher_id and topic:
            from packages.agents.teaching_pack.teacher_memory import write_vocabulary
            write_vocabulary(
                store, teacher_id,
                _string_field(contract, "subject", "general"),
                _string_field(contract, "grade_band", "Grade 5"),
                topic,
                [],
            )
    snapshot_ids = state.get("approved_snapshot_ids", [])
    approved_snapshots = [
        snapshot for snapshot in _rendered_snapshots_for_export(state)
        if str(snapshot.get("snapshot_id")) in snapshot_ids
    ]
    registry = ExporterRegistry.default()
    exported_files = [
        file_path
        for export_format in requested_export_formats(state.get("contract", {}))
        for file_path in registry.export(ExportRequest(
            run_id=state["run_id"],
            format=export_format,
            snapshots=approved_snapshots,
            contract=state.get("contract", {}),
        ))
    ]
    return {
        "run_id": state["run_id"],
        "exported_files": exported_files,
        "quality_recovery_route": "",
        "quality_issues": [],
        "escalate": False,
    }


def _rendered_snapshots_for_export(state: TeachingPackState) -> list[JsonObject]:
    snapshots = state.get("rendered_snapshots")
    if isinstance(snapshots, list):
        return [snapshot for snapshot in snapshots if isinstance(snapshot, dict)]
    approval_gate = state.get("approval_gate")
    if isinstance(approval_gate, dict):
        gate_snapshots = approval_gate.get("rendered_snapshots")
        if isinstance(gate_snapshots, list):
            return [snapshot for snapshot in gate_snapshots if isinstance(snapshot, dict)]
    return []


def route_after_teacher_approval(state: TeachingPackState) -> str:
    if state.get("teacher_approved", False) and state.get("component_strategy_plan") and not state.get("artifacts"):
        return "artifact_workflow"
    if state.get("teacher_approved", False):
        return "export_finalize"
    if is_scoped_teacher_action(state.get("gate_payload", {})):
        return "artifact_workflow"
    if has_scoped_section_edit(state.get("gate_payload", {})):
        return "artifact_workflow"
    if _scoped_rejections(state):
        return "artifact_workflow"
    return "export_finalize"


def route_after_compliance_gate(state: TeachingPackState) -> str:
    if state.get("compliance_passed", False):
        return "teacher_approval"
    return "artifact_workflow"


def route_after_triage(state: TeachingPackState) -> str:
    contract = state.get("contract", {})
    if contract.get("mode") == "plan_unit":
        return "unit_planning"
    return "preplanning_search"


def route_after_unit_approval(state: TeachingPackState) -> str:
    if state.get("teacher_approved", False):
        return "unit_prep"
    if state.get("teacher_decision") in {"edit", "reject"}:
        return "unit_planning"
    return "unit_planning"


def _can_reenter_stage(state: TeachingPackState, stage: StageEnum) -> bool:
    if stage.value == "artifact_workflow" and artifact_send_fanout_v1_enabled():
        if not state.get("artifact_fanout_complete", False):
            return True
        return state.get("quality_recovery_route") in ("artifact_workflow", "planning_blueprint") or bool(_scoped_rejections(state))
    if stage.value == "render_quality" and artifact_send_fanout_v1_enabled():
        return state.get("quality_recovery_route") == "artifact_workflow" or bool(_scoped_rejections(state))
    if stage.value == "teacher_approval":
        if state.get("component_strategy_plan") and state.get("artifacts"):
            return state.get("quality_recovery_route") == "artifact_workflow" or bool(_scoped_rejections(state))
        if artifact_send_fanout_v1_enabled():
            return state.get("quality_recovery_route") == "artifact_workflow" or bool(_scoped_rejections(state))
    # Allow re-entry of planning/research stages when quality gate routes back to them.
    recovery_route = state.get("quality_recovery_route", "")
    if stage.value == "planning_blueprint" and recovery_route == "planning_blueprint":
        return True
    if stage.value == "post_blueprint_research" and recovery_route in ("planning_blueprint", "post_blueprint_research"):
        return True
    return False


def _complete_stage(state: TeachingPackState, stage: StageEnum) -> TeachingPackState:
    return {
        **state,
        "current_stage": stage,
        "current_step": stage,
        "completed_stages": [*state.get("completed_stages", []), stage],
    }


def _artifact_types(contract: JsonObject) -> list[str]:
    values = contract.get("artifact_types")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    return ["lesson", "worksheet", "quiz", "recap"]


def _artifact_types_for_generation(state: TeachingPackState, contract: JsonObject) -> list[str]:
    rejected_types = rejected_artifact_types(
        state.get("artifacts", []),
        state.get("gate_payload", {}),
    )
    if rejected_types:
        return rejected_types
    return state.get("artifact_types", _artifact_types(contract))


def _scoped_rejections(state: TeachingPackState) -> list[JsonObject]:
    return scoped_rejections(state.get("artifacts", []), state.get("gate_payload", {}))


def _topic(contract: JsonObject) -> str:
    return _string_field(contract, "topic", "Teaching Pack")


def _class_info(contract: JsonObject) -> JsonObject:
    return {
        "topic": _topic(contract),
        "grade": _grade_value(contract),
        "grade_band": _string_field(contract, "grade_band", "Grade 5"),
        "subject": _string_field(contract, "subject", "general"),
        "language": _string_field(contract, "instruction_language", "en"),
        "student_count": contract.get("student_count", 30),
    }


def _grade_value(contract: JsonObject) -> JsonValue:
    value = contract.get("grade")
    if isinstance(value, int | str):
        return value
    grade_band = _string_field(contract, "grade_band", "Grade 5")
    parts = grade_band.split()
    if parts and parts[-1].isdigit():
        return int(parts[-1])
    return 5


def _json_object(value: JsonValue | object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default

def _component_strategy_gate_summary(state: TeachingPackState) -> JsonObject:
    summary = state.get("component_strategy_summary")
    if isinstance(summary, dict):
        return summary
    return {}
