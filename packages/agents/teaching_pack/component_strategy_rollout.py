from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TypedDict

from packages.agents.config.features import features
from packages.agents.teaching_pack.nodes import TeachingPackState


class ComponentStrategyRolloutState(TypedDict):
    enabled: bool
    source: str
    reason: str


@dataclass(frozen=True, slots=True)
class ComponentStrategyRolloutPolicy:
    app_env: str
    teacher_allowlist: frozenset[str]
    kill_switch: bool


@dataclass(frozen=True, slots=True)
class ComponentStrategyRolloutMetrics:
    invocation_count: int
    fallback_rate: float
    no_match_rate: float
    primary_tier_share: float
    error_rate: float
    p95_latency_ms: float


@dataclass(frozen=True, slots=True)
class ComponentStrategySloThresholds:
    min_invocations: int
    max_fallback_rate: float
    max_no_match_rate: float
    min_primary_tier_share: float
    max_error_rate: float
    max_p95_latency_ms: float


@dataclass(frozen=True, slots=True)
class ComponentStrategyAdvisorGate:
    enabled: bool = False
    evaluation_proof: bool = False
    security_review: bool = False
    decision_source_telemetry: bool = False


def component_strategy_enabled_for_state(state: TeachingPackState) -> bool:
    pinned = state.get("component_strategy_rollout")
    if pinned is not None:
        return pinned["enabled"]
    policy = _rollout_policy_from_env()
    if policy.kill_switch or not features().component_strategist_v1:
        return False
    if policy.app_env == "production":
        teacher_id = _teacher_id(state)
        return teacher_id in policy.teacher_allowlist
    return True


def component_strategy_rollout_state(state: TeachingPackState) -> ComponentStrategyRolloutState:
    enabled = component_strategy_enabled_for_state(state)
    return {
        "enabled": enabled,
        "source": "pinned" if "component_strategy_rollout" in state else "evaluated",
        "reason": _rollout_reason(enabled),
    }


def emit_safe_prose_fallback_event(state: TeachingPackState, rollout: ComponentStrategyRolloutState) -> None:
    from packages.agents.events import emit_run_event

    emit_run_event(
        state["run_id"],
        "component_strategy",
        {
            "status": "safe_prose_fallback",
            "fallback_reason": rollout["reason"],
            "fallback_used": True,
        },
    )


def public_rollout_gate_issues(
    metrics: ComponentStrategyRolloutMetrics,
    thresholds: ComponentStrategySloThresholds,
    cleanup_owner: str,
    cleanup_deadline: str,
    sampled_moet_qa_passed: bool,
) -> tuple[str, ...]:
    issues: list[str] = []
    if metrics.invocation_count < thresholds.min_invocations:
        issues.append("baseline_window_incomplete")
    if metrics.fallback_rate > thresholds.max_fallback_rate:
        issues.append("fallback_rate_slo_breached")
    if metrics.no_match_rate > thresholds.max_no_match_rate:
        issues.append("no_match_rate_slo_breached")
    if metrics.primary_tier_share < thresholds.min_primary_tier_share:
        issues.append("primary_tier_share_slo_breached")
    if metrics.error_rate > thresholds.max_error_rate:
        issues.append("error_rate_slo_breached")
    if metrics.p95_latency_ms > thresholds.max_p95_latency_ms:
        issues.append("latency_slo_breached")
    if not sampled_moet_qa_passed:
        issues.append("sampled_moet_qa_missing")
    if not cleanup_owner:
        issues.append("cleanup_owner_missing")
    if not cleanup_deadline:
        issues.append("cleanup_deadline_missing")
    return tuple(issues)


def component_strategy_advisor_issues(gate: ComponentStrategyAdvisorGate) -> tuple[str, ...]:
    if not gate.enabled:
        return ("advisor_disabled",)
    issues: list[str] = []
    if not gate.evaluation_proof:
        issues.append("advisor_eval_proof_missing")
    if not gate.security_review:
        issues.append("advisor_security_review_missing")
    if not gate.decision_source_telemetry:
        issues.append("advisor_decision_source_telemetry_missing")
    return tuple(issues)


def _rollout_policy_from_env() -> ComponentStrategyRolloutPolicy:
    return ComponentStrategyRolloutPolicy(
        app_env=os.getenv("APP_ENV", "development").lower(),
        teacher_allowlist=frozenset(_split_env_csv(os.getenv("FEATURE_COMPONENT_STRATEGIST_INTERNAL_TEACHERS", ""))),
        kill_switch=os.getenv("FEATURE_COMPONENT_STRATEGIST_KILL_SWITCH", "false").lower() == "true",
    )


def _split_env_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _teacher_id(state: TeachingPackState) -> str:
    contract = state.get("contract", {})
    value = contract.get("teacher_id") or contract.get("teacher_id_hash")
    return value if isinstance(value, str) else ""


def _rollout_reason(enabled: bool) -> str:
    if enabled:
        return "enabled"
    policy = _rollout_policy_from_env()
    if policy.kill_switch:
        return "kill_switch"
    if not features().component_strategist_v1:
        return "feature_flag_off"
    if policy.app_env == "production":
        return "not_allowlisted"
    return "disabled"
