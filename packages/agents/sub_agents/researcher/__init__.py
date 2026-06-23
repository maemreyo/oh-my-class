"""Researcher Agent — source gathering and cross-referencing.

Delegates to deepseek-v4-flash via LiteLLM.
Output: ResearchBundle JSON with verified sources and citations.
"""

from packages.agents.sub_agents.researcher.agent import research_sources

__all__ = ["research_sources"]
