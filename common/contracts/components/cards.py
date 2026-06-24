"""Card grid components — StatGrid, PatternGrid, TraitGrid, TaxonomyGrid."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class StatCard(BaseModel):
    label: str
    value: str
    variant: Literal["target", "now", "default"] = "default"


class StatGrid(BaseModel):
    type: Literal["stat_grid"] = "stat_grid"
    stats: list[StatCard]


class PatternCard(BaseModel):
    id: str
    group: str
    title: str
    description: str


class PatternGrid(BaseModel):
    type: Literal["pattern_grid"] = "pattern_grid"
    patterns: list[PatternCard]


class TraitCard(BaseModel):
    icon: str
    title: str
    body: str


class TraitGrid(BaseModel):
    type: Literal["trait_grid"] = "trait_grid"
    traits: list[TraitCard]


class TaxonomyItem(BaseModel):
    icon: str
    title: str
    body: str
    example: str


class TaxonomyGrid(BaseModel):
    type: Literal["taxonomy_grid"] = "taxonomy_grid"
    items: list[TaxonomyItem]
