"""#465 (Content Intelligence Graph): deterministic prerequisite closure.

A narrow, honest first slice of the graph the issue describes -- stable
node/edge contracts for prerequisite relationships between knowledge
components, plus the one deterministic query port the issue names by name:
"Prerequisite closure is deterministic and detects cycles, missing nodes,
and scope conflicts." Standards/misconceptions/evidence nodes already exist
in `subject_capability_pack.py` and `component_strategy_knowledge_models.py`
-- this module does not duplicate those, only adds the missing prerequisite
graph and its closure algorithm.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# #465: "Support private_teacher, organization, and system scopes without
# cross-tenant cache keys or retrieval." Mirrors the same three-tier tenant
# scope already established (and tested) for Source Collections
# (`services/gateway/routers/source_collections.py`) -- reused here, not
# reinvented. Distinct from `PrerequisiteNode.scope` (a subject/grade-band
# key), which is about curriculum modeling, not tenant access.
ContentAccessScope = Literal["private_teacher", "organization", "system"]


class PrerequisiteGraphError(ValueError):
    """Base class for structural defects in a prerequisite graph."""


class PrerequisiteCycleError(PrerequisiteGraphError):
    def __init__(self, cycle: tuple[str, ...]) -> None:
        self.cycle = cycle
        super().__init__("prerequisite cycle detected: " + " -> ".join((*cycle, cycle[0])))


class PrerequisiteMissingNodeError(PrerequisiteGraphError):
    def __init__(self, node_id: str, missing_requirement_id: str) -> None:
        self.node_id = node_id
        self.missing_requirement_id = missing_requirement_id
        super().__init__(f"node {node_id!r} requires undeclared node {missing_requirement_id!r}")


class PrerequisiteScopeConflictError(PrerequisiteGraphError):
    def __init__(self, node_id: str, expected_scope: str, actual_scope: str) -> None:
        self.node_id = node_id
        self.expected_scope = expected_scope
        self.actual_scope = actual_scope
        super().__init__(
            f"node {node_id!r} has scope {actual_scope!r}, expected {expected_scope!r} "
            "(a prerequisite must not span outside its dependent's declared scope)",
        )


class PrerequisiteAccessDeniedError(PrerequisiteGraphError):
    """Tenant-isolation failure: a node outside the requester's visible
    access scopes, or a `private_teacher` node owned by someone else."""

    def __init__(self, node_id: str, access_scope: str) -> None:
        self.node_id = node_id
        self.access_scope = access_scope
        super().__init__(f"node {node_id!r} (access_scope={access_scope!r}) is not visible to this requester")


class PrerequisiteNode(BaseModel):
    """One knowledge-component node in the prerequisite graph."""

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    scope: str = Field(min_length=1, max_length=80, description="e.g. a subject or subject+grade-band key")
    requires: tuple[str, ...] = Field(default_factory=tuple, description="node_ids this node depends on")
    # #465 tenant isolation: who may see this node at all, independent of
    # the curriculum `scope` above. `owner_id` is required and checked only
    # for "private_teacher" (a system/organization node has no single owner).
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class PrerequisiteGraph(BaseModel):
    """An immutable, versioned snapshot of prerequisite relationships.

    Snapshot immutability matters here specifically because #465's
    acceptance criteria require that "updating a graph version does not
    mutate historical ArtifactDocument provenance" -- a frozen model makes
    that a type-level guarantee for anything holding a reference to one.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[PrerequisiteNode, ...] = Field(min_length=1)

    def node_by_id(self, node_id: str) -> PrerequisiteNode | None:
        return next((node for node in self.nodes if node.node_id == node_id), None)


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


def prerequisite_closure(
    graph: PrerequisiteGraph,
    target_id: str,
    *,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
) -> tuple[str, ...]:
    """Return every prerequisite of `target_id`, deepest-first, deterministically ordered.

    Fails closed (raises) rather than silently truncating or ignoring a
    defect:
    - `PrerequisiteMissingNodeError` if any required node_id isn't declared.
    - `PrerequisiteCycleError` if the requirement edges form a cycle.
    - `PrerequisiteScopeConflictError` if a prerequisite's scope doesn't
      match the dependent's scope (a prerequisite must stay within the same
      subject/grade-band scope it's claimed for -- cross-scope requirements
      are a modeling error, not a valid dependency).
    - `PrerequisiteAccessDeniedError` (#465 tenant isolation) if traversal
      would cross into a node outside `visible_access_scopes`, or into a
      `private_teacher` node owned by someone other than `requester_id`.
      The caller (gateway) resolves a user's role into the scope set it may
      see -- this module has no knowledge of roles, only the resulting set,
      keeping `common/contracts` a dependency-free leaf.
    """
    target = graph.node_by_id(target_id)
    if target is None:
        raise PrerequisiteMissingNodeError(target_id, target_id)

    visited: set[str] = set()
    ordering: list[str] = []
    in_progress: list[str] = []

    def _assert_visible(node: PrerequisiteNode) -> None:
        if node.access_scope not in visible_access_scopes:
            raise PrerequisiteAccessDeniedError(node.node_id, node.access_scope)
        if node.access_scope == "private_teacher" and node.owner_id != requester_id:
            raise PrerequisiteAccessDeniedError(node.node_id, node.access_scope)

    def visit(node_id: str, expected_scope: str) -> None:
        node = graph.node_by_id(node_id)
        if node is None:
            parent = in_progress[-1] if in_progress else target_id
            raise PrerequisiteMissingNodeError(parent, node_id)
        _assert_visible(node)
        if node_id != target_id and node.scope != expected_scope:
            raise PrerequisiteScopeConflictError(node_id, expected_scope, node.scope)
        if node_id in in_progress:
            cycle_start = in_progress.index(node_id)
            raise PrerequisiteCycleError(tuple(in_progress[cycle_start:]))
        if node_id in visited:
            return
        in_progress.append(node_id)
        for requirement_id in node.requires:
            visit(requirement_id, node.scope)
        in_progress.pop()
        visited.add(node_id)
        if node_id != target_id:
            ordering.append(node_id)

    _assert_visible(target)
    visit(target_id, target.scope)
    return tuple(ordering)
