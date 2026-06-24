"""ContentComponent discriminated union — all 14 typed component variants.

The union is discriminated on the `type` field. LLM output is validated
against this union; Eta templates dispatch by `component.type`.
"""
from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from common.contracts.components.cards import (
    PatternCard,
    PatternGrid,
    StatCard,
    StatGrid,
    TaxonomyGrid,
    TaxonomyItem,
    TraitCard,
    TraitGrid,
)
from common.contracts.components.concept import (
    ConceptMap,
    ConceptNode,
    TimelineComponent,
    TimelineEvent,
)
from common.contracts.components.questions import QuestionCard, QuestionList
from common.contracts.components.tabular import Table
from common.contracts.components.textual import (
    Callout,
    Heading,
    OrderedList,
    Paragraph,
    UnorderedList,
)
from common.contracts.components.timeline import (
    FlowItem,
    FlowStep,
    PhaseBlock,
    PhaseTimeline,
    RoadmapPhase,
)

ContentComponent = Annotated[
    Union[
        Heading,
        Paragraph,
        Callout,
        OrderedList,
        UnorderedList,
        Table,
        StatGrid,
        PatternGrid,
        TraitGrid,
        TaxonomyGrid,
        PhaseTimeline,
        FlowStep,
        QuestionCard,
        QuestionList,
        ConceptMap,
        TimelineComponent,
    ],
    Field(discriminator="type"),
]

__all__ = [
    "ContentComponent",
    # textual
    "Heading",
    "Paragraph",
    "Callout",
    "OrderedList",
    "UnorderedList",
    # tabular
    "Table",
    # cards
    "StatCard",
    "StatGrid",
    "PatternCard",
    "PatternGrid",
    "TraitCard",
    "TraitGrid",
    "TaxonomyItem",
    "TaxonomyGrid",
    # timeline
    "PhaseBlock",
    "RoadmapPhase",
    "PhaseTimeline",
    "FlowItem",
    "FlowStep",
    # questions
    "QuestionCard",
    "QuestionList",
    # concept
    "ConceptNode",
    "ConceptMap",
    "TimelineEvent",
    "TimelineComponent",
]
