# Module: contracts

**Path:** `common/contracts`
**Role:** Pydantic v2 models — the single source of truth for all data schemas in the monorepo. Every model that validates agent output lives here, not in `packages/agents` or `services/gateway` (INVARIANT-10).

## Public interface

### Core pipeline contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `RunContract` | Pydantic model | `run_contract.py:39` | Pipeline run configuration (topic, grade, subject, locale, artifact types, export formats) |
| `ContractRevision` | Pydantic model | `run_contract.py:62` | Versioned contract revision with actor/source/reason |
| `DecompositionIntent` | Pydantic model | `run_contract.py:31` | Unit decomposition intent (sessions, duration, rationale) |
| `LessonPlan` | Pydantic model | `lesson_plan.py:61` | Planner Agent output (UbD, Gagné 9-event, Bloom levels) |
| `LearningObjective` | Pydantic model | `lesson_plan.py:28` | Single LO with Bloom level + assessment method |
| `AssessmentCheckpoint` | Pydantic model | `lesson_plan.py:47` | Formative assessment checkpoint |
| `ArtifactContent` | Pydantic model | `artifact.py:46` | Content Creator output (12 artifact types, sections, metadata) |
| `FlashcardDeckData` | Pydantic model | `artifact.py:28` | Flashcard deck structure (mirrors TS `FlashcardDeckData`) |
| `Flashcard` | Pydantic model | `artifact.py:19` | Single flashcard (front, back, hint) |
| `TeachingPack` | Pydantic model | `artifact.py:105` | Complete teaching pack (run_id + artifacts + metadata) |
| `JudgeOutput` | Pydantic model | `judge_output.py:29` | Reviewer Agent output (G-Eval scores, pass/fail, rationale) |
| `LayerScore` | Pydantic model | `judge_output.py:12` | Single quality layer score (format/content/presentation) |

### Content components

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `ContentComponent` | Annotated union | `components/__init__.py:60` | 22-variant discriminated union (discriminated on `type` field) |
| `Heading`, `Paragraph`, `Callout` | Pydantic models | `components/textual.py` | Text components |
| `Table` | Pydantic model | `components/tabular.py` | Tabular data component |
| `StatGrid`, `PatternGrid`, `TraitGrid`, `TaxonomyGrid` | Pydantic models | `components/cards.py` | Card grid components |
| `PhaseTimeline`, `FlowStep` | Pydantic models | `components/timeline.py` | Timeline/flow components |
| `QuestionCard`, `QuestionList` | Pydantic models | `components/questions.py` | Question components |
| `ConceptMap`, `VocabCluster`, `ContrastivePairs`, `PhrasalVerbCluster` | Pydantic models | `components/concept.py` | Concept/vocabulary components |
| `FilmClipActivity`, `RoleplayScript`, `ActiveRecallPrompt` | Pydantic models | `components/vocab_lesson.py` | Vocabulary lesson components |

### Research contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `ResearchBundle` | Pydantic model | `research_bundle.py` | Researcher Agent output (sources, cross-references) |
| `ResearchSource` | Pydantic model | `research_bundle.py:13` | Single research source with credibility |
| `ResearchBrief` | Pydantic model | `research_brief.py` | Pre-planning search brief |
| `PrePlanningSearchBrief` | Pydantic model | `research_brief.py` | Pre-planning search parameters |
| `EvidenceCitation` | Pydantic model | `research_brief.py` | Citation with evidence level |

### Quality contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `QualityIssue` | Pydantic model | `quality.py` | Single quality issue |
| `QualityFailureClass` | StrEnum | `quality.py:8` | 11 failure classes (schema_invalid, answer_key_leakage, etc.) |
| `HealingDecision` | Pydantic model | `quality.py` | Healing strategy decision |
| `HealingStrategy` | StrEnum | `quality.py` | retry/rewrite/reroute/replan/escalate |
| `ArtifactQualityReport` | Pydantic model | `quality.py` | Per-artifact quality report |
| `ExportReadinessReport` | Pydantic model | `quality.py` | Export readiness assessment |

### Student/diagnostic contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `StudentProfile` | Pydantic model | `student_profile.py` | Student learning profile |
| `StudentResponse` | Pydantic model | `student_response.py` | Student response data |
| `DiagnosticReport` | Pydantic model | `diagnostic_report.py` | Diagnostic analysis (gaps, misconceptions) |

### Slide deck contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `SlideDeckData` | Pydantic model | `slide_deck.py` | Full slide deck structure (487 lines, most complex contract) |
| `SlideDeckSlide`, `SlideDeckBlock`, `SlideDeckInteraction` | Pydantic models | `slide_deck.py` | Slide sub-components |
| `SlideDeckTeacherOnly` | Pydantic model | `slide_deck.py` | Teacher-only data (answer keys, rationale) |

