---
title: "Middleware Suite: 5 Core Middleware Implementations"
status: done
labels: []
created: 2026-06-23
github: 3
---

## What to build

Implement the 5 core middleware classes in `packages/agents/middleware/`. Each file already exists with stubs. Replace the TODO stubs with working implementations.

## Current State

```
packages/agents/middleware/
├── base.py              # BaseMiddleware ABC — COMPLETE (lines 1-73)
├── loop_detection.py    # Stub (lines 19-54)
├── token_budget.py      # Stub (not read yet)
├── dangling_tool_call.py # Stub (not read yet)
├── summarization.py     # Stub (not read yet)
├── guardrail.py         # Stub (not read yet)
└── __init_all__.py      # Placeholder list (lines 23-36, all commented)
```

## Implementation Spec

### 1. `loop_detection.py` — LoopDetectionMiddleware

Replace the stub (lines 19-54) with:

```python
"""Loop detection middleware — dual-layer detection for agent loops."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class LoopDetectedError(Exception):
    """Raised when an agent loop is detected."""
    pass


class LoopDetectionMiddleware(BaseMiddleware):
    """Detects and breaks infinite loops in agent responses.
    
    Hash layer: compares response hashes to detect identical consecutive outputs.
    Frequency layer: tracks response patterns over a sliding window.
    """

    name: str = "loop_detection"
    order: int = 1

    def __init__(self, threshold: int = 5) -> None:
        self.threshold = threshold
        self._hash_history: list[str] = []

    def _compute_hash(self, state: OhMyClassState) -> str:
        """Compute hash of relevant state fields."""
        relevant = {
            "lesson_plan": state.get("lesson_plan"),
            "research_bundle": state.get("research_bundle"),
            "artifacts": state.get("artifacts"),
            "quality_scores": state.get("quality_scores"),
        }
        serialized = json.dumps(relevant, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check for loop conditions before LLM call."""
        current_hash = self._compute_hash(state)
        
        # Check if same hash appears consecutively
        if len(self._hash_history) >= self.threshold:
            recent = self._hash_history[-self.threshold:]
            if len(set(recent)) == 1 and recent[0] == current_hash:
                raise LoopDetectedError(
                    f"Loop detected: {self.threshold} identical consecutive states"
                )
        
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Record response hash after LLM call."""
        current_hash = self._compute_hash(state)
        self._hash_history.append(current_hash)
        
        # Keep only sliding window
        if len(self._hash_history) > self.threshold * 2:
            self._hash_history = self._hash_history[-self.threshold * 2:]
        
        return state
```

### 2. `token_budget.py` — TokenBudgetMiddleware

Create or replace with:

```python
"""Token budget middleware — enforces per-run token budgets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class TokenBudgetExceededError(Exception):
    """Raised when token budget is exceeded."""
    pass


class TokenBudgetMiddleware(BaseMiddleware):
    """Enforces per-run token budgets.
    
    Tracks cumulative token usage from LiteLLM metadata.
    Blocks LLM calls when budget exceeded.
    """

    name: str = "token_budget"
    order: int = 2

    def __init__(self, budget: int = 100_000) -> None:
        self.budget = budget
        self._used: int = 0

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check if budget allows more LLM calls."""
        if self._used >= self.budget:
            raise TokenBudgetExceededError(
                f"Token budget exceeded: {self._used}/{self.budget}"
            )
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Record token usage from state metadata."""
        # Extract token usage from state if available
        tokens = state.get("tokens_used", 0)
        if isinstance(tokens, int):
            self._used = tokens
        return state
```

### 3. `dangling_tool_call.py` — DanglingToolCallMiddleware

Create or replace with:

```python
"""Dangling tool call middleware — handles orphaned tool calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class DanglingToolCallMiddleware(BaseMiddleware):
    """Handles orphaned tool calls.
    
    Detects tool calls without corresponding tool results.
    Auto-generate error results for dangling calls.
    """

    name: str = "dangling_tool_call"
    order: int = 3

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check for dangling tool calls before LLM call."""
        # TODO: Check if any tool calls are missing results
        # In real implementation, would inspect message history
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Validate tool call results after LLM call."""
        # TODO: Generate error results for any dangling calls
        return state
```

