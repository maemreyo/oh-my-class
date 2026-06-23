"""Sub-agents package — all specialized agents for the oh-my-class pipeline.

Contains planner, researcher, content_creator, and reviewer agents.
Each agent is a standalone module with its own tools, prompts, and config.
"""

from packages.agents.sub_agents.content_creator import generate_artifacts
from packages.agents.sub_agents.planner import design_lesson_plan
from packages.agents.sub_agents.researcher import research_sources
from packages.agents.sub_agents.reviewer import quality_review

__all__ = [
    "design_lesson_plan",
    "research_sources",
    "generate_artifacts",
    "quality_review",
]
