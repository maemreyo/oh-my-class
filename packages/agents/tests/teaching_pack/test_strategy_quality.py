from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from packages.agents.events import clear_run, get_run_events
from packages.agents.teaching_pack.content_orchestrator import InMemoryArtifactContentStore
from packages.agents.teaching_pack.quality_runtime import render_quality
from packages.agents.teaching_pack.strategy_quality import (
    VALIDATOR_REGISTRY,
    emit_strategy_quality_events,
    post_generation_strategy_issues,
    pre_generation_strategy_issues,
)

def test_validator_registry_has_deterministic_metadata() -> None:
    priorities = [validator.priority for validator in VALIDATOR_REGISTRY]

    assert priorities == sorted(priorities)
    assert all(validator.version for validator in VALIDATOR_REGISTRY)
    assert {validator.phase for validator in VALIDATOR_REGISTRY} == {"pre_generation", "post_generation"}


def test_pre_generation_gate_rejects_unsupported_component_type() -> None:
    issues = pre_generation_strategy_issues(_plan(component_type="unsupported_component"))

    assert any(issue.code == "unsupported_component_type" and issue.severity == "hard" for issue in issues)


def test_pre_generation_gate_rejects_invalid_budget() -> None:
    issues = pre_generation_strategy_issues(_plan(budget={
        "ideal_time_minutes": 10,
        "max_time_minutes": 5,
        "ideal_item_count": 1,
        "max_item_count": 2,
    }))

    assert any(issue.code == "invalid_slot_budget" for issue in issues)

def test_pre_generation_gate_rejects_missing_learning_move_and_objective() -> None:
    slot = _slot("slot-1")
    slot["learning_move_id"] = ""
    slot["objective_refs"] = []

    issues = pre_generation_strategy_issues(_plan(slots=[slot]))

    assert {issue.code for issue in issues} >= {"missing_learning_move", "missing_objective_coverage"}

def test_pre_generation_gate_rejects_prose_only_strategy_and_missing_retrieval() -> None:
    issues = pre_generation_strategy_issues(_plan(component_type="paragraph"))

    assert {issue.code for issue in issues} >= {"prose_only_strategy", "missing_retrieval_or_formative_check"}

def test_pre_generation_gate_rejects_fallback_without_reason() -> None:
    slot = _slot("slot-1")
    slot["fallback_metadata"] = {"fallback_component_type": "callout"}

    issues = pre_generation_strategy_issues(_plan(slots=[slot]))

    assert any(issue.code == "fallback_without_reason" for issue in issues)


def test_pre_generation_gate_warns_on_low_diversity() -> None:
    plan = _plan(extra_slots=[_slot("slot-2", component_type="question_list")])

    issues = pre_generation_strategy_issues(plan)

    assert any(issue.code == "low_component_diversity" and issue.severity == "warning" for issue in issues)


def test_post_generation_gate_rejects_missing_selected_slot() -> None:
    issues = post_generation_strategy_issues(_plan(), [_artifact(slot_ids=[])])

    assert any(issue.code == "selected_slot_order_changed" for issue in issues)


def test_post_generation_gate_rejects_prose_downgrade_without_fallback() -> None:
    artifact = _artifact(component_type="paragraph")

    issues = post_generation_strategy_issues(_plan(), [artifact])

    assert any(issue.code == "prose_only_component_downgrade" for issue in issues)

def test_post_generation_gate_rejects_teacher_only_fields_on_student_surface() -> None:
    slot = _slot("slot-1")
    slot["audience_policy"] = ["student_no_answers"]

    issues = post_generation_strategy_issues(_plan(slots=[slot]), [_artifact()])

    assert any(issue.code == "teacher_only_field_on_student_surface" for issue in issues)

def test_post_generation_gate_rejects_budget_exceeded() -> None:
    issues = post_generation_strategy_issues(_plan(budget={
        "ideal_time_minutes": 5,
        "max_time_minutes": 7,
        "ideal_item_count": 1,
        "max_item_count": 0,
    }), [_artifact()])

    assert any(issue.code == "slot_budget_exceeded" for issue in issues)

def test_post_generation_gate_rejects_unmet_fill_requirement() -> None:
    slot = _slot("slot-1")
    slot["fill_requirements"] = ["worked example steps"]

    issues = post_generation_strategy_issues(_plan(slots=[slot]), [_artifact()])

    assert any(issue.code == "fill_requirement_not_met" for issue in issues)


