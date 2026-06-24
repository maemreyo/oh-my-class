"""RoadmapContent model — typed artifact for personalized learning roadmaps.

Produced by the RoadmapAgent. Consumed by the renderer's roadmap.eta template.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from common.contracts.components import ContentComponent, StatCard


class NavItem(BaseModel):
    label: str
    href: str
    group: str = "a"


class LegendItem(BaseModel):
    color: str
    label: str


class RoadmapHero(BaseModel):
    eyebrow: str = ""
    title: str
    lede: str = ""
    stamp: str = ""
    stats: list[StatCard] = Field(default_factory=list)


class RoadmapSidebar(BaseModel):
    title: str
    subtitle: str
    stats: list[StatCard] = Field(default_factory=list)
    nav: list[NavItem] = Field(default_factory=list)
    legend: list[LegendItem] = Field(default_factory=list)


class RoadmapSection(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    tag_num: str | None = None
    components: list[ContentComponent] = Field(default_factory=list)


class RoadmapContent(BaseModel):
    artifact_type: Literal["roadmap"] = "roadmap"
    title: str
    theme: str = "default"
    hero: RoadmapHero
    sections: list[RoadmapSection] = Field(default_factory=list)
    sidebar: RoadmapSidebar
    accessibility: dict = Field(default_factory=lambda: {"language": "vi"})
