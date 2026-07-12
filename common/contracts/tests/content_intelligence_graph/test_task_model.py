from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.content_intelligence_graph.task_model import (
    TaskModelAccessDeniedError,
    TaskModelCatalog,
    TaskModelMissingError,
    TaskModelNode,
    lookup_task_model,
)


def _node(task_model_id: str, access_scope: str = "system", owner_id: str | None = None) -> TaskModelNode:
    return TaskModelNode(
        task_model_id=task_model_id,
        description="A multiple-choice item with one correct option.",
        access_scope=access_scope,
        owner_id=owner_id,
    )


def test_lookup_task_model_returns_declared_node() -> None:
    catalog = TaskModelCatalog(snapshot_version="v1", nodes=(_node("multiple_choice"),))
    node = lookup_task_model(catalog, "multiple_choice")
    assert node.task_model_id == "multiple_choice"


def test_lookup_task_model_fails_closed_for_undeclared_id() -> None:
    catalog = TaskModelCatalog(snapshot_version="v1", nodes=(_node("multiple_choice"),))
    with pytest.raises(TaskModelMissingError):
        lookup_task_model(catalog, "short_answer")


def test_lookup_task_model_denies_out_of_scope_node() -> None:
    catalog = TaskModelCatalog(snapshot_version="v1", nodes=(_node("multiple_choice", access_scope="organization"),))
    with pytest.raises(TaskModelAccessDeniedError):
        lookup_task_model(catalog, "multiple_choice")


def test_lookup_task_model_denies_other_teachers_private_node() -> None:
    catalog = TaskModelCatalog(
        snapshot_version="v1",
        nodes=(_node("custom_format", access_scope="private_teacher", owner_id="teacher-1"),),
    )
    with pytest.raises(TaskModelAccessDeniedError):
        lookup_task_model(
            catalog, "custom_format",
            visible_access_scopes=frozenset({"private_teacher"}),
            requester_id="teacher-2",
        )


def test_task_model_catalog_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate node id"):
        TaskModelCatalog(snapshot_version="v1", nodes=(_node("dup"), _node("dup")))
