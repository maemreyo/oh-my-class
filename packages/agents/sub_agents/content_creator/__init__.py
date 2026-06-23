"""Content Creator Agent — artifact content generation.

Delegates to deepseek-free (via 9Router) with fallback chain.
Output: ArtifactContent JSON validated against common.contracts.artifact.
"""

from packages.agents.sub_agents.content_creator.agent import generate_artifacts

__all__ = ["generate_artifacts"]
