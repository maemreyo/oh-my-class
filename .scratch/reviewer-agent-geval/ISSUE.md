---
title: "Reviewer Agent + G-Eval Layer 4"
status: ready-for-agent
labels: []
created: 2026-06-23
github: 8
---

## What to build

Implement the Reviewer Agent node in `packages/agents/sub_agents/reviewer/agent.py` and the G-Eval scorer in `packages/quality/layer4_judge/geval.py`. Both files exist with stubs.

## Current State

```python
# packages/agents/sub_agents/reviewer/agent.py (lines 29-52)
async def quality_review(state: OhMyClassState) -> dict[str, Any]:
    # TODO: Implement with LangGraph agent
    raise NotImplementedError("quality_review() stub")

# packages/quality/layer4_judge/geval.py (lines 52-73)
async def score(self, artifacts, *, lesson_plan=None) -> JudgeOutput:
    # TODO: Implement G-Eval scoring
    raise NotImplementedError("GEvalScorer.score() stub")

# packages/quality/layer4_judge/majority_vote.py — NOT YET CREATED
# packages/agents/sub_agents/reviewer/prompts.py — NOT YET CREATED
# common/contracts/judge_output.py — COMPLETE (JudgeOutput schema exists)
```

## Implementation Spec

### 1. Create `packages/agents/sub_agents/reviewer/prompts.py` (new file)

```python
"""Reviewer Agent prompts — system prompt for G-Eval scoring."""

from __future__ import annotations

REVIEWER_SYSTEM_PROMPT: str = """\
You are the Reviewer Agent for oh-my-class.

## Role
Evaluate generated teaching artifacts using G-Eval methodology.
Score each artifact across 3 layers with weighted aggregation.

## Scoring Layers
1. Format compliance (15%): DOCTYPE, no CDN, brand strings, responsive
2. Content quality (55%): Accuracy, completeness, relevance, reasoning
3. Presentation (30%): Readability, engagement, accessibility

## Output Format
Return a JSON object matching the JudgeOutput schema:
```json
{
  "overall_score": "float 0.0-10.0",
  "layer_scores": [
    {"layer": "format_compliance", "score": 8.0, "weight": 0.15, "issues": []},
    {"layer": "content_quality", "score": 7.5, "weight": 0.55, "issues": []},
    {"layer": "presentation", "score": 8.0, "weight": 0.30, "issues": []}
  ],
  "critical_issues": [],
  "passed": true,
  "rationale": "string explaining the scores"
}
```

## Bias Mitigations
- Write rationale BEFORE computing scores (think-before-score)
- Do NOT rate longer answers higher
- Be strict but fair — focus on educational value

## Pass Threshold
- overall_score >= 7.0 AND no critical_issues
"""
```

### 2. Create `packages/quality/layer4_judge/majority_vote.py` (new file)

```python
"""Majority vote logic for G-Eval scoring."""

from __future__ import annotations

from typing import Any

from common.contracts.judge_output import JudgeOutput


def majority_vote(judge_outputs: list[JudgeOutput]) -> JudgeOutput:
    """Calculate majority vote across multiple judge outputs.
    
    Args:
        judge_outputs: List of JudgeOutput from independent judge calls.
    
    Returns:
        JudgeOutput with aggregated scores and pass/fail status.
    
    Rules:
        - 2/3 must pass for overall pass
        - Scores are averaged across judges
        - Critical issues are unioned
    """
    if not judge_outputs:
        raise ValueError("No judge outputs provided")
    
    # Count passes
    pass_count = sum(1 for j in judge_outputs if j.passed)
    total = len(judge_outputs)
    
    # Average scores
    avg_overall = sum(j.overall_score for j in judge_outputs) / total
    
    # Average layer scores
    layer_scores = []
    for layer_name in ["format_compliance", "content_quality", "presentation"]:
        layer_vals = []
        for j in judge_outputs:
            for ls in j.layer_scores:
                if ls.layer == layer_name:
                    layer_vals.append(ls.score)
        if layer_vals:
            avg_score = sum(layer_vals) / len(layer_vals)
            # Get weight from first judge
            weight = next(
                ls.weight for j in judge_outputs 
                for ls in j.layer_scores 
                if ls.layer == layer_name
            )
            layer_scores.append({
                "layer": layer_name,
                "score": avg_score,
                "weight": weight,
                "issues": [],
            })
    
    # Union critical issues
    critical_issues = []
    for j in judge_outputs:
        critical_issues.extend(j.critical_issues)
    critical_issues = list(set(critical_issues))  # deduplicate
    
    # Majority pass (2/3)
    passed = pass_count >= (total * 2 / 3) and avg_overall >= 7.0 and not critical_issues
    
    # Use rationale from first judge
    rationale = judge_outputs[0].rationale if judge_outputs else ""
    
    return JudgeOutput(
        overall_score=avg_overall,
        layer_scores=layer_scores,
        critical_issues=critical_issues,
        passed=passed,
        rationale=rationale,
    )
```

