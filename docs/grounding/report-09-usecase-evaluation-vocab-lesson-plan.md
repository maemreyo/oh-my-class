# Grounding Report: Report 09 — Use Case Evaluation: Vocabulary Lesson Plan

**Date**: 2026-06-25  
**Prepared for**: Implementation planning for Report 09 tickets  
**Source Report**: `docs/reports/core/09-usecase-evaluation-vocab-lesson-plan.md` (999 lines)  
**Primary Reference**: `docs/templates/learning-vocab-template.html` (435-line static HTML reference)

---

## 1. Report 09 Summary

**Title**: Use Case Evaluation: Vocabulary Lesson Plan (Concept-Map + Film-Based Methodology)  
**Purpose**: Evaluate whether oh-my-class can produce a detailed vocabulary lesson plan (`giáo án`) for Unit 2: Travel and Transport using concept-map/contrastive-pairs methodology, film-based learning, shy-student-friendly 1-on-1 activities, active recall, and "why options are wrong" reasoning.

### The Use Case

A teacher asks the system to generate an actual detailed lesson plan for Unit 2 vocabulary, not merely an outline. The requested methodology has 6 pedagogical requirements:

| Code | Requirement | Teacher Need |
|---|---|---|
| R1 | Concept-map / contrastive-pairs | Teach vocabulary through semantic mapping and explicit contrast, not rote flashcards |
| R2 | Film-based learning | Use short film clips as context and a vocabulary hunt sheet |
| R3 | Shy-student-friendly 1-on-1 | Scripted, low-pressure roleplay; no public speaking pressure |
| R4 | Active recall via drawing | Student redraws the concept map from memory |
| R5 | Why-wrong reasoning | MCQs explain why each distractor is wrong, plus essence/tip |
| R6 | Rich standalone HTML | Sidebar, hero, film cards, concept maps, contrast tables, phrasal clusters, roleplay, timed quiz, homework |

### Key Grounding Verdict

The system **cannot produce the Report 09 reference lesson today**. However, several Report 09 claims are stale after Report 08 work:

- `question_mc.html` is not a TODO stub; it is a functional 43-line MCQ component.
- `lesson.html` is not a 2-line stub; it is a 54-line partial lesson template rendering objectives, sections, and vocabulary cards.
- Report 08 implementation added useful reusable schema/components (`QuestionCard`, `ConceptMap`, stat/timeline/card components), but Report 09-specific methodology schemas and rich lesson components are still missing.

The grounded status is therefore: **schema foundations are partial, rendering is partial, pedagogy/prompting is missing, and pipeline generation is not wired end-to-end.**

---

## 2. Issue / Tracker Status

No dedicated local issue file for Report 09 was found during this grounding pass. Existing references are primarily:

| Source | Role |
|---|---|
| `docs/reports/core/09-usecase-evaluation-vocab-lesson-plan.md` | Source report and implementation roadmap |
| `docs/templates/learning-vocab-template.html` | Static visual/output target |
| Report 08 components/contracts | Reusable foundation for `QuestionCard`, `ContentComponent`, answer-key/roadmap patterns |

Recommendation: create `.scratch/vocab-lesson-plan/ISSUE.md` or equivalent before implementation, because Report 09 touches schema, renderer, prompt, graph, and quality layers.

---

## 3. Implementation Status Matrix

### 3.1 Pedagogical Requirements

| Req | Status | Grounded Evidence | Verdict |
|---|---|---|---|
| R1 Concept-map / contrastive-pairs | 🟡 Partial | `ConceptMap` exists but only has `nodes`; `comparison_table.html` exists and is reusable; no `edges`, `contrastivePairs`, `VocabCluster`, or phrasal cluster schema | Data foundation exists, methodology does not |
| R2 Film-based learning | ❌ Not done | `roadmap_agent` prompt mentions film learners, but no lesson-level `FilmClip`, `FilmClipActivity`, `film_card`, or `hunt_sheet` schema/template exists | Blocks film warm-up and hunt sheet |
| R3 Shy-student 1-on-1 | 🟡 Partial | `dialogue_completion` exercise type exists; `StudentProfile` exists from Report 08; no `RoleplayScript` lesson component/template | Can model some input, cannot render requested roleplay |
| R4 Active recall drawing | 🟡 Partial | Report 07 mentions `diagram_space`; current code has `ConceptMap` and timeline components, but no `ActiveRecallPrompt` or drawing/self-check component | Needs explicit schema + template |
| R5 Why-wrong reasoning | 🟡 Partial | `QuestionCard` has `wrong_reasons`, `essence`, `tip`; `question_mc.html` renders answer/explain but not per-option wrong reasons/essence/tip | Data exists; lesson MCQ rendering is not rich enough |
| R6 Rich HTML output | 🟡 Partial / mostly missing | `lesson.html` renders objectives, sections, vocabulary; no sidebar/hero/stat grid/film cards/phrasal clusters/roleplay/timed quiz/homework tag components | Needs major template work |

