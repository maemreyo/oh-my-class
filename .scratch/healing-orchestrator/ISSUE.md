---
title: "Healing Orchestrator: H3 Pattern — Dedicated Node, 5-Layer Strategies"
status: ready
labels: [architecture, agents, self-healing]
created: 2026-06-24
priority: p0
report: "02"
---

## What to build

Implement a dedicated `healing_node` that receives fail signals from any gate node and selects + applies the appropriate healing strategy. The 5 strategies live in separate files under `healing/strategies/`.

**Design decision (grilling Q2-H3):** Central orchestrator, not distributed retry logic. One place to understand and change healing behavior. Strategies are independently testable pure functions.

## Healing Flow

```
Any gate fail
    │ state: fail_layer, fail_count, fail_type, fail_context
    ▼
healing_node (HealingOrchestrator.heal)
    │
    ├─ fail_count=1 + fail_type="transient"    → retry    (backoff, same inputs)
    ├─ fail_count=1 + fail_type="validation"   → rewrite  (same model f.light, inject errors)
    ├─ fail_count=2 + fail_type="model_error"  → reroute  (swap f.light → f.pro)
    ├─ fail_count=3                            → replan   (clear artifacts, back to step_08)
    └─ fail_count>3 OR budget_exhausted        → escalate (set escalate=True, notify)
    │
    ▼
conditional edge → step_08_generate / escalate_node
```

## File Structure

```
packages/agents/healing/
├── orchestrator.py             # HealingOrchestrator class + healing_node fn
├── strategies/
│   ├── __init__.py
│   ├── retry.py                # Layer 0: exponential backoff + jitter
│   ├── rewrite.py              # Layer 1: inject error context, re-prompt
│   ├── reroute.py              # Layer 2: swap model light↔pro
│   ├── replan.py               # Layer 3: clear artifacts, reset to step_08
│   └── escalate.py             # Layer 4: set escalate flag, trigger notification
├── html_healer.py              # HTML-specific healing (DOCTYPE, unclosed tags)
└── circuit_breaker.py          # CircuitBreaker(threshold, recovery_timeout)
```

## Implementation Spec

### `healing/orchestrator.py`

```python
from __future__ import annotations
from packages.agents.state import OhMyClassState
from packages.agents.healing.strategies import retry, rewrite, reroute, replan, escalate
from packages.agents.config.gate_config import GateConfig


class HealingOrchestrator:
    """Selects and applies the right healing strategy based on fail signal.

    Strategy selection table:
        fail_count=1, transient   → retry
        fail_count=1, validation  → rewrite
        fail_count=2, model_error → reroute
        fail_count=3              → replan
        fail_count>3              → escalate
    """

    def __init__(self, config: GateConfig | None = None):
        self.config = config or GateConfig()

    def heal(self, state: OhMyClassState) -> dict:
        fail_count = state.get("fail_count", 0) + 1
        fail_type = state.get("fail_type", "validation")
        fail_layer = state.get("fail_layer", "unknown")

        if fail_count > self.config.max_retries:
            return escalate.apply(state, fail_count)

        if fail_count == 1 and fail_type == "transient":
            return retry.apply(state, fail_count)

        if fail_count == 1 and fail_type in ("validation", "score"):
            return rewrite.apply(state, fail_count)

        if fail_count == 2:
            return reroute.apply(state, fail_count)

        if fail_count == 3:
            return replan.apply(state, fail_count)

        return escalate.apply(state, fail_count)


def healing_node(state: OhMyClassState) -> dict:
    """Graph node — delegates to HealingOrchestrator."""
    return HealingOrchestrator().heal(state)


def route_after_healing(state: OhMyClassState) -> str:
    """Route: escalate if flagged, otherwise back to generate."""
    if state.get("escalate"):
        return "escalate_node"
    return "step_08_generate"
```

### `healing/strategies/retry.py`

```python
import time
import random


def apply(state: dict, fail_count: int) -> dict:
    """Exponential backoff with ±25% jitter. Same inputs, retry immediately."""
    base_delay = 0.5
    max_delay = 10.0
    delay = min(base_delay * (2 ** (fail_count - 1)), max_delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    time.sleep(delay + jitter)

    return {
        "fail_count": fail_count,
        "healing_strategy": "retry",
        "healing_note": f"Retrying after {delay:.1f}s backoff (attempt {fail_count})",
    }
```

### `healing/strategies/rewrite.py`

