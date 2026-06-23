---
title: "Content Creator Agent"
status: done
labels: []
created: 2026-06-23
github: 7
---

## What to build

Implement the Content Creator Agent node in `packages/agents/sub_agents/content_creator/agent.py`. The file exists with a stub (lines 24-52). Replace with working implementation.

## Current State

```python
# packages/agents/sub_agents/content_creator/agent.py (lines 24-52)
async def generate_artifacts(state: OhMyClassState) -> dict[str, Any]:
    # TODO: Implement with LangGraph agent
    raise NotImplementedError("generate_artifacts() stub")

# packages/agents/sub_agents/content_creator/prompts.py — NOT YET CREATED
# packages/agents/sub_agents/content_creator/tools.py — NOT YET CREATED
# common/contracts/artifact.py — COMPLETE (ArtifactContent schema exists)
```

## Implementation Spec

### 1. Create `packages/agents/sub_agents/content_creator/prompts.py` (new file)

```python
"""Content Creator Agent prompts — system prompt for artifact generation."""

from __future__ import annotations

CONTENT_CREATOR_SYSTEM_PROMPT: str = """\
You are the Content Creator Agent for oh-my-class.

## Role
Generate structured JSON content for each artifact type.
Output is rendered via Eta templates — never raw HTML directly.

## Artifact Types
- lesson: Full lesson plan with sections
- worksheet: Practice exercises
- quiz: Assessment questions
- drill: Repetition exercises
- recap: Summary/review
- infographic: Visual summary

## Output Format
Return a JSON object matching the ArtifactContent schema:
```json
{
  "artifact_type": "lesson|worksheet|quiz|drill|recap|infographic",
  "theme": "default|ocean|forest",
  "title": "string (3-200 chars)",
  "sections": [
    {
      "title": "string",
      "content": "string or structured data",
      "teacher_only": false
    }
  ],
  "metadata": {},
  "accessibility": {
    "language": "en",
    "reading_level": "grade_5",
    "alt_texts": {}
  }
}
```

## Hard Constraints
- Return JSON only — never raw HTML
- No CDN references in data
- No student PII (name, email, score) in output
- Answer keys MUST be in separate teacher_only sections
"""
```

### 2. Create `packages/agents/sub_agents/content_creator/tools.py` (new file)

```python
"""Content Creator Agent tools — file read/write wrappers."""

from __future__ import annotations

import os
from typing import Any


async def read_file(path: str) -> str:
    """Read content from a file.
    
    Args:
        path: File path to read.
    
    Returns:
        File content as text.
    """
    # TODO: Implement with real file I/O
    # For now, return mock content
    return f"Content from {path}"


async def write_file(path: str, content: str) -> bool:
    """Write content to a file.
    
    Args:
        path: File path to write.
        content: Content to write.
    
    Returns:
        True if successful.
    """
    # TODO: Implement with real file I/O
    # For now, return success
    return True
```

### 3. Replace `generate_artifacts()` stub (lines 24-52)

```python
"""Content Creator Agent — node implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from common.contracts.artifact import ArtifactContent

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def generate_artifacts(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Content Creator Agent.
    
    Takes the lesson plan, research bundle, and pack scope,
    and generates ArtifactContent JSON for each requested artifact type.
    
    Args:
        state: Current pipeline state with lesson_plan, research_bundle,
            artifact_types, and theme.
    
    Returns:
        Partial state update containing 'artifacts' list.
    """
    import litellm
    
    # 1. Extract data from state
    lesson_plan = state.get("lesson_plan", {})
    research_bundle = state.get("research_bundle", {})
    artifact_types = state.get("artifact_types", ["lesson"])
    theme = state.get("theme", "default")
    
    # 2. Format content creator prompt
    from packages.agents.sub_agents.content_creator.prompts import CONTENT_CREATOR_SYSTEM_PROMPT
    
    user_prompt = f"""
    Generate artifacts for the following lesson:
    
    Lesson Plan:
    {json.dumps(lesson_plan, indent=2)}
    
    Research Bundle:
    {json.dumps(research_bundle, indent=2)}
    
    Artifact types to generate: {artifact_types}
    Theme: {theme}
    
    Please generate one ArtifactContent JSON for each artifact type.
    Return a JSON array of artifacts.
    """
    
    messages = [
        {"role": "system", "content": CONTENT_CREATOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    # 3. Call LLM via LiteLLM with metadata tags (INVARIANT-07)
    try:
        response = await litellm.acompletion(
            model="deepseek-free",
            messages=messages,
            temperature=0.7,
            extra_body={
                "metadata": {
                    "tags": [
                        "agent:content_creator",
                        f"step:{state.get('current_step', 8)}",
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
        
        artifacts_data = json.loads(json_str)
        
        # Handle both single artifact and array
        if isinstance(artifacts_data, dict):
            artifacts_data = [artifacts_data]
        
        # 5. Validate each artifact against ArtifactContent schema
        artifacts = []
        for artifact_data in artifacts_data:
            artifact = ArtifactContent.model_validate(artifact_data)
            artifacts.append(artifact.model_dump())
        
        # 6. Return partial state update
        return {"artifacts": artifacts}
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e
    except Exception as e:
        raise ValueError(f"Content creator agent failed: {e}") from e
```

