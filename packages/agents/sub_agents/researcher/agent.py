"""Researcher Agent — node implementation.

Gathers, cross-references, and synthesizes sources for lesson content.
Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
Minimum verification: 2 independent sources for every HIGH-risk claim.

Uses deepseek-v4-flash via 9Router combo: f.light (fast free tier)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def research_sources(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Researcher Agent.

    Takes the approved lesson plan and gathers research sources.
    Verifies factual claims against ≥2 independent sources.

    Args:
        state: Current pipeline state with lesson_plan and research_policy.

    Returns:
        Partial state update containing 'research_bundle' dict.

    Research policies:
        - basic: 2-3 sources, factual accuracy only
        - standard: 5+ sources, citations required
        - rigorous: 10+ sources, peer-reviewed preferred
    """
    # TODO: Implement with LangGraph agent
    # 1. Extract lesson_plan and research_policy from state
    # 2. Format research prompt
    # 3. Call LLM with web_search and web_fetch tools
    # 4. Cross-reference findings (FACT protocol)
    # 5. Return {"research_bundle": bundle}
    raise NotImplementedError("research_sources() stub — implement with Researcher agent")
