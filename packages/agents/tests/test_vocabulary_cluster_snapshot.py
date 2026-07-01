from __future__ import annotations

from packages.agents.teaching_pack.vocabulary_snapshot import vocabulary_cluster_snapshot_hash


def test_cluster_snapshot_hash_is_deterministic_across_mapping_order() -> None:
    left = {
        "cluster_id": "cluster-1",
        "semantic_anchor_cluster": {"title": "Travel", "terms": ["travel", "journey"]},
        "practice_set": {"items": [{"item_id": "item-1", "answer": "journey"}]},
    }
    right = {
        "practice_set": {"items": [{"answer": "journey", "item_id": "item-1"}]},
        "semantic_anchor_cluster": {"terms": ["travel", "journey"], "title": "Travel"},
        "cluster_id": "cluster-1",
    }

    assert vocabulary_cluster_snapshot_hash(left) == vocabulary_cluster_snapshot_hash(right)


def test_cluster_snapshot_hash_changes_when_contract_changes() -> None:
    base = {"cluster_id": "cluster-1", "review_status": "needs_review"}
    changed = {"cluster_id": "cluster-1", "review_status": "passed"}

    assert vocabulary_cluster_snapshot_hash(base) != vocabulary_cluster_snapshot_hash(changed)
