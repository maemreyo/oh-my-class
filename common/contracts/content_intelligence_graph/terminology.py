"""#465 (Content Intelligence Graph): terminology node/edge contract.

The issue's Scope lists "terminology" among the node types the graph needs
stable contracts for -- `ContentBrief.terminology` (`content_brief.py`) is
already a live field, but until now it was just `list[str]`, with no
versioned, tenant-scoped, bilingual source node behind those strings. This
gives terminology the same shape as its siblings (`prerequisite.py`,
`misconception.py`): frozen nodes, a frozen versioned graph, deterministic
retrieval, tenant isolation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.contracts.content_intelligence_graph.prerequisite import ContentAccessScope
from common.contracts.content_intelligence_graph.snapshot import assert_unique_node_ids


class TerminologyNode(BaseModel):
    """One bilingual term tied to the knowledge component it belongs to."""

    model_config = ConfigDict(frozen=True)

    term_id: str = Field(min_length=1, max_length=80)
    knowledge_component_id: str = Field(min_length=1, max_length=80)
    term_en: str = Field(min_length=1, max_length=200)
    term_vi: str = Field(min_length=1, max_length=200)
    definition_en: str = Field(min_length=1, max_length=500)
    definition_vi: str = Field(min_length=1, max_length=500)
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class TerminologyGraph(BaseModel):
    """An immutable, versioned snapshot of terminology entries."""

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[TerminologyNode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_unique_node_ids(self) -> TerminologyGraph:
        assert_unique_node_ids(node.term_id for node in self.nodes)
        return self


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


class TerminologyAccessDeniedError(ValueError):
    def __init__(self, term_id: str, access_scope: str) -> None:
        self.term_id = term_id
        self.access_scope = access_scope
        super().__init__(f"term {term_id!r} (access_scope={access_scope!r}) is not visible to this requester")


def retrieve_terminology(
    graph: TerminologyGraph,
    knowledge_component_id: str,
    *,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
) -> tuple[TerminologyNode, ...]:
    """Return every term tied to `knowledge_component_id`, deterministically
    ordered by `term_id`. Same tenant-isolation and empty-result-is-valid
    conventions as `retrieve_misconceptions`/`retrieve_exercise_candidates`.
    """
    matches = sorted(
        (node for node in graph.nodes if node.knowledge_component_id == knowledge_component_id),
        key=lambda node: node.term_id,
    )
    visible: list[TerminologyNode] = []
    for node in matches:
        if node.access_scope not in visible_access_scopes:
            raise TerminologyAccessDeniedError(node.term_id, node.access_scope)
        if node.access_scope == "private_teacher" and node.owner_id != requester_id:
            raise TerminologyAccessDeniedError(node.term_id, node.access_scope)
        visible.append(node)
    return tuple(visible)
