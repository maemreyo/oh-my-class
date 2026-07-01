from __future__ import annotations

import pytest

from packages.agents.teaching_pack.vocabulary_memory import (
    promote_shared_term_distinction,
    read_reusable_term_distinctions,
    read_shared_term_distinction,
)


@pytest.fixture()
def mem_store():
    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def test_shared_db_promotion_requires_reviewed_state(mem_store) -> None:
    with pytest.raises(ValueError, match="reviewed=True"):
        promote_shared_term_distinction(
            mem_store,
            terms=["trip", "journey"],
            distinction_notes=["Trip is specific; journey is process."],
            edge_cases=[],
            source_ids=["source-1", "source-2"],
            reviewed=False,
        )

    assert read_shared_term_distinction(mem_store, ["trip", "journey"]) is None


def test_reviewed_shared_record_is_reused_across_teachers(mem_store) -> None:
    promote_shared_term_distinction(
        mem_store,
        terms=["trip", "journey"],
        distinction_notes=["Trip is specific; journey is process."],
        edge_cases=["business trip"],
        source_ids=["source-1", "source-2"],
        reviewed=True,
        reviewer_id="reviewer-1",
    )

    records = read_reusable_term_distinctions(mem_store, "teacher-any", ["journey", "trip", "voyage"])

    assert len(records) == 1
    assert records[0]["reviewer_id"] == "reviewer-1"
    assert records[0]["source_ids"] == ["source-1", "source-2"]
