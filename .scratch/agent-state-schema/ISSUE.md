---
title: "Agent State Schema: F2 Separation — Graph State vs Agent States"
status: ready
labels: [architecture, agents, state]
created: 2026-06-24
priority: p0
---

## What to build

Separate the monolithic `OhMyClassState` into graph-level state + per-agent states. Each sub-agent gets its own `state.py` with a minimal `TypedDict`. The graph node adapters handle extract/inject between graph state and agent state.

**Design decision (grilling Q6):** F2 — separate schemas per agent. Agent states are independently testable, versionable, and deployable without touching graph schema.

## Current State

```
packages/agents/
├── state.py           # OhMyClassState TypedDict (graph-level) — EXISTS
├── lead_agent/
│   └── agent.py       # raise NotImplementedError stubs
├── planner/
│   └── planner.py     # real LLM calls, NOT wired to graph
├── researcher/
│   └── researcher.py  # real LLM calls, NOT wired to graph
├── content_creator/
│   └── content_creator.py
└── reviewer/
    └── reviewer.py
```

No per-agent state files exist. All agents currently use the full `OhMyClassState` or their own ad-hoc dicts.

## Target Structure

```
packages/agents/
├── state.py                    # OhMyClassState — graph-level ONLY (keep, trim)
├── lead_agent/
│   ├── agent.py
│   └── state.py                # LeadAgentState (NEW)
├── planner/
│   ├── planner.py
│   └── state.py                # PlannerState (NEW)
├── researcher/
│   ├── researcher.py
│   └── state.py                # ResearcherState (NEW)
├── content_creator/
│   ├── content_creator.py
│   └── state.py                # ContentCreatorState (NEW)
└── reviewer/
    ├── reviewer.py
    └── state.py                # ReviewerState (NEW)
```

## Implementation Spec

### 1. `packages/agents/state.py` — Trim to graph-level only

Keep these fields (graph routing + HITL gate data):
```python
class OhMyClassState(TypedDict):
    # Run identity
    run_id: str
    teacher_id: str

    # Input
    raw_request: str
    class_info: dict

    # Pipeline outputs (one per step)
    lesson_plan: dict | None            # Step 03 → Blueprint
    scope: dict | None                  # Step 05 → Pack Scope
    visual_config: dict | None          # Step 06 → Visual Engine
    research_results: list[dict] | None # Step 07 → Research
    artifacts: list[dict] | None        # Step 08 → Generate
    review_results: dict | None         # Step 10 → Review

    # Gate data
    teacher_decision: str | None        # "approve" | "reject" | "edit"
    teacher_feedback: str | None
    gate_payload: dict | None           # data shown to teacher at gate

    # Control flow
    revision_count: int
    overall_score: float | None
    error: str | None

    # Token tracking (for middleware)
    token_usage: dict | None            # {"input": int, "output": int, "total": int}
```

Remove from `OhMyClassState`: agent-internal scratchpads, messages lists, tool_calls — those belong in agent states.

### 2. `packages/agents/lead_agent/state.py` — NEW

```python
from __future__ import annotations
from typing import Annotated
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages


class LeadAgentState(MessagesState):
    """Internal state for the Lead Agent ReAct loop.

    Extends MessagesState (adds `messages: Annotated[list, add_messages]`).
    The Lead Agent reads task context from this state and writes tool results.
    Graph state (OhMyClassState) is injected by node adapters, NOT directly accessed.
    """
    # Injected by graph node adapter before agent.invoke()
    task: str                           # current task description
    context: dict                       # relevant fields from OhMyClassState

    # Written by agent, extracted by node adapter after agent.invoke()
    result: dict | None                 # structured output for graph state
    recovery_guidance: str | None       # D3: semantic guidance for next retry
```

### 3. `packages/agents/planner/state.py` — NEW

```python
from __future__ import annotations
from langgraph.graph import MessagesState


class PlannerState(MessagesState):
    """Internal state for the Planner Agent."""
    raw_request: str
    class_info: dict
    lesson_plan: dict | None            # output
```

### 4. `packages/agents/researcher/state.py` — NEW

```python
from __future__ import annotations
from langgraph.graph import MessagesState


class ResearcherState(MessagesState):
    """Internal state for the Researcher Agent."""
    lesson_plan: dict
    research_results: list[dict] | None  # output
```

### 5. `packages/agents/content_creator/state.py` — NEW

```python
from __future__ import annotations
from langgraph.graph import MessagesState


class ContentCreatorState(MessagesState):
    """Internal state for the Content Creator Agent."""
    lesson_plan: dict
    research_results: list[dict]
    scope: dict
    visual_config: dict
    artifacts: list[dict] | None        # output
```

### 6. `packages/agents/reviewer/state.py` — NEW

```python
from __future__ import annotations
from langgraph.graph import MessagesState


class ReviewerState(MessagesState):
    """Internal state for the Reviewer Agent."""
    artifacts: list[dict]
    lesson_plan: dict                   # used for alignment check
    review_results: dict | None         # output: {overall_score, per_artifact, feedback}
```

## Acceptance Criteria

- [ ] Each agent has its own `state.py` with a minimal `TypedDict`/`MessagesState` subclass
- [ ] `OhMyClassState` contains only graph-routing fields (no agent-internal scratchpads)
- [ ] Each agent state can be instantiated independently without `OhMyClassState`
- [ ] All existing agent code that references `OhMyClassState` directly is updated to use node adapters (extract fields → build agent state → inject result back)
- [ ] Tests: each state file has a basic instantiation test

## Dependencies

- Blocks: `sub-agent-compiled-graphs`, `lead-agent-react`, `hitl-gate-wrapper`
- Blocked by: nothing (can start immediately)
