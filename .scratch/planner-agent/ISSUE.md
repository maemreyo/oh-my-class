---
title: "ResearchBundle Model + Planner Agent"
status: ready-for-agent
labels: []
created: 2026-06-23
github: 5
---

## What to build

1. **ResearchBundle Pydantic Model** — Add missing schema to `common/contracts/`
2. **Planner Agent** — Replace stub in `packages/agents/sub_agents/planner/agent.py` with working implementation

## Current State

```python
# packages/agents/sub_agents/planner/agent.py (lines 18-41)
async def design_lesson_plan(state: OhMyClassState) -> dict[str, Any]:
    # TODO: Implement with LangGraph agent
    raise NotImplementedError("design_lesson_plan() stub")

# packages/agents/sub_agents/planner/prompts.py — COMPLETE (lines 1-44)
# common/contracts/lesson_plan.py — COMPLETE (lines 1-72)
# common/contracts/research_bundle.py — MISSING (needs to be created)
```

## Implementation Spec

### 1. Create `common/contracts/research_bundle.py` (new file)

```python
"""Research bundle Pydantic models — output contract for the Researcher Agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    """A single research source with credibility assessment."""
    
    title: str = Field(..., min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    credibility_score: float = Field(..., ge=0.0, le=1.0)
    verification_status: Literal["VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"]


class ResearchBundle(BaseModel):
    """Structured research output from the Researcher Agent.
    
    Follows the FACT protocol (Find → Assess → Cross-reference → Tag).
    Minimum sources depend on research_policy.
    """
    
    topic: str = Field(..., min_length=1, max_length=200)
    sources: list[ResearchSource] = Field(
        ...,
        min_length=2,
        description="Minimum 2 sources for basic, 5+ for standard, 10+ for rigorous",
    )
    key_findings: list[str] = Field(default_factory=list)
    cross_references: list[dict] = Field(default_factory=list)
    research_policy: Literal["basic", "standard", "rigorous"] = "standard"
```

### 2. Update `common/contracts/__init__.py` — Add export

Add to the imports:

```python
from common.contracts.research_bundle import ResearchBundle, ResearchSource
```

### 3. Replace `design_lesson_plan()` stub (lines 18-41)

```python
"""Planner Agent — node implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.lesson_plan import LessonPlan

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def design_lesson_plan(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Planner Agent.
    
    Takes the teacher's raw request and class info, produces a structured
    LessonPlan JSON conforming to common.contracts.lesson_plan.LessonPlan.
    
    Args:
        state: Current pipeline state with raw_request and class_info.
    
    Returns:
        Partial state update containing 'lesson_plan' dict.
    """
    import litellm
    
    # 1. Format prompt from state
    from packages.agents.sub_agents.planner.prompts import PLANNER_SYSTEM_PROMPT
    
    user_prompt = f"""
    Teacher request: {state['raw_request']}
    
    Class information:
    - Grade: {state['class_info'].get('grade', 'Unknown')}
    - Subject: {state['class_info'].get('subject', 'Unknown')}
    - Student count: {state['class_info'].get('student_count', 'Unknown')}
    - Language: {state['class_info'].get('language', 'en')}
    """
    
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    # 2. Call LLM via LiteLLM with metadata tags (INVARIANT-07)
    try:
        response = await litellm.acompletion(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.7,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:planner",
                        f"step:{state.get('current_step', 3)}",
                        f"run:{state['run_id']}",
                        "pipeline:oh-my-class",
                    ]
                }
            },
        )
        
        # 3. Parse JSON response
        content = response.choices[0].message.content
        # Extract JSON from response (may be wrapped in markdown code block)
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()
        
        plan_data = json.loads(json_str)
        
        # 4. Validate against LessonPlan schema
        plan = LessonPlan.model_validate(plan_data)
        
        # 5. Return partial state update
        return {"lesson_plan": plan.model_dump()}
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Planner agent failed: {e}") from e
```

