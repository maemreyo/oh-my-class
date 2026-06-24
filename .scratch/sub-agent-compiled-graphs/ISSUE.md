---
title: "Sub-Agent Compiled Graphs: C2 Pattern — Each Agent as Standalone CompiledGraph"
status: ready
labels: [architecture, agents, langgraph]
created: 2026-06-24
priority: p0
report: "01"
---

## What to build

Refactor each sub-agent (planner, researcher, content_creator, reviewer) from ad-hoc LLM call wrappers into **LangGraph compiled graphs** with their own state, nodes, and edges. Each agent becomes independently testable, runnable standalone, and usable as a tool adapter by the Lead Agent.

**Design decision (grilling Q3):** C2 — compiled subgraph per agent. Exposed to Lead Agent via thin `@tool` adapters (C1 interface on top of C2 implementation).

## Current State

Agents exist as class-based wrappers with direct LLM calls:
- `packages/agents/planner/planner.py` → `PlannerAgent.design_lesson_plan()`
- `packages/agents/researcher/researcher.py` → `ResearcherAgent.research()`
- `packages/agents/content_creator/content_creator.py` → `ContentCreatorAgent.create_content()`
- `packages/agents/reviewer/reviewer.py` → `ReviewerAgent.review()`

None are LangGraph compiled graphs. None have state files. None can be run standalone.

## Target Pattern (per sub-agent)

```
packages/agents/planner/
├── agent.py          # make_planner_agent() → CompiledGraph   [REWRITE]
├── state.py          # PlannerState                           [from agent-state-schema issue]
├── nodes.py          # individual node functions              [NEW]
├── prompts/
│   └── system.md     # system prompt as markdown              [from prompt-management issue]
└── tests/
    └── test_planner.py  # test compiled graph standalone      [NEW]
```

## Implementation Spec

### Pattern for ALL sub-agents

Each agent follows this factory pattern:

```python
# packages/agents/{name}/agent.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from packages.agents.{name}.state import {Name}State
from packages.agents.{name}.nodes import {name}_node


def make_{name}_agent(checkpointer=None) -> CompiledGraph:
    """Factory — returns a compiled graph for the {Name} Agent.

    Can be run standalone:
        agent = make_planner_agent()
        result = agent.invoke({"raw_request": "...", "class_info": {...}})
    """
    builder = StateGraph({Name}State)
    builder.add_node("{name}", {name}_node)
    builder.set_entry_point("{name}")
    builder.add_edge("{name}", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())
```

### 1. Planner Agent

`packages/agents/planner/nodes.py`:
```python
from langchain_core.messages import HumanMessage
from packages.agents.planner.state import PlannerState


async def planner_node(state: PlannerState) -> dict:
    """Calls LLM to design a lesson blueprint from raw_request + class_info."""
    # Load existing logic from planner.py PlannerAgent.design_lesson_plan()
    # Return: {"lesson_plan": {...}, "messages": [...]}
    ...
```

`packages/agents/planner/agent.py` — `make_planner_agent() → CompiledGraph`

### 2. Researcher Agent

`packages/agents/researcher/nodes.py`:
```python
async def researcher_node(state: ResearcherState) -> dict:
    """Searches and synthesizes research for the lesson plan."""
    # Load from researcher.py ResearcherAgent.research()
    # Return: {"research_results": [...], "messages": [...]}
    ...
```

### 3. Content Creator Agent

`packages/agents/content_creator/nodes.py`:
```python
async def content_creator_node(state: ContentCreatorState) -> dict:
    """Generates lesson artifacts (lesson, worksheet, quiz) from plan + research."""
    # Load from content_creator.py ContentCreatorAgent.create_content()
    # Return: {"artifacts": [...], "messages": [...]}
    ...
```

### 4. Reviewer Agent

`packages/agents/reviewer/nodes.py`:
```python
async def reviewer_node(state: ReviewerState) -> dict:
    """Reviews artifacts using G-Eval criteria. Returns scores + feedback."""
    # Load from reviewer.py ReviewerAgent.review()
    # Return: {"review_results": {...}, "messages": [...]}
    ...
```

