"""#465 (Content Intelligence Graph): deterministic misconception retrieval.

Another narrow, honest slice of the graph the issue describes -- the second
deterministic query port it names by name: "misconception retrieval". Reuses
the same tenant-scope conventions as `prerequisite_graph.py` (not reinvented)
and the existing ADR-054 fail-closed grounding rule
(`claim_evidence.assert_high_risk_claims_are_grounded`) so a misconception
whose evidence can't be substantiated is refused rather than silently
returned -- the issue's "fail closed when ... high-risk evidence cannot be
substantiated; return explicit generic/degraded alternatives" requirement.

Out of scope here, same as `prerequisite_graph.py`: seeding real MOET/CCSS/
NGSS misconception catalogs is content authorship, not engineering, and is
not attempted by this module.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.claim_evidence import ClaimEvidence, assert_high_risk_claims_are_grounded
from common.contracts.prerequisite_graph import ContentAccessScope


class MisconceptionGraphError(ValueError):
    """Base class for structural defects in a misconception graph or query."""


class MisconceptionAccessDeniedError(MisconceptionGraphError):
    """Tenant-isolation failure: a node outside the requester's visible
    access scopes, or a `private_teacher` node owned by someone else."""

    def __init__(self, misconception_id: str, access_scope: str) -> None:
        self.misconception_id = misconception_id
        self.access_scope = access_scope
        super().__init__(
            f"misconception {misconception_id!r} (access_scope={access_scope!r}) "
            "is not visible to this requester",
        )


class MisconceptionUngroundedError(MisconceptionGraphError):
    """Fail-closed (ADR-054): a high-risk misconception claim lacks
    grounded evidence -- the caller must not silently return it."""

    def __init__(self, misconception_id: str, reason: str) -> None:
        self.misconception_id = misconception_id
        self.reason = reason
        super().__init__(f"misconception {misconception_id!r} failed grounding check: {reason}")


class MisconceptionNode(BaseModel):
    """One documented misconception targeting a specific knowledge component."""

    model_config = ConfigDict(frozen=True)

    misconception_id: str = Field(min_length=1, max_length=80)
    knowledge_component_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    evidence: tuple[ClaimEvidence, ...] = Field(default_factory=tuple)
    # Same tenant-isolation model as PrerequisiteNode -- see that module for
    # why this is independent of curriculum scoping.
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class MisconceptionGraph(BaseModel):
    """An immutable, versioned snapshot of documented misconceptions.

    Frozen for the same reason as `PrerequisiteGraph`: #465 requires that
    "updating a graph version does not mutate historical ArtifactDocument
    provenance" -- immutability makes that a type-level guarantee.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[MisconceptionNode, ...] = Field(min_length=1)


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


def retrieve_misconceptions(
    graph: MisconceptionGraph,
    knowledge_component_id: str,
    *,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
    require_grounded_evidence: bool = True,
) -> tuple[MisconceptionNode, ...]:
    """Return every misconception targeting `knowledge_component_id`,
    deterministically ordered by `misconception_id`.

    A knowledge component with no documented misconceptions returns an empty
    tuple -- that's a valid, unremarkable result, not an error. Fails closed
    (raises) instead:
    - `MisconceptionAccessDeniedError` (#465 tenant isolation) for a node
      outside `visible_access_scopes`, or a `private_teacher` node owned by
      someone other than `requester_id`.
    - `MisconceptionUngroundedError` (ADR-054, when `require_grounded_evidence`
      is True) if a matching misconception carries a `high` risk_level claim
      that isn't cited and `VERIFIED` -- refuses to hand back an unsubstantiated
      misconception rather than silently degrading its quality.
    """
    matches = tuple(
        sorted(
            (node for node in graph.nodes if node.knowledge_component_id == knowledge_component_id),
            key=lambda node: node.misconception_id,
        ),
    )

    visible: list[MisconceptionNode] = []
    for node in matches:
        if node.access_scope not in visible_access_scopes:
            raise MisconceptionAccessDeniedError(node.misconception_id, node.access_scope)
        if node.access_scope == "private_teacher" and node.owner_id != requester_id:
            raise MisconceptionAccessDeniedError(node.misconception_id, node.access_scope)
        if require_grounded_evidence:
            failures = assert_high_risk_claims_are_grounded(list(node.evidence))
            if failures:
                raise MisconceptionUngroundedError(node.misconception_id, failures[0].reason)
        visible.append(node)

    return tuple(visible)
