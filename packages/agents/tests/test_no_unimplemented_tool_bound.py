from __future__ import annotations

import pytest

from packages.agents.tools.capabilities import AGENT_CAPABILITIES, ToolStatus, bind_agent_tools
from packages.agents.tools.fs import ToolUnavailableError


def test_no_unimplemented_tool_bound() -> None:
    for agent, capabilities in AGENT_CAPABILITIES.items():
        implemented = tuple(
            capability.name
            for capability in capabilities
            if capability.status is ToolStatus.IMPLEMENTED
        )

        assert bind_agent_tools(agent, implemented) == implemented


def test_deliberately_bound_stub_is_caught() -> None:
    with pytest.raises(ToolUnavailableError) as exc_info:
        bind_agent_tools("content_creator", ("task",))

    assert exc_info.value.fail_type == "tool_unavailable"
    assert exc_info.value.reason == ToolStatus.UNIMPLEMENTED.value


def test_production_tool_entrypoints_call_capability_registry() -> None:
    import inspect

    from packages.agents.sub_agents.content_creator import tools as content_creator_tools
    from packages.agents.sub_agents.planner import tools as planner_tools
    from packages.agents.sub_agents.researcher import tools as researcher_tools
    from packages.agents.sub_agents.reviewer import tools as reviewer_tools

    modules = (content_creator_tools, planner_tools, researcher_tools, reviewer_tools)
    for module in modules:
        source = inspect.getsource(module)
        assert "bind_agent_tools(" in source
