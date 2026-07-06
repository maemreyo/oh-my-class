from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from common.contracts.component_strategy import ComponentStrategyRequest
from common.contracts.component_strategy_selector import plan_component_strategy

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = PROJECT_ROOT / ".scratch" / "component-strategist" / "fixtures"


@pytest.mark.parametrize(
    ("fixture_name", "family_id", "expected_components", "min_score"),
    (
        (
            "cs08_vocabulary_language_request.json",
            "vocabulary_language",
            {"contrastive_pairs", "vocab_cluster"},
            0.8,
        ),
        (
            "cs08_exam_prep_request.json",
            "exam_assessment_prep",
            {"question_list"},
            0.7,
        ),
        (
            "cs08_concept_math_science_request.json",
            "concept_math_science",
            {"flow_step"},
            0.66,
        ),
    ),
)
def test_golden_scenarios_select_pedagogically_expected_components(
    fixture_name: str,
    family_id: str,
    expected_components: set[str],
    min_score: float,
) -> None:
    result = plan_component_strategy(_request(fixture_name))

    assert result.status == "planned"
    assert result.plan is not None
    assert result.plan.recommended.strategy_family_id == family_id
    components = {slot.component_type for slot in result.plan.recommended.learning_sequence}
    assert components >= expected_components
    assert result.plan.recommended.quality_score.overall >= min_score
    assert result.plan.recommended.export_projection_status


def test_cli_smoke_prints_provisional_and_final_release_gate_summary() -> None:
    output = subprocess.check_output(
        [
            sys.executable,
            "scripts/run_component_strategy_selector.py",
            str(FIXTURE_DIR / "cs08_vocabulary_language_request.json"),
            "--mode",
            "both",
        ],
        cwd=PROJECT_ROOT,
        text=True,
    )
    payload = json.loads(output)

    assert payload[0]["mode"] == "provisional"
    assert payload[0]["research_questions"]
    assert payload[0]["hypotheses"]
    assert payload[1]["mode"] == "final"
    assert payload[1]["selected_moves"]
    assert payload[1]["selected_components"] == ["contrastive_pairs", "vocab_cluster"]
    assert payload[1]["fallback_status"] == "none"
    assert payload[1]["score_summary"]["compliance_safety"] == "pass"


def test_feedback_conflict_fixture_blocks_with_typed_issue() -> None:
    result = plan_component_strategy(_request("cs08_feedback_conflict_request.json"))

    assert result.status == "blocked"
    assert result.plan is None
    assert result.blocking_issues
    issue = result.blocking_issues[0]
    assert getattr(issue, "code", None) == "feedback_conflict"
    assert getattr(issue, "affected_objective_ids", ()) == ("LO-conflict-1",)


def test_missing_personalization_fixture_keeps_safe_fallback_ready_plan() -> None:
    result = plan_component_strategy(_request("cs08_missing_personalization_fallback_request.json"))

    assert result.status == "planned"
    assert result.plan is not None
    assert result.plan.recommended.learning_sequence
    assert result.plan.recommended.quality_score.compliance_safety == "pass"
    assert result.plan.recommended.quality_score.overall >= 0.66


def test_release_gate_improves_over_frozen_prose_only_baseline() -> None:
    result = plan_component_strategy(_request("cs08_vocabulary_language_request.json"))
    assert result.plan is not None
    selected_components = [slot.component_type for slot in result.plan.recommended.learning_sequence]
    old_path_baseline = {"prose_only_slots": 2, "component_diversity": 0.0, "unsupported_components": 0}

    assert selected_components.count("paragraph") == 0
    assert len(set(selected_components)) > old_path_baseline["component_diversity"]
    assert old_path_baseline["prose_only_slots"] > 0
    assert _unsupported_components(selected_components) == old_path_baseline["unsupported_components"]


def _request(fixture_name: str) -> ComponentStrategyRequest:
    return ComponentStrategyRequest.model_validate_json((FIXTURE_DIR / fixture_name).read_text())


def _unsupported_components(components: list[str]) -> int:
    supported = {"contrastive_pairs", "vocab_cluster", "question_list", "flow_step"}
    return sum(1 for component in components if component not in supported)
