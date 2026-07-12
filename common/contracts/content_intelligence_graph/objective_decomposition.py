"""#465 (Content Intelligence Graph): deterministic objective decomposition.

Third query port #465 names by name -- "objective decomposition". Given a
learning objective, deterministically returns the knowledge components it
decomposes into, the same way `prerequisite_graph.py` returns a prerequisite
closure and `misconception_graph.py` returns targeted misconceptions. Same
tenant-scope conventions as both siblings, reused rather than reinvented.

Out of scope here, same as the other two: seeding real MOET/CCSS/NGSS
objective catalogs is content authorship, not engineering, and is not
attempted by this module.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.contracts.content_intelligence_graph.prerequisite import ContentAccessScope
from common.contracts.content_intelligence_graph.snapshot import assert_unique_node_ids


class ObjectiveDecompositionGraphError(ValueError):
    """Base class for structural defects in an objective-decomposition graph or query."""


class ObjectiveMissingError(ObjectiveDecompositionGraphError):
    def __init__(self, objective_id: str) -> None:
        self.objective_id = objective_id
        super().__init__(f"objective {objective_id!r} is not declared in this graph snapshot")


class ObjectiveAccessDeniedError(ObjectiveDecompositionGraphError):
    """Tenant-isolation failure: an objective outside the requester's visible
    access scopes, or a `private_teacher` objective owned by someone else."""

    def __init__(self, objective_id: str, access_scope: str) -> None:
        self.objective_id = objective_id
        self.access_scope = access_scope
        super().__init__(
            f"objective {objective_id!r} (access_scope={access_scope!r}) is not visible to this requester",
        )


class ObjectiveNode(BaseModel):
    """One learning objective, decomposed into the knowledge components that
    make it up. `knowledge_component_ids` are plain identifiers here, not
    validated against `PrerequisiteNode`/`MisconceptionNode` -- cross-graph
    referential integrity is a caller/composition concern, not this module's;
    keeping the three graphs independently loadable/versionable is deliberate.
    """

    model_config = ConfigDict(frozen=True)

    objective_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    knowledge_component_ids: tuple[str, ...] = Field(min_length=1)
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class ObjectiveDecompositionGraph(BaseModel):
    """An immutable, versioned snapshot of objective decompositions.

    Frozen for the same reason as its sibling graphs: #465 requires that
    "updating a graph version does not mutate historical ArtifactDocument
    provenance" -- immutability makes that a type-level guarantee.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[ObjectiveNode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_unique_node_ids(self) -> ObjectiveDecompositionGraph:
        assert_unique_node_ids(node.objective_id for node in self.nodes)
        return self

    def node_by_id(self, objective_id: str) -> ObjectiveNode | None:
        return next((node for node in self.nodes if node.objective_id == objective_id), None)


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


def decompose_objective(
    graph: ObjectiveDecompositionGraph,
    objective_id: str,
    *,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
) -> tuple[str, ...]:
    """Return `objective_id`'s knowledge components, deterministically ordered.

    Fails closed (raises) rather than silently returning an empty/partial
    result:
    - `ObjectiveMissingError` if `objective_id` isn't declared in the graph.
    - `ObjectiveAccessDeniedError` (#465 tenant isolation) if the objective is
      outside `visible_access_scopes`, or is a `private_teacher` objective
      owned by someone other than `requester_id`.

    Order is the objective's own declared `knowledge_component_ids` order
    (an objective's decomposition is an authored sequence, not a set -- unlike
    prerequisite closure or misconception retrieval, there is no natural sort
    key independent of authoring intent, so declaration order *is* the
    deterministic order and is preserved verbatim).
    """
    node = graph.node_by_id(objective_id)
    if node is None:
        raise ObjectiveMissingError(objective_id)
    if node.access_scope not in visible_access_scopes:
        raise ObjectiveAccessDeniedError(node.objective_id, node.access_scope)
    if node.access_scope == "private_teacher" and node.owner_id != requester_id:
        raise ObjectiveAccessDeniedError(node.objective_id, node.access_scope)
    return node.knowledge_component_ids