### 3. Replace `GEvalScorer.score()` stub (lines 52-73)

```python
async def score(
    self,
    artifacts: list[dict[str, Any]],
    *,
    lesson_plan: dict[str, Any] | None = None,
) -> JudgeOutput:
    """Score artifacts using G-Eval across 3 layers.
    
    Args:
        artifacts: Generated artifact content dicts.
        lesson_plan: Original lesson plan for alignment scoring.
    
    Returns:
        JudgeOutput with scores, issues, and pass/fail status.
    """
    import litellm
    import json
    from common.contracts.judge_output import JudgeOutput
    
    from packages.agents.sub_agents.reviewer.prompts import REVIEWER_SYSTEM_PROMPT
    
    # Format the scoring prompt
    user_prompt = f"""
    Evaluate the following teaching artifacts:
    
    Artifacts:
    {json.dumps(artifacts, indent=2)}
    
    {f"Lesson Plan for alignment: {json.dumps(lesson_plan, indent=2)}" if lesson_plan else ""}
    
    Score each artifact across the 3 layers and provide overall assessment.
    """
    
    messages = [
        {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    
    # Run num_judges independent judge calls
    judge_outputs = []
    for i in range(self.config.num_judges):
        try:
            response = await litellm.acompletion(
                model="content-fusion",
                messages=messages,
                temperature=0.3 + (i * 0.1),  # Different seeds for diversity
                extra_body={
                    "metadata": {
                        "tags": [
                            "agent:reviewer",
                            f"judge:{i+1}",
                            "pipeline:oh-my-class",
                        ]
                    }
                },
            )
            
            content = response.choices[0].message.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            output_data = json.loads(json_str)
            judge_output = JudgeOutput.model_validate(output_data)
            judge_outputs.append(judge_output)
            
        except Exception as e:
            # Log error but continue with other judges
            print(f"Judge {i+1} failed: {e}")
            continue
    
    if not judge_outputs:
        raise ValueError("All judge calls failed")
    
    # Aggregate via majority vote
    from packages.quality.layer4_judge.majority_vote import majority_vote
    return majority_vote(judge_outputs)
```

### 4. Replace `quality_review()` stub (lines 29-52)

```python
"""Reviewer Agent — node implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


async def quality_review(state: OhMyClassState) -> dict[str, Any]:
    """LangGraph node for the Reviewer Agent.
    
    Takes generated artifacts and produces quality scores via G-Eval.
    Runs 3 independent judge calls and takes majority vote.
    
    Args:
        state: Current pipeline state with artifacts and lesson_plan.
    
    Returns:
        Partial state update containing 'quality_scores' and 'quality_passed'.
    """
    from packages.quality.layer4_judge.geval import GEvalScorer
    
    artifacts = state.get("artifacts", [])
    lesson_plan = state.get("lesson_plan")
    
    scorer = GEvalScorer()
    judge_output = await scorer.score(artifacts, lesson_plan=lesson_plan)
    
    return {
        "quality_scores": judge_output.model_dump(),
        "quality_passed": judge_output.passed,
    }
```

