"""oh-my-class agent pipeline — LangGraph multi-agent orchestration.

Contains the state schema, graph builder, middleware chain, and all agent
definitions. This package is self-contained and must NOT import from app.*.
"""

from packages.agents.graph import build_oh_my_class_graph
from packages.agents.state import OhMyClassState, merge_artifacts

__all__ = [
    "OhMyClassState",
    "merge_artifacts",
    "build_oh_my_class_graph",
]
