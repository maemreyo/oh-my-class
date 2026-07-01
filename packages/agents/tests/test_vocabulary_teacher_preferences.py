from __future__ import annotations

import pytest

from packages.agents.teaching_pack.vocabulary_memory import (
    read_vocabulary_preferences,
    write_vocabulary_correction,
)


@pytest.fixture()
def mem_store():
    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def test_teacher_correction_writes_and_reads_as_preference(mem_store) -> None:
    write_vocabulary_correction(
        mem_store,
        "teacher-1",
        field_path="summary_rows.0",
        previous_value="Journey is moving.",
        next_value="Journey is the process and experience.",
        tone="encouraging",
        depth="deep",
        example_style="exam_context",
        anchor_intensity="strong",
    )

    preferences = read_vocabulary_preferences(mem_store, "teacher-1")

    assert preferences["tone"] == "encouraging"
    assert preferences["depth"] == "deep"
    assert preferences["example_style"] == "exam_context"
    assert preferences["anchor_intensity"] == "strong"
    assert preferences["correction_history"] == [
        {
            "field_path": "summary_rows.0",
            "previous_value": "Journey is moving.",
            "next_value": "Journey is the process and experience.",
        }
    ]


def test_later_correction_preserves_existing_style_preferences(mem_store) -> None:
    write_vocabulary_correction(
        mem_store,
        "teacher-1",
        field_path="title",
        previous_value="Travel",
        next_value="Travel word boundaries",
        tone="warm",
        depth="standard",
        example_style="daily_life",
        anchor_intensity="light",
    )
    write_vocabulary_correction(
        mem_store,
        "teacher-1",
        field_path="contrast_notes.0",
        previous_value="Trip is concrete.",
        next_value="Trip is a specific visit with a purpose.",
    )

    preferences = read_vocabulary_preferences(mem_store, "teacher-1")

    assert preferences["tone"] == "warm"
    assert preferences["example_style"] == "daily_life"
    assert preferences["anchor_intensity"] == "light"
    assert len(preferences["correction_history"]) == 2
