---
title: "Lead Agent ReAct: B2 Pattern — Tool Sequencer with Semantic Recovery"
status: ready
labels: [architecture, agents, langgraph]
created: 2026-06-24
priority: p0
---

## What to build

Implement `make_lead_agent()` as a LangGraph ReAct agent (`create_react_agent`) that orchestrates sub-agents via tool calls. The Lead Agent has genuine decision-making power at retry/recovery points (D3: semantic recovery), while the graph's conditional edges enforce structural guardrails (max retries, score thresholds).

**Design decisions:**
- **B2**: Tool sequencer with LLM-driven recovery (not pure ReAct, not thin wrapper)
- **C2 + adapter**: Sub-agents are compiled graphs exposed via `@tool` wrappers
- **D3**: Graph handles structural retry limits; Lead Agent provides semantic recovery guidance
- **E3**: HITL gates are wrapper nodes in the graph — Lead Agent is transparent to them
- **G2**: System prompt loaded from `prompts/system.md` markdown file

## Current State

```python
# packages/agents/lead_agent/agent.py
def make_lead_agent():
    raise NotImplementedError("make_lead_agent() stub")

def lead_agent_node(state):
    raise NotImplementedError("lead_agent_node() stub")
```

## Target Structure

```
packages/agents/lead_agent/
├── agent.py          # make_lead_agent() → CompiledGraph     [REWRITE]
├── state.py          # LeadAgentState                        [from agent-state-schema]
├── tools.py          # @tool adapters for sub-agents         [from sub-agent-compiled-graphs]
├── recovery.py       # D3 semantic recovery logic            [NEW]
├── prompts/
│   └── system.md     # system prompt                        [from prompt-management]
└── tests/
    └── test_lead_agent.py
```

## Implementation Spec

### `packages/agents/lead_agent/agent.py`

```python
from __future__ import annotations

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import CompiledGraph
from langgraph.checkpoint.memory import MemorySaver

from packages.agents.lead_agent.state import LeadAgentState
from packages.agents.lead_agent.tools import (
    run_planner,
    run_researcher,
    run_content_creator,
    run_reviewer,
)
from packages.agents.lead_agent.prompts import load_system_prompt


TOOLS = [run_planner, run_researcher, run_content_creator, run_reviewer]


def make_lead_agent(
    model=None,
    checkpointer=None,
    tools: list | None = None,
) -> CompiledGraph:
    """Factory — returns a compiled ReAct graph for the Lead Agent.

    The Lead Agent sequences tool calls deterministically for the standard path,
    and uses LLM reasoning for semantic recovery when review scores are low (D3).
    """
    from langchain_openai import ChatOpenAI

    llm = model or ChatOpenAI(model="gpt-4o", temperature=0)
    system_prompt = load_system_prompt()

    return create_react_agent(
        model=llm,
        tools=tools or TOOLS,
        state_schema=LeadAgentState,
        state_modifier=SystemMessage(content=system_prompt),
        checkpointer=checkpointer or MemorySaver(),
    )
```

### `packages/agents/lead_agent/prompts/__init__.py`

```python
from pathlib import Path


def load_system_prompt(name: str = "system") -> str:
    """Load a prompt from the prompts/ directory."""
    path = Path(__file__).parent / f"{name}.md"
    return path.read_text(encoding="utf-8")
```

### `packages/agents/lead_agent/prompts/system.md`

```markdown
# Oh My Class — Lead Agent

You are the Lead Agent for Oh My Class, an AI-powered educational content creation system.
Your role is to orchestrate the creation of high-quality lesson materials for teachers.

## Standard Workflow

Follow this sequence for every lesson creation request:

1. **Design Blueprint** → call `run_planner` with the teacher's request
2. **Research Content** → call `run_researcher` with the lesson plan
3. **Generate Artifacts** → call `run_content_creator` with plan + research results
4. **Review Quality** → call `run_reviewer` with the generated artifacts

## Recovery Guidance

When the reviewer returns a low score (< 7.0), you will be called again with:
- The reviewer's specific feedback in your context
- The current `revision_count`

In this case, call `run_content_creator` again but include targeted improvement guidance
in your call. Be specific: address the exact weaknesses the reviewer identified.

Do NOT start over from the planner unless the lesson plan itself was the problem.
Do NOT call `run_researcher` again unless the research was explicitly flagged as insufficient.

## Constraints

- Always complete the full sequence before stopping
- Maximum 3 revision cycles (enforced by the graph — you will not be called after that)
- Keep artifact content appropriate for the specified grade level
- Return results in structured format matching the tool output schemas
```

### `packages/agents/lead_agent/recovery.py`