### 3.2 Source File Grounding

| File | Current Reality | Report 09 Claim | Grounded Correction |
|---|---|---|---|
| `common/contracts/lesson_plan.py` | `LessonPlan` has topic, grade, subject, duration, objectives, Gagné-style `learning_plan`, checkpoints | Schema defined | Correct, but no vocabulary methodology fields |
| `common/contracts/components/questions.py` | `QuestionCard` includes `wrong_reasons`, `essence`, `tip` | Data supports why-wrong | Correct |
| `common/contracts/components/concept.py` | `ConceptMap` has only `nodes: list[ConceptNode]` | Too primitive | Correct; no edges/relationships/contrast |
| `common/contracts/artifact.py` | Generic `ArtifactContent` supports `lesson`, `answer_key`, `roadmap`, etc. | Base artifact model | Correct |
| `packages/agents/sub_agents/content_creator/prompts/system.md` | Generic 35-line prompt; no concept-map, film, roleplay, active-recall, or why-wrong methodology | Blocks R1-R5 | Correct |
| `packages/agents/graph.py` | Step 08 remains `_make_dummy_node(8, "generate")` | Content generation not wired | Correct and critical |
| `packages/renderer/templates/pages/lesson.html` | 54-line partial template: objectives, sections, vocabulary grid | Report says 2-line stub | Stale claim; partial implementation exists |
| `packages/renderer/templates/components/question_mc.html` | 43-line WCAG-style MCQ component with radio inputs and explanation | Report says TODO stub | Stale claim; component is functional but not rich why-wrong |
| `packages/renderer/templates/components/concept_map.html` | 8-line node-label renderer | Minimal | Correct |
| `packages/renderer/templates/components/comparison_table.html` | 21-line dynamic table renderer | Reusable for contrasts | Correct |
| `packages/renderer/src/contracts/lesson.ts` | `LessonData` has title, subject, gradeLevel, objectives, sections, vocabulary | Basic lesson renderer contract | Exists, but too simple for Report 09 |
| `common/schemas/src/exercise-types/english.ts` | 19 English exercise types including `vocabulary_scaffolded`, `dialogue_completion`, `collocation`, `matching_vocabulary`, `word_analysis` | Strong exercise schema base | Correct |

---

## 4. Acceptance Criteria Derived From Report 09

| AC | Acceptance Criterion | Status | Evidence / Gap |
|---|---|---|---|
| AC-01 | `LessonPlan` supports methodology metadata (`concept-map`, `contrastive-pairs`, `film-based`, etc.) | ❌ Not done | `LessonPlan` has no methodology fields |
| AC-02 | `ConceptMap` supports edges / semantic relationships | ❌ Not done | `ConceptMap` only has nodes |
| AC-03 | `VocabCluster` / contrastive-pair schema exists | ❌ Not done | No `VocabCluster` or `ContrastivePair` in code |
| AC-04 | `PhrasalVerbCluster` schema exists | ❌ Not done | No matching symbol beyond report text |
| AC-05 | `FilmClip` or `FilmClipActivity` schema exists | ❌ Not done | No lesson-level film schema |
| AC-06 | `RoleplayScript` schema/template exists | ❌ Not done | `dialogue_completion` exists, but no renderer component |
| AC-07 | `ActiveRecallPrompt` or diagram-space drawing prompt exists | ❌ Not done | No current contract/template |
| AC-08 | `QuestionCard` supports wrong reasons, essence, tip | ✅ Done | `questions.py` has all fields |
| AC-09 | Lesson MCQ template renders per-option wrong reasons | ❌ Not done | `question_mc.html` renders only answer/explain |
| AC-10 | `lesson.html` renders objectives, sections, vocabulary | ✅ Basic done | Current template does this |
| AC-11 | `lesson.html` matches `learning-vocab-template.html` shell/sidebar/hero design | ❌ Not done | Current base is single-column; no sticky sidebar |
| AC-12 | Film card + hunt sheet components exist | ❌ Not done | Missing |
| AC-13 | Phrasal verb cluster component exists | ❌ Not done | Missing |
| AC-14 | Roleplay script component with blanks + answer key exists | ❌ Not done | Missing |
| AC-15 | Timed quiz component exists | ❌ Not done | Missing timer/countdown UI |
| AC-16 | Homework list with tags exists | ❌ Not done | Missing dedicated component |
| AC-17 | Content Creator prompt includes Report 09 methodology | ❌ Not done | Current prompt is generic |
| AC-18 | Content Creator is wired into graph step 08 | ❌ Not done | Step 08 is dummy |
| AC-19 | Pedagogical quality gate checks methodology compliance | ❌ Not done | `test_layer2_content.py` is placeholder; no methodology checks |
| AC-20 | Renderer tests cover Report 09 reference-like output | ❌ Not done | Existing lesson tests cover only objectives/sections/vocabulary |

