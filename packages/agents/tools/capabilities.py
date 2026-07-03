from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packages.agents.tools.fs import ToolUnavailableError


class ToolStatus(StrEnum):
    IMPLEMENTED = "IMPLEMENTED"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    FORBIDDEN = "FORBIDDEN"


@dataclass(frozen=True, slots=True)
class ToolCapability:
    name: str
    status: ToolStatus


AGENT_CAPABILITIES: dict[str, tuple[ToolCapability, ...]] = {
    "planner": (
        ToolCapability("web_search", ToolStatus.IMPLEMENTED),
        ToolCapability("read_file", ToolStatus.IMPLEMENTED),
        ToolCapability("write_file", ToolStatus.FORBIDDEN),
        ToolCapability("task", ToolStatus.UNIMPLEMENTED),
    ),
    "researcher": (
        ToolCapability("web_search", ToolStatus.IMPLEMENTED),
        ToolCapability("web_fetch", ToolStatus.IMPLEMENTED),
        ToolCapability("read_file", ToolStatus.IMPLEMENTED),
        ToolCapability("write_file", ToolStatus.FORBIDDEN),
        ToolCapability("task", ToolStatus.UNIMPLEMENTED),
    ),
    "content_creator": (
        ToolCapability("read_file", ToolStatus.IMPLEMENTED),
        ToolCapability("write_file", ToolStatus.IMPLEMENTED),
        ToolCapability("task", ToolStatus.UNIMPLEMENTED),
    ),
    "reviewer": (
        ToolCapability("read_file", ToolStatus.IMPLEMENTED),
        ToolCapability("write_file", ToolStatus.FORBIDDEN),
        ToolCapability("task", ToolStatus.UNIMPLEMENTED),
    ),
}


def bind_agent_tools(agent: str, requested: tuple[str, ...]) -> tuple[str, ...]:
    capabilities = {capability.name: capability.status for capability in AGENT_CAPABILITIES[agent]}
    bound: list[str] = []
    for tool_name in requested:
        status = capabilities.get(tool_name, ToolStatus.FORBIDDEN)
        match status:
            case ToolStatus.IMPLEMENTED:
                bound.append(tool_name)
            case ToolStatus.UNIMPLEMENTED | ToolStatus.FORBIDDEN:
                raise ToolUnavailableError(tool_name, status.value)
    return tuple(bound)
