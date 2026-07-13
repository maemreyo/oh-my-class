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

### Content Intelligence Graph package (#465 — partial)

`common/contracts/content_intelligence_graph/` — package-owned home unifying the
four deterministic graph/query-port modules built incrementally across prior
#465 sessions (previously flat files directly under `common/contracts/`),
plus three new node/edge contracts and shared snapshot-versioning/uniqueness
machinery added this session. `content_intelligence_graph/__init__.py`
re-exports everything below (including `ClaimEvidence`, `CurriculumStandard`,
etc. from where they already live) as one importable surface — nothing was
duplicated to build the unified surface, only re-exported.

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `PrerequisiteGraph`, `PrerequisiteNode` | Pydantic models (frozen) | `prerequisite.py` | Versioned (`snapshot_version`), immutable node/edge graph of knowledge-component prerequisite relationships. `PrerequisiteNode.access_scope` (`private_teacher`/`organization`/`system`) + `owner_id` mirror the tenant-scope pattern already established for Source Collections (`services/gateway/routers/source_collections.py`). Rejects duplicate `node_id`s (`DuplicateNodeIdError` via `snapshot.py`) |
| `prerequisite_closure` | Function | `prerequisite.py` | Deterministic, deepest-first closure over one target node; fails closed via `PrerequisiteCycleError`/`PrerequisiteMissingNodeError`/`PrerequisiteScopeConflictError`/`PrerequisiteAccessDeniedError` instead of silently truncating. `visible_access_scopes`/`requester_id` params enforce tenant isolation at every traversal hop, not just the target |
| `MisconceptionGraph`, `MisconceptionNode` | Pydantic models (frozen) | `misconception.py` | Versioned, immutable graph of documented misconceptions, each targeting one `knowledge_component_id` and carrying zero or more `ClaimEvidence` (reused from `claim_evidence.py`, not redefined). Rejects duplicate `misconception_id`s |
| `retrieve_misconceptions` | Function | `misconception.py` | Deterministic (sorted by `misconception_id`), tenant-scope-checked; reuses `claim_evidence.assert_high_risk_claims_are_grounded` and raises `MisconceptionUngroundedError` instead of silently handing back an unsubstantiated high-risk misconception |
| `ObjectiveDecompositionGraph`, `ObjectiveNode` | Pydantic models (frozen) | `objective_decomposition.py` | Versioned, immutable graph mapping one learning objective to the `knowledge_component_ids` it decomposes into. Rejects duplicate `objective_id`s |
| `decompose_objective` | Function | `objective_decomposition.py` | Fails closed via `ObjectiveMissingError`/`ObjectiveAccessDeniedError`. Order is the objective's own authored `knowledge_component_ids` sequence, preserved verbatim |
| `ExerciseCandidateGraph`, `ExerciseCandidateNode` | Pydantic models (frozen) | `exercise_candidate.py` | Versioned, immutable graph of candidate exercise/task templates, each targeting one `knowledge_component_id` and optionally naming `misconception_targets` — the objective/KC/misconception/task-model linkage #465's acceptance criteria ask assessment items to carry. Rejects duplicate `candidate_id`s |
| `retrieve_exercise_candidates` | Function | `exercise_candidate.py` | Deterministic (sorted by `candidate_id`), filterable by `target_misconception_id`, tenant-scope-checked |
| `TerminologyGraph`, `TerminologyNode`, `retrieve_terminology` | Pydantic models + function (frozen) | `terminology.py` | **New this session.** Bilingual term catalog tied to a `knowledge_component_id` — #465's Scope names "terminology" as a node type needing a contract; `ContentBrief.terminology` was previously just `list[str]` with no source node behind it. Same versioning/tenant-isolation/uniqueness/determinism conventions as the four graphs above |
| `ExampleGraph`, `ExampleNode`, `retrieve_examples` | Pydantic models + function (frozen) | `example.py` | **New this session.** Worked-example catalog tied to a `knowledge_component_id`. Same conventions |
| `TaskModelCatalog`, `TaskModelNode`, `lookup_task_model` | Pydantic models + function (frozen) | `task_model.py` | **New this session.** Flat catalog of valid task-model formats (`ExerciseCandidateNode.task_model` was already a live free-text field; this is its declared-value catalog). Unlike the per-KC ports, an undeclared task model fails closed (`TaskModelMissingError`) rather than returning an empty result — a candidate must reference a real, catalogued format |
| `compute_snapshot_version`, `assert_unique_node_ids`, `DuplicateNodeIdError` | Functions/error | `snapshot.py` | **New this session.** `compute_snapshot_version` derives a graph's `snapshot_version` deterministically (sha256 over canonicalized node JSON, order-independent) instead of a manually-chosen label — the issue's "version graph snapshots deterministically (hash-based)" ask. `assert_unique_node_ids` is the shared uniqueness check wired into all seven graph/catalog models above |
| `CurriculumAlignmentRecord`, `assert_alignment_is_grounded` | Pydantic model + function (frozen) | `alignment.py` | **New this session.** Links a `knowledge_component_id` to a versioned `CurriculumStandard` (`subject_capability_pack.py`) via a `ClaimEvidence` (`claim_evidence.py`) — the acceptance criterion "every claimed curriculum alignment resolves to a versioned source node and evidence record". `assert_alignment_is_grounded` applies the same ADR-054 fail-closed rule as `MisconceptionUngroundedError` |
| `seeds/ccss_math_sample.py` | Data module | `seeds/ccss_math_sample.py` | **New this session — small, honest sample, not a certified catalog.** 5 real CCSS Math standard codes (verified against the public corestandards.org text) wired to 5 knowledge components via `CurriculumAlignmentRecord`, plus an illustrative `PrerequisiteGraph` sequencing them across grades 3-7. Covers one framework out of the three the issue names (MOET 2018, NGSS unseeded — no reliable source text available this session; fabricating codes was rejected as worse than an explicit TODO) |

