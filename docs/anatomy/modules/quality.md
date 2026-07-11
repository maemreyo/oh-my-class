# Module: quality

**Path:** `packages/quality`
**Role:** The 6-layer quality gate system that validates, judges, and gates every artifact produced by the teaching pack pipeline. Pure validation library — zero orchestration; all pipeline integration lives in `packages/agents/teaching_pack/`.

## Public interface

- `compliance_policy.py` — **Single source of truth** for all deterministic hard-block checks
  - `html_hard_blocks(html)` → `(hard_blocks: list[str], warnings: list[str])` — 16 hard-block codes
  - `answer_key_issues(value)` → `list[str]` — Detects English/Vietnamese answer-key leakage markers
  - `check_artifact_answer_key_leakage(artifact)` → `ComplianceResultDict` — INVARIANT-05 enforcement
  - `hard_block_violations(deterministic_issues, *, teacher_approved)` → `list[str]` — Final gate decision
- `calibrate_gates(labeled_data, *, target_kappa)` → stub (`raise NotImplementedError`)
- **Layer 1:** `validate_schema(data, schema_model, *, max_retries)` → `BaseModel`; `check_placeholder_content(data)`; `check_bloom_coverage(objectives, min_levels=2)`; `check_answer_key_separation(artifact)`; `validate_component_minimums(artifact)`; `CircuitBreaker` (3-state with cooldown)
- **Layer 2:** `FACTChecker` (async: `find_claims`, `assess_sources`, `cross_reference`, `check_claims`); `check_age_appropriateness(text, grade_level)` → `AgeAppropriatenessResult`; `check_readability(text, target_grade)` → `ReadabilityResult`; `check_pedagogical_metrics(content, *, lesson_plan, research_bundle)` → `PedagogicalResult`; `detect_pii(value)` / `scrub_pii(value)` → `PiiAuditEvent` / `PiiScrubResult`; `check_methodology_compliance(sections, methodology_tags)` → `MethodologyGateResult`; `score_component_usage(artifact, lesson_plan)` → `ComponentScoringResult`; `validate_inverse_thinking_pack(payload)` → `InverseThinkingGateResult`
- **Layer 3:** `HTMLValidator().validate(html)` → `HTMLValidationResult`; `AccessibilityValidator().validate(html)` → `AccessibilityValidationResult`; `check_responsive(html, *, viewports, environment)` → `ResponsiveCheckResult`
- **Layer 4:** `AdaptiveJudge(judges=3, pass_threshold=7.0).judge(artifacts, *, artifact_type, ...)` → `JudgeResult`; `majority_vote(judge_outputs)` → `JudgeOutput`; `enforce_hard_blocks(judge_output, deterministic_issues, teacher_approved)` → `(JudgeOutput, bool, list[str])`; `RubricSelector().select(artifact_type, ...)` → `Rubric`; `judge_policy_decision(context)` → `JudgePolicyDecision`
- **Layer 5:** `InterruptHandler(config).create_gate(gate_type, state)` / `.handle_timeout(gate_type)` — LangGraph `interrupt()` for teacher approval
- **Layer 6:** `ExportValidator().validate(artifacts, export_formats)` → `ExportValidationResult`
- **Semantic Anchoring:** `SemanticAnchoringQualityGate().evaluate(quality_input)` → `SemanticAnchoringQualityResult`

## Internal structure

### compliance_policy.py (282 lines)
The **single owner** for deterministic hard-block policy. 16 hard-block codes (`COMPLIANCE_HARD_BLOCK_CODES`): `schema_invalid`, `missing_doctype`, `external_assets`, `external_asset`, `native_radio_inputs`, `unmanaged_js_runtime`, `missing_brand_string`, `contrast_below_aa`, `missing_alt_text`, `broken_heading_order`, `missing_form_label`, `missing_lang`, `missing_long_description`, `answer_key_leakage`, `pii_leakage`, `teacher_gate_not_approved`. Includes full WCAG AA contrast computation (`_relative_luminance`, `_linear`).

### layer1_schema/ (3 files)
- `validators.py` — Pydantic v2 schema validation with `ModelRetry` up to 3 retries, placeholder patterns (`[TBD]`, `lorem ipsum`, `TODO`, `PLACEHOLDER`, `[INSERT]`), Bloom coverage (≥2 levels), answer-key separation. Also contains a simple `CircuitBreaker` (threshold-only).
- `component_gate.py` — `validate_component_minimums()` per artifact type; `extract_components(sections)` helper
- `circuit_breaker.py` — Full stateful `CircuitBreaker` with CLOSED/OPEN/HALF_OPEN states and 30s cooldown timer

