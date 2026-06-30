from __future__ import annotations

import importlib.util

_REMOVED_WRAPPER_MODULES = (
    "packages.agents.sub_agents.planner.agent",
    "packages.agents.sub_agents.planner.adapters",
    "packages.agents.sub_agents.researcher.agent",
    "packages.agents.sub_agents.researcher.adapters",
    "packages.agents.sub_agents.content_creator.agent",
    "packages.agents.sub_agents.content_creator.adapters",
    "packages.agents.sub_agents.diagnostician.agent",
    "packages.agents.sub_agents.diagnostician.adapters",
    "packages.agents.sub_agents.roadmap_agent.agent",
    "packages.agents.sub_agents.roadmap_agent.adapters",
    "packages.agents.sub_agents.reviewer.agent",
    "packages.agents.sub_agents.reviewer.adapters",
)


def test_legacy_subagent_stategraph_wrappers_are_removed() -> None:
    for module_name in _REMOVED_WRAPPER_MODULES:
        assert importlib.util.find_spec(module_name) is None


def test_retained_node_modules_still_resolve() -> None:
    retained_modules = (
        "packages.agents.sub_agents.planner.nodes",
        "packages.agents.sub_agents.researcher.nodes",
        "packages.agents.sub_agents.content_creator.nodes",
        "packages.agents.sub_agents.diagnostician.nodes",
        "packages.agents.sub_agents.roadmap_agent.nodes",
        "packages.agents.sub_agents.reviewer.nodes",
    )

    for module_name in retained_modules:
        assert importlib.util.find_spec(module_name) is not None
