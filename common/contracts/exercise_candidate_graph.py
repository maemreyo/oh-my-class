"""#465 (Content Intelligence Graph): deterministic exercise-candidate retrieval.

Fourth and final query port #465 names by name ("exercise candidates") --
sibling to `prerequisite_graph.py`, `misconception_graph.py`, and
`objective_decomposition_graph.py`; same tenant-scope conventions, same
fail-closed-on-defect posture, same "not attempting real content" scope
boundary.

A candidate targets one knowledge component and, optionally, one or more
misconceptions it's designed to surface/remediate -- the link the issue's
acceptance criteria ask for: "every generated assessment item can link to
objective, knowledge component, misconception target, and task model where
applicable."
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.prerequisite_graph import ContentAccessScope


class ExerciseCandidateGraphError(ValueError):
    """Base class for structural defects in an exercise-candidate graph or query."""


class ExerciseCandidateAccessDeniedError(ExerciseCandidateGraphError):
    """Tenant-isolation failure: a candidate outside the requester's visible
    access scopes, or a `private_teacher` candidate owned by someone else."""

    def __init__(self, candidate_id: str, access_scope: str) -> None:
        self.candidate_id = candidate_id
        self.access_scope = access_scope
        super().__init__(
            f"exercise candidate {candidate_id!r} (access_scope={access_scope!r}) "
            "is not visible to this requester",
        )


class ExerciseCandidateNode(BaseModel):
    """One candidate exercise/task template targeting a knowledge component."""

    model_config = ConfigDict(frozen=True)

    candidate_id: str = Field(min_length=1, max_length=80)
    knowledge_component_id: str = Field(min_length=1, max_length=80)
    task_model: str = Field(min_length=1, max_length=80, description="e.g. multiple_choice, short_answer, worked_example")
    misconception_targets: tuple[str, ...] = Field(
        default_factory=tuple, description="misconception_id(s) this candidate is designed to surface/remediate",
    )
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class ExerciseCandidateGraph(BaseModel):
    """An immutable, versioned snapshot of exercise candidates.

    Frozen for the same reason as its sibling graphs: #465 requires that
    "updating a graph version does not mutate historical ArtifactDocument
    provenance" -- immutability makes that a type-level guarantee.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[ExerciseCandidateNode, ...] = Field(min_length=1)


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


def retrieve_exercise_candidates(
    graph: ExerciseCandidateGraph,
    knowledge_component_id: str,
    *,
    target_misconception_id: str | None = None,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
) -> tuple[ExerciseCandidateNode, ...]:
    """Return exercise candidates for `knowledge_component_id`, deterministically
    ordered by `candidate_id`.

    `target_misconception_id`, when given, additionally filters to only
    candidates whose `misconception_targets` includes it -- the "candidates
    that surface this specific misconception" query the issue's assessment
    item linkage requires.

    A knowledge component (or misconception target) with no matching
    candidates returns an empty tuple -- a valid, unremarkable result, not an
    error. Fails closed (raises) only for tenant-isolation violations:
    `ExerciseCandidateAccessDeniedError` for a node outside
    `visible_access_scopes`, or a `private_teacher` node owned by someone
    other than `requester_id`.
    """
    matches = tuple(
        sorted(
            (
                node for node in graph.nodes
                if node.knowledge_component_id == knowledge_component_id
                and (target_misconception_id is None or target_misconception_id in node.misconception_targets)
            ),
            key=lambda node: node.candidate_id,
        ),
    )

    visible: list[ExerciseCandidateNode] = []
    for node in matches:
        if node.access_scope not in visible_access_scopes:
            raise ExerciseCandidateAccessDeniedError(node.candidate_id, node.access_scope)
        if node.access_scope == "private_teacher" and node.owner_id != requester_id:
            raise ExerciseCandidateAccessDeniedError(node.candidate_id, node.access_scope)
        visible.append(node)

    return tuple(visible)
