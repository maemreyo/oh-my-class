---
title: "ContentComponent Discriminated Union — Modular Python-first Schema"
status: ready
labels: [schema, contracts, typescript]
created: 2026-06-24
priority: p0
report: "08"
---

## What to build

A typed `ContentComponent` discriminated union in Python Pydantic + auto-generated TypeScript Zod. Replaces the loose `sections: list[dict[str, Any]]` in `ArtifactContent`. Also adds `AnswerKeyContent` and `RoadmapContent` artifact models.

**Design decision:** Python Pydantic is canonical. TypeScript Zod is auto-generated. Components split into category files — no god-file.

## File Structure

```
common/contracts/components/
├── __init__.py          # exports ContentComponent union + all component models
├── textual.py           # Heading, Paragraph, Callout, OrderedList, UnorderedList
├── tabular.py           # Table
├── cards.py             # StatGrid, PatternGrid, TraitGrid, TaxonomyGrid
├── timeline.py          # PhaseTimeline (with RoadmapPhase), FlowStep
├── questions.py         # QuestionCard, QuestionList
└── concept.py           # ConceptMap, TimelineEvent

common/contracts/
├── answer_key.py        # AnswerKeyContent, AnswerKeySection
└── roadmap.py           # RoadmapContent, RoadmapSection, RoadmapSidebar
```

## Implementation Spec

### `components/textual.py`
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

class Heading(BaseModel):
    type: Literal["heading"] = "heading"
    level: Literal[1, 2, 3, 4]
    text: str
    id: str | None = None

class Paragraph(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    text: str

class Callout(BaseModel):
    type: Literal["callout"] = "callout"
    variant: Literal["note", "warning", "tip", "alert"]
    title: str | None = None
    body: str

class OrderedList(BaseModel):
    type: Literal["ordered_list"] = "ordered_list"
    items: list[str]

class UnorderedList(BaseModel):
    type: Literal["unordered_list"] = "unordered_list"
    items: list[str]
```

### `components/tabular.py`
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

class Table(BaseModel):
    type: Literal["table"] = "table"
    columns: list[str]
    rows: list[list[str]]
    caption: str | None = None
```

### `components/cards.py`
```python
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
```

### `components/timeline.py`
```python
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
```

### `components/questions.py`
```python
from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel

class QuestionCard(BaseModel):
    type: Literal["question_card"] = "question_card"
    id: int | str
    text: str
    options: dict[str, str]          # {"A": "...", "B": "...", ...}
    answer: str                       # correct option letter
    explain: str
    group: str = "a"
    wrong_reasons: dict[str, str] | None = None    # {"B": "why B wrong", ...}
    essence: str | None = None        # "bản chất" — core knowledge point
    tip: str | None = None            # "mẹo làm bài" — test-taking strategy

class QuestionList(BaseModel):
    type: Literal["question_list"] = "question_list"
    questions: list[QuestionCard]
    section_key: str
    group: str
    title: str
    sub: str | None = None
    instruction: str | None = None
    summary: str | None = None
    range: str | None = None
```

### `components/concept.py`
```python
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
```

### `components/__init__.py`
```python
from __future__ import annotations
from typing import Annotated, Union
from pydantic import Field

from common.contracts.components.textual import Heading, Paragraph, Callout, OrderedList, UnorderedList
from common.contracts.components.tabular import Table
from common.contracts.components.cards import StatGrid, PatternGrid, TraitGrid, TaxonomyGrid
from common.contracts.components.timeline import PhaseTimeline, FlowStep
from common.contracts.components.questions import QuestionCard, QuestionList
from common.contracts.components.concept import ConceptMap, TimelineComponent

ContentComponent = Annotated[
    Union[
        Heading, Paragraph, Callout, OrderedList, UnorderedList,
        Table,
        StatGrid, PatternGrid, TraitGrid, TaxonomyGrid,
        PhaseTimeline, FlowStep,
        QuestionCard, QuestionList,
        ConceptMap, TimelineComponent,
    ],
    Field(discriminator="type"),
]

__all__ = [
    "ContentComponent",
    "Heading", "Paragraph", "Callout", "OrderedList", "UnorderedList",
    "Table",
    "StatGrid", "StatCard", "PatternGrid", "PatternCard",
    "TraitGrid", "TraitCard", "TaxonomyGrid", "TaxonomyItem",
    "PhaseTimeline", "RoadmapPhase", "PhaseBlock", "FlowStep", "FlowItem",
    "QuestionCard", "QuestionList",
    "ConceptMap", "TimelineComponent",
]
```

### `answer_key.py`
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from common.contracts.components import ContentComponent

class AnswerKeySection(BaseModel):
    id: str
    title: str
    sub: str | None = None
    range: str | None = None
    group: str = "a"
    instruction: str | None = None
    summary: str | None = None
    components: list[ContentComponent] = []

class AnswerKeyMetadata(BaseModel):
    total_questions: int
    groups: dict[str, dict[str, str]] = {}  # {"a": {"label": "...", "color": "..."}}

class AnswerKeyContent(BaseModel):
    artifact_type: Literal["answer_key"] = "answer_key"
    title: str
    theme: str = "default"
    sections: list[AnswerKeySection] = []
    metadata: AnswerKeyMetadata = Field(default_factory=AnswerKeyMetadata)
    accessibility: dict = Field(default_factory=lambda: {"language": "vi"})
```

### `roadmap.py`
```python
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

class RoadmapSidebar(BaseModel):
    title: str
    subtitle: str
    stats: list[StatCard] = []
    nav: list[NavItem] = []
    legend: list[LegendItem] = []

class RoadmapHero(BaseModel):
    eyebrow: str = ""
    title: str
    lede: str = ""
    stamp: str = ""
    stats: list[StatCard] = []

class RoadmapSection(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    tag_num: str | None = None
    components: list[ContentComponent] = []

class RoadmapContent(BaseModel):
    artifact_type: Literal["roadmap"] = "roadmap"
    title: str
    theme: str = "default"
    hero: RoadmapHero
    sections: list[RoadmapSection] = []
    sidebar: RoadmapSidebar
    accessibility: dict = Field(default_factory=lambda: {"language": "vi"})
```

### Update `common/contracts/artifact.py`
Add `"answer_key"` and `"roadmap"` to the `artifact_type` Literal:
```python
artifact_type: Literal[
    "lesson", "worksheet", "quiz", "drill", "recap", "infographic",
    "answer_key", "roadmap"
]
```

## Tests

```
common/contracts/tests/test_components.py
common/contracts/tests/test_answer_key.py
common/contracts/tests/test_roadmap.py
```

Test each component type instantiation, discriminated union parsing, and invalid type rejection.

## Acceptance Criteria

- [ ] All 14 component types defined in separate category files
- [ ] `ContentComponent` discriminated union exported from `__init__.py`
- [ ] `AnswerKeyContent` and `RoadmapContent` models defined
- [ ] `artifact_type` Literal includes `"answer_key"` and `"roadmap"`
- [ ] Each component type has at least 3 tests (valid, invalid, edge case)
- [ ] No single file > 150 lines

## Dependencies

- Blocks: `template-engine`, `answer-key-template`, `roadmap-template`, `diagnostic-agent`, `roadmap-agent`
- Priority: p0
