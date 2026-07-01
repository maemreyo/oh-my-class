"""LLM client package for oh-my-class.

Provides:
- LLMClient: thin wrapper over openai.AsyncOpenAI, injected into all agents
- MockLLMClient: deterministic fake for agent tests
- build_tags(): cost attribution metadata for LiteLLM
"""

from packages.llm_client.client import ChatMessage, ChatResponse, LLMClient
from packages.llm_client.middleware import CallMiddlewareRunner
from packages.llm_client.mock import MockLLMClient
from packages.llm_client.tags import build_tags

__all__ = ["LLMClient", "MockLLMClient", "ChatMessage", "ChatResponse", "CallMiddlewareRunner", "build_tags"]
