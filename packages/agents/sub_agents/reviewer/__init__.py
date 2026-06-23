"""Reviewer Agent — LLM-as-Judge quality scoring.

Delegates to gpt-5.4 (different model from generator for bias mitigation).
Output: JudgeOutput JSON with G-Eval scores across 3 layers.
"""

from packages.agents.sub_agents.reviewer.agent import quality_review

__all__ = ["quality_review"]
