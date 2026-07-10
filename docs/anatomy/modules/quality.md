# Module: quality

**Path:** `packages/quality`
**Role:** The 6-layer quality gate system that validates, judges, and gates every artifact produced by the teaching pack pipeline. Pure validation library — zero orchestration; all pipeline integration lives in `packages/agents/teaching_pack/`.

## Public interface

- `compliance_policy.py` — **Single source of truth** for all deterministic hard-block checks
  - `html_hard_blocks(html)` — Returns (hard_blocks, warnings) for 16 hard-block codes
  - `answer_key_issues(value)` — Detects English/Vietnamese answer-key leakage markers
  - `check_artifact_answer_key_leakage(artifact)` — Validates artifact against INVARIANT-05
  - `hard_block_violations(deterministic_issues, *, teacher_approved)` — Final gate decision
- `calibrate_gates` — Cohen's κ calibration stub (not yet implemented)
- Layer 1: `validate_schema()`, `check_placeholder_content()`, `check_bloom_coverage()`, `check_answer_key_separation()`, `validate_component_minimums()`, `CircuitBreaker`
- Layer 2: `FACTChecker`, `check_age_appropriateness()`, `check_readability()`, `check_pedagogical_metrics()`, `detect_pii()`, `scrub_pii()`, `check_methodology_compliance()`, `score_component_usage()`, `validate_inverse_thinking_pack()`
- Layer 3: `HTMLValidator.validate()`, `AccessibilityValidator.validate()`, `check_responsive()`
- Layer 4: `AdaptiveJudge` (3-judge pipeline with rubric selection), `majority_vote()`, `enforce_hard_blocks()`, `RubricSelector`, `judge_policy_decision()`
- Layer 5: `InterruptHandler` (LangGraph `interrupt()` for blueprint/content approval)
- Layer 6: `ExportValidator`, `check_export_readiness()`
- Semantic Anchoring: `SemanticAnchoringQualityGate.evaluate()`

## Internal structure

### compliance_policy.py (282 lines)
The **single owner** for deterministic hard-block policy. 16 hard-block codes: `schema_invalid`, `missing_doctype`, `external_assets`, `external_asset`, `native_radio_inputs`, `unmanaged_js_runtime`, `missing_brand_string`, `contrast_below_aa`, `missing_alt_text`, `broken_heading_order`, `missing_form_label`, `missing_lang`, `missing_long_description`, `answer_key_leakage`, `pii_leakage`, `teacher_gate_not_approved`. Enforced by test `test_no_legacy_compliance_policy.py`.

### layer1_schema/ (3 files)
- `validators.py` — Pydantic v2 schema validation, placeholder detection, Bloom coverage (≥2 levels), answer-key separation
- `component_gate.py` — `validate_component_minimums()` per artifact type
- `circuit_breaker.py` — 3-state CLOSED/OPEN/HALF_OPEN with 30s cooldown

### layer2_content/ (8 files)
- `fact_check.py` — FACT protocol: VERIFIED/MODIFIED/REMOVED/UNCERTAIN, min 2 sources, relevance ≥0.8
- `age_check.py` / `age_band.py` — 6 age bands, Flesch-Kincaid grade check
- `readability_checker.py` — `MAX_DEVIATION = 2.0`; non-Latin text auto-passes
- `pedagogical.py` — 5 measured + 5 unmeasured metrics
- `pii.py` — 7 PII categories with SHA-256 hashed audit trail
- `methodology.py` — Validates sections against methodology tags (R1-R5)
- `component_scorer.py` — 0-10 score with diversity bonus, stuffing penalty
- `inverse_thinking.py` — Pydantic validation + residual PII + quality warnings

### layer3_html/ (3 files)
- `html_validator.py` — Delegates to `compliance_policy.html_hard_blocks()`
- `accessibility_validator.py` — Lang, alt text, SVG, heading order, form labels, contrast (WCAG AA ≥4.5:1)
- `responsive_check.py` — Playwright at 375/768/1280/1920px, skipped in dev

### layer4_judge/ (11 files)
- `judge_interface.py` — `AdaptiveJudge`: 3 judges, temperature 0.3/0.4/0.5
- `majority_vote.py` — Requires ≥2/3 pass AND avg_score ≥7.0 AND no critical issues
- `hard_blocks.py` — Deterministic overrides forcing `passed=False`
- `rubric_selector.py` — 3-criterion rubric with artifact-type weight overrides
- `judge_policy.py` — Risk level, borderline score (6.5-7.5) gating
- `judge_prompts.py` / `prompts/` — System prompts loaded from .md files
- `judge_transport.py` — LLMTransport protocol via LLMClient
- `config.py` — `QualityModelConfig`: default model "4omc"

### layer5_human/ (1 file)
- `interrupt_handler.py` — `InterruptHandler` with 24h timeout, max 3 revisions

### layer6_export/ (1 file)
- `export_validator.py` — Format-specific requirements + 3-judge consensus (≥0.67 pass rate)
- FORMAT_REQUIREMENTS: html→lesson, gift→quiz, h5p→quiz+drill, qti→quiz, anki_apkg→flashcard_deck

### semantic_anchoring/ (1 file)
- `gate.py` — 5-layer check for vocabulary cluster workflows (schema/lexical/pedagogy/projection/html)

## Depends on

- **`contracts`** — imports 27 Pydantic models: `ArtifactContent`, `LessonPlan`, `JudgeOutput`, `ComponentStrategyResult`, etc. (all layer files)
- external: `pydantic>=2.0`, `pyyaml>=6.0`
- external: `playwright` (for responsive check, dev-only)

## Used by

- **`agents`** — `compliance.py` calls `html_hard_blocks()`, `pii.py`; `gates/presentation/answer_key_guard.py`; `gates/llm_judge.py`; `gates/content_reviewer.py`; `middleware/safety/guardrail.py` (PII detection); `teaching_pack/quality_runtime.py`; `teaching_pack/compliance.py`; `teaching_pack/quality.py` (`packages/agents/teaching_pack/quality.py`, `compliance.py`, `quality_runtime.py`)
- **`gateway`** — `teaching_pack_quality_gate.py` combines L2 sub-checks + L3 HTML for per-artifact evaluation (`services/gateway/teaching_pack_quality_gate.py`)
- **`tests`** — `tests/quality/`, `tests/security/`, `tests/integration/`

## Data & side effects

- Reads: `gate_config.yaml` (thresholds, weights, enable/disable flags)
- Writes: None (pure validation; violations emit `hard_block_violation` observability events)
- Network calls: None from quality itself; L4 judge calls go through `LLMClient` → 9Router

## Notes / discrepancies vs existing docs

- AGENTS.md §5.1 listed only 5 active pedagogical metrics; the code confirms 5 measured (prompt_alignment, bloom_coverage, cognitive_load, readability_level, misconception_coverage) + 5 unmeasured (factual_correctness, contextual_relevance, engagement, harmful_content_avoidance, solution_accuracy) — 10 total.
- The compliance_policy.py is the **single source of truth** for hard-blocks, but AGENTS.md §7 "Hard Blocks" section only mentions it under "Hard Blocks (auto-fail regardless of score)" without noting that all other layers (L3 HTML, L4 judge hard-blocks, presentation gate) **delegate** to it. This is a critical architectural detail that should be explicit in the docs.

---

_Traced from source on 2026-07-10. Files examined in depth: all 72 files in packages/quality. The compliance_policy.py is the most important file — every other layer's hard-block check eventually calls it._
