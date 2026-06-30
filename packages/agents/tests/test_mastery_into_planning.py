from __future__ import annotations

from packages.agents.sub_agents.unit_planner.mastery_planning import (
    MasteryDecision,
    MasterySignal,
    decide_mastery_action,
)


def test_low_mastery_reteaches_high_mastery_assumes_and_cold_start_falls_back() -> None:
    assert decide_mastery_action(MasterySignal("KC-X", 0.2, "high")) is MasteryDecision.RETEACH
    assert decide_mastery_action(MasterySignal("KC-X", 0.9, "high")) is MasteryDecision.ASSUME
    assert decide_mastery_action(MasterySignal("KC-X", 0.9, "low")) is MasteryDecision.FALLBACK
    assert decide_mastery_action(None) is MasteryDecision.FALLBACK