## Acceptance criteria

- [ ] `quality_review()` calls `GEvalScorer.score()` with artifacts
- [ ] `quality_review()` returns `{"quality_scores": ..., "quality_passed": ...}`
- [ ] `GEvalScorer.score()` calls LiteLLM `num_judges` times (default 3)
- [ ] `GEvalScorer.score()` uses different temperature for each judge
- [ ] `majority_vote()` counts passes correctly (2/3 threshold)
- [ ] `majority_vote()` averages overall_score across judges
- [ ] `majority_vote()` unions critical_issues
- [ ] `majority_vote()` returns passed=True only if pass_count >= 2/3 AND score >= 7.0
- [ ] Unit test: majority_vote with all pass → passed
- [ ] Unit test: majority_vote with 2 pass + 1 fail → passed
- [ ] Unit test: majority_vote with 1 pass + 2 fail → failed
- [ ] Unit test: majority_vote with score < 7.0 → failed

## Test suite

Create `packages/quality/layer4_judge/tests/test_geval.py`:

```python
import pytest
from common.contracts.judge_output import JudgeOutput, LayerScore
from packages.quality.layer4_judge.majority_vote import majority_vote


def make_judge_output(passed=True, score=8.0):
    """Helper to create test JudgeOutput."""
    return JudgeOutput(
        overall_score=score,
        layer_scores=[
            LayerScore(layer="format_compliance", score=score, weight=0.15, issues=[]),
            LayerScore(layer="content_quality", score=score, weight=0.55, issues=[]),
            LayerScore(layer="presentation", score=score, weight=0.30, issues=[]),
        ],
        critical_issues=[],
        passed=passed,
        rationale="Test rationale",
    )


class TestMajorityVote:
    def test_all_pass(self):
        outputs = [make_judge_output(passed=True) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is True
    
    def test_two_pass_one_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=True),
            make_judge_output(passed=False),
        ]
        result = majority_vote(outputs)
        assert result.passed is True
    
    def test_one_pass_two_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=False),
            make_judge_output(passed=False),
        ]
        result = majority_vote(outputs)
        assert result.passed is False
    
    def test_score_below_threshold(self):
        outputs = [make_judge_output(passed=True, score=6.0) for _ in range(3)]
        result = majority_vote(outputs)
        assert result.passed is False
        assert result.overall_score < 7.0
    
    def test_critical_issues_fail(self):
        outputs = [
            make_judge_output(passed=True),
            make_judge_output(passed=True),
            make_judge_output(passed=True),
        ]
        outputs[0].critical_issues = ["Critical issue"]
        result = majority_vote(outputs)
        assert result.passed is False
    
    def test_averages_scores(self):
        outputs = [
            make_judge_output(score=8.0),
            make_judge_output(score=6.0),
            make_judge_output(score=7.0),
        ]
        result = majority_vote(outputs)
        assert result.overall_score == pytest.approx(7.0)
```

## File paths

| File | Action |
|------|--------|
| `packages/agents/sub_agents/reviewer/agent.py` | MODIFY: Replace stub (lines 29-52) |
| `packages/agents/sub_agents/reviewer/prompts.py` | CREATE: System prompt |
| `packages/quality/layer4_judge/geval.py` | MODIFY: Replace score() stub (lines 52-73) |
| `packages/quality/layer4_judge/majority_vote.py` | CREATE: New file |
| `packages/quality/layer4_judge/tests/test_geval.py` | CREATE: Full test suite |

## Dependencies

- `common/contracts/judge_output.py` — JudgeOutput, LayerScore (already exists)
- `litellm` — LLM client (already installed)
- `packages/agents/state.py` — OhMyClassState (already exists)

## Edge cases to handle

1. All judge calls fail → raise ValueError
2. Single judge output → majority_vote still works (1/1 = 100%)
3. Empty artifacts → LLM may produce poor output (not handled here)
4. Critical issues present → forced fail regardless of score
5. Score exactly 7.0 → passes (>= 7.0)
