# Module: contracts

**Path:** `common/contracts`
**Role:** The single source of truth for all Pydantic v2 data schemas in the monorepo. Every model that validates agent output lives here, not in `packages/agents` or `services/gateway` (INVARIANT-10).

## Public interface

- 120+ Pydantic models exported from `__init__.py`
- `RunContract`, `PipelineMode`, `ArtifactType`, `ExportFormat` (run_contract.py)
- `LessonPlan`, `LearningObjective`, `AssessmentCheckpoint` (lesson_plan.py)
- `ArtifactContent`, `TeachingPack`, `Flashcard`, `FlashcardDeckData` (artifact.py)
- `JudgeOutput`, `LayerScore` (judge_output.py)
- `SlideDeckData` + 15 supporting models (slide_deck.py, 486 lines — largest file)
- `LessonSequence`, `SessionPlan`, `KnowledgeComponent`, `PrerequisiteEdge` (lesson_sequence.py)
- `UnitView`, `UnitAggregate`, `UnitEventEnvelope` (unit_view.py)
- `ComponentStrategyPlan`, `ComponentStrategyResult`, `StrategyVariant`, 15 StrEnums (component_strategy.py + 13 supporting files)
- `ContentComponent` — discriminated union of 22+ component variants (components/__init__.py)
- `METHODOLOGY_REGISTRY` — 10 teaching methodologies (methodology_registry.py)
- `InverseThinkingPack`, `InverseThinkingCase` (inverse_thinking.py)
- `SemanticAnchorCluster`, `LexicalGroundingBundle` + 15 vocabulary models (vocabulary_batch.py, 242 lines)

## Internal structure

### Core Pipeline Contracts (run_contract, artifact, lesson_plan, research_bundle, research_brief, judge_output)
The data shapes passed between pipeline stages. Seam contracts (seam_contracts.py) validate fail-closed transitions.

### Quality & Error Contracts (quality, errors, rubric)
Typed error responses, quality issues, healing decisions, versioned rubrics with SHA-256 content hashing.

### Student & Class Contracts (student_profile, student_response, diagnostic_report, class_profile, outcome)
Privacy-safe learning outcomes (PDPD 13/2023 compliance).

### Artifact-Specific Contracts (slide_deck, roadmap, answer_key, flashcard_deck)
The 10 artifact types' data shapes. Slide deck is by far the most complex (486 lines).

### Component System (components/)
- `textual.py` — 5 types: Heading, Paragraph, Callout, OrderedList, UnorderedList
- `cards.py` — 8 types: StatCard, PatternCard, TraitCard, TaxonomyItem, etc.
- `questions.py` — 2 types: QuestionCard, QuestionList
- `timeline.py` — 5 types: PhaseBlock, FlowItem, FlowStep, etc.
- `concept.py` — 12 types: ConceptNode, ConceptMap, VocabCluster, PhrasalVerbGroup, etc.
- `vocab_lesson.py` — 5 types: FilmClip, RoleplayScript, ActiveRecallPrompt, etc.
- `registry.py` — COMPONENT_REGISTRY (24 entries), PedagogicalIntent (8 values)

### Component Strategy (largest subsystem, 14 files)
`component_strategy.py` + 13 supporting files for the full strategy planning subsystem: modes, statuses, risk levels, knowledge DB integration, slot contracts, fallback validation, MOET support.

### Cross-Cutting Contracts
inverse_thinking, methodology_registry, lesson_sequence, unit_view, seam_contracts, objective_lineage, vocabulary_batch (242 lines), vocabulary_cluster_workflow, log_context, auth.

## Depends on

- **None** (leaf package — INVARIANT-10 enforced)
- external: `pydantic>=2.0.0` (only)

## Used by

- **`agents`** — 147 imports (`teaching_pack/nodes.py`, `sub_agents/*/nodes.py`)
- **`gateway`** — 72 imports (all store/model files)
- **`quality`** — 27 imports (all layer files)
- **`methodologies`** — imports for projection
- **`renderer`** — via generated TypeScript in `common/schemas/`
- **`tests`** — 43 test files, 19 imports

## Data & side effects

- No I/O — pure schema definitions
- 44 test files with golden fixtures (slide deck, component strategy, inverse thinking, vocabulary cluster, seam contracts)

---

_Traced from source on 2026-07-10. Files examined: all 143 files. The largest subsystems are component_strategy (14 files) and slide_deck (486 lines single file)._
