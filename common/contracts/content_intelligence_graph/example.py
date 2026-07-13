"""#465 (Content Intelligence Graph): worked-example node/edge contract.

Sibling to `terminology.py`: the issue's Scope lists "examples" among the
node types needing a stable contract, and none existed anywhere in the
codebase (only free-text example content inline in prompts/skills). Same
shape and conventions as the rest of this package.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from common.contracts.content_intelligence_graph.prerequisite import ContentAccessScope
from common.contracts.content_intelligence_graph.snapshot import assert_unique_node_ids


class ExampleNode(BaseModel):
    """One worked example illustrating a knowledge component."""

    model_config = ConfigDict(frozen=True)

    example_id: str = Field(min_length=1, max_length=80)
    knowledge_component_id: str = Field(min_length=1, max_length=80)
    prompt_en: str = Field(min_length=1, max_length=2_000)
    prompt_vi: str = Field(min_length=1, max_length=2_000)
    access_scope: ContentAccessScope = "system"
    owner_id: str | None = Field(default=None, max_length=80)


class ExampleGraph(BaseModel):
    """An immutable, versioned snapshot of worked examples."""

    model_config = ConfigDict(frozen=True)

    snapshot_version: str = Field(min_length=1, max_length=80)
    nodes: tuple[ExampleNode, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_unique_node_ids(self) -> ExampleGraph:
        assert_unique_node_ids(node.example_id for node in self.nodes)
        return self


_DEFAULT_VISIBLE_ACCESS_SCOPES: frozenset[ContentAccessScope] = frozenset({"system"})


class ExampleAccessDeniedError(ValueError):
    def __init__(self, example_id: str, access_scope: str) -> None:
        self.example_id = example_id
        self.access_scope = access_scope
        super().__init__(f"example {example_id!r} (access_scope={access_scope!r}) is not visible to this requester")


def retrieve_examples(
    graph: ExampleGraph,
    knowledge_component_id: str,
    *,
    visible_access_scopes: frozenset[ContentAccessScope] = _DEFAULT_VISIBLE_ACCESS_SCOPES,
    requester_id: str | None = None,
) -> tuple[ExampleNode, ...]:
    """Return every worked example tied to `knowledge_component_id`,
    deterministically ordered by `example_id`. Same tenant-isolation and
    empty-result-is-valid conventions as the rest of this package.
    """
    matches = sorted(
        (node for node in graph.nodes if node.knowledge_component_id == knowledge_component_id),
        key=lambda node: node.example_id,
    )
    visible: list[ExampleNode] = []
    for node in matches:
        if node.access_scope not in visible_access_scopes:
            raise ExampleAccessDeniedError(node.example_id, node.access_scope)
        if node.access_scope == "private_teacher" and node.owner_id != requester_id:
            raise ExampleAccessDeniedError(node.example_id, node.access_scope)
        visible.append(node)
    return tuple(visible)