```python
def apply(state: dict, fail_count: int) -> dict:
    """Inject error context into generation prompt, same model."""
    fail_context = state.get("fail_context", {})
    errors = fail_context.get("errors", [])
    error_summary = "; ".join(str(e) for e in errors[:3])  # top 3 errors

    # Inject into generation context so Content Creator sees what went wrong
    healing_context = state.get("healing_context", {})
    healing_context["rewrite_instruction"] = (
        f"Previous attempt failed validation. Fix these issues:\n{error_summary}"
    )

    return {
        "fail_count": fail_count,
        "healing_strategy": "rewrite",
        "healing_context": healing_context,
        "artifacts": None,  # clear artifacts to force regeneration
    }
```

### `healing/strategies/reroute.py`

```python
from packages.agents.config.models import MODELS


def apply(state: dict, fail_count: int) -> dict:
    """Swap model: if was using f.light → upgrade to f.pro."""
    current_model = state.get("generation_model", MODELS["content_generation"])
    fallback = "f.pro" if current_model == "f.light" else "f.light"

    return {
        "fail_count": fail_count,
        "healing_strategy": "reroute",
        "generation_model": fallback,  # Content Creator reads this
        "healing_note": f"Switching model: {current_model} → {fallback}",
        "artifacts": None,
    }
```

### `healing/strategies/replan.py`

```python
def apply(state: dict, fail_count: int) -> dict:
    """Full regeneration: clear all downstream state, back to step_08."""
    return {
        "fail_count": fail_count,
        "healing_strategy": "replan",
        "artifacts": None,
        "review_results": None,
        "judge_score": None,
        "content_review_passed": None,
        "schema_valid": None,
        "healing_note": "Full regeneration triggered after 3 failed attempts",
        # lesson_plan preserved — only re-generate content, not blueprint
    }
```

### `healing/strategies/escalate.py`

```python
def apply(state: dict, fail_count: int) -> dict:
    """Mark for human escalation. Notifications handled by NotificationSystem."""
    return {
        "fail_count": fail_count,
        "healing_strategy": "escalate",
        "escalate": True,
        "escalate_reason": (
            f"Auto-escalated after {fail_count} failed healing attempts. "
            f"Last fail layer: {state.get('fail_layer')}. "
            f"Last error: {state.get('fail_context', {}).get('errors', ['unknown'])}"
        ),
        "error": f"Escalated: {state.get('fail_layer')} gate failed {fail_count} times",
    }
```

### `healing/circuit_breaker.py`

```python
import time


class CircuitBreaker:
    """Prevents cascading failures by stopping calls after threshold failures."""

    def __init__(self, threshold: int = 3, recovery_timeout: float = 60.0):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "closed"   # closed | open | half-open
        self.last_failure_time = 0.0

    def call(self, fn, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError(
                    f"Circuit open — wait {self.recovery_timeout}s before retry"
                )
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def _on_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "open"


class CircuitOpenError(Exception):
    pass
```

## Tests

```python
# packages/agents/healing/tests/test_orchestrator.py

def test_rewrite_on_first_validation_fail():
    state = {"fail_count": 0, "fail_type": "validation",
             "fail_context": {"errors": ["missing sections"]}}
    result = HealingOrchestrator().heal(state)
    assert result["healing_strategy"] == "rewrite"
    assert result["artifacts"] is None

def test_reroute_on_second_fail():
    state = {"fail_count": 1, "fail_type": "validation",
             "generation_model": "f.light"}
    result = HealingOrchestrator().heal(state)
    assert result["healing_strategy"] == "reroute"
    assert result["generation_model"] == "f.pro"

def test_escalate_after_max_retries():
    state = {"fail_count": 4, "fail_type": "validation", "fail_layer": "schema"}
    result = HealingOrchestrator().heal(state)
    assert result["healing_strategy"] == "escalate"
    assert result["escalate"] is True

def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(threshold=3)
    for _ in range(3):
        with pytest.raises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
    assert cb.state == "open"
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: None)
```

## Acceptance Criteria

- [ ] `healing_node()` graph node registered in `graph.py`
- [ ] `route_after_healing()` routes to `escalate_node` or `step_08_generate`
- [ ] Each strategy in its own file, pure function `apply(state, fail_count) -> dict`
- [ ] `HealingOrchestrator` strategy selection table matches the fail_count/fail_type matrix
- [ ] `CircuitBreaker` used by `schema_validator.py` (Layer 1)
- [ ] `html_healer.py` has `validate_and_heal(html, max_attempts=3) -> dict`
- [ ] Tests for each strategy + orchestrator routing logic

## Dependencies

- Blocked by: `quality-gate-nodes` (needs fail signal schema), `gate-config` (needs GateConfig)
- Blocks: nothing (healing is a leaf node — routes back to existing nodes)
- Priority: p0
