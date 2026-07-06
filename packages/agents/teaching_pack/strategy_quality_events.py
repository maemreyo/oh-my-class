from __future__ import annotations

from typing import Literal, Protocol

from common.contracts.component_strategy_privacy import StrategyObservabilitySummary
from packages.agents.events import emit_run_event


class StrategyQualityEventIssue(Protocol):
    code: str
    severity: Literal["hard", "warning"]
    location: str
    validator_id: str


def emit_strategy_quality_events(run_id: str, issues: list[StrategyQualityEventIssue], *, phase: str) -> None:
    if not issues:
        return

    for issue in issues:
        payload = StrategyObservabilitySummary(
            status="blocked" if issue.severity == "hard" else "warning",
            knowledge_db_version="runtime_state",
            selector_version="runtime_state",
            blocking_issue_codes=(issue.code,),
            cache_status="not_applicable",
        ).event_payload()
        emit_run_event(run_id, "hard_block_violation", {
            **payload,
            "code": issue.code,
            "location": issue.location,
            "phase": phase,
            "source": "component_strategy_gate",
            "validator_id": issue.validator_id,
        })
