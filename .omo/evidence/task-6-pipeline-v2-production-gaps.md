# Task 6: Adaptive LLM Judge × Deterministic Quality Gates Integration

**Date**: 2026-06-28
**Status**: COMPLETE
**Pipeline version**: v2

---

## Summary

Integrated an adaptive LLM judge with the existing deterministic quality gates.
The judge selects rubrics by artifact type and failure context, calls the LLM
through an injectable transport, enforces hard blocks from deterministic gates,
and tracks full rubric provenance. Deterministic gates remain authoritative —
no LLM score can override them.

---

## Files Created

| File | Purpose | LOC |
|------|---------|-----|
| `packages/quality/layer4_judge/rubric_selector.py` | RubricSelector — maps (artifact_type, failure_context) → Rubric | 238 |
| `packages/quality/layer4_judge/judge_interface.py` | AdaptiveJudge — LLM judge + hard block enforcement + fail-closed | 440 |
| `packages/quality/tests/test_judge_interface.py` | 34 deterministic fake-LLM tests | 400 |

## Files Modified

| File | Change |
|------|--------|
| `packages/quality/layer4_judge/__init__.py` | Added exports: AdaptiveJudge, JudgeResult, JudgeUnavailableError, UnavailableStrategy, RubricSelector |

---

## Architecture

```
AdaptiveJudge.judge()
  │
  ├─ 1. RubricSelector.select(artifact_type, failure_context)
  │     └─ Returns Rubric with version_id provenance
  │
  ├─ 2. _call_llm_judges(artifacts, rubric, messages)
  │     ├─ Builds rubric-augmented system prompt
  │     ├─ Calls LLM transport N times (default: 3 judges)
  │     ├─ Each call gets: model, messages, temperature, metadata tags
  │     ├─ Metadata includes: agent:judge, judge:{n}, rubric:{version_id}
  │     └─ Raises last exception if ALL calls fail (fail-closed)
  │
  ├─ 3. majority_vote(judge_outputs) — aggregation (existing)
  │
  └─ 4. _enforce_hard_blocks(judge_output, deterministic_issues, teacher_approved)
        ├─ Checks issue codes against HARD_BLOCK_CODES (frozenset)
        ├─ Checks teacher_approved flag
        ├─ If ANY hard block found → forces passed=False
        ├─ Adds violations to critical_issues
        ├─ Appends override note to rationale
        └─ Returns (final_output, was_blocked, violations)
```

---

## Hard Block Enforcement (Critical Invariant)

**Theorem**: A perfect LLM score (10.0) can NEVER override a deterministic gate failure.

**Proof (test)**: `test_high_llm_score_cannot_override_hard_block`

```python
perfect_output = JudgeOutput(
    overall_score=10.0,
    layer_scores=[
        LayerScore(layer="format_compliance", score=10.0, weight=0.15),
        LayerScore(layer="content_quality", score=10.0, weight=0.55),
        LayerScore(layer="presentation", score=10.0, weight=0.30),
    ],
    critical_issues=[],
    passed=True,
    rationale="Perfect score",
)
result, blocked, violations = _enforce_hard_blocks(
    perfect_output, ["missing_doctype", "external_assets"], teacher_approved=True
)
assert result.passed is False       # LLM 10.0 overridden
assert blocked is True
assert len(violations) == 2
```

**Hard block codes covered** (HARD_BLOCK_CODES frozenset):

| Code | Source |
|------|--------|
| `missing_doctype` | HTML validator, QualityFailureClass |
| `external_assets` | HTML validator |
| `external_asset` | QualityFailureClass |
| `answer_key_leakage` | Both |
| `pii_leakage` | QualityFailureClass |
| `native_radio_inputs` | HTML validator |
| `unmanaged_js_runtime` | HTML validator |
| `missing_brand_string` | HTML validator |
| `schema_invalid` | QualityFailureClass |

---

## Rubric Selection

