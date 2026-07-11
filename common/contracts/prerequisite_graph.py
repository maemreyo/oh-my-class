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

from pydantic import BaseModel, ConfigDict, Field


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


class PrerequisiteNode(BaseModel):
    """One knowledge-component node in the prerequisite graph."""

    model_config = ConfigDict(frozen=True)

    node_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    scope: str = Field(min_length=1, max_length=80, description="e.g. a subject or subject+grade-band key")
    requires: tuple[str, ...] = Field(default_factory=tuple, description="node_ids this node depends on")


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


def prerequisite_closure(graph: PrerequisiteGraph, target_id: str) -> tuple[str, ...]:
    """Return every prerequisite of `target_id`, deepest-first, deterministically ordered.

    Fails closed (raises) rather than silently truncating or ignoring a
    defect:
    - `PrerequisiteMissingNodeError` if any required node_id isn't declared.
    - `PrerequisiteCycleError` if the requirement edges form a cycle.
    - `PrerequisiteScopeConflictError` if a prerequisite's scope doesn't
      match the dependent's scope (a prerequisite must stay within the same
      subject/grade-band scope it's claimed for -- cross-scope requirements
      are a modeling error, not a valid dependency).
    """
    target = graph.node_by_id(target_id)
    if target is None:
        raise PrerequisiteMissingNodeError(target_id, target_id)

    visited: set[str] = set()
    ordering: list[str] = []
    in_progress: list[str] = []

    def visit(node_id: str, expected_scope: str) -> None:
        node = graph.node_by_id(node_id)
        if node is None:
            parent = in_progress[-1] if in_progress else target_id
            raise PrerequisiteMissingNodeError(parent, node_id)
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

    visit(target_id, target.scope)
    return tuple(ordering)
