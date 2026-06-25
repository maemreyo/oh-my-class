"""Concept and timeline components — ConceptMap (with edges), VocabCluster, ContrastivePairs, PhrasalVerbCluster."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ConceptRelationType = Literal["synonymy", "contrast", "collocation", "register", "part_of", "example_of"]
GroupColor = Literal["a", "b", "c", "d", "e"]


class ConceptNode(BaseModel):
    id: str
    label: str


class ConceptEdge(BaseModel):
    source: str
    target: str
    relation: ConceptRelationType
    label: str | None = None


class ConceptMap(BaseModel):
    type: Literal["concept_map"] = "concept_map"
    nodes: list[ConceptNode]
    edges: list[ConceptEdge] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    time: str
    label: str


class TimelineComponent(BaseModel):
    type: Literal["timeline"] = "timeline"
    events: list[TimelineEvent]


class VocabItem(BaseModel):
    word: str
    definition: str
    example: str | None = None


class VocabCluster(BaseModel):
    type: Literal["vocab_cluster"] = "vocab_cluster"
    title: str
    description: str | None = None
    items: list[VocabItem] = Field(default_factory=list)
    discrimination_prompt: str | None = None


class ContrastivePairRow(BaseModel):
    terms: str
    distinction: str


class ContrastivePairs(BaseModel):
    type: Literal["contrastive_pairs"] = "contrastive_pairs"
    title: str | None = None
    rows: list[ContrastivePairRow] = Field(default_factory=list)


class PhrasalVerbItem(BaseModel):
    verb: str
    meaning: str
    example: str | None = None


class PhrasalVerbGroup(BaseModel):
    label: str
    color: GroupColor = "a"
    items: list[PhrasalVerbItem] = Field(default_factory=list)


class PhrasalVerbCluster(BaseModel):
    type: Literal["phrasal_verb_cluster"] = "phrasal_verb_cluster"
    groups: list[PhrasalVerbGroup] = Field(default_factory=list)
