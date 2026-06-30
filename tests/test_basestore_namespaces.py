"""Issue agent-interaction/002a: BaseStore substrate — namespace isolation.

Tests put/get across all 6 memory-concern namespaces using a real InMemoryStore
(same BaseStore interface as PostgresStore, swapped in for deterministic testing).
Cross-teacher isolation and TTL-convention assertions. No LLM.
"""
from __future__ import annotations

import pytest

from packages.agents.teaching_pack.store import get_development_store
from packages.agents.teaching_pack.store_namespaces import (
    RESEARCH_CACHE_TTL_MINUTES,
    class_knowledge_graph_ns,
    component_effectiveness_ns,
    kt_mastery_ns,
    research_cache_ns,
    seq_templates_ns,
    teacher_preferences_ns,
)


@pytest.fixture
def store():
    return get_development_store()


class TestNamespaceFactories:
    def test_research_cache_ns_structure(self):
        ns = research_cache_ns("teacher-1", "photosynthesis")
        assert ns == ("teacher-1", "research_cache", "photosynthesis")

    def test_seq_templates_ns_structure(self):
        ns = seq_templates_ns("teacher-1", "template-42")
        assert ns == ("teacher-1", "seq_templates", "template-42")

    def test_class_knowledge_graph_ns_structure(self):
        ns = class_knowledge_graph_ns("teacher-1", "class-A")
        assert ns == ("teacher-1", "class-A", "knowledge_graph")

    def test_kt_mastery_ns_structure(self):
        ns = kt_mastery_ns("teacher-1", "class-A")
        assert ns == ("teacher-1", "class-A", "kt_mastery")

    def test_teacher_preferences_ns_structure(self):
        ns = teacher_preferences_ns("teacher-1")
        assert ns == ("teacher-1", "preferences")

    def test_component_effectiveness_ns_structure(self):
        ns = component_effectiveness_ns("teacher-1")
        assert ns == ("teacher-1", "component_effectiveness")

    def test_research_cache_ttl_is_defined(self):
        assert isinstance(RESEARCH_CACHE_TTL_MINUTES, int)
        assert RESEARCH_CACHE_TTL_MINUTES > 0


class TestBasestoreNamespaceIsolation:
    def test_put_and_get_research_cache(self, store):
        ns = research_cache_ns("teacher-1", "topic-key")
        store.put(ns, "result", {"facts": ["fact-1"]})
        item = store.get(ns, "result")
        assert item is not None
        assert item.value["facts"] == ["fact-1"]

    def test_put_and_get_seq_templates(self, store):
        ns = seq_templates_ns("teacher-1", "tpl-001")
        store.put(ns, "template", {"sessions": 5})
        item = store.get(ns, "template")
        assert item.value["sessions"] == 5

    def test_put_and_get_class_knowledge_graph(self, store):
        ns = class_knowledge_graph_ns("teacher-1", "class-A")
        store.put(ns, "graph", {"nodes": [], "edges": []})
        item = store.get(ns, "graph")
        assert item.value["nodes"] == []

    def test_put_and_get_kt_mastery(self, store):
        ns = kt_mastery_ns("teacher-1", "class-A")
        store.put(ns, "mastery", {"kc_001": 0.85})
        item = store.get(ns, "mastery")
        assert item.value["kc_001"] == pytest.approx(0.85)

    def test_put_and_get_teacher_preferences(self, store):
        ns = teacher_preferences_ns("teacher-1")
        store.put(ns, "prefs", {"language": "vi", "methodology": "inquiry"})
        item = store.get(ns, "prefs")
        assert item.value["language"] == "vi"

    def test_put_and_get_component_effectiveness(self, store):
        ns = component_effectiveness_ns("teacher-1")
        store.put(ns, "comp-lesson", {"score": 0.9, "n": 12})
        item = store.get(ns, "comp-lesson")
        assert item.value["score"] == pytest.approx(0.9)

    def test_cross_teacher_isolation_by_namespace(self, store):
        """A write by teacher-1 must not be visible to teacher-2."""
        ns_t1 = research_cache_ns("teacher-1", "topic-key")
        ns_t2 = research_cache_ns("teacher-2", "topic-key")
        store.put(ns_t1, "result", {"owner": "teacher-1"})
        item_t2 = store.get(ns_t2, "result")
        assert item_t2 is None

    def test_cross_class_isolation(self, store):
        """Class-A KT mastery must not leak to class-B."""
        ns_a = kt_mastery_ns("teacher-1", "class-A")
        ns_b = kt_mastery_ns("teacher-1", "class-B")
        store.put(ns_a, "mastery", {"kc_001": 1.0})
        item_b = store.get(ns_b, "mastery")
        assert item_b is None

    def test_missing_key_returns_none(self, store):
        ns = research_cache_ns("teacher-1", "nonexistent")
        item = store.get(ns, "missing-key")
        assert item is None

    def test_overwrite_by_same_key(self, store):
        ns = teacher_preferences_ns("teacher-1")
        store.put(ns, "prefs", {"language": "en"})
        store.put(ns, "prefs", {"language": "vi"})
        item = store.get(ns, "prefs")
        assert item.value["language"] == "vi"

    def test_all_six_namespaces_independent(self, store):
        """The same key in different namespace concerns must not collide."""
        store.put(research_cache_ns("t1", "k"), "data", {"ns": "research"})
        store.put(seq_templates_ns("t1", "k"), "data", {"ns": "seq"})
        store.put(teacher_preferences_ns("t1"), "data", {"ns": "prefs"})
        store.put(component_effectiveness_ns("t1"), "data", {"ns": "comp"})

        assert store.get(research_cache_ns("t1", "k"), "data").value["ns"] == "research"
        assert store.get(seq_templates_ns("t1", "k"), "data").value["ns"] == "seq"
        assert store.get(teacher_preferences_ns("t1"), "data").value["ns"] == "prefs"
        assert store.get(component_effectiveness_ns("t1"), "data").value["ns"] == "comp"