### layer2_content/ (8 files)
- `fact_check.py` — `FACTChecker` class implementing Find-Assess-Cross-reference-Tag protocol. `VerificationTag` enum: VERIFIED/MODIFIED/REMOVED/UNCERTAIN. `VerifiedClaim` dataclass with claim, tag, sources, confidence.
- `age_check.py` / `age_band.py` — 6 ACIF age bands (Early Childhood → Pre-Tertiary) with Lexile ceilings and Bloom ceilings. `compute_flesch_kincaid()` + deviation check.
- `readability_checker.py` — `MAX_DEVIATION = 2.0`; `ReadabilityResult` with FK grade level, target, deviation, warning.
- `pedagogical.py` — 5 measured metrics (prompt_alignment, bloom_coverage, cognitive_load, readability_level, misconception_coverage) + 5 unmeasured (factual_correctness, contextual_relevance, engagement, harmful_content_avoidance, solution_accuracy) = 10 total.
- `pii.py` — 7 PII categories (email, phone, url, social_handle, student_id, school_id, person_name) with SHA-256 hashed audit trail. `PiiScrubResult` with audit event and low-confidence matches.
- `methodology.py` — Validates sections against methodology tags from `METHODOLOGY_REGISTRY`. `validate_composite_projection_plan()` for composite plans.
- `component_scorer.py` — `ComponentScoringResult` with 0-10 score, diversity ratio, overuse/stuffing penalties, methodology bonus. Uses `PedagogicalIntent` from contracts.
- `inverse_thinking.py` — `validate_inverse_thinking_pack()` validates semantic rules, delegates to `packages.methodologies.inverse_thinking.validate_semantics()`.

### layer3_html/ (3 files)
- `html_validator.py` — `HTMLValidator` with 7 checks delegating to `compliance_policy.html_hard_blocks()`: DOCTYPE, external assets, brand string, viewport, native radio, external JS, answer key separation
- `accessibility_validator.py` — `AccessibilityValidator` checking lang attr, image alt, SVG long description, heading order, form labels, contrast ratio (WCAG AA ≥4.5:1)
- `responsive_check.py` — Playwright-based viewport testing at 375/768/1280/1920px, skipped in dev environment

### layer4_judge/ (11 files)
- `judge_interface.py` — `AdaptiveJudge` orchestrator: constructs `RubricSelector`, runs N judges via `LLMTransport`, applies `enforce_hard_blocks()`, runs `majority_vote()`. Temperature ramping: 0.3/0.4/0.5 across judges.
- `majority_vote.py` — Requires ≥2/3 pass AND avg_score ≥7.0 AND no critical issues from individual judges
- `hard_blocks.py` — Deterministic override layer using `COMPLIANCE_HARD_BLOCK_CODES` — forces `passed=False` on hard-block violations
- `rubric_selector.py` — `RubricSelector` with `RubricRegistry` from contracts. Selects rubric by artifact type, subject, locale, curriculum, risk level.
- `judge_policy.py` — `JudgePolicyContext` / `JudgePolicyDecision`: risk levels (low/standard/high/rigorous), borderline score gating (6.5-7.5), `rubric_version_id()` for tracking
- `judge_prompts.py` — System prompt template with `{rubric_version}` and `{rubric_text}` placeholders; `build_user_prompt()` serializes artifacts
- `judge_transport.py` — `LLMTransport` protocol (async callable), `default_litellm_transport()` implementation using `LLMClient`
- `config.py` — `QualityModelConfig(BaseSettings)`: default model `"4omc"`, env prefix `QUALITY_`
- `prompts/__init__.py` — `load_system_prompt(name="system")` reads from `.md` files

### layer5_human/ (1 file)
- `interrupt_handler.py` — `InterruptHandler` with `InterruptConfig` (24h timeout, max 3 revisions, optional webhook URL). `GateResponse` dataclass: action/feedback/edits.

### layer6_export/ (1 file)
- `export_validator.py` — `ExportValidator` with `FORMAT_REQUIREMENTS`: html→lesson, gift→quiz, h5p→quiz+drill, qti→quiz, anki_apkg→flashcard_deck. 3-judge consensus with `required_pass_rate=0.67`. `skip_threshold=0.20` (stops if ≥20% items fail).

### semantic_anchoring/ (1 file)
- `gate.py` — `SemanticAnchoringQualityGate` with 5-layer check for vocabulary cluster workflows (schema/lexical/pedagogy/projection/html). Uses `QualityFailureClass` from contracts. Outputs `SemanticAnchoringQualityResult` with verdict (passed/needs_review/failed), withholding flags, and evidence entry.

## Depends on

### common.contracts (12 import sites — heaviest dependency)

