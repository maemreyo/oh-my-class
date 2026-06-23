---
title: "Researcher Agent"
status: done
labels: []
created: 2026-06-23
github: 6
---

## What to build

Implement the Researcher Agent node in `packages/agents/sub_agents/researcher/agent.py`. The file exists with a stub (lines 18-41). Replace with working implementation.

## Current State

```python
# packages/agents/sub_agents/researcher/agent.py (lines 18-41)
async def research_sources(state: OhMyClassState) -> dict[str, Any]:
    # TODO: Implement with LangGraph agent
    raise NotImplementedError("research_sources() stub")

# packages/agents/sub_agents/researcher/prompts.py — NOT YET CREATED (needs prompts)
# packages/agents/sub_agents/researcher/tools.py — NOT YET CREATED (needs tools)
# common/contracts/research_bundle.py — CREATED in Issue #5
```

## Implementation Spec

### 1. Create `packages/agents/sub_agents/researcher/prompts.py` (new file)

```python
"""Researcher Agent prompts — system prompt for research gathering."""

from __future__ import annotations

RESEARCHER_SYSTEM_PROMPT: str = """\
You are the Researcher Agent for oh-my-class.

## Role
Gather, cross-reference, and synthesize sources for lesson content.
Follow the FACT protocol: Find → Assess → Cross-reference → Tag.

## FACT Protocol
1. **Find**: Locate 2-10 relevant sources (depending on research_policy)
2. **Assess**: Evaluate each source's credibility (0.0-1.0 score)
3. **Cross-reference**: Verify claims against ≥2 independent sources
4. **Tag**: Mark each claim as VERIFIED, MODIFIED, REMOVED, or UNCERTAIN

## Research Policies
- basic: 2-3 sources, factual accuracy only
- standard: 5+ sources, citations required
- rigorous: 10+ sources, peer-reviewed preferred

## Output Format
Return a JSON object matching the ResearchBundle schema:
```json
{
  "topic": "string",
  "sources": [
    {
      "title": "string",
      "url": "string or null",
      "credibility_score": "float 0.0-1.0",
      "verification_status": "VERIFIED|MODIFIED|REMOVED|UNCERTAIN"
    }
  ],
  "key_findings": ["string"],
  "cross_references": [{}],
  "research_policy": "basic|standard|rigorous"
}
```

## Constraints
- Minimum 2 sources for any policy
- Each source must have credibility_score and verification_status
- Cross-references required for standard and rigorous policies
"""
```

### 2. Create `packages/agents/sub_agents/researcher/tools.py` (new file)

```python
"""Researcher Agent tools — web search and fetch wrappers."""

from __future__ import annotations

import asyncio
from typing import Any


async def web_search(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    """Search the web for information.
    
    Args:
        query: Search query string.
        num_results: Number of results to return.
    
    Returns:
        List of search results with title, url, snippet.
    """
    # TODO: Implement with real web search API
    # For now, return mock results
    return [
        {"title": f"Result {i+1}", "url": f"https://example.com/{i}", "snippet": f"Snippet {i+1}"}
        for i in range(num_results)
    ]


async def web_fetch(url: str) -> str:
    """Fetch content from a URL.
    
    Args:
        url: URL to fetch.
    
    Returns:
        Page content as text.
    """
    # TODO: Implement with real HTTP client
    # For now, return mock content
    return f"Content from {url}"
```

### 3. Replace `research_sources()` stub (lines 18-41)