### Component strategy contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `ComponentStrategyRequest` | Pydantic model | `component_strategy.py` | Strategy generation request |
| `ComponentStrategyPlan` | Pydantic model | `component_strategy.py` | Strategy plan with slots |
| `ComponentStrategyResult` | Pydantic model | `component_strategy.py` | Strategy execution result |
| `StrategySlot` | Pydantic model | `component_strategy.py` | Individual strategy slot |

### Error contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `ErrorResponse` | Pydantic model | `errors.py:47` | Standard API error envelope |
| `PipelineErrorResponse` | Pydantic model | `errors.py:76` | Pipeline-specific error (run_id, step, agent) |
| `ErrorCode` | StrEnum | `errors.py:15` | 10 machine-readable error categories |
| `ValidationErrorDetail` | Pydantic model | `errors.py:34` | Field-level validation failure |

### Auth contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `User` | Pydantic model | `auth.py:13` | Authenticated user |
| `Token` | Pydantic model | `auth.py:21` | JWT token response |
| `Role` | StrEnum | `auth.py:8` | teacher/admin |

### Other contracts

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `ClassProfile` | Pydantic model | `class_profile.py` | Class configuration |
| `InverseThinkingPack` | Pydantic model | `inverse_thinking.py` | Inverse-thinking methodology output |
| `RoadmapContent` | Pydantic model | `roadmap.py` | Learning roadmap structure |
| `VocabularyBatchConfig` | Pydantic model | `vocabulary_batch.py` | Vocabulary batch configuration |
| `SemanticAnchorCluster` | Pydantic model | `vocabulary_batch.py` | Semantic anchor cluster |
| `PracticeSet` | Pydantic model | `vocabulary_batch.py` | Practice item set |
| `Rubric`, `RubricCriterion` | Pydantic models | `rubric.py` | Assessment rubric |
| `LogContext` | Pydantic model | `log_context.py` | Structured logging context |
| `MethodologyRegistryEntry` | Pydantic model | `methodology_registry.py` | Methodology lookup table |

## Internal structure

### File inventory (57 Python files)

**Core pipeline:**
`run_contract.py`, `lesson_plan.py`, `artifact.py`, `artifact_document.py`, `artifact_workflow.py`, `judge_output.py`, `quality.py`, `errors.py`, `auth.py`

**Content components (`components/` sub-package):**
`__init__.py` (ContentComponent union), `cards.py`, `concept.py`, `questions.py`, `tabular.py`, `textual.py`, `timeline.py`, `vocab_lesson.py`

**Research:**
`research_bundle.py`, `research_brief.py`, `source_collection.py`, `claim_evidence.py`

**Student/diagnostic:**
`student_profile.py`, `student_response.py`, `diagnostic_report.py`

**Slide deck:**
`slide_deck.py` (487 lines — largest single file)

**Component strategy:**
`component_strategy.py`, `component_strategy_capabilities.py`, `component_strategy_coverage.py`, `component_strategy_enums.py`, `component_strategy_fallback_validation.py`, `component_strategy_knowledge.py`, `component_strategy_knowledge_index.py`, `component_strategy_knowledge_models.py`, `component_strategy_moet.py`, `component_strategy_privacy.py`, `component_strategy_selector.py`, `component_strategy_selector_fallback.py`, `component_strategy_selector_support.py`, `component_strategy_slot_contracts.py`, `component_strategy_slot_policy.py`, `component_strategy_smoke_benchmark.py`

**Other:**
`answer_key.py`, `answer_set.py`, `class_profile.py`, `content_brief.py`, `decision_provenance.py`, `grade_band.py`, `inverse_thinking.py`, `lesson_sequence.py`, `log_context.py`, `media_asset.py`, `methodology_registry.py`, `objective_lineage.py`, `outcome.py`, `research_brief.py`, `roadmap.py`, `rubric.py`, `seam_contracts.py`, `strategy_review.py`, `subject_capability_pack.py`, `teaching_brief.py`, `teaching_pack_capabilities.py`, `unit_view.py`, `visual_source_suggestion.py`, `vocabulary_batch.py`, `vocabulary_cluster_workflow.py`

### Package configuration

`pyproject.toml` declares:
- Python ≥3.12
- Single runtime dependency: `pydantic>=2.0.0`
- Build system: `hatchling`

## Depends on

_None (leaf node)._

| Dependency | Kind | Import sites | Verified |
|-----------|------|-------------|----------|
| `pydantic` (PyPI) | runtime | Every `.py` file — `from pydantic import BaseModel, Field` | ✅ |

### Internal imports (within common/contracts)

All imports are within the `common.contracts` package. Key internal imports:

| Import site | What is imported |
|-------------|-----------------|
| `__init__.py:7-176` | Re-exports from 40+ sub-modules |
| `artifact.py:14` | `ContentComponent` from `common.contracts.components` |
| `lesson_plan.py:13-14` | `InverseThinkingPack` from `common.contracts.inverse_thinking`, `MethodologyTag` from `common.contracts.methodology_registry` |
| `slide_deck.py:9-10` | `CoreArtifactType` from `common.contracts.artifact_workflow`, `is_remote_source` from `common.contracts.media_asset` |
| `components/__init__.py:12-58` | 10 sub-modules within `common.contracts.components` |
| `component_strategy.py` | Various component_strategy_* sub-modules |

### Outbound imports to other project modules

**NONE.** Verified across all 57 files. The contracts package has zero imports from `packages/*`, `services/*`, or `apps/*`. This is a true leaf node in the dependency graph.

## Used by

- **`agents`** — 157 imports across 125 files; ArtifactContent, LessonPlan, JudgeOutput, RunContract, SlideDeckData
- **`quality`** — ~20 imports; ArtifactContent, QualityIssue, QualityFailureClass
- **`gateway`** — ~40 imports; RunContract, ArtifactContent, ErrorResponse, User, Token, SlideDeckData

| Consumer | Import count | Key imports |
|---------|-------------|-------------|
| **agents** (`packages/agents`) | ~157 imports across 125 files | `ArtifactContent`, `LessonPlan`, `JudgeOutput`, `QualityIssue`, `RunContract`, `SlideDeckData`, `SemanticAnchorCluster`, `ResearchBundle`, `DiagnosticReport`, etc. |
| **quality** (`packages/quality`) | ~20 imports | `ArtifactContent`, `QualityIssue`, `QualityFailureClass` |
| **gateway** (`services/gateway`) | ~40 imports | `RunContract`, `ArtifactContent`, `ErrorResponse`, `User`, `Token`, `SlideDeckData` |
| **web** (`apps/web`) | indirect via gateway API | TypeScript types generated from Pydantic models |

### Not consumed by

- **renderer** (`packages/renderer`) — TypeScript, imports from `@oh-my-class/schemas` (TS package), NOT from Python contracts
- **exporters** (`packages/exporters`) — TypeScript, imports from `@oh-my-class/schemas` (TS package), NOT from Python contracts

## Data & side effects

- **None.** This is a pure schema/contract module with no I/O, no network calls, no file access, no side effects. It defines data shapes only.

## Notes / discrepancies vs existing docs

1. **INVARIANT-10 compliance**: Confirmed — all Pydantic models that validate agent output are in `common/contracts`, not in `packages/agents` or `services/gateway`. The only exception is `ComponentStrategyMode` which is also referenced by agents, but it's defined here.

2. **Phase 3 hypothesis "contracts has no outbound imports to other project modules"** — CONFIRMED. Zero imports from `packages/*`, `services/*`, or `apps/*`. The only runtime dependency is `pydantic>=2.0.0`.

3. **Phase 3 hypothesis "External: pydantic"** — CONFIRMED. `pyproject.toml:7` shows `pydantic>=2.0.0`.

4. **slide_deck.py is the largest file** at 487 lines. It contains 15+ Pydantic models for the slide deck structure, including layout types, interaction types, teacher-only data, and display preferences. It imports from `artifact_workflow` and `media_asset` (both within contracts).

5. **Component strategy sub-package is substantial** — 16 files covering strategy generation, selection, knowledge indexing, slot policies, MoET alignment, privacy (decision ledger), and smoke benchmarks. This is a significant portion of the contracts module.

6. **ContentComponent union has 22 variants** (not the "20 typed component variants" mentioned in some docs). The actual union in `components/__init__.py:60-62` includes: `Heading | Paragraph | Callout | OrderedList | UnorderedList | Table | StatGrid | PatternGrid | TraitGrid | TaxonomyGrid | PhaseTimeline | FlowStep | QuestionCard | QuestionList | ConceptMap | TimelineComponent | VocabCluster | ContrastivePairs | PhrasalVerbCluster | FilmClipActivity | RoleplayScript | ActiveRecallPrompt`.

7. **TS schemas package** (`common/schemas`) is a separate TypeScript package (`@oh-my-class/schemas`) that provides Zod schemas. It is NOT the same as the Python contracts, though they define overlapping shapes. The renderer and exporters import from `@oh-my-class/schemas`, not from `common/contracts`.

---
_Traced from source on 2026-07-11. Files examined in depth: `__init__.py`, `run_contract.py`, `lesson_plan.py`, `artifact.py`, `judge_output.py`, `errors.py`, `quality.py`, `auth.py`, `research_bundle.py`, `components/__init__.py`, `components/questions.py`, `slide_deck.py` (first 20 lines), `pyproject.toml`. Verified zero outbound imports across all 57 files via grep and manual inspection of representative files._
