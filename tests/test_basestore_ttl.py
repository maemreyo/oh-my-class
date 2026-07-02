"""Issue agent-interaction/002a: BaseStore substrate — TTL and staleness.

Verifies TTL conventions and that build_teaching_pack_graph accepts a store.
InMemoryStore is used for the staleness item test (real TTL sweep requires Postgres).
No LLM.
"""
from __future__ import annotations

import pytest

from packages.agents.teaching_pack.store import get_development_store
from packages.agents.teaching_pack.store_namespaces import (
    RESEARCH_CACHE_TTL_MINUTES,
    research_cache_ns,
)


class TestResearchCacheTTLConventions:
    def test_research_cache_ttl_is_positive_integer(self):
        assert isinstance(RESEARCH_CACHE_TTL_MINUTES, int)
        assert RESEARCH_CACHE_TTL_MINUTES > 0

    def test_research_cache_ttl_is_at_least_one_day(self):
        # Research cache should be valid for at least 1 day (1440 min)
        assert RESEARCH_CACHE_TTL_MINUTES >= 1440

    def test_development_store_does_not_support_ttl(self):
        # InMemoryStore is TTL-unaware (raises NotImplementedError).
        # Real TTL enforcement requires PostgresStore (see open_teaching_pack_store).
        # This test documents the boundary so callers don't assume InMemoryStore has TTL.
        from langgraph.store.memory import InMemoryStore

        store = get_development_store()
        assert isinstance(store, InMemoryStore)
        assert not store.supports_ttl

    def test_put_without_ttl_for_permanent_items(self):
        """Namespaces with None TTL (permanent) should not require ttl parameter."""
        from packages.agents.teaching_pack.store_namespaces import (
            SEQ_TEMPLATES_TTL_MINUTES,
            seq_templates_ns,
        )

        assert SEQ_TEMPLATES_TTL_MINUTES is None
        store = get_development_store()
        ns = seq_templates_ns("teacher-1", "tpl-001")
        store.put(ns, "data", {"permanent": True})
        item = store.get(ns, "data")
        assert item is not None
        assert item.value["permanent"] is True


class TestGraphAcceptsStore:
    def test_build_teaching_pack_graph_accepts_store_none(self):
        from packages.agents.teaching_pack.graph import build_teaching_pack_graph

        graph = build_teaching_pack_graph(store=None)
        assert graph is not None

    def test_build_teaching_pack_graph_accepts_in_memory_store(self):
        from packages.agents.teaching_pack.graph import build_teaching_pack_graph

        store = get_development_store()
        graph = build_teaching_pack_graph(store=store)
        assert graph is not None

    def test_graph_with_store_has_expected_stages(self):
        from packages.agents.teaching_pack.graph import build_teaching_pack_graph
        from packages.agents.teaching_pack.stages import TEACHING_PACK_STAGES

        store = get_development_store()
        graph = build_teaching_pack_graph(store=store)
        expected_nodes = {stage.value for stage in TEACHING_PACK_STAGES}
        actual_nodes = set(graph.nodes) - {"__start__", "__end__"}
        # Every stage must be a node; the graph also has worker nodes beyond the stage
        # list (e.g. generate_one_artifact from the Send fan-out, asf-002).
        assert expected_nodes <= actual_nodes


class TestStoreFactory:
    def test_get_development_store_returns_in_memory_store(self):
        from langgraph.store.memory import InMemoryStore

        store = get_development_store()
        assert isinstance(store, InMemoryStore)

    def test_sync_connection_string_strips_asyncpg(self):
        from packages.agents.teaching_pack.store import sync_connection_string

        asyncpg_url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = sync_connection_string(asyncpg_url)
        assert result == "postgresql://user:pass@host:5432/db"
        assert "+asyncpg" not in result

    def test_sync_connection_string_handles_postgres_prefix(self):
        from packages.agents.teaching_pack.store import sync_connection_string

        url = "postgres+asyncpg://user:pass@host/db"
        result = sync_connection_string(url)
        assert result == "postgresql://user:pass@host/db"

    def test_sync_connection_string_passthrough_for_plain_url(self):
        from packages.agents.teaching_pack.store import sync_connection_string

        plain = "postgresql://user:pass@host/db"
        assert sync_connection_string(plain) == plain
