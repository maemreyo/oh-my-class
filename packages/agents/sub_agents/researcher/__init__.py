"""Researcher Agent — source gathering and cross-referencing."""

from packages.agents.sub_agents.researcher.agent import make_researcher_agent, researcher_graph_node
from packages.agents.sub_agents.researcher.nodes import researcher_node

__all__ = ["make_researcher_agent", "researcher_node", "researcher_graph_node"]
