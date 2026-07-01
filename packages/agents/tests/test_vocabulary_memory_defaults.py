from __future__ import annotations

import pytest

from packages.agents.teaching_pack.teacher_memory import read_class_vocabulary
from packages.agents.teaching_pack.vocabulary_memory import (
    read_cluster_snapshot,
    read_reusable_term_distinctions,
    read_vocabulary_context,
    read_vocabulary_preferences,
    write_cluster_snapshot,
    write_vocabulary_context,
)


@pytest.fixture()
def mem_store():
    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def test_absent_vocabulary_memory_returns_defaults(mem_store) -> None:
    assert read_vocabulary_preferences(mem_store, "teacher-missing") == {
        "tone": "supportive",
        "depth": "standard",
        "example_style": "classroom",
        "anchor_intensity": "medium",
        "correction_history": [],
    }
    assert read_vocabulary_context(mem_store, "teacher-missing", "class-a") == {
        "audience_level": None,
        "target_cefr": None,
        "exam_target": None,
        "topic_context": [],
    }
    assert read_reusable_term_distinctions(mem_store, "teacher-missing", ["trip", "journey"]) == []


def test_per_class_run_context_preserves_audience_and_exam_targets(mem_store) -> None:
    context = write_vocabulary_context(
        mem_store,
        "teacher-1",
        "Grade 8A",
        audience_level="A2",
        target_cefr="B1",
        exam_target="IELTS foundation",
        topic_context=["travel writing", "school trip"],
    )

    assert context == read_vocabulary_context(mem_store, "teacher-1", "Grade 8A")
    assert context["topic_context"] == ["travel writing", "school trip"]


def test_cluster_snapshot_preserves_generated_and_reviewed_content(mem_store) -> None:
    generated = {"title": "Travel", "summary_rows": ["Journey is process."]}
    reviewed = {"title": "Travel word boundaries", "summary_rows": ["Journey is process plus experience."]}

    write_cluster_snapshot(
        mem_store,
        "teacher-1",
        "run-1",
        snapshot_id="cluster-1",
        generated_content=generated,
        reviewed_content=reviewed,
    )

    snapshot = read_cluster_snapshot(mem_store, "teacher-1", "run-1", "cluster-1")

    assert snapshot == {
        "snapshot_id": "cluster-1",
        "generated_content": generated,
        "reviewed_content": reviewed,
    }


def test_existing_teacher_class_memory_regression(mem_store) -> None:
    assert read_class_vocabulary(mem_store, "teacher-1", "English", "Grade 8") == {"vocabulary": [], "topics": []}