**Score**: 2 done, 1 basic partial, 17 not done.  
**Practical completion**: ~10-15% for the full use case, higher (~35%) for reusable foundations.

---

## 5. Test Status

### Existing Relevant Tests

| Test Area | File | Status | Relevance |
|---|---|---|---|
| LessonPlan Python contract | `common/contracts/tests/test_lesson_plan.py` | ❌ Placeholder only | Does not validate lesson plan schema |
| Content components | `common/contracts/tests/test_components.py` | ✅ Strong | Covers `QuestionCard`, `ConceptMap`, component union |
| Renderer lesson page | `packages/renderer/__tests__/template-library.test.ts` | ✅ Basic | Covers objectives, section content, vocabulary card rendering |
| Renderer quiz/MCQ | `template-library.test.ts`, `question_mc.html` usage | ✅ Basic | Confirms MCQ rendering, radio inputs |
| Content Creator node | `packages/agents/tests/sub_agents/test_content_creator.py` | ✅ Strong generic tests | Validates JSON parsing, schema validation, model route, metadata tags |
| Layer 2 content quality | `packages/quality/tests/test_layer2_content.py` | ❌ Placeholder only | No methodology/age/content-type checks |
| Layer 4 judge | `packages/quality/tests/test_layer4_judge.py` | ✅ Good | G-Eval / majority-vote infrastructure exists |

### Test Gaps

1. No tests for concept-map edges or contrastive-pair semantics.
2. No tests for film-card / hunt-sheet rendering.
3. No tests for roleplay script rendering.
4. No tests for `wrong_reasons` rendering in lesson/MCQ templates.
5. No tests for pedagogical methodology compliance.
6. No end-to-end graph test from teacher request → content creator → lesson HTML.
7. `test_lesson_plan.py` and `test_layer2_content.py` are placeholders.

---

## 6. File Inventory: Exists vs Missing

### Exists and Reusable

| Layer | File | Reuse |
|---|---|---|
| Contract | `common/contracts/lesson_plan.py` | Lesson plan base |
| Contract | `common/contracts/components/questions.py` | Why-wrong data fields |
| Contract | `common/contracts/components/concept.py` | Minimal concept map foundation |
| TS schema | `common/schemas/src/exercise-types/english.ts` | Vocabulary/dialogue/collocation exercise types |
| Renderer | `packages/renderer/templates/pages/lesson.html` | Basic lesson shell |
| Renderer | `packages/renderer/templates/components/question_mc.html` | Basic MCQ component |
| Renderer | `packages/renderer/templates/components/comparison_table.html` | Contrast table foundation |
| Agent | `packages/agents/sub_agents/content_creator/nodes.py` | Content generation node exists |
| Prompt | `packages/agents/sub_agents/content_creator/prompts/system.md` | Needs methodology extension |

### Missing / Needed

| Layer | Needed File / Model | Purpose |
|---|---|---|
| Contract | `ConceptEdge`, extended `ConceptMap` | Semantic relationships and contrastive links |
| Contract | `VocabCluster`, `ContrastivePair` | Contrastive-pairs pedagogy |
| Contract | `PhrasalVerbCluster` | Phrasal verb semantic grouping |
| Contract | `FilmClipActivity` | Film warm-up and hunt sheet |
| Contract | `RoleplayScript` | Shy-student-friendly scripted dialogue |
| Contract | `ActiveRecallPrompt` | Draw-from-memory activity |
| Renderer | `sidebar.eta/html` | Sticky navigation and stats |
| Renderer | `hero.eta/html` | Hero, lede, stat cards, objectives |
| Renderer | `film_card`, `hunt_sheet` | R2 output |
| Renderer | `phrasal_clusters` | R1 output |
| Renderer | `roleplay_script` | R3 output |
| Renderer | `question_card` rich renderer | R5 output |
| Renderer | `timed_quiz` | R6 output |
| Quality | methodology compliance gate | Check output follows requested pedagogy |
| Graph | real step 08 content generation | End-to-end generation |