| File:Line | What imported |
|-----------|---------------|
| `layer2_content/methodology.py:19` | `METHODOLOGY_REGISTRY`, `CompositeProjectionPlan` |
| `layer2_content/inverse_thinking.py:7` | `InverseThinkingPack` |
| `layer2_content/component_scorer.py:16` | `PedagogicalIntent`, `get_entry` from `contracts.components.registry` |
| `layer4_judge/judge_interface.py:22` | `JudgeOutput` |
| `layer4_judge/judge_interface.py:23` | `Rubric` |
| `layer4_judge/majority_vote.py:9` | `JudgeOutput`, `LayerScore` |
| `layer4_judge/hard_blocks.py:11` | `JudgeOutput` |
| `layer4_judge/rubric_selector.py:16` | `Rubric`, `RubricCriterion`, `RubricLevel`, `RubricRegistry` |
| `semantic_anchoring/gate.py:7` | `QualityFailureClass` |
| `semantic_anchoring/gate.py:8` | `PracticeSet`, `SemanticAnchorCluster` |
| `semantic_anchoring/gate.py:9` | `JsonValue`, `VocabularyClusterEvidenceEntry` |

### packages.agents (1 lazy import)

| File:Line | What imported |
|-----------|---------------|
| `layer6_export/export_validator.py:106` | `GateConfig` from `packages.agents.config.gate_config` (lazy, inside `_run_judge_consensus`) |

### packages.methodologies (1 import)

| File:Line | What imported |
|-----------|---------------|
| `layer2_content/inverse_thinking.py:8` | `validate_semantics` from `packages.methodologies.inverse_thinking` |

### packages.llm_client (1 lazy import)

| File:Line | What imported |
|-----------|---------------|
| `layer4_judge/judge_transport.py:34` | `ChatMessage`, `LLMClient` (lazy, inside `default_litellm_transport`) |

### External

- `pydantic>=2.0.0` (core validators)
- `pyyaml>=6.0` (gate_config.yaml loading)
- `playwright` (responsive check, optional)

## Used by

- **agents** — Multiple touch points:
  - `teaching_pack/compliance.py` → `html_hard_blocks()`, `check_artifact_answer_key_leakage()`
  - `teaching_pack/quality.py` → Layer 2 sub-checks
  - `teaching_pack/quality_runtime.py` → orchestrates Layer 1-4
  - `gates/presentation/answer_key_guard.py` → `check_answer_key_separation()`
  - `gates/llm_judge.py` → `AdaptiveJudge`
  - `gates/content_reviewer.py` → `FACTChecker`, `check_pedagogical_metrics()`
  - `middleware/safety/guardrail.py` → `detect_pii()`
  - `healing/circuit_breaker.py` → `CircuitBreaker`
- **gateway** — `teaching_pack_quality_gate.py` combines L2 sub-checks + L3 HTML for per-artifact evaluation
- **tests** — `tests/quality/`, `tests/security/`, `tests/integration/`

## Data & side effects

- **Config:** Reads `packages/quality/gate_config.yaml` (thresholds, weights, enable/disable flags)
- **Config:** `QualityModelConfig` reads `QUALITY_*` env vars
- **Config:** `TokenBudgetConfig` reads `BUDGET_*` env vars (via llm_client)
- **Writes:** None (pure validation)
- **Network:** None directly; L4 judge calls go through `LLMClient` → 9Router
- **Observable:** Violations emit `hard_block_violation` observability events

## Notes / discrepancies vs existing docs

- **Phase 3 hypothesis "quality → contracts: 27 imports" is understated** — I found 12 distinct import *sites* but they bring in 17+ individual types. The previous count of 27 may have counted individual type names across all files.
- **Phase 3 hypothesis "quality → agents: 2 imports" is now 1** — the `export_validator.py:106` lazy import of `GateConfig` is the sole cross-boundary import from agents. This is a potential INVARIANT-02 concern: quality should not depend on agents config. The import is lazy (inside a function) to avoid circular import, but the structural coupling exists.
- **Phase 3 hypothesis "quality → methodologies: 1 import" confirmed** — `inverse_thinking.py:8` calls `validate_semantics()`. This is a clean dependency (quality validates what methodologies produces).
- **Two CircuitBreaker implementations** exist in Layer 1: a simple threshold-only one in `validators.py` and a full stateful one in `circuit_breaker.py`. The stateful one is what `layer1_schema/__init__.py` exports. The simple one in `validators.py` appears unused from outside the file.
- **`calibrate.py` is a stub** — raises `NotImplementedError`. Cohen's κ calibration is not yet implemented.
- AGENTS.md §5.1 listed 5 active pedagogical metrics; code confirms 5 measured + 5 unmeasured = 10 total (same conclusion as previous trace).
- `compliance_policy.py` is the **single source of truth** for hard-blocks. All other layers (L3 HTML, L4 judge, presentation gate) delegate to it via direct function calls.

---
_Traced from source on 2026-07-11. Files examined in depth: all 72 files in packages/quality. Key cross-module imports verified with file:line citations: 12 sites in contracts, 1 in agents (lazy), 1 in methodologies, 1 in llm_client (lazy)._