### 4. Add validation helpers (after generate_artifacts)

```python
def validate_no_cdn(artifacts: list[dict[str, Any]]) -> list[str]:
    """Check for CDN references in artifacts."""
    issues = []
    cdn_patterns = ["cdn.", "cloudflare.com", "jsdelivr.net", "unpkg.com"]
    
    for i, artifact in enumerate(artifacts):
        content = json.dumps(artifact)
        for pattern in cdn_patterns:
            if pattern in content:
                issues.append(f"CDN reference found in artifact {i}: {pattern}")
    
    return issues


def validate_no_pii(artifacts: list[dict[str, Any]]) -> list[str]:
    """Check for PII in artifacts."""
    import re
    issues = []
    
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    
    for i, artifact in enumerate(artifacts):
        content = json.dumps(artifact)
        if email_pattern.search(content):
            issues.append(f"Email found in artifact {i}")
        if phone_pattern.search(content):
            issues.append(f"Phone number found in artifact {i}")
    
    return issues
```

## Acceptance criteria

- [ ] `generate_artifacts()` calls LiteLLM with model `deepseek-free`
- [ ] `generate_artifacts()` includes metadata tags with agent, step, run_id, pipeline
- [ ] `generate_artifacts()` returns `{"artifacts": [artifact.model_dump() for ...]}`
- [ ] `generate_artifacts()` handles single artifact or array response
- [ ] `generate_artifacts()` validates each artifact against ArtifactContent schema
- [ ] `validate_no_cdn()` detects CDN references in artifacts
- [ ] `validate_no_pii()` detects email and phone in artifacts
- [ ] Unit test: Content creator returns valid ArtifactContent
- [ ] Unit test: Content creator handles LLM errors
- [ ] Unit test: validate_no_cdn detects CDN
- [ ] Unit test: validate_no_pii detects PII

## Test suite

Create `packages/agents/sub_agents/content_creator/tests/test_content_creator.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from common.contracts.artifact import ArtifactContent
from packages.agents.sub_agents.content_creator.agent import (
    generate_artifacts,
    validate_no_cdn,
    validate_no_pii,
)


class TestContentCreatorAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_artifact_content(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        ```json
        {
            "artifact_type": "lesson",
            "theme": "default",
            "title": "Photosynthesis Lesson",
            "sections": [{"title": "Intro", "content": "Content here"}],
            "metadata": {},
            "accessibility": {"language": "en"}
        }
        ```
        '''
        
        with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
            state = {
                "lesson_plan": {"topic": "Photosynthesis"},
                "research_bundle": {"sources": []},
                "artifact_types": ["lesson"],
                "theme": "default",
                "run_id": "test-run",
                "current_step": 8,
            }
            result = await generate_artifacts(state)
            
            assert "artifacts" in result
            assert len(result["artifacts"]) == 1
            artifact = ArtifactContent.model_validate(result["artifacts"][0])
            assert artifact.artifact_type == "lesson"


class TestValidationHelpers:
    def test_validate_no_cdn_catches_cdn(self):
        artifacts = [{"content": "Visit cdn.example.com"}]
        issues = validate_no_cdn(artifacts)
        assert len(issues) == 1
        assert "CDN" in issues[0]
    
    def test_validate_no_cdn_clean(self):
        artifacts = [{"content": "No CDN here"}]
        issues = validate_no_cdn(artifacts)
        assert len(issues) == 0
    
    def test_validate_no_pii_catches_email(self):
        artifacts = [{"content": "Contact john@example.com"}]
        issues = validate_no_pii(artifacts)
        assert len(issues) == 1
        assert "Email" in issues[0]
    
    def test_validate_no_pii_clean(self):
        artifacts = [{"content": "No PII here"}]
        issues = validate_no_pii(artifacts)
        assert len(issues) == 0
```

## File paths

| File | Action |
|------|--------|
| `packages/agents/sub_agents/content_creator/agent.py` | MODIFY: Replace stub (lines 24-52) |
| `packages/agents/sub_agents/content_creator/prompts.py` | CREATE: System prompt |
| `packages/agents/sub_agents/content_creator/tools.py` | CREATE: File read/write tools |
| `packages/agents/sub_agents/content_creator/tests/test_content_creator.py` | CREATE: Full test suite |

## Dependencies

- `common/contracts/artifact.py` — ArtifactContent schema (already exists)
- `litellm` — LLM client (already installed)
- `packages/agents/state.py` — OhMyClassState (already exists)

## Edge cases to handle

1. Missing lesson_plan or research_bundle → use empty dict
2. LLM returns invalid JSON → ValueError with details
3. LLM returns single artifact instead of array → wrap in list
4. LLM returns valid JSON but wrong schema → Pydantic ValidationError
5. Empty artifact_types → no artifacts generated (return empty list)