def test_strategy_quality_events_do_not_include_teacher_id_or_debug_ledger() -> None:
    clear_run("run-strategy-events")
    issues = pre_generation_strategy_issues(_plan(component_type="unsupported_component"))

    emit_strategy_quality_events("run-strategy-events", issues, phase="pre_generation")

    events = get_run_events("run-strategy-events")
    assert events[0]["event_type"] == "hard_block_violation"
    assert events[0]["source"] == "component_strategy_gate"
    assert events[0]["validator_id"] == "component_strategy.renderability"
    assert events[0]["status"] == "blocked"
    assert events[0]["blocking_issue_codes"] == ["unsupported_component_type"]
    assert "teacher_id" not in events[0]
    assert "debug_ledger" not in events[0]
    assert "reason" not in events[0]


@pytest.mark.anyio
async def test_render_quality_routes_strategy_fill_mismatch_and_emits_event() -> None:
    clear_run("run-strategy-render")

    store = InMemoryArtifactContentStore()
    artifact_data = _artifact(slot_ids=[])
    artifact_id = str(artifact_data.get("artifact_id", "lesson-1"))
    parsed = ArtifactContent.model_validate(
        {k: v for k, v in artifact_data.items() if k != "artifact_id"},
    )
    ref = await store.persist(
        "run-strategy-render", "run-strategy-render:artifact:1", parsed, artifact_id,
    )

    result = await render_quality({
        "run_id": "run-strategy-render",
        "component_strategy_plan": _plan(),
        "artifact_references": [ref.as_state()],
    }, quality_gate=_PassingQualityGate(), content_store=store)

    assert result["quality_recovery_route"] == "artifact_workflow"
    assert "component_strategy.selected_slot_order_changed: lesson" in result["quality_issues"]
    events = get_run_events("run-strategy-render")
    assert any(event["code"] == "selected_slot_order_changed" for event in events)


class _PassingQualityGate:
    async def evaluate(self, state, _artifact):
        from common.contracts.quality import ArtifactQualityReport

        return ArtifactQualityReport(
            artifact_id=state.artifact_id,
            artifact_type=state.artifact_type,
            passed=True,
        )


def _plan(
    *,
    component_type: str = "question_list",
    budget: dict[str, int] | None = None,
    extra_slots: list[dict[str, object]] | None = None,
    slots: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    selected_slots = slots or [_slot("slot-1", component_type=component_type, budget=budget), *(extra_slots or [])]
    return {
        "recommended": {
            "learning_sequence": selected_slots,
            "artifact_strategies": [{"artifact_type": "lesson", "ordered_slot_ids": [str(slot["slot_id"]) for slot in selected_slots]}],
        },
    }


def _slot(
    slot_id: str,
    *,
    component_type: str = "question_list",
    budget: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "slot_id": slot_id,
        "learning_move_id": "retrieval_check",
        "component_type": component_type,
        "objective_refs": [{"objective_id": "LO-1", "objective_revision": "rev-1"}],
        "target_artifacts": ["lesson"],
        "budget": budget or {
            "ideal_time_minutes": 5,
            "max_time_minutes": 7,
            "ideal_item_count": 1,
            "max_item_count": 2,
        },
    }


def _artifact(
    *,
    slot_ids: list[str] | None = None,
    component_type: str = "question_list",
) -> dict[str, object]:
    ids = ["slot-1"] if slot_ids is None else slot_ids
    components = [
        {
            "type": component_type,
            "strategy_slot_id": "slot-1",
            "questions": [{
                "type": "question_card",
                "id": "q1",
                "text": "Which idea matches the lesson?",
                "options": {"A": "Equivalent fractions", "B": "Unrelated"},
                "answer": "A",
                "explain": "Grounded in the lesson.",
            }],
            "section_key": "guided_practice",
            "group": "a",
            "title": "Check",
        }
    ] if ids else []
    return {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Equivalent Fractions Lesson",
        "sections": [{"title": "Practice", "content": "Equivalent fractions", "components": components}],
        "metadata": {"component_strategy": {"slot_ids": ids, "fallbacks": []}},
        "accessibility": {"language": "en"},
    }