```python
from __future__ import annotations


def build_recovery_context(review_results: dict, revision_count: int) -> str:
    """Build semantic recovery guidance for the Lead Agent after a low review score.

    This is the D3 hybrid: graph handles structural retry limits,
    Lead Agent handles semantic improvement guidance.
    """
    feedback = review_results.get("feedback", "")
    overall_score = review_results.get("overall_score", 0)
    per_artifact = review_results.get("per_artifact", {})

    weak_artifacts = [
        artifact_type
        for artifact_type, scores in per_artifact.items()
        if scores.get("overall", 10) < 7.0
    ]

    lines = [
        f"## Recovery Context (Revision {revision_count})",
        f"Overall score: {overall_score:.1f}/10 — below threshold.",
        "",
        "### Reviewer Feedback",
        feedback,
    ]

    if weak_artifacts:
        lines.append("")
        lines.append(f"### Weak artifacts: {', '.join(weak_artifacts)}")
        for artifact_type in weak_artifacts:
            scores = per_artifact[artifact_type]
            lines.append(f"- **{artifact_type}**: {scores}")

    lines.extend([
        "",
        "### Your Task",
        "Regenerate ONLY the weak artifacts with targeted improvements.",
        "Address the specific feedback above. Do not regenerate passing artifacts.",
    ])

    return "\n".join(lines)
```

### `packages/agents/lead_agent/node.py` — graph node adapter

```python
from __future__ import annotations
from packages.agents.state import OhMyClassState
from packages.agents.lead_agent.agent import make_lead_agent
from packages.agents.lead_agent.recovery import build_recovery_context

_lead_agent = None


def lead_agent_node(state: OhMyClassState) -> dict:
    """Graph node adapter — bridges OhMyClassState ↔ LeadAgentState.

    Extracts relevant context from graph state, invokes Lead Agent,
    injects structured result back into graph state.
    """
    global _lead_agent
    if _lead_agent is None:
        _lead_agent = make_lead_agent()

    # Build task message
    task = f"Create lesson materials for: {state['raw_request']}"
    context = {
        "class_info": state["class_info"],
        "lesson_plan": state.get("lesson_plan"),
        "research_results": state.get("research_results"),
        "artifacts": state.get("artifacts"),
        "revision_count": state.get("revision_count", 0),
    }

    # D3: inject semantic recovery guidance on retry
    messages = [{"role": "user", "content": task}]
    if state.get("review_results") and state.get("revision_count", 0) > 0:
        recovery_ctx = build_recovery_context(
            state["review_results"],
            state["revision_count"],
        )
        messages.insert(0, {"role": "system", "content": recovery_ctx})

    result = _lead_agent.invoke({
        "messages": messages,
        "task": task,
        "context": context,
    })

    # Extract structured outputs from agent result
    # Tool calls write to state via tools.py — extract final values
    updates = {}
    if result.get("lesson_plan"):
        updates["lesson_plan"] = result["lesson_plan"]
    if result.get("research_results"):
        updates["research_results"] = result["research_results"]
    if result.get("artifacts"):
        updates["artifacts"] = result["artifacts"]
    if result.get("review_results"):
        updates["review_results"] = result["review_results"]

    return updates
```

## Tests

```python
# packages/agents/lead_agent/tests/test_lead_agent.py

import pytest
from unittest.mock import patch, MagicMock
from packages.agents.lead_agent.agent import make_lead_agent
from packages.agents.lead_agent.recovery import build_recovery_context


def test_make_lead_agent_returns_compiled_graph():
    with patch("packages.agents.lead_agent.agent.ChatOpenAI"):
        agent = make_lead_agent()
    assert agent is not None
    assert hasattr(agent, "invoke")


def test_build_recovery_context_includes_feedback():
    review = {
        "overall_score": 5.5,
        "feedback": "Content is too abstract for Grade 3.",
        "per_artifact": {"lesson": {"overall": 5.0}},
    }
    ctx = build_recovery_context(review, revision_count=1)
    assert "5.5" in ctx
    assert "Content is too abstract" in ctx
    assert "lesson" in ctx


def test_build_recovery_context_identifies_weak_artifacts():
    review = {
        "overall_score": 6.0,
        "feedback": "Worksheet is too hard.",
        "per_artifact": {
            "lesson": {"overall": 8.0},
            "worksheet": {"overall": 4.0},
        },
    }
    ctx = build_recovery_context(review, revision_count=2)
    assert "worksheet" in ctx
    assert "lesson" not in ctx.split("Weak artifacts")[1].split("\n")[0]


def test_system_prompt_loads():
    from packages.agents.lead_agent.prompts import load_system_prompt
    prompt = load_system_prompt()
    assert "Lead Agent" in prompt
    assert "run_planner" in prompt
```

## Acceptance Criteria

- [ ] `make_lead_agent()` returns a `CompiledGraph` using `create_react_agent`
- [ ] System prompt loaded from `prompts/system.md` (not hardcoded string)
- [ ] `lead_agent_node()` is a graph node adapter that bridges `OhMyClassState` ↔ `LeadAgentState`
- [ ] `recovery.py` builds semantic recovery context for D3 hybrid retry
- [ ] On retry (revision_count > 0), recovery context injected into agent messages
- [ ] Tests: `make_lead_agent()` callable, `build_recovery_context()` correct, prompt loads

## Dependencies

- Blocked by: `agent-state-schema`, `sub-agent-compiled-graphs`
- Blocks: `hitl-gate-wrapper` (needs lead_agent_node to exist)
