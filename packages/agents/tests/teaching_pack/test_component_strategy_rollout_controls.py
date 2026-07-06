from __future__ import annotations

from packages.agents.events import drain_observability_events
from packages.agents.config.features import reset_features
from packages.agents.teaching_pack.component_strategy_rollout import (
    ComponentStrategyAdvisorGate,
    ComponentStrategyRolloutMetrics,
    ComponentStrategySloThresholds,
    component_strategy_advisor_issues,
    component_strategy_enabled_for_state,
    public_rollout_gate_issues,
)
from packages.agents.teaching_pack.nodes import TeachingPackState, _can_reenter_stage, make_stage_node, route_after_teacher_approval
from packages.agents.teaching_pack.stages import TeachingPackStage


def test_component_strategy_hidden_internal_rollout_respects_allowlist_and_kill_switch(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_V1", "true")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_INTERNAL_TEACHERS", "teacher-allowed,teacher-other")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_KILL_SWITCH", "false")
    reset_features()

    allowed = TeachingPackState(run_id="run-allowed", contract={"teacher_id": "teacher-allowed"})
    blocked = TeachingPackState(run_id="run-blocked", contract={"teacher_id": "teacher-blocked"})

    assert component_strategy_enabled_for_state(allowed) is True
    assert component_strategy_enabled_for_state(blocked) is False

    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_KILL_SWITCH", "true")
    reset_features()

    assert component_strategy_enabled_for_state(allowed) is False


def test_component_strategy_rollout_pins_existing_run_decision(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_V1", "true")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_INTERNAL_TEACHERS", "teacher-allowed")
    reset_features()

    previously_enabled = TeachingPackState(
        run_id="run-pinned",
        contract={"teacher_id": "teacher-blocked"},
        component_strategy_rollout={"enabled": True, "source": "pinned"},
    )

    assert component_strategy_enabled_for_state(previously_enabled) is True


async def test_final_strategy_stage_emits_minimum_privacy_safe_telemetry(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_V1", "true")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_INTERNAL_TEACHERS", "teacher-allowed")
    reset_features()
    run_id = "cs15-telemetry"

    stage_node = make_stage_node(TeachingPackStage.FINALIZE_COMPONENT_STRATEGY)
    await stage_node(TeachingPackState(
        run_id=run_id,
        contract={
            "teacher_id": "teacher-allowed",
            "teacher_id_hash": "teacher-hash",
            "topic": "Private raw teacher prompt must not leak",
            "grade_band": "Grade 5",
            "subject": "language",
            "duration_minutes": 45,
            "export_formats": ["html"],
        },
        artifact_types=["lesson"],
        lesson_plan={
            "topic": "Vocabulary boundaries",
            "grade_level": "Grade 5",
            "subject": "language",
            "duration_minutes": 45,
            "learning_objectives": [
                {
                    "objective_id": "LO-1",
                    "objective_revision": "rev-1",
                    "description": "Compare confusable words",
                    "bloom_level": "understand",
                }
            ],
        },
        research_brief={"factual_risk": "low", "source_confidence": "high", "prerequisite_risk": "met"},
    ))

    events = drain_observability_events(run_id)
    strategist_events = [event for event in events if event.event_type == "component_strategy" and event.payload.get("status") == "planned"]

    assert len(strategist_events) == 1
    assert strategist_events[0].run_id == run_id
    assert strategist_events[0].teacher_id == "teacher-allowed"
    payload = strategist_events[0].payload
    assert payload["environment"] == "production"
    assert payload["feature_variant"] == "internal_hidden"
    assert payload["strategy_family_id"] == "vocabulary_language"
    assert payload["selected_component_types"] == ["contrastive_pairs", "vocab_cluster"]
    assert "Private raw teacher prompt" not in str(payload)


