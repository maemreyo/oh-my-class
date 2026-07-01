from __future__ import annotations

from common.contracts.vocabulary_batch import NormalizedVocabularyCluster


def test_term_distinction_cache_key_is_deterministic() -> None:
    from packages.agents.sub_agents.researcher.lexical_grounding import term_distinction_cache_key

    left = term_distinction_cache_key(("Travel", "journey", "trip", "voyage"))
    right = term_distinction_cache_key(("voyage", "trip", "journey", "travel"))

    assert left == right
    assert left == "lexical-grounding:terms:journey|travel|trip|voyage"


def test_cluster_cache_key_uses_snapshot_hash() -> None:
    from packages.agents.sub_agents.researcher.lexical_grounding import lexical_grounding_cache_keys

    cluster = NormalizedVocabularyCluster(
        cluster_id="travel-words",
        terms=("travel", "journey"),
        raw_input_span="travel / journey",
        title_hint=None,
        notes=(),
        confidence=0.9,
    )

    keys = lexical_grounding_cache_keys(cluster, cluster_snapshot_hash="abc123")

    assert keys.cluster_snapshot_key == "lexical-grounding:cluster:abc123"
    assert keys.term_distinction_key == "lexical-grounding:terms:journey|travel"