**Scope note:** the five deterministic query ports #465 names by name (prerequisite closure, misconception retrieval, objective decomposition, exercise candidates, claim evidence) all exist. Standards/evidence node contracts (`subject_capability_pack.py`, `component_strategy_knowledge_models.py`) and now terminology/example/task-model contracts all exist and are unified under one package. Still missing from #465's full scope: MOET 2018 and NGSS content seeding (CCSS Math has a small 5-record sample only), golden query tests across all four subjects × all four grade bands using literal graph traversal (the existing `test_*_capability_pack_release_gate.py` golden tests check standards/misconceptions query *results*, not these graph ports), and a live production caller for any of the graph ports (still no real curriculum content backs a pipeline integration — the CCSS Math sample is reviewed and tested but not wired into a specialist/orchestrator flow).

**Snapshot-version pinning:** `ContentBrief.knowledge_db_version` and `DecisionProvenance.knowledge_db_version` (both `content_brief.py`/`decision_provenance.py`, optional `str | None`) pin the same `knowledge_db_version` identifier already threaded live through `ComponentStrategyPlan` (`component_strategy.py:187`) and the privacy decision ledger (`component_strategy_privacy.py`) — so a later graph/knowledge-DB version bump never retroactively changes what an already-approved brief or persisted document's provenance meant. `services/gateway/routers/content_briefs.py`'s `CreateContentBriefRequest` accepts it optionally; defaults to `None` for a teacher-authored brief with no graph snapshot behind it. `test_content_brief_and_decision_provenance_pin_the_same_graph_snapshot` (`common/contracts/tests/content_intelligence_graph/test_ccss_math_sample.py`) is the live-path proof this session added: a `ContentBrief` and a `DecisionProvenance` built from the same seeded snapshot pin the identical `knowledge_db_version` and cite the identical evidence id. `make check-content-intelligence` (new this session) runs this package's full test suite.

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