Rubrics are selected by `(artifact_type, failure_context)` → `Rubric` from
a `RubricRegistry`. The selector:

1. **Base criteria**: format_compliance (15%), content_quality (55%), presentation (30%)
2. **Artifact-type overrides**: quiz→60% content, infographic→50% presentation, etc.
3. **Failure-context boosts**: answer_key_leakage→+10% content_quality, missing_doctype→+10% presentation
4. **Normalization**: all weights re-normalized to sum to 1.0

**Provenance tracking**: Every `JudgeResult` includes:
- `rubric_version`: e.g. `"rubric-quiz-answer_key_leakage"`
- `rubric_description`: human-readable
- `deterministic_blocked`: bool
- `hard_block_violations`: list[str]

---

## Judge-Unavailable Path

Two strategies via `UnavailableStrategy` enum:

| Strategy | Behavior |
|----------|----------|
| `FAIL_CLOSED` (default) | Raises `JudgeUnavailableError` — caller must escalate or fail the run |
| `USE_DETERMINISTIC_ONLY` | Returns `JudgeOutput(passed=False, score=0.0, critical_issues=["llm_judge_unavailable"])` |

**Both paths result in `passed=False`** — no silent pass.

---

## Test Results

```
packages/quality/tests/test_judge_interface.py — 34 tests
  TestRubricSelector (10): ALL PASS
  TestHardBlockEnforcement (11): ALL PASS
  TestAdaptiveJudge (9): ALL PASS
  TestHardBlockCodeCoverage (2): ALL PASS
  TestLLMTransportMetadata (2): ALL PASS

packages/quality/tests/test_layer4_judge.py — 18 tests: ALL PASS (no regressions)
services/gateway/tests/test_quality_gates.py — 6 tests: ALL PASS (no regressions)

Full packages/quality/ — 265 tests: ALL PASS
```

---

## Ruff Lint

```
uv run ruff check packages/quality/layer4_judge/ packages/quality/tests/test_judge_interface.py
All checks passed!
```

---

## Integration Points

### Existing callers can adopt incrementally:

```python
# New way (task 6):
from packages.quality.layer4_judge import AdaptiveJudge, UnavailableStrategy

judge = AdaptiveJudge(unavailable_strategy=UnavailableStrategy.FAIL_CLOSED)
result = await judge.judge(
    artifacts=artifacts,
    artifact_type="quiz",
    deterministic_issues=["answer_key_leakage"],  # from quality_gates.py
    teacher_approved=True,                         # from pipeline state
)
assert result.judge_output.passed  # would be False if hard block present
assert result.rubric_version       # provenance for audit trail

# Old way (still works, no breaking change):
from packages.quality.layer4_judge import GEvalScorer
scorer = GEvalScorer()
output = await scorer.score(artifacts)
```

### Deterministic gates remain at:
- `services/gateway/quality_gates.py` — regex-based validation (unchanged)
- `packages/quality/layer3_html/html_validator.py` — HTML presentation checks (unchanged)
- `packages/quality/layer1_schema/` — Pydantic schema validation (unchanged)

### The adaptive judge sits alongside:
- `packages/quality/layer4_judge/geval.py` — legacy G-Eval scorer (unchanged)
- `packages/quality/layer4_judge/majority_vote.py` — reused by AdaptiveJudge (unchanged)

---

## INVARIANT Compliance

| Invariant | Status |
|-----------|--------|
| INVARIANT-02 (import boundaries) | PASS — all new code in packages/quality/, imports only from common/contracts |
| INVARIANT-04 (no external assets) | N/A — judge doesn't produce HTML |
| INVARIANT-05 (answer key separation) | PASS — answer_key_leakage is a hard block code |
| INVARIANT-07 (metadata tags) | PASS — all LLM calls include agent:judge, rubric:{version_id}, pipeline:oh-my-class |
| INVARIANT-10 (contracts in common/) | PASS — uses existing JudgeOutput, Rubric from common/contracts |