async def test_final_strategy_stage_emits_safe_fallback_when_not_allowlisted(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_V1", "true")
    monkeypatch.setenv("FEATURE_COMPONENT_STRATEGIST_INTERNAL_TEACHERS", "teacher-allowed")
    reset_features()
    run_id = "cs18-safe-fallback"

    stage_node = make_stage_node(TeachingPackStage.FINALIZE_COMPONENT_STRATEGY)
    result = await stage_node(TeachingPackState(
        run_id=run_id,
        contract={"teacher_id": "teacher-blocked", "subject": "language", "grade_band": "Grade 5"},
        artifact_types=["lesson"],
        lesson_plan={"subject": "language", "learning_objectives": []},
    ))

    assert "component_strategy_plan" not in result
    events = drain_observability_events(run_id)
    fallback_events = [event for event in events if event.event_type == "component_strategy" and event.payload.get("status") == "safe_prose_fallback"]

    assert len(fallback_events) == 1
    assert fallback_events[0].payload["fallback_reason"] == "not_allowlisted"


def test_component_strategy_content_approval_reenters_when_fanout_is_rolled_back(monkeypatch) -> None:
    monkeypatch.setenv("OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1", "true")
    state = TeachingPackState(
        run_id="cs-content-approval-reentry",
        completed_stages=[TeachingPackStage.TEACHER_APPROVAL],
        teacher_approved=True,
        component_strategy_plan={"strategy_id": "strategy-run-1"},
        artifacts=[{"artifact_type": "lesson"}],
        quality_recovery_route="artifact_workflow",
    )

    assert _can_reenter_stage(state, TeachingPackStage.TEACHER_APPROVAL) is True
    assert route_after_teacher_approval(state) == "export_finalize"


def test_public_rollout_gate_passes_with_baseline_slo_and_cleanup_owner() -> None:
    metrics = ComponentStrategyRolloutMetrics(
        invocation_count=250,
        fallback_rate=0.02,
        no_match_rate=0.01,
        primary_tier_share=0.86,
        error_rate=0.0,
        p95_latency_ms=180.0,
    )
    thresholds = ComponentStrategySloThresholds(
        min_invocations=200,
        max_fallback_rate=0.05,
        max_no_match_rate=0.03,
        min_primary_tier_share=0.75,
        max_error_rate=0.01,
        max_p95_latency_ms=250.0,
    )

    issues = public_rollout_gate_issues(
        metrics,
        thresholds,
        cleanup_owner="component-strategist-oncall",
        cleanup_deadline="2026-09-30",
        sampled_moet_qa_passed=True,
    )

    assert issues == ()


def test_public_rollout_gate_fails_closed_on_regression_and_missing_owner() -> None:
    metrics = ComponentStrategyRolloutMetrics(
        invocation_count=20,
        fallback_rate=0.12,
        no_match_rate=0.08,
        primary_tier_share=0.40,
        error_rate=0.03,
        p95_latency_ms=900.0,
    )
    thresholds = ComponentStrategySloThresholds(
        min_invocations=200,
        max_fallback_rate=0.05,
        max_no_match_rate=0.03,
        min_primary_tier_share=0.75,
        max_error_rate=0.01,
        max_p95_latency_ms=250.0,
    )

    issues = public_rollout_gate_issues(
        metrics,
        thresholds,
        cleanup_owner="",
        cleanup_deadline="",
        sampled_moet_qa_passed=False,
    )

    assert issues == (
        "baseline_window_incomplete",
        "fallback_rate_slo_breached",
        "no_match_rate_slo_breached",
        "primary_tier_share_slo_breached",
        "error_rate_slo_breached",
        "latency_slo_breached",
        "sampled_moet_qa_missing",
        "cleanup_owner_missing",
        "cleanup_deadline_missing",
    )


def test_llm_advisor_gate_is_disabled_by_default_and_cannot_influence_v1() -> None:
    gate = ComponentStrategyAdvisorGate()

    issues = component_strategy_advisor_issues(gate)

    assert issues == ("advisor_disabled",)


def test_llm_advisor_gate_requires_future_eval_security_and_telemetry() -> None:
    gate = ComponentStrategyAdvisorGate(enabled=True, evaluation_proof=False, security_review=False, decision_source_telemetry=False)

    issues = component_strategy_advisor_issues(gate)

    assert issues == (
        "advisor_eval_proof_missing",
        "advisor_security_review_missing",
        "advisor_decision_source_telemetry_missing",
    )