## Tool Adapters (Lead Agent interface)

After sub-agent graphs are built, wrap each as a `@tool` in `packages/agents/lead_agent/tools.py`:

```python
from langchain_core.tools import tool
from packages.agents.planner.agent import make_planner_agent
from packages.agents.researcher.agent import make_researcher_agent
from packages.agents.content_creator.agent import make_content_creator_agent
from packages.agents.reviewer.agent import make_reviewer_agent

# Lazy-init (avoid re-compiling on every call)
_planner = None
_researcher = None
_creator = None
_reviewer = None


@tool
def run_planner(raw_request: str, class_info: dict) -> dict:
    """Design a lesson blueprint from the teacher's request."""
    global _planner
    if _planner is None:
        _planner = make_planner_agent()
    result = _planner.invoke({"raw_request": raw_request, "class_info": class_info})
    return result.get("lesson_plan", {})


@tool
def run_researcher(lesson_plan: dict) -> list:
    """Research content for the lesson plan."""
    global _researcher
    if _researcher is None:
        _researcher = make_researcher_agent()
    result = _researcher.invoke({"lesson_plan": lesson_plan})
    return result.get("research_results", [])


@tool
def run_content_creator(lesson_plan: dict, research_results: list, scope: dict, visual_config: dict) -> list:
    """Generate lesson artifacts (lesson, worksheet, quiz)."""
    global _creator
    if _creator is None:
        _creator = make_content_creator_agent()
    result = _creator.invoke({
        "lesson_plan": lesson_plan,
        "research_results": research_results,
        "scope": scope,
        "visual_config": visual_config,
    })
    return result.get("artifacts", [])


@tool
def run_reviewer(artifacts: list, lesson_plan: dict) -> dict:
    """Review artifacts using G-Eval criteria. Returns overall_score and feedback."""
    global _reviewer
    if _reviewer is None:
        _reviewer = make_reviewer_agent()
    result = _reviewer.invoke({"artifacts": artifacts, "lesson_plan": lesson_plan})
    return result.get("review_results", {})
```

## Tests

Each sub-agent must have a standalone test that does NOT require the full graph:

```python
# packages/agents/planner/tests/test_planner.py

import pytest
from unittest.mock import patch, MagicMock
from packages.agents.planner.agent import make_planner_agent


def test_planner_agent_standalone():
    """Planner can be invoked as a compiled graph without the main pipeline."""
    with patch("packages.agents.planner.nodes.ChatOpenAI") as mock_llm:
        mock_llm.return_value.invoke.return_value = MagicMock(
            content='{"topic": "Photosynthesis", "grade_level": "Grade 5"}'
        )
        agent = make_planner_agent()
        result = agent.invoke({
            "raw_request": "Teach photosynthesis to Grade 5",
            "class_info": {"grade": 5, "subject": "science"},
        })
    assert result["lesson_plan"] is not None


def test_planner_returns_lesson_plan_structure():
    """Lesson plan output has required keys."""
    ...
```

## Acceptance Criteria

- [ ] `make_planner_agent()`, `make_researcher_agent()`, `make_content_creator_agent()`, `make_reviewer_agent()` all return `CompiledGraph`
- [ ] Each compiled graph can be `.invoke()`d standalone without the main `graph.py`
- [ ] `packages/agents/lead_agent/tools.py` exports `run_planner`, `run_researcher`, `run_content_creator`, `run_reviewer` as `@tool`
- [ ] Each sub-agent has its own `nodes.py` with node functions separate from agent factory
- [ ] Each sub-agent has standalone tests (mock LLM, verify state structure)
- [ ] Existing `planner.py`, `researcher.py`, `content_creator.py`, `reviewer.py` logic migrated (not duplicated)

## Dependencies

- Blocked by: `agent-state-schema` (needs per-agent state files)
- Blocks: `lead-agent-react` (needs tools.py to exist)
