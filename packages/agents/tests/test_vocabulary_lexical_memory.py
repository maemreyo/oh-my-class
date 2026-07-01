from __future__ import annotations

import pytest

from packages.agents.teaching_pack.vocabulary_memory import (
    read_reusable_term_distinctions,
    write_teacher_term_distinction,
)


@pytest.fixture()
def mem_store():
    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def test_term_distinction_reused_for_variant_cluster(mem_store) -> None:
    write_teacher_term_distinction(
        mem_store,
        "teacher-1",
        terms=["journey", "trip"],
        distinction_notes=["Trip is a specific visit; journey emphasizes process."],
        edge_cases=["business trip is more natural than business journey"],
        source_ids=["cambridge-trip", "oxford-journey"],
        reviewed=True,
    )

    records = read_reusable_term_distinctions(mem_store, "teacher-1", ["travel", "trip", "journey"])

    assert len(records) == 1
    assert records[0]["terms"] == ["journey", "trip"]
    assert records[0]["distinction_notes"] == ["Trip is a specific visit; journey emphasizes process."]
    assert records[0]["reviewed"] is True


def test_term_distinctions_are_scoped_per_teacher(mem_store) -> None:
    write_teacher_term_distinction(
        mem_store,
        "teacher-a",
        terms=["look", "see"],
        distinction_notes=["Look is intentional; see is perception."],
        edge_cases=[],
        source_ids=["source-1"],
        reviewed=True,
    )

    assert read_reusable_term_distinctions(mem_store, "teacher-b", ["look", "see"]) == []
