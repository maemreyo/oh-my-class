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

### V2 domain document contracts (#463 cutover)

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `ArtifactDocument` | Pydantic model | `artifact_document.py` | Immutable V2 document: typed `ArtifactPayload` union (assessment/block/rich/slide_deck), `audience` (student/teacher/print), version lineage (`parent_document_id`, `source_document_id`) |
| `ArtifactPayload` | Discriminated union | `artifact_document.py` | `payload_kind`-discriminated payload: `assessment_document` (questions/options), `block_document`, `rich_document`, `slide_deck_document` |
| `artifact_document_from_content` | Function | `artifact_projection_mapper.py:22` | V1 `ArtifactContent` → V2 `ArtifactDocument`; strips teacher-only data for `audience="student"` — generic leaf-key scrub (`_student_value`) for assessment/rich/block payloads, whole-object `teacher_only`/`teacher_notes` removal for slide decks (`_student_safe_slide_deck`, required-field-safe) |
| `artifact_content_from_document` | Function | `artifact_projection_mapper.py:56` | V2 `ArtifactDocument` → V1 `ArtifactContent` projection (read-compatibility path for renderer/quality/export consumers not yet V2-native) |
| `ArtifactProjectionConversionError` | Exception | `artifact_projection_mapper.py:18` | Raised on an unmappable/lossy conversion instead of silently dropping fields |

### Education policy taxonomy (#462 canonical vocabulary)

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `EDUCATION_POLICY_VERSION` | Constant | `education_policy.py:6` | `"education_policy.v1"` — pinned onto `RunContract`, `ContentBrief`, `TeachingBrief`, `ArtifactDocument`, `quality.py` reports |
| `SubjectKey`, `CurriculumFramework`, `Audience`, `ArtifactKind`, `CapabilityStatus`, `ClaimRisk`, `ResearchRigor` | StrEnums | `education_policy.py` | Canonical taxonomy values shared across strategy/specialists/renderer/exporter/quality/analytics |
| `normalize_subject`, `normalize_language`, `curriculum_framework_for` | Functions | `education_policy.py:73,105,115` | Bounded legacy-literal adapters (e.g. `"maths"` → `SubjectKey.MATH`) — the compatibility seam #462 requires instead of ad hoc branching |

### Dependency plan (#464 ADR-053 Content Orchestrator — partial)

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `DependencyPlan` | Pydantic model (frozen) | `dependency_plan.py` | Versioned generation-wave/dependency structure; validates every dependency references a strictly earlier wave (rejects unknown/same-wave/forward dependencies) |
| `DEFAULT_DEPENDENCY_PLAN` | Constant | `dependency_plan.py` | ADR-053's default plan (Wave 0 lesson → Wave 1 worksheet/quiz/slide_deck/... → Wave 2 recap/answer_key) — consumed directly by `packages/agents/teaching_pack/artifact_fanout.py`, replacing that module's own bare tuples |

### Prerequisite graph (#465 Content Intelligence Graph — partial)

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `PrerequisiteGraph`, `PrerequisiteNode` | Pydantic models (frozen) | `prerequisite_graph.py` | Versioned (`snapshot_version`), immutable node/edge graph of knowledge-component prerequisite relationships. `PrerequisiteNode.access_scope` (`private_teacher`/`organization`/`system`) + `owner_id` mirror the tenant-scope pattern already established for Source Collections (`services/gateway/routers/source_collections.py`) |
| `prerequisite_closure` | Function | `prerequisite_graph.py` | Deterministic, deepest-first closure over one target node; fails closed via `PrerequisiteCycleError`/`PrerequisiteMissingNodeError`/`PrerequisiteScopeConflictError`/`PrerequisiteAccessDeniedError` instead of silently truncating. `visible_access_scopes`/`requester_id` params enforce tenant isolation at every traversal hop, not just the target — a `system`-scoped node requiring a `private_teacher` node owned by someone else raises instead of pulling it into the closure |
| `MisconceptionGraph`, `MisconceptionNode` | Pydantic models (frozen) | `misconception_graph.py` | Versioned, immutable graph of documented misconceptions, each targeting one `knowledge_component_id` and carrying zero or more `ClaimEvidence` (reused from `claim_evidence.py`, not redefined). Same `access_scope`/`owner_id` tenant-isolation fields as `PrerequisiteNode` |
| `retrieve_misconceptions` | Function | `misconception_graph.py` | The second query port #465 names by name ("misconception retrieval"), deterministic (sorted by `misconception_id`) and tenant-scope-checked the same way as `prerequisite_closure`. Also enforces #465's fail-closed evidence rule directly: reuses `claim_evidence.assert_high_risk_claims_are_grounded` per matching node and raises `MisconceptionUngroundedError` (caller-opt-outable via `require_grounded_evidence=False`) instead of silently handing back an unsubstantiated high-risk misconception. An unknown `knowledge_component_id` returns `()`, not an error — no misconceptions documented is a valid result, distinct from a structural defect |
| `ObjectiveDecompositionGraph`, `ObjectiveNode` | Pydantic models (frozen) | `objective_decomposition_graph.py` | Versioned, immutable graph mapping one learning objective to the `knowledge_component_ids` it decomposes into. Same tenant-scope fields as the other two graphs |
| `decompose_objective` | Function | `objective_decomposition_graph.py` | The third query port #465 names by name ("objective decomposition"). Fails closed via `ObjectiveMissingError`/`ObjectiveAccessDeniedError`. Unlike the other two ports, order is the objective's own authored `knowledge_component_ids` sequence (preserved verbatim), not a sort — an objective's decomposition is an authored sequence, not a set with an independent sort key |
| `ExerciseCandidateGraph`, `ExerciseCandidateNode` | Pydantic models (frozen) | `exercise_candidate_graph.py` | Versioned, immutable graph of candidate exercise/task templates, each targeting one `knowledge_component_id` and optionally naming the `misconception_targets` (misconception ids) it surfaces/remediates — the objective/KC/misconception/task-model linkage #465's acceptance criteria ask assessment items to carry |
| `retrieve_exercise_candidates` | Function | `exercise_candidate_graph.py` | The fourth and last query port #465 names by name ("exercise candidates"), deterministic (sorted by `candidate_id`), filterable by `target_misconception_id`, tenant-scope-checked the same way as the other three ports |