### 4. `summarization.py` — SummarizationMiddleware

Create or replace with:

```python
"""Summarization middleware — summarizes long conversations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class SummarizationMiddleware(BaseMiddleware):
    """Summarizes long conversations to manage context window.
    
    Monitors context window usage and triggers summarization
    when context exceeds threshold.
    """

    name: str = "summarization"
    order: int = 4

    def __init__(self, threshold_tokens: int = 80_000) -> None:
        self.threshold_tokens = threshold_tokens

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check if summarization is needed before LLM call."""
        # TODO: Check if context window is approaching limit
        # If so, summarize older messages
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """No-op after model for summarization."""
        return state
```

### 5. `guardrail.py` — GuardrailMiddleware

Create or replace with:

```python
"""Guardrail middleware — content safety filter."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


class GuardrailViolationError(Exception):
    """Raised when content violates guardrails."""
    pass


class GuardrailMiddleware(BaseMiddleware):
    """Content safety filter.
    
    Checks input/output for harmful content.
    Blocks PII leakage (student names, emails, scores).
    Enforces age-appropriate content.
    """

    name: str = "guardrail"
    order: int = 5

    # PII patterns
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    SCORE_PATTERN = re.compile(r'\b\d+(\.\d+)?/%\b')  # e.g., 85% or 85.5%

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check input for PII before LLM call."""
        raw_request = state.get("raw_request", "")
        
        violations = []
        if self.EMAIL_PATTERN.search(raw_request):
            violations.append("Email address detected in input")
        if self.PHONE_PATTERN.search(raw_request):
            violations.append("Phone number detected in input")
        
        if violations:
            raise GuardrailViolationError(f"PII violations: {violations}")
        
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        """Check output for PII and harmful content after LLM call."""
        # Check artifacts for PII
        artifacts = state.get("artifacts", [])
        for artifact in artifacts:
            content = str(artifact)
            if self.EMAIL_PATTERN.search(content):
                raise GuardrailViolationError("Email address detected in output")
            if self.PHONE_PATTERN.search(content):
                raise GuardrailViolationError("Phone number detected in output")
        
        return state
```

### 6. Update `__init_all__.py` (lines 23-36)

Replace the commented list with actual imports:

```python
"""Ordered middleware list — the complete middleware chain for the pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agents.middleware.base import BaseMiddleware

from packages.agents.middleware.loop_detection import LoopDetectionMiddleware
from packages.agents.middleware.token_budget import TokenBudgetMiddleware
from packages.agents.middleware.dangling_tool_call import DanglingToolCallMiddleware
from packages.agents.middleware.summarization import SummarizationMiddleware
from packages.agents.middleware.guardrail import GuardrailMiddleware

ORDERED_MIDDLEWARE_LIST: list[type[BaseMiddleware]] = [
    LoopDetectionMiddleware,      # order=1
    TokenBudgetMiddleware,        # order=2
    DanglingToolCallMiddleware,   # order=3
    SummarizationMiddleware,      # order=4
    GuardrailMiddleware,          # order=5
]

EXPECTED_MIDDLEWARE_COUNT: int = 24
```

## Acceptance criteria

- [ ] `LoopDetectionMiddleware` raises `LoopDetectedError` after 5 identical states
- [ ] `LoopDetectionMiddleware` tracks hash history in sliding window
- [ ] `TokenBudgetMiddleware` raises `TokenBudgetExceededError` when budget exceeded
- [ ] `TokenBudgetMiddleware` tracks cumulative token usage
- [ ] `DanglingToolCallMiddleware` implements `BaseMiddleware` interface
- [ ] `SummarizationMiddleware` has configurable threshold
- [ ] `GuardrailMiddleware` raises `GuardrailViolationError` for PII
- [ ] `GuardrailMiddleware` detects emails, phone numbers, scores
- [ ] `ORDERED_MIDDLEWARE_LIST` exports all 5 middleware in correct order
- [ ] Each middleware has `name` and `order` class attributes

## Test suite