```python
"""Researcher Agent — node implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.research_bundle import ResearchBundle

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def research_sources(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Researcher Agent.
    
    Takes the approved lesson plan and gathers research sources.
    Verifies factual claims against ≥2 independent sources.
    
    Args:
        state: Current pipeline state with lesson_plan and research_policy.
    
    Returns:
        Partial state update containing 'research_bundle' dict.
    """
    import litellm
    
    # 1. Extract lesson_plan and research_policy from state
    lesson_plan = state.get("lesson_plan", {})
    research_policy = state.get("research_policy", "standard")
    topic = lesson_plan.get("topic", "General topic")
    
    # 2. Format research prompt
    from packages.agents.sub_agents.researcher.prompts import RESEARCHER_SYSTEM_PROMPT
    
    user_prompt = f"""
    Research topic: {topic}
    
    Research policy: {research_policy}
    
    Learning objectives:
    {json.dumps(lesson_plan.get('learning_objectives', []), indent=2)}
    
    Please gather and verify sources following the FACT protocol.
    """
    
    messages = [
        {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    # 3. Call LLM via LiteLLM with metadata tags (INVARIANT-07)
    try:
        response = await litellm.acompletion(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.7,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:researcher",
                        f"step:{state.get('current_step', 7)}",
                        f"run:{state['run_id']}",
                        "pipeline:oh-my-class",
                    ]
                }
            },
        )
        
        # 4. Parse JSON response
        content = response.choices[0].message.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()
        
        bundle_data = json.loads(json_str)
        
        # 5. Validate against ResearchBundle schema
        bundle = ResearchBundle.model_validate(bundle_data)
        
        # 6. Return partial state update
        return {"research_bundle": bundle.model_dump()}
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Researcher agent failed: {e}") from e
```

## Acceptance criteria

- [ ] `research_sources()` calls LiteLLM with model `deepseek-v4-flash`
- [ ] `research_sources()` includes metadata tags with agent, step, run_id, pipeline
- [ ] `research_sources()` returns `{"research_bundle": bundle.model_dump()}`
- [ ] `research_sources()` handles JSON parse errors gracefully
- [ ] `research_sources()` handles LLM API errors gracefully
- [ ] `RESEARCHER_SYSTEM_PROMPT` includes FACT protocol instructions
- [ ] `web_search()` returns list of search results
- [ ] `web_fetch()` returns page content as text
- [ ] Unit test: Researcher returns valid ResearchBundle
- [ ] Unit test: Researcher handles LLM errors

## Test suite

Create `packages/agents/sub_agents/researcher/tests/test_researcher.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from common.contracts.research_bundle import ResearchBundle


class TestResearcherAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_research_bundle(self):
        from packages.agents.sub_agents.researcher.agent import research_sources
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        ```json
        {
            "topic": "Photosynthesis",
            "sources": [
                {"title": "Source 1", "credibility_score": 0.9, "verification_status": "VERIFIED"},
                {"title": "Source 2", "credibility_score": 0.8, "verification_status": "VERIFIED"}
            ],
            "key_findings": ["Finding 1"],
            "research_policy": "standard"
        }
        ```
        '''
        
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            state = {
                "lesson_plan": {"topic": "Photosynthesis", "learning_objectives": []},
                "research_policy": "standard",
                "run_id": "test-run",
                "current_step": 7,
            }
            result = await research_sources(state)
            
            assert "research_bundle" in result
            bundle = ResearchBundle.model_validate(result["research_bundle"])
            assert bundle.topic == "Photosynthesis"
            assert len(bundle.sources) == 2
```

## File paths

| File | Action |
|------|--------|
| `packages/agents/sub_agents/researcher/agent.py` | MODIFY: Replace stub (lines 18-41) |
| `packages/agents/sub_agents/researcher/prompts.py` | CREATE: System prompt |
| `packages/agents/sub_agents/researcher/tools.py` | CREATE: Web search/fetch tools |
| `packages/agents/sub_agents/researcher/tests/test_researcher.py` | CREATE: Full test suite |

## Dependencies

- `common/contracts/research_bundle.py` — ResearchBundle schema (created in Issue #5)
- `litellm` — LLM client (already installed)
- `packages/agents/state.py` — OhMyClassState (already exists)

## Edge cases to handle

1. Missing lesson_plan in state → use default topic
2. LLM returns invalid JSON → ValueError with details
3. LLM returns valid JSON but wrong schema → Pydantic ValidationError
4. LLM API timeout → caught by try/except, re-raise as ValueError
5. Empty sources list → ResearchBundle validation will reject (min_length=2)
