"""Content Creator Agent — node implementation.

Generates structured JSON content for each artifact type.
Output is rendered via Eta templates — never raw HTML directly.

Hard constraints:
- Return JSON only — never raw HTML
- No CDN references in data
- No student PII in output
- Answer keys in separate teacher_only section

Uses deepseek-free via 9Router combo: f.light (zero-cost priority)
Fallback: deepseek-compressed via 9Router combo: f.light (RTK compression)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def generate_artifacts(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Content Creator Agent.

    Takes the lesson plan, research bundle, and pack scope,
    and generates ArtifactContent JSON for each requested artifact type.

    Args:
        state: Current pipeline state with lesson_plan, research_bundle,
            artifact_types, and theme.

    Returns:
        Partial state update containing 'artifacts' list.

    Output contract:
        Each artifact validated against ArtifactContent schema:
        - artifact_type: lesson|worksheet|quiz|drill|recap|infographic
        - theme: default|ocean|forest
        - title: 3-200 chars
        - sections: list of dicts, min 1
        - metadata, accessibility: dicts
    """
    # TODO: Implement with LangGraph agent
    # 1. Extract lesson_plan, research_bundle, artifact_types, theme from state
    # 2. For each artifact_type, format prompt with relevant context
    # 3. Call LLM (deepseek-free → fallback chain)
    # 4. Parse response into ArtifactContent schema
    # 5. Validate via Pydantic (common.contracts.artifact.ArtifactContent)
    # 6. Return {"artifacts": [artifact.model_dump() for artifact in artifacts]}
    raise NotImplementedError("generate_artifacts() stub — implement with Content Creator agent")
