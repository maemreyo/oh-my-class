"""Shared tool definitions for the oh-my-class agent pipeline.

Tools are standalone, independently testable units that agents invoke via
the task() delegation mechanism or directly via LangGraph tool calls.
"""

from packages.agents.tools.ninerouter_web import (
    FetchResult,
    NineRouterFetchRequest,
    NineRouterSearchRequest,
    NineRouterWebClient,
    SearchResult,
)
from packages.agents.tools.read_file import read_file
from packages.agents.tools.task import task
from packages.agents.tools.web_search import web_search
from packages.agents.tools.write_file import write_file

__all__ = [
    "FetchResult",
    "NineRouterFetchRequest",
    "NineRouterSearchRequest",
    "NineRouterWebClient",
    "SearchResult",
    "read_file",
    "task",
    "web_search",
    "write_file",
]
