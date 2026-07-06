from __future__ import annotations

from common.contracts.objective_lineage import (
    BlueprintEditIntent,
    ObjectiveAssessmentIntent,
    ObjectiveImportance,
    compare_objective_revisions,
    normalize_learning_objectives,
)


def test_objective_ids_are_stable_across_reorder() -> None:
    first = normalize_learning_objectives([
        {"description": "Compare equivalent fractions", "bloom_level": "understand"},
        {"description": "Solve fraction word problems", "bloom_level": "apply"},
    ])
    reordered = normalize_learning_objectives([
        {"description": "Solve fraction word problems", "bloom_level": "apply"},
        {"description": "Compare equivalent fractions", "bloom_level": "understand"},
    ])

    assert {item.objective_id for item in first.objectives} == {item.objective_id for item in reordered.objectives}


def test_missing_priority_and_assessability_are_inferred_deterministically() -> None:
    result = normalize_learning_objectives([
        {"description": "Identify vocabulary meaning", "bloom_level": "remember"},
        {"description": "Create a short explanation", "bloom_level": "create", "assessment_method": "exit ticket"},
    ])

    assert result.objectives[0].importance is ObjectiveImportance.CORE
    assert result.objectives[0].assessable is False
    assert result.objectives[0].assessment_intent is ObjectiveAssessmentIntent.NONE
    assert "inferred" in result.objectives[0].inference_reason
    assert result.objectives[1].assessment_intent is ObjectiveAssessmentIntent.FORMATIVE


def test_light_wording_edit_preserves_revision_when_marked_wording_only() -> None:
    previous = normalize_learning_objectives([
        {"description": "Compare equivalent fractions", "bloom_level": "understand"},
    ])
    current = normalize_learning_objectives([
        {"description": "Compare equivalent fractions accurately", "bloom_level": "understand"},
    ])

    decision = compare_objective_revisions(previous, current, edit_intent=BlueprintEditIntent.WORDING_ONLY)

    assert decision.strategy_invalidated is False
    assert decision.materiality == "cosmetic"


def test_semantic_learning_target_edit_invalidates_strategy() -> None:
    previous = normalize_learning_objectives([
        {"description": "Compare equivalent fractions", "bloom_level": "understand"},
    ])
    current = normalize_learning_objectives([
        {"description": "Evaluate competing fraction strategies", "bloom_level": "evaluate"},
    ])

    decision = compare_objective_revisions(previous, current)

    assert decision.strategy_invalidated is True
    assert decision.materiality == "semantic"
