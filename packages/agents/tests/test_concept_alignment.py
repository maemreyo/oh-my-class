from __future__ import annotations

from packages.agents.concept_alignment import (
    ConceptAlignmentRequest,
    SiblingKC,
    verify_concept_alignment,
    verify_concept_alignment_with_majority,
)
from packages.agents.teaching_pack.scoped_repair import scoped_repair_plan


def test_sibling_kc_that_answers_question_is_flagged_misaligned() -> None:
    verdict = verify_concept_alignment(ConceptAlignmentRequest(
        question_id="q-compare-denominator",
        prompt="Which denominator shows the number of equal parts in a fraction?",
        assigned_kc_id="KC-numerator",
        assigned_kc_description="Identify the numerator as the number of selected parts.",
        sibling_kcs=(
            SiblingKC("KC-denominator", "Identify the denominator as the number of equal parts."),
        ),
    ))

    assert verdict.passed is False
    assert verdict.suggested_kc_id == "KC-denominator"
    assert "sibling" in verdict.rationale


def test_correctly_aligned_question_passes() -> None:
    verdict = verify_concept_alignment(ConceptAlignmentRequest(
        question_id="q-numerator",
        prompt="What does the numerator count in 3/5?",
        assigned_kc_id="KC-numerator",
        assigned_kc_description="Identify the numerator as the number of selected parts.",
        sibling_kcs=(
            SiblingKC("KC-denominator", "Identify the denominator as the number of equal parts."),
        ),
    ))

    assert verdict.passed is True
    assert verdict.suggested_kc_id == "KC-numerator"


def test_misalignment_routes_to_scoped_kc_correction() -> None:
    verdict = verify_concept_alignment(ConceptAlignmentRequest(
        question_id="quiz-1.sections[0].components[1]",
        prompt="Choose the denominator in 3/5.",
        assigned_kc_id="KC-numerator",
        assigned_kc_description="Identify selected parts.",
        sibling_kcs=(SiblingKC("KC-denominator", "Identify equal total parts."),),
    ))

    plan = scoped_repair_plan(verdict.to_quality_issue("quiz-1.sections[0].components[1]").message)

    assert plan.scope.section_index == 0
    assert plan.scope.component_index == 1
    assert plan.failure_class.value == "pedagogical_mismatch"


async def test_majority_judge_flags_sibling_kc_misalignment() -> None:
    calls: list[dict[str, object]] = []

    async def transport(*, model: str, messages: list[dict[str, str]], temperature: float) -> str:
        calls.append({"model": model, "messages": messages, "temperature": temperature})
        if len(calls) < 3:
            return '{"passed": false, "suggested_kc_id": "KC-denominator", "rationale": "sibling answers it"}'
        return '{"passed": true, "suggested_kc_id": "KC-numerator", "rationale": "assigned is acceptable"}'

    verdict = await verify_concept_alignment_with_majority(
        ConceptAlignmentRequest(
            question_id="q-majority",
            prompt="Choose the denominator in 3/5.",
            assigned_kc_id="KC-numerator",
            assigned_kc_description="Identify selected parts.",
            sibling_kcs=(SiblingKC("KC-denominator", "Identify equal total parts."),),
        ),
        transport=transport,
    )

    assert len(calls) == 3
    assert {call["model"] for call in calls} == {"4omc"}
    assert verdict.passed is False
    assert verdict.suggested_kc_id == "KC-denominator"
    assert "majority 1/3 passed" in verdict.rationale
