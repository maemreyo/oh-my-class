"""Concept and timeline components — ConceptMap, TimelineComponent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ConceptNode(BaseModel):
    id: str
    label: str


class ConceptMap(BaseModel):
    type: Literal["concept_map"] = "concept_map"
    nodes: list[ConceptNode]


class TimelineEvent(BaseModel):
    time: str
    label: str


class TimelineComponent(BaseModel):
    type: Literal["timeline"] = "timeline"
    events: list[TimelineEvent]
