from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.contracts.component_strategy import (
    ComponentStrategyMode,
    ComponentStrategyRequest,
    StrategyBlockingIssue,
)
from common.contracts.component_strategy_selector import plan_component_strategy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument(
        "--mode",
        choices=("fixture", "provisional", "final", "both"),
        default="fixture",
        help="Run the fixture as-is, override to one mode, or run provisional and final smoke checks.",
    )
    args = parser.parse_args()
    request = ComponentStrategyRequest.model_validate_json(args.fixture.read_text())
    modes = modes_for(request, args.mode)
    payload = [summary_for(request.model_copy(update={"mode": mode})) for mode in modes]
    print(json.dumps(payload[0] if len(payload) == 1 else payload, sort_keys=True))


def modes_for(request: ComponentStrategyRequest, mode: str) -> tuple[ComponentStrategyMode, ...]:
    if mode == "both":
        return (ComponentStrategyMode.PROVISIONAL, ComponentStrategyMode.FINAL)
    if mode == "provisional":
        return (ComponentStrategyMode.PROVISIONAL,)
    if mode == "final":
        return (ComponentStrategyMode.FINAL,)
    return (request.mode,)


def summary_for(request: ComponentStrategyRequest) -> dict[str, object]:
    result = plan_component_strategy(request)
    payload: dict[str, object] = {"mode": request.mode, "status": result.status}
    if result.plan is not None:
        selected = list(result.plan.recommended.learning_sequence)
        quality = result.plan.recommended.quality_score
        payload["strategy_family_id"] = result.plan.recommended.strategy_family_id
        payload["selected_moves"] = [slot.learning_move_id for slot in selected]
        payload["selected_components"] = [slot.component_type for slot in selected]
        payload["strategy_quality_overall"] = quality.overall
        payload["fallback_status"] = "fallback_used" if result.plan.recommended.fallback_metadata else "none"
        payload["score_summary"] = {
            "objective_alignment": quality.objective_alignment,
            "evidence_signal_coverage": quality.evidence_signal_coverage,
            "component_diversity": quality.component_diversity,
            "compliance_safety": quality.compliance_safety,
        }
    else:
        payload["blocking_issues"] = [blocking_issue_summary(issue) for issue in result.blocking_issues]
        payload["research_questions"] = list(result.research_questions)
        payload["hypotheses"] = list(result.hypotheses)
    return payload


def blocking_issue_summary(issue: StrategyBlockingIssue | object) -> object:
    if isinstance(issue, StrategyBlockingIssue):
        return issue.model_dump(mode="json")
    return str(issue)


if __name__ == "__main__":
    main()
