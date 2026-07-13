"""#465 (Content Intelligence Graph): task-model catalog contract.

`ExerciseCandidateNode.task_model` (`exercise_candidate.py`) is already a
live free-text field ("e.g. multiple_choice, short_answer, worked_example")
-- this gives the catalog of valid task models its own versioned, tenant-scoped
node contract, the same way `terminology.py`/`example.py` do for their catalogs.
Deliberately a flat catalog (one graph, looked up by id), not a per-knowledge-
component graph like its siblings: a task model (e.g. "multiple_choice") is a
reusable format, not something scoped to one knowledge component.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.contracts.content_intelligence_graph.prerequisite import ContentAccessScope
from common.contracts.content_intelligence_graph.snapshot import assert_unique_node_ids


class TaskModelNode(BaseModel):
    """One task-model format an exercise candidate may declare."""

    model_config = ConfigDict(frozen=True)

    task_model_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class TaskModelCatalog(BaseModel):
    """An immutable, versioned snapshot of the task-model catalog."""

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[TaskModelNode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_unique_node_ids(self) -> TaskModelCatalog:
        assert_unique_node_ids(node.task_model_id for node in self.nodes)
        return self


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


class TaskModelMissingError(ValueError):
    def __init__(self, task_model_id: str) -> None:
        self.task_model_id = task_model_id
        super().__init__(f"task model {task_model_id!r} is not declared in this catalog snapshot")


class TaskModelAccessDeniedError(ValueError):
    def __init__(self, task_model_id: str, access_scope: str) -> None:
        self.task_model_id = task_model_id
        self.access_scope = access_scope
        super().__init__(
            f"task model {task_model_id!r} (access_scope={access_scope!r}) is not visible to this requester",
        )


def lookup_task_model(
    catalog: TaskModelCatalog,
    task_model_id: str,
    *,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
) -> TaskModelNode:
    """Return the declared task model for `task_model_id`.

    Fails closed rather than returning `None` for an undeclared task model
    (unlike the per-knowledge-component retrieval ports, an unknown task model
    is a defect, not a valid empty result -- an exercise candidate must
    reference a real, catalogued format): `TaskModelMissingError` if
    undeclared, `TaskModelAccessDeniedError` for a tenant-isolation violation.
    """
    node = next((n for n in catalog.nodes if n.task_model_id == task_model_id), None)
    if node is None:
        raise TaskModelMissingError(task_model_id)
    if node.access_scope not in visible_access_scopes:
        raise TaskModelAccessDeniedError(node.task_model_id, node.access_scope)
    if node.access_scope == "private_teacher" and node.owner_id != requester_id:
        raise TaskModelAccessDeniedError(node.task_model_id, node.access_scope)
    return node
