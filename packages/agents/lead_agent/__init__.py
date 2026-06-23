"""Lead Agent — supervisor for the oh-my-class pipeline.

INVARIANT-01: Lead Agent NEVER calls an LLM to generate content.
It only delegates via task(agent_name, prompt).
"""

from packages.agents.lead_agent.agent import make_lead_agent
from packages.agents.lead_agent.config import LEAD_AGENT_CONFIG

__all__ = ["make_lead_agent", "LEAD_AGENT_CONFIG"]
