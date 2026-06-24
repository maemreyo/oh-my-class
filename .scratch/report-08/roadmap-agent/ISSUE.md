---
title: "Roadmap Agent: StudentProfile + LearningRoadmap Generation"
status: ready
labels: [agents, roadmap, student-profile]
created: 2026-06-24
priority: p1
report: "08"
---

## What to build

A `RoadmapAgent` sub-agent: takes `DiagnosticReport` + `StudentProfile` → generates a `RoadmapContent` artifact (the personalized learning roadmap). New `StudentProfile` contract. New `roadmap` artifact type wired into pipeline.

**Design decision:** Same sub-agent pattern. `StudentProfile` is a separate contract (not part of `class_info`) to keep student-level concerns separate from class-level concerns (SoC).

## File Structure

```
common/contracts/
├── student_profile.py       # StudentProfile, LearningStyle, PersonalityTrait

packages/agents/sub_agents/
└── roadmap_agent/
    ├── __init__.py
    ├── agent.py             # make_roadmap_agent() + roadmap_graph_node()
    ├── nodes.py             # roadmap_node() — generates RoadmapContent JSON
    ├── state.py             # RoadmapAgentState TypedDict
    ├── tools.py             # book_recommender(), milestone_calculator()
    └── prompts/
        ├── __init__.py
        └── system.md        # system prompt for roadmap generation
```

## Implementation Spec

### `common/contracts/student_profile.py`
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

class PersonalityTrait(BaseModel):
    trait: str              # "shy" | "film_learner" | "depth_oriented" | ...
    vn_name: str
    teaching_principle: str  # how to adapt teaching for this trait

class LearningStyle(BaseModel):
    primary: str            # "visual" | "auditory" | "kinesthetic" | "reading"
    media_preference: str | None = None   # "film" | "podcast" | "text" | ...
    format_preference: str | None = None  # "1v1" | "group" | "self-study"

class StudentProfile(BaseModel):
    student_id: str
    learning_style: LearningStyle
    personality_traits: list[PersonalityTrait] = []
    weaknesses: list[str] = []          # ["vocabulary", "nuance", "collocation"]
    strengths: list[str] = []
    target_score: int | None = None     # e.g., 40 (for HSA)
    target_exam: str | None = None      # "HSA" | "IELTS" | "TOEIC"
    study_duration_months: int = 6
    tools: list[str] = []               # ["google_classroom", "homework_app"]
    raw_context: str = ""               # original teacher description
```

### `sub_agents/roadmap_agent/tools.py`
```python
@tool
def book_recommender(level: str, weak_skills: list[str]) -> dict:
    """Recommend textbooks based on level and weak skills (Destination B2/C1, etc.)."""
    ...

@tool
def milestone_calculator(
    target_score: int,
    current_error_rate: float,
    months: int
) -> list[dict]:
    """Calculate monthly score milestones for a target exam."""
    ...
```

### Pipeline integration
Add `step_04b_roadmap` between `step_03_blueprint` and `gate_01_blueprint_approval` when `diagnostic_report` is present. Output: `RoadmapContent` added to `artifacts[]`.

## Prompt

`prompts/system.md` instructs agent to:
1. Read `DiagnosticReport` for knowledge gaps and error patterns
2. Read `StudentProfile` for personality, learning style, tools
3. Generate `RoadmapContent` JSON with 5-7 phases, each with goal, blocks, output
4. Incorporate book recommendations (Destination B2/C1) per phase
5. Factor personality traits into activity design (shy → no group pressure, film → use video)

## Tests

```
packages/agents/tests/sub_agents/test_roadmap_agent.py
common/contracts/tests/test_student_profile.py
```

## Acceptance Criteria

- [ ] `StudentProfile` contract defined with personality traits, learning style, weaknesses
- [ ] `RoadmapAgent` returns `RoadmapContent`-shaped dict from `roadmap_node()`
- [ ] `book_recommender` tool covers B1/B2/C1 levels with Destination series entries
- [ ] `milestone_calculator` returns list of monthly milestone dicts
- [ ] `step_04b_roadmap` node added to graph, skipped when no diagnostic_report
- [ ] `OhMyClassState.student_profile` field added

## Dependencies

- Blocked by: `diagnostic-agent` (needs DiagnosticReport), `roadmap-template` (renders output)
- Priority: p1
