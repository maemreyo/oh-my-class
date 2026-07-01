from __future__ import annotations

from common.contracts.vocabulary_batch import PracticeItem, PracticeSet


def test_student_practice_projection_excludes_answers_and_rationales() -> None:
    from packages.agents.sub_agents.practice_generator.semantic_anchor import student_practice_projection

    practice = PracticeSet(
        practice_set_id="practice-1",
        cluster_id="cluster-1",
        items=(PracticeItem(
            item_id="item-1",
            intent="core_trigger_recall",
            prompt="transport price → ?",
            answer="fare",
            rationale="Fare is the transport price anchor.",
        ),),
    )

    projection = student_practice_projection(practice)
    item = projection.items[0]

    assert item.prompt == "transport price → ?"
    assert not hasattr(item, "answer")
    assert not hasattr(item, "rationale")