---

## 7. Dependency Graph

### Critical Path

```text
1. Extend data contracts
   ├─ ConceptMap edges / ContrastivePair / VocabCluster
   ├─ FilmClipActivity + HuntSheet
   ├─ RoleplayScript
   └─ ActiveRecallPrompt
        ↓
2. Extend Content Creator prompt
   ├─ concept-map / contrastive-pairs methodology
   ├─ film-based warm-up
   ├─ shy-student script-based roleplay
   ├─ active recall drawing
   └─ why-wrong reasoning
        ↓
3. Build renderer components
   ├─ shared: sidebar, hero, note_callout, rich question_card
   ├─ vocab-specific: concept_box, contrast_cards, vocab_cards
   ├─ film_card, hunt_sheet
   ├─ phrasal_clusters
   ├─ roleplay_script, timed_quiz, hw_list
   └─ full lesson page composition
        ↓
4. Wire step_08_generate to real Content Creator
        ↓
5. Add methodology quality gates + tests
        ↓
6. E2E test: teacher request → lesson artifact → standalone HTML
```

### Parallelizable Work

| Workstream | Can Start After | Notes |
|---|---|---|
| Contract extensions | Immediately | Defines JSON shape for everything else |
| Shared templates (`sidebar`, `hero`, `note_callout`) | Immediately | Shared with Reports 08/09 |
| Rich `question_card` renderer | After confirming `QuestionCard` shape | Shared with answer key and vocab lesson |
| Film/hunt templates | After `FilmClipActivity` schema | Independent of concept map work |
| Roleplay template | After `RoleplayScript` schema | Independent of film work |
| Quality gate | After prompt + schema definitions | Needs final expected fields |

---

## 8. Research Grounding Notes

Report 09's pedagogy direction is plausible and aligned with common EFL teaching practice, but the research-backed recommendations should be encoded as data contracts rather than freeform prompt prose.

### Concept Maps / Contrastive Pairs

Report 09 correctly identifies that the current `ConceptMap` is too weak. For vocabulary teaching, a useful concept graph needs at minimum:

- nodes with word/phrase metadata
- edges with relationship type (`synonymy`, `collocation`, `contrast`, `register`, `part-of`, etc.)
- explicit contrastive pairs with a discrimination prompt
- active recall task metadata

Current implementation only stores `{id, label}` nodes.

### Film-Based Learning

Report 09 asks for film clip recommendations plus vocabulary spotting. This is not equivalent to existing `multimedia_video`, which is described as student-produced media/homework. The needed shape is closer to:

```typescript
interface FilmClipActivity {
  title: string
  sourceLabel?: string
  sceneDescription: string
  vocabularyChips: string[]
  watchPrompts: string[]
  postViewingQuestions: string[]
}
```

No equivalent exists today.

### Scripted Roleplay for Shy Learners

`dialogue_completion` is a good foundation because it has speaker turns and blanks. But the requested lesson output needs presentation-specific fields: character labels, blank rendering, scaffolding level, answer key, and low-pressure instructions.

### Why-Wrong Reasoning

The data model exists (`wrong_reasons`, `essence`, `tip`), but the current MCQ component renders only answer/explanation. Report 09's original claim that the component is empty is false, but the desired per-option reasoning still is not implemented in the lesson renderer.

---

## 9. Implementation Roadmap

### Phase 0 — Correct the Report 09 Baseline (0.5 day)

Update implementation issue text to reflect current code reality:

- `question_mc.html` is functional, not a TODO stub.
- `lesson.html` is partial, not a 2-line stub.
- `QuestionCard` already has `wrong_reasons`, `essence`, `tip`.
- `StudentProfile` exists from Report 08 and can support shy/film learner context.

### Phase 1 — Schema and Contract Extensions (4-5 days)

| Task | Effort | Output |
|---|---:|---|
| Extend `ConceptMap` with edges and relationship metadata | 1 day | `ConceptEdge`, relationship enum |
| Add `VocabCluster` / `ContrastivePair` | 1 day | First-class contrastive-pairs model |
| Add `PhrasalVerbCluster` | 0.5 day | Semantic phrasal verb groups |
| Add `FilmClipActivity` / hunt sheet | 1 day | Film warm-up data contract |
| Add `RoleplayScript` and `ActiveRecallPrompt` | 1-1.5 days | R3/R4 contracts |

