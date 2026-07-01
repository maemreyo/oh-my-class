"""Unit tests for teacher_memory.py — all deterministic, no LLM."""
from __future__ import annotations

import pytest

from packages.agents.teaching_pack.teacher_memory import (
    read_class_vocabulary,
    read_gate_approval_history,
    write_gate_approval,
    write_vocabulary,
)


@pytest.fixture()
def mem_store():
    from langgraph.store.memory import InMemoryStore
    return InMemoryStore()


# ── vocabulary ────────────────────────────────────────────────────────────────


def test_write_and_read_vocabulary(mem_store) -> None:
    write_vocabulary(mem_store, "teacher-1", "math", "Grade 5", "Hình học phẳng", ["hình chữ nhật", "diện tích"])
    result = read_class_vocabulary(mem_store, "teacher-1", "math", "Grade 5")
    assert "hình chữ nhật" in result["vocabulary"]
    assert "diện tích" in result["vocabulary"]
    assert "Hình học phẳng" in result["topics"]


def test_vocabulary_absent_returns_empty(mem_store) -> None:
    result = read_class_vocabulary(mem_store, "teacher-x", "science", "Grade 3")
    assert result == {"vocabulary": [], "topics": []}


def test_vocabulary_accumulates_across_calls(mem_store) -> None:
    write_vocabulary(mem_store, "t1", "math", "Grade 4", "Phân số", ["tử số", "mẫu số"])
    write_vocabulary(mem_store, "t1", "math", "Grade 4", "Phép chia", ["thương", "số bị chia"])
    result = read_class_vocabulary(mem_store, "t1", "math", "Grade 4")
    assert len(result["topics"]) == 2
    assert "Phân số" in result["topics"]
    assert "Phép chia" in result["topics"]
    assert "tử số" in result["vocabulary"]
    assert "thương" in result["vocabulary"]


def test_vocabulary_deduplicates(mem_store) -> None:
    write_vocabulary(mem_store, "t2", "math", "Grade 5", "Topic A", ["apple", "banana"])
    write_vocabulary(mem_store, "t2", "math", "Grade 5", "Topic A", ["apple", "cherry"])
    result = read_class_vocabulary(mem_store, "t2", "math", "Grade 5")
    assert result["vocabulary"].count("apple") == 1
    assert "banana" in result["vocabulary"]
    assert "cherry" in result["vocabulary"]
    assert result["topics"].count("Topic A") == 1


def test_vocabulary_scoped_per_teacher(mem_store) -> None:
    write_vocabulary(mem_store, "teacher-A", "math", "Grade 5", "Topic A", ["term-a"])
    write_vocabulary(mem_store, "teacher-B", "math", "Grade 5", "Topic B", ["term-b"])
    a = read_class_vocabulary(mem_store, "teacher-A", "math", "Grade 5")
    b = read_class_vocabulary(mem_store, "teacher-B", "math", "Grade 5")
    assert "term-a" in a["vocabulary"]
    assert "term-b" not in a["vocabulary"]
    assert "term-b" in b["vocabulary"]
    assert "term-a" not in b["vocabulary"]


# ── approval history ──────────────────────────────────────────────────────────


def test_approval_history_starts_at_zero(mem_store) -> None:
    result = read_gate_approval_history(mem_store, "teacher-new", "content_approval")
    assert result == {"approved": 0, "edited": 0, "rejected": 0}


def test_write_and_read_approve(mem_store) -> None:
    write_gate_approval(mem_store, "t3", "content_approval", "approve", ["lesson", "quiz"])
    write_gate_approval(mem_store, "t3", "content_approval", "approve", ["lesson"])
    result = read_gate_approval_history(mem_store, "t3", "content_approval")
    assert result["approved"] == 2
    assert result["edited"] == 0
    assert result["rejected"] == 0


def test_write_and_read_reject(mem_store) -> None:
    write_gate_approval(mem_store, "t4", "content_approval", "reject", ["lesson"])
    result = read_gate_approval_history(mem_store, "t4", "content_approval")
    assert result["rejected"] == 1


def test_gate_history_scoped_per_gate(mem_store) -> None:
    write_gate_approval(mem_store, "t5", "content_approval", "approve", [])
    write_gate_approval(mem_store, "t5", "blueprint_approval", "reject", [])
    ca = read_gate_approval_history(mem_store, "t5", "content_approval")
    ba = read_gate_approval_history(mem_store, "t5", "blueprint_approval")
    assert ca["approved"] == 1 and ca["rejected"] == 0
    assert ba["rejected"] == 1 and ba["approved"] == 0