## Acceptance criteria

- [ ] `ResearchBundle` model exists in `common/contracts/research_bundle.py`
- [ ] `ResearchSource` has `title`, `url`, `credibility_score`, `verification_status`
- [ ] `ResearchBundle` has `topic`, `sources`, `key_findings`, `cross_references`, `research_policy`
- [ ] `ResearchBundle.sources` requires min_length=2
- [ ] `design_lesson_plan()` calls LiteLLM with model `deepseek-v4-flash`
- [ ] `design_lesson_plan()` includes metadata tags with agent, step, run_id, pipeline
- [ ] `design_lesson_plan()` returns `{"lesson_plan": plan.model_dump()}`
- [ ] `design_lesson_plan()` handles JSON parse errors gracefully
- [ ] `design_lesson_plan()` handles LLM API errors gracefully
- [ ] Unit test: ResearchBundle validates with 2+ sources
- [ ] Unit test: ResearchBundle rejects < 2 sources
- [ ] Unit test: Planner returns valid LessonPlan

## Test suite

Create `packages/agents/sub_agents/planner/tests/test_planner.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from common.contracts.research_bundle import ResearchBundle, ResearchSource
from common.contracts.lesson_plan import LessonPlan


class TestResearchBundle:
    def test_valid_with_2_sources(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [
                {"title": "Source 1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
                {"title": "Source 2", "credibility_score": 0.8, "verification_status": "VERIFIED"},
            ],
        }
        bundle = ResearchBundle.model_validate(data)
        assert len(bundle.sources) == 2
    
    def test_invalid_with_1_source(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [
                {"title": "Source 1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
            ],
        }
        with pytest.raises(Exception):
            ResearchBundle.model_validate(data)
    
    def test_default_policy(self):
        data = {
            "topic": "Photosynthesis",
            "sources": [
                {"title": "S1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
                {"title": "S2", "credibility_score": 0.8, "verification_status": "VERIFIED"},
            ],
        }
        bundle = ResearchBundle.model_validate(data)
        assert bundle.research_policy == "standard"


class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_lesson_plan(self):
        from packages.agents.sub_agents.planner.agent import design_lesson_plan
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        ```json
        {
            "topic": "Photosynthesis",
            "grade_level": "Grade 5",
            "subject": "science",
            "duration_minutes": 45,
            "learning_objectives": [
                {"description": "Understand photosynthesis", "bloom_level": "understand"},
                {"description": "Apply knowledge", "bloom_level": "apply"}
            ]
        }
        ```
        '''
        
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            state = {
                "raw_request": "Teach photosynthesis",
                "class_info": {"grade": 5, "subject": "science"},
                "run_id": "test-run",
                "current_step": 3,
            }
            result = await design_lesson_plan(state)
            
            assert "lesson_plan" in result
            plan = LessonPlan.model_validate(result["lesson_plan"])
            assert plan.topic == "Photosynthesis"
```

## File paths

| File | Action |
|------|--------|
| `common/contracts/research_bundle.py` | CREATE: New Pydantic model |
| `common/contracts/__init__.py` | MODIFY: Add ResearchBundle export |
| `packages/agents/sub_agents/planner/agent.py` | MODIFY: Replace stub (lines 18-41) |
| `packages/agents/sub_agents/planner/tests/test_planner.py` | CREATE: Full test suite |

## Dependencies

- `common/contracts/lesson_plan.py` — LessonPlan schema (already exists)
- `litellm` — LLM client (already installed)
- `packages/agents/sub_agents/planner/prompts.py` — System prompt (already exists)

## Edge cases to handle

1. LLM returns invalid JSON → ValueError with details
2. LLM returns valid JSON but wrong schema → Pydantic ValidationError
3. LLM API timeout → caught by try/except, re-raise as ValueError
4. Empty raw_request → LLM may produce poor output (not handled here)
5. Missing class_info fields → use defaults ("Unknown")