### Phase 2 — Content Creator Methodology Prompt (1-2 days)

Extend `content_creator/prompts/system.md` with:

- concept-map/contrastive-pairs rules
- film-based warm-up rules
- shy-student 1-on-1 constraints
- active recall drawing pattern
- why-wrong MCQ output expectations
- required JSON component shapes

Add prompt tests that assert those methodology terms appear.

### Phase 3 — Renderer Components (8-10 days)

| Component | Priority | Notes |
|---|---|---|
| `sidebar` | P0 | Shared across Report 08/09 |
| `hero` / stat grid | P0 | Shared across Report 08/09 |
| rich `question_card` | P0 | Must render wrong reasons, essence, tip |
| `concept_box`, `contrast_cards`, `vocab_cards` | P0 | Core R1 output |
| `film_card`, `hunt_sheet` | P1 | R2 output |
| `phrasal_clusters` | P1 | R1 phrasal verb output |
| `roleplay_script` | P1 | R3 output |
| `timed_quiz`, `hw_list`, `section_head` | P2 | R6 polish/completeness |
| full `lesson.html` rewrite | P0 | Compose all components into reference-like page |

### Phase 4 — Pipeline Integration (2 days)

Replace `step_08_generate` dummy node in `packages/agents/graph.py` with the real Content Creator adapter/node, preserving graph invariants and fail-closed behavior.

### Phase 5 — Quality Gates and Tests (4-5 days)

| Area | Required Tests |
|---|---|
| Contracts | Invalid edge types, missing contrast dimensions, malformed film activities |
| Renderer | Reference-like vocab lesson render, no external assets, print/mobile behavior |
| Prompt | Methodology rules included |
| Quality | Checks for R1-R5 presence in output |
| E2E | Teacher request → lesson artifact → standalone HTML |

### Total Estimate

**Grounded estimate: 20-24 days**, not 25-30, because some renderer foundations are already implemented. If pixel-level parity with `learning-vocab-template.html` is required, add 3-5 days for visual QA and responsive polish.

---

## 10. Risk Assessment

| Risk | Probability | Impact | Evidence | Mitigation |
|---|---|---|---|---|
| Pipeline still cannot generate real artifacts | High | High | `step_08_generate` is dummy | Wire Content Creator before claiming E2E support |
| Prompt-only methodology may drift | High | Medium | Current schema has no methodology fields | Encode methodology in schemas + quality gates |
| Template scope creep | Medium | High | Reference has 15+ visual patterns | Prioritize P0 shared components first |
| TS/Python schema drift | Medium | High | Python `ContentComponent` richer than TS `LessonData` | Add TS/Zod runtime schemas or generated schemas |
| Quality gates miss pedagogy | High | Medium | `test_layer2_content.py` placeholder | Implement content-type methodology checks |
| External asset temptation | Medium | Medium | Reference uses Google Fonts; project forbids CDN | Use system fonts and inline CSS only |
| Hardcoded Vietnamese strings | Medium | Low | `lesson.html` has Vietnamese labels inline | Add locale-aware labels later |

---

## 11. Recommendations

### Immediate Priority

1. Create a Report 09 implementation issue from this grounded matrix.
2. Fix Report 09 stale claims before implementation starts.
3. Wire step 08 only after contract/prompt expectations are decided.

### Build Order

Do not begin with the full visual template. Start with the typed JSON shape:

1. Contracts for concept/film/roleplay/active recall.
2. Prompt instructions to produce those shapes.
3. Minimal renderer components for those shapes.
4. Then visual parity with the static HTML reference.

### Acceptance Standard

Report 09 should be considered done only when a single test fixture can render a standalone HTML lesson containing:

- film warm-up + hunt sheet
- concept-map/contrastive-pair section
- phrasal verb clusters
- guided MCQs with per-option wrong reasons
- timed quiz section
- roleplay script with blanks and answer key
- homework list with Google Classroom instruction
- no external assets
- responsive + print-safe output

---

## 12. Final Verdict

**Current status**: Not implemented end-to-end.  
**Feasibility**: High.  
**Main blocker**: Template + prompt + graph wiring, not new agent architecture.  
**Implementation size**: Medium-large, ~20-24 days grounded effort.  
**Most important correction to Report 09**: the renderer is less empty than the report states (`lesson.html` and `question_mc.html` are partial/functional), but still far from the 435-line reference lesson output.

Report 09 remains a valid direction, but implementation should be scoped as a typed lesson-component system rather than a one-off vocabulary template.
