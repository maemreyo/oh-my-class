"""Timeline components — PhaseTimeline (roadmap phases), FlowStep (lesson flow)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PhaseBlock(BaseModel):
    label: str
    items: list[str] | None = None
    text: str | None = None
    full: bool = False


class RoadmapPhase(BaseModel):
    title: str
    when: str
    goal: str | None = None
    blocks: list[PhaseBlock] = []
    output: str | None = None
    group: str = "a"


class PhaseTimeline(BaseModel):
    type: Literal["phase_timeline"] = "phase_timeline"
    phases: list[RoadmapPhase]


class FlowItem(BaseModel):
    time: str
    title: str
    body: str


class FlowStep(BaseModel):
    type: Literal["flow_step"] = "flow_step"
    steps: list[FlowItem]