**Scope note:** these four query ports (prerequisite closure, misconception retrieval, objective decomposition, exercise candidates) are the full deterministic-query-port list #465 names by name; the fifth, claim evidence, already existed (`claim_evidence.py`, ADR-054). Standards/evidence node contracts already existed too (`subject_capability_pack.py`, `component_strategy_knowledge_models.py`). Still missing from #465's full scope: real MOET/CCSS/NGSS content seeding, the golden query tests across subjects/grade bands, and `make check-content-intelligence`. **None of the four ports is yet wired to a live caller** (no real curriculum content has been authored to back a production integration) — each is tested and correct in isolation, but #465 remains open pending that content.

**Snapshot-version pinning (#465, done this session):** `ContentBrief.knowledge_db_version` and `DecisionProvenance.knowledge_db_version` (both `content_brief.py`/`decision_provenance.py`, optional `str | None`) pin the same `knowledge_db_version` identifier already threaded live through `ComponentStrategyPlan` (`component_strategy.py:187`) and the privacy decision ledger (`component_strategy_privacy.py`) — so a later graph/knowledge-DB version bump never retroactively changes what an already-approved brief or persisted document's provenance meant. `services/gateway/routers/content_briefs.py`'s `CreateContentBriefRequest` accepts it optionally; defaults to `None` for a teacher-authored brief with no graph snapshot behind it.

### Gate/breaker runtime config

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `GateConfig` | Pydantic Settings | `gate_config.py:6` | `GATE_`-prefixed env-driven thresholds (schema retries, judge model/score, HITL timeout, export consensus) — consumed widely across `packages/agents/gates/*`, `packages/agents/healing/*`, `packages/quality` |
| `ProviderCircuitBreaker` | Frozen dataclass | `provider_circuit_breaker.py:14` | Per-provider open/half-open/closed breaker with pluggable `BreakerStore`; consumed by `packages/llm_client/circuit_breaker.py` |

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
`answer_key.py`, `answer_set.py`, `artifact_projection_mapper.py` (#463 V1↔V2 mapper), `class_profile.py`, `content_brief.py`, `decision_provenance.py`, `education_policy.py` (#462 canonical taxonomy), `gate_config.py`, `grade_band.py`, `inverse_thinking.py`, `lesson_sequence.py`, `log_context.py`, `media_asset.py`, `methodology_registry.py`, `objective_lineage.py`, `outcome.py`, `provider_circuit_breaker.py`, `research_brief.py`, `roadmap.py`, `rubric.py`, `seam_contracts.py`, `strategy_review.py`, `subject_capability_pack.py`, `teaching_brief.py`, `teaching_pack_capabilities.py`, `unit_view.py`, `visual_source_suggestion.py`, `vocabulary_batch.py`, `vocabulary_cluster_workflow.py`

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

- **`agents`** — 157 imports across 125 files; ArtifactContent, LessonPlan, JudgeOutput, RunContract, SlideDeckData; `content_orchestrator.py` also calls `artifact_projection_mapper.artifact_document_from_content`/`artifact_content_from_document` (`teaching_pack/content_orchestrator.py:224`)
- **`quality`** — ~20 imports; ArtifactContent, QualityIssue, QualityFailureClass
- **`gateway`** — ~40 imports; RunContract, ArtifactContent, ErrorResponse, User, Token, SlideDeckData; `artifact_document_content_store.py` imports `artifact_projection_mapper` directly (`services/gateway/artifact_document_content_store.py:5`)

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