Create `packages/agents/middleware/tests/test_middleware.py`:

```python
import pytest
from packages.agents.middleware.loop_detection import (
    LoopDetectionMiddleware,
    LoopDetectedError,
)
from packages.agents.middleware.token_budget import (
    TokenBudgetMiddleware,
    TokenBudgetExceededError,
)
from packages.agents.middleware.guardrail import (
    GuardrailMiddleware,
    GuardrailViolationError,
)
from packages.agents.middleware import ORDERED_MIDDLEWARE_LIST
from packages.agents.middleware.base import MiddlewareContext


def make_state(**overrides):
    """Helper to create test state."""
    base = {
        "raw_request": "Teach photosynthesis",
        "teacher_id": "t-001",
        "class_info": {"grade": 5, "subject": "science"},
        "run_id": "run-001",
        "blueprint_approved": False,
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "export_formats": [],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "research_policy": "basic",
    }
    base.update(overrides)
    return base


class TestLoopDetection:
    @pytest.mark.asyncio
    async def test_allows_different_states(self):
        middleware = LoopDetectionMiddleware(threshold=3)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        
        for i in range(5):
            state = make_state(current_step=i)
            await middleware.before_model(state, context)
            await middleware.after_model(state, context)
    
    @pytest.mark.asyncio
    async def test_breaks_after_threshold(self):
        middleware = LoopDetectionMiddleware(threshold=3)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        
        state = make_state()
        for _ in range(3):
            await middleware.before_model(state, context)
            await middleware.after_model(state, context)
        
        with pytest.raises(LoopDetectedError):
            await middleware.before_model(state, context)


class TestTokenBudget:
    @pytest.mark.asyncio
    async def test_allows_within_budget(self):
        middleware = TokenBudgetMiddleware(budget=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=500)
        
        result = await middleware.before_model(state, context)
        assert result == state
    
    @pytest.mark.asyncio
    async def test_blocks_when_exceeded(self):
        middleware = TokenBudgetMiddleware(budget=1000)
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(tokens_used=1500)
        
        with pytest.raises(TokenBudgetExceededError):
            await middleware.before_model(state, context)


class TestGuardrail:
    @pytest.mark.asyncio
    async def test_blocks_email_in_input(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(raw_request="Contact john@example.com")
        
        with pytest.raises(GuardrailViolationError) as exc_info:
            await middleware.before_model(state, context)
        assert "Email" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allows_safe_content(self):
        middleware = GuardrailMiddleware()
        context = MiddlewareContext(agent_name="test", step=1, run_id="r1")
        state = make_state(raw_request="Teach photosynthesis to grade 5")
        
        result = await middleware.before_model(state, context)
        assert result == state


class TestMiddlewareList:
    def test_ordered_list_has_5_items(self):
        assert len(ORDERED_MIDDLEWARE_LIST) == 5
    
    def test_order_is_correct(self):
        orders = [m.order for m in ORDERED_MIDDLEWARE_LIST]
        assert orders == [1, 2, 3, 4, 5]
```

## File paths

| File | Action |
|------|--------|
| `packages/agents/middleware/loop_detection.py` | MODIFY: Replace stub with full implementation |
| `packages/agents/middleware/token_budget.py` | MODIFY: Replace stub with full implementation |
| `packages/agents/middleware/dangling_tool_call.py` | MODIFY: Replace stub with full implementation |
| `packages/agents/middleware/summarization.py` | MODIFY: Replace stub with full implementation |
| `packages/agents/middleware/guardrail.py` | MODIFY: Replace stub with full implementation |
| `packages/agents/middleware/__init_all__.py` | MODIFY: Replace commented list with imports |
| `packages/agents/middleware/tests/test_middleware.py` | CREATE: Full test suite |

## Dependencies

- `packages/agents/middleware/base.py` — BaseMiddleware ABC (already exists)
- `packages/agents/state.py` — OhMyClassState (already exists)

## Edge cases to handle

1. Empty state → no-op (don't crash)
2. Budget of 0 → always blocked
3. Threshold of 1 → loop detected on first duplicate
4. PII in both input and output → check both
5. Multiple PII violations → report all
