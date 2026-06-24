# 09 — Use Case Evaluation: Vocabulary Lesson Plan (Concept-Map + Film-Based Methodology)

> **Date**: 2026-06-24
> **Evaluated by**: Sisyphus (4 parallel explore agents + direct codebase analysis)
> **Scope**: Can oh-my-class produce a detailed vocabulary lesson plan (giáo án) following concept-map/contrastive-pairs methodology with film-based learning, shy-student-friendly 1-on-1, active recall, and "why options are wrong" reasoning?
> **References**:
> - `docs/templates/learning-vocab-template.html` (435-line static HTML reference)
> - `docs/reports/core/08-usecase-evaluation-answer-key.md` (prior evaluation)

---

## Table of Contents

1. [The Use Case](#1-the-use-case)
2. [Current System Capabilities](#2-current-system-capabilities)
3. [Gap Analysis](#3-gap-analysis)
4. [Template Reference Analysis](#4-template-reference-analysis)
5. [What Exists That We Can Leverage](#5-what-exists-that-we-can-leverage)
6. [What Needs to Be Built](#6-what-needs-to-be-built)
7. [Recommendation](#7-recommendation)
8. [Research: Concept-Map / Contrastive-Pairs](#8-research-findings-development-directions)
9. [Research: Film-Based Learning](#9-research-findings-film-based-learning)
10. [Research: Scripted Roleplay](#10-research-findings-scripted-roleplay-for-shy-learners)
11. [Research: "Why Wrong" Reasoning](#11-research-findings-why-wrong-reasoning-in-assessment)
12. [Research: Phrasal Verb Clustering](#12-research-findings-phrasal-verb-clustering)
13. [Updated Development Roadmap](#13-updated-development-roadmap)

---

## 1. The Use Case

The teacher's workflow (verbatim):

```
Create a lesson plan for teaching this Unit 2 vocabulary (Travel and transport) following my suggested methodology:

1. Concept-map / contrastive-pairs approach (not rote flashcards)
   - Since "Topic vocabulary in contrast" section already exists in this unit naturally!
2. Film-based learning component (use short film clips for context)
3. 1-on-1 shy-student-friendly approach (no public speaking pressure, light roleplay)
4. Active recall via the student drawing back the concept map themselves
5. Teaching với "why options are wrong" reasoning style
6. Lesson structure: warm-up (film clip) → teach new concept (concept map/contrastive) → guided practice → timed quiz → review & homework

This is a content-creation task — build an actual detailed LESSON (giáo án)
for this specific Unit 2: Travel and Transport, using my own methodology.
```

**Reference output**: `learning-vocab-template.html` — a 435-line standalone HTML document with:

| Element | Description |
|---|---|
| Sticky sidebar | Navigation, stats (time, phase, error reference), section links |
| Hero section | Eyebrow, title, lede, note box, stat grid (4 cards), learning objectives |
| Section 1: Warm-up (phim) | Film options (2 films), "hunt sheet" with vocabulary chips |
| Section 2: Concept map & clusters | Contrastive pairs (arrive/reach/enter), 5-word vocabulary set, rapid-fire comparison table, phrasal verb clusters (5 groups × 3-4 items) |
| Section 3: Guided practice | 10 MCQ questions with full answer + "why wrong" explanations per option |
| Section 4: Timed quiz | 5 questions in exam format, timed |
| Section 5: Roleplay | Fill-in-the-blank dialogue script with answer key |
| Section 6: Homework | Tagged homework list with Google Classroom instructions |

**Decomposed into 6 pedagogical requirements:**

| # | Requirement | Description |
|---|---|---|
| R1 | **Concept-map/contrastive-pairs** | Teach vocabulary via semantic mapping and contrast (not flashcard drilling) |
| R2 | **Film-based learning** | Use film clips as warm-up context, with a "hunt sheet" for vocabulary spotting |
| R3 | **Shy-student-friendly 1-on-1** | Script-based roleplay (read, don't improvise), no public speaking, low-pressure activities |
| R4 | **Active recall via drawing** | Student redraws concept map from memory as review |
| R5 | **"Why wrong" reasoning** | Every MCQ shows why each wrong option is wrong, not just the correct answer |
| R6 | **Rich HTML output** | Standalone HTML with sidebar, concept maps, phrasal verb clusters, roleplay scripts, timed quiz |

---

## 2. Current System Capabilities

### What oh-my-class CAN do today

| Capability | Evidence | Maturity |
|---|---|---|
| LessonPlan schema | `common/contracts/lesson_plan.py` — topic, grade, Bloom objectives, Gagné phases | ✅ Schema defined |
| UbD backward design | `skills/blueprint-designer/SKILL.md` — UbD + Gagné + Bloom | ✅ Skill defined |
| 50+ exercise types | `common/schemas/src/exercise-types/` — MC, TF, cloze, vocabulary_scaffolded, dialogue_completion, collocation, etc. | ✅ Schema defined |
| Vocabulary-specific types | `english.ts` — `vocabulary_scaffolded` (4-stage), `matching_vocabulary`, `collocation`, `word_analysis` | ✅ Schema defined |
| `wrong_reasons` on QuestionCard | `common/contracts/components/questions.py` — per-option wrong-reason field | ✅ Schema defined |
| `dialogue_completion` exercise type | `english.ts` — speaker turns + blanks with expected intent | ✅ Schema defined |
| Teacher approval gates | LangGraph `interrupt()` at 2 points | ✅ Implemented |
| Quality gate system (6 layers) | `packages/quality/` — schema, content, HTML, judge, human, export | ✅ Partially implemented |
| Standalone HTML rendering | `packages/renderer/` — Eta templates, CSS inlining, no CDN | ⚠️ Scaffold (stubs) |
| Flashcard deck template | `pages/flashcard_deck.html` + `FlashcardDeckData` | ✅ Implemented |
| Concept map component | `components/concept_map.html` — nodes with labels | ⚠️ Minimal (8 lines) |
| Comparison table component | `components/comparison_table.html` — dynamic columns/rows | ✅ Implemented |

### What oh-my-class CANNOT do today

| Missing Capability | Evidence | Impact |
|---|---|---|
| **Pedagogical methodology in prompts** | Content Creator `system.md` (35 lines) has zero instructions about concept-maps, contrastive pairs, film-based learning, or any specific teaching approach | 🔴 Blocks R1, R2, R3, R4, R5 |
| **Lesson template (giáo án)** | `pages/lesson.html` is 2 lines — just title + objective count. Doesn't render sections, vocabulary, or any structured content | 🔴 Blocks R6 |
| **Sidebar navigation** | No sidebar component exists. `base.html` is single-column: header → main → footer | 🔴 Blocks R6 |
| **Film/video integration** | No schema field for media references, film clips, or "watch and answer" activities. `multimedia_video` is for student recording, not content viewing | 🔴 Blocks R2 |
| **Roleplay/dialogue components** | No dialogue script component. `dialogue_completion` exercise type exists but no template renders it as a fill-in-blank script | 🔴 Blocks R3 |
| **Active recall drawing prompts** | No `diagram_space` block or "draw from memory" instruction type | 🟡 Blocks R4 |
| **Phrasal verb cluster component** | No contract or component for grouping phrasal verbs by semantic cluster | 🟡 Blocks R1 |
| **Rich question rendering** | `question_mc.html` is a TODO stub (empty body). `wrong_reasons` data exists but can't be rendered | 🔴 Blocks R5 |
| **Vocabulary rendering** | `LessonData` has `vocabulary?: VocabEntry[]` but the lesson template ignores it. No vocabulary card component | 🔴 Blocks R1 |
| **Timed quiz component** | No timer/countdown UI component. Quiz template is 2 lines | 🟡 Blocks R6 |
| **Pedagogical quality gate** | No gate checks whether content follows the requested teaching methodology | 🟡 Blocks quality |

---

## 3. Gap Analysis

### R1: Concept-Map / Contrastive-Pairs Approach

**What the teacher needs:**
- Vocabulary taught via semantic mapping (e.g., "arrive/reach/enter" contrasted by meaning, grammar, usage)
- Visual concept maps showing relationships between vocabulary clusters
- Rapid-fire comparison tables (e.g., "fare vs ticket vs fee")
- Phrasal verbs grouped by semantic cluster (not alphabetical)
- Active recall: student redraws the concept map from memory

**What exists:**
- `ConceptMap` contract (basic: nodes with id + label — no edges, no relationships, no contrast)
- `concept_map.html` template (8 lines: just renders node labels)
- `comparison_table.html` component (dynamic columns/rows — usable but untested)
- `vocabulary_scaffolded` exercise type (4-stage: recognition → comprehension → sentence → paragraph production)
- `matching_vocabulary` exercise type (definition/synonym/antonym matching)
- `collocation` exercise type (verb-noun, adjective-noun pairings)

**Gap: 🔴 CRITICAL**

The system has no concept of "teaching vocabulary via contrastive pairs." The `ConceptMap` contract is too primitive (nodes only, no edges/relationships). The content creator prompt has no instructions about contrastive pedagogy. The lesson template can't render concept maps, comparison tables, or phrasal verb clusters in a structured way.

### R2: Film-Based Learning

**What the teacher needs:**
- Film clip recommendations (e.g., "Up in the Air" opening, "The Holiday" opening)
- A "hunt sheet" with vocabulary chips to spot while watching
- Post-film discussion questions (low-pressure, pointing at checklist)

**What exists:**
- `multimedia_video` exercise type — but this is for **student recording**, not content viewing
- No schema for "teacher provides film clip → student watches → answers questions"
- No template for film recommendation cards or hunt sheets

**Gap: 🔴 CRITICAL**

The system has zero infrastructure for film-based content. There's no schema, no template, no component for embedding film references or creating watch-and-answer activities. This is a fundamentally new content type that doesn't exist in the exercise type catalog.

### R3: Shy-Student-Friendly 1-on-1

**What the teacher needs:**
- Script-based roleplay (read the script, don't improvise)
- Fill-in-the-blank dialogue with answer key
- No public speaking pressure
- Low-stakes activities (pointing at checklists, filling in blanks)

**What exists:**
- `dialogue_completion` exercise type (speaker turns + blanks with expected intent) — **closest match**
- No template renders dialogue scripts as fill-in-the-blank roleplay
- `DifferentiationGuide` schema exists in `.scratch/educational-content-research/ISSUE.md` (forStruggling, forAdvanced, forELL) — but **NOT implemented** in `common/contracts/`
- No student profile model (shy, film-based learner, etc.)

**Gap: 🟡 PARTIAL**

The `dialogue_completion` exercise type could serve as the data model for roleplay scripts, but there's no template that renders it as a fill-in-the-blank dialogue with character labels and answer keys. The differentiation/personalization infrastructure is spec'd but not built.

### R4: Active Recall via Drawing

**What the teacher needs:**
- Instruction: "Draw the concept map from memory"
- Blank space or structured prompt for the student to recreate the map
- Self-check against the original

**What exists:**
- `drawing` exercise type (canvas-based) — could theoretically support this
- No template for "draw from memory" prompts
- No self-check mechanism

**Gap: 🟡 PARTIAL**

The `drawing` exercise type exists but there's no pedagogical wrapper for "active recall via drawing." The template would need a simple instruction block + blank space + self-check prompt.

### R5: "Why Options Are Wrong" Reasoning

**What the teacher needs:**
- Every MCQ shows: correct answer + why A is wrong + why B is wrong + why C is wrong + why D is wrong
- "Bản chất" (essence) of the question
- "Mẹo làm bài" (test-taking tip)

**What exists:**
- `QuestionCard` contract has `wrong_reasons: dict[str, str] | None` — **data model supports it**
- `answer_key.html` reference template (1067 lines) has full wrongReasons rendering — **but not implemented in Eta templates**
- `question_mc.html` template is a TODO stub (empty body)

**Gap: 🟡 PARTIAL (data exists, rendering doesn't)**

The data model can represent everything needed. The reference template shows exactly how it should look. But the Eta template `question_mc.html` is empty, so the data can be generated by the LLM but never rendered to HTML.

### R6: Rich HTML Output (Sidebar, Concept Maps, Phrasal Verbs, Roleplay, Timed Quiz)

**What the teacher needs:**
A single standalone HTML file with:
- Sticky sidebar with navigation, stats, section links
- Hero section with learning objectives
- Multiple content sections with different visual treatments
- Concept map visualization
- Phrasal verb cluster cards (color-coded by semantic group)
- Practice questions with wrong-reason explanations
- Roleplay dialogue scripts with fill-in-the-blank
- Timed quiz section
- Homework list with tags

**What exists:**
- `base.html` shell (single-column, no sidebar)
- 10 page templates (most are 2-line stubs)
- 15 component templates (6 are TODO stubs)
- 3 theme variants (default, ocean, forest)
- CSS custom properties system

**What's missing for this specific template:**

| Component | Needed | Exists? |
|---|---|---|
| Sidebar with nav | Yes | ❌ No sidebar component |
| Hero with stat grid | Yes | ❌ No hero component |
| Concept map (contrastive) | Yes | ⚠️ Minimal (nodes only) |
| Phrasal verb clusters | Yes | ❌ No component |
| MCQ with wrong-reasons | Yes | ❌ `question_mc.html` is TODO |
| Roleplay script | Yes | ❌ No component |
| Timed quiz | Yes | ❌ No timer component |
| Homework list with tags | Yes | ❌ No component |
| Section with time badge | Yes | ❌ No component |
| Note/callout boxes | Yes | ❌ No component |

**Gap: 🔴 CRITICAL**

The current template system cannot produce anything close to the reference template. The `learning-vocab-template.html` uses ~15 distinct CSS component patterns (sidebar, hero, stat-grid, concept-box, tri-card, fiveset, quickpairs table, pv-clusters, pq question cards, script dialogue, hw-list, note-callout, huntsheet, chip-list, section-head with time badge) — **none of which exist as Eta components today**.

---

## 4. Template Reference Analysis

### 4.1 `learning-vocab-template.html` — Vocabulary Lesson Plan (435 lines)

A **static HTML reference** for a complete vocabulary teaching session. Contains:

| Element | Lines | CSS Pattern | Description |
|---|---|---|---|
| CSS variables | 10-25 | `:root` | Paper/card/ink colors, 5 group colors, radius, shadow |
| Shell layout | 37-39 | `.shell`, `.sidebar`, `.main` | Flexbox: 252px sticky sidebar + fluid main |
| Sidebar | 41-58 | `.side-title`, `.side-stat`, `.side-nav` | Logo, title, subtitle, 3 stat cards, nav links, linkback |
| Hero | 60-78 | `.hero`, `.eyebrow`, `.lede`, `.note-box`, `.stat-grid`, `.obj-card` | Eyebrow label, title, lede paragraph, note box, 4 stat cards, objectives list |
| Film options | 91-96 | `.film-opt`, `.film-card` | 2-column grid of film recommendations |
| Hunt sheet | 96-99 | `.huntsheet`, `.chiplist`, `.chip` | Vocabulary chip checklist for film viewing |
| Concept box | 102-110 | `.concept-box`, `.cb-title`, `.cb-link` | Bordered card with title + link + content |
| Tri-card grid | 105-110 | `.tri`, `.tri-card` | 3-column contrast cards (arrive/reach/enter) |
| Five-set grid | 112-115 | `.fiveset`, `.fcard` | 5-column vocabulary cards (voyage/journey/trip/travel/excursion) |
| Quickpairs table | 117-120 | `.quickpairs` | Dark-header comparison table (fare/ticket/fee, miss/lose, view/sight) |
| Phrasal verb clusters | 122-133 | `.pv-clusters`, `.pv-cluster`, `.pv1`-`.pv5` | 2-column grid of color-coded semantic clusters |
| Practice questions | 136-142 | `.pq`, `.pq-n`, `.pq-text`, `.pq-opts`, `.pq-ans`, `.pq-why` | Question cards with number badge, text, options, answer, wrong-reason explanation |
| Roleplay script | 145-152 | `.script`, `.line`, `.who`, `.what`, `.blank`, `.script-key` | Dialogue with character labels, blank spaces, answer key |
| Note callout | 154-155 | `.note-callout` | Gold-bordered tip box |
| Homework list | 157-159 | `.hw-list`, `.hwtag` | Tagged homework items |
| Responsive | 164-168 | `@media (max-width:880px)` | Sidebar collapses to top on mobile |

### 4.2 Comparison with Existing Template System

| Feature | `learning-vocab-template.html` | Current Renderer | Gap |
|---|---|---|---|
| **Layout** | Sidebar + main (flexbox) | Single-column (header → main → footer) | 🔴 No sidebar layout |
| **Typography** | Spectral (headings), Be Vietnam Pro (body), IBM Plex Mono (labels) | System font stack only (INVARIANT-04) | 🟡 Must use system fonts |
| **Color system** | Paper/card/ink + 5 group colors + tints | Theme tokens (`--color-primary`, etc.) | 🟡 Different token naming |
| **Components** | 15+ distinct patterns | 9 working + 6 TODO components | 🔴 Most patterns missing |
| **Data model** | Hardcoded HTML (no data binding) | Eta templates with `it.` variables | 🟡 Need to define data contracts |
| **External assets** | Google Fonts (CDN) | No CDN allowed (INVARIANT-04) | 🟡 Violates invariant — must remove |

### 4.3 New Components Needed

To render a document like `learning-vocab-template.html`, the following **new Eta components** are needed:

| # | Component | CSS Pattern | Complexity |
|---|---|---|---|
| 1 | `sidebar.eta` | `.shell > .sidebar` (sticky nav, stats, links) | High |
| 2 | `hero.eta` | `.hero` (eyebrow, title, lede, note-box, stat-grid, obj-card) | High |
| 3 | `concept_box.eta` | `.concept-box` (bordered card with title + content) | Medium |
| 4 | `contrast_cards.eta` | `.tri` / `.tri-card` (3-column comparison grid) | Medium |
| 5 | `vocab_cards.eta` | `.fiveset` / `.fcard` (5-column vocabulary grid) | Medium |
| 6 | `quickpairs_table.eta` | `.quickpairs` (dark-header comparison table) | Low |
| 7 | `phrasal_clusters.eta` | `.pv-clusters` / `.pv-cluster` (color-coded semantic groups) | Medium |
| 8 | `question_card.eta` | `.pq` (number badge, text, options, answer, why-wrong) | High |
| 9 | `roleplay_script.eta` | `.script` (character labels, blanks, answer key) | Medium |
| 10 | `film_card.eta` | `.film-opt` / `.film-card` (film recommendation cards) | Low |
| 11 | `hunt_sheet.eta` | `.huntsheet` / `.chiplist` / `.chip` (vocabulary chip checklist) | Low |
| 12 | `note_callout.eta` | `.note-callout` (gold-bordered tip box) | Low |
| 13 | `hw_list.eta` | `.hw-list` / `.hwtag` (tagged homework items) | Low |
| 14 | `section_head.eta` | `.section-head` (title + time badge) | Low |

---

## 5. What Exists That We Can Leverage

### Reusable contracts and schemas

| Component | Location | Reuse for |
|---|---|---|
| `LessonPlan` schema | `common/contracts/lesson_plan.py` | Base for lesson plan data model |
| `LearningObjective` + `bloom_level` | `common/contracts/lesson_plan.py` | Learning objectives with Bloom tagging |
| `ArtifactContent` model | `common/contracts/artifact.py` | Base for lesson artifact type |
| `QuestionCard` with `wrong_reasons` | `common/contracts/components/questions.py` | "Why wrong" reasoning data model |
| `ConceptMap` (basic) | `common/contracts/components/concept.py` | Foundation for concept map (needs extension) |
| `vocabulary_scaffolded` type | `common/schemas/src/exercise-types/english.ts` | 4-stage vocabulary teaching sequence |
| `dialogue_completion` type | `common/schemas/src/exercise-types/english.ts` | Roleplay script data model |
| `collocation` type | `common/schemas/src/exercise-types/english.ts` | Phrasal verb / collocation data |
| `matching_vocabulary` type | `common/schemas/src/exercise-types/english.ts` | Contrastive pair matching |
| `comparison_table.html` | `packages/renderer/templates/components/` | Reusable for contrastive pairs |
| `concept_map.html` (basic) | `packages/renderer/templates/components/` | Foundation for concept map rendering |
| Quality gate system | `packages/quality/` | Validate lesson plan quality |
| Teacher gate interrupts | `packages/agents/graph.py` | Blueprint approval flow |

### Reusable architectural patterns

| Pattern | From | Apply to |
|---|---|---|
| Component dispatcher | Report 08 proposal (`dispatcher.eta`) | Route lesson components to Eta partials |
| Discriminated union | Report 08 proposal (`ContentComponent`) | Type-safe lesson content blocks |
| Theme CSS system | `common/branding/` | Color-coded clusters, group styling |
| Blueprint designer skill | `skills/blueprint-designer/SKILL.md` | Extend with methodology instructions |

### Existing reference designs

| Reference | Location | Value |
|---|---|---|
| `learning-vocab-template.html` | `docs/templates/` | **Primary reference** — the exact output format |
| `key-template.html` | `docs/templates/` | Shared design system (colors, sidebar, cards) |
| `path-template.html` | `docs/templates/` | Phase timeline, stat grid patterns |

---

## 6. What Needs to Be Built

### 6.1 Schema Layer

| # | Component | Type | Effort | Blocks |
|---|---|---|---|---|
| 1 | `LessonContent` discriminated union | Schema | 2 days | All templates |
| 2 | Extend `LessonPlan` with methodology fields | Contract | 1 day | R1-R5 |
| 3 | `VocabCluster` schema (contrastive pairs) | Contract | 1 day | R1 |
| 4 | `PhrasalVerbCluster` schema | Contract | 0.5 days | R1 |
| 5 | `FilmClip` schema (title, description, hunt sheet) | Contract | 0.5 days | R2 |
| 6 | `RoleplayScript` schema (characters, lines, blanks) | Contract | 0.5 days | R3 |
| 7 | `ActiveRecallPrompt` schema | Contract | 0.5 days | R4 |

### 6.2 Template Layer

| # | Component | Type | Effort | Blocks |
|---|---|---|---|---|
| 8 | `sidebar.eta` | Template | 2 days | R6 |
| 9 | `hero.eta` (with stat-grid, obj-card) | Template | 1 day | R6 |
| 10 | `concept_box.eta` | Template | 1 day | R1 |
| 11 | `contrast_cards.eta` (tri-card grid) | Template | 1 day | R1 |
| 12 | `vocab_cards.eta` (fiveset grid) | Template | 1 day | R1 |
| 13 | `quickpairs_table.eta` | Template | 0.5 days | R1 |
| 14 | `phrasal_clusters.eta` | Template | 1 day | R1 |
| 15 | `question_card.eta` (with wrong-reasons) | Template | 2 days | R5 |
| 16 | `roleplay_script.eta` | Template | 1 day | R3 |
| 17 | `film_card.eta` + `hunt_sheet.eta` | Template | 1 day | R2 |
| 18 | `pages/lesson.eta` (full lesson plan page) | Template | 2 days | R6 |
| 19 | `dispatcher.eta` (component router) | Template | 1 day | All |

### 6.3 Agent Layer

| # | Component | Type | Effort | Blocks |
|---|---|---|---|---|
| 20 | Extend Content Creator prompt with methodology instructions | Prompt | 1 day | R1-R5 |
| 20a | Add concept-map/contrastive-pairs methodology to prompt | | | R1 |
| 20b | Add film-based learning instructions | | | R2 |
| 20c | Add shy-student-friendly activity design | | | R3 |
| 20d | Add "why wrong" reasoning instructions | | | R5 |
| 21 | Extend Blueprint Designer skill with vocabulary pedagogy | Skill | 1 day | R1-R4 |
| 22 | Wire Content Creator into pipeline graph (step 08 is dummy) | Graph | 2 days | All |

### 6.4 Quality Layer

| # | Component | Type | Effort | Blocks |
|---|---|---|---|---|
| 23 | Pedagogical methodology quality gate | Gate | 2 days | R1-R5 |
| 24 | Lesson plan completeness check | Gate | 1 day | R6 |

### Total estimated effort: ~25-30 days

---

## 7. Recommendation

### Verdict: The system **cannot** produce this lesson plan today. But the building blocks are more available than the answer-key use case (Report 08).

### Key insight: This is primarily a **template + prompt engineering** problem, not an agent architecture problem.

Unlike Report 08 (which required new agents: DiagnosticAgent, RoadmapAgent), this use case can be addressed by:

1. **Extending the Content Creator prompt** (1 day) — add methodology instructions for concept-map, contrastive pairs, film-based learning, shy-student design, and "why wrong" reasoning
2. **Building the lesson template** (2 weeks) — 14 new Eta components + 1 page template + dispatcher
3. **Wiring the pipeline** (2 days) — connect the Content Creator agent into the graph (step 08 is currently a dummy)

### Comparison with Report 08

| Dimension | Report 08 (Answer Key) | This Report (Vocab Lesson) |
|---|---|---|
| **New agents needed** | Yes (DiagnosticAgent, RoadmapAgent) | No — existing agents suffice |
| **New schemas needed** | Yes (StudentResponse, DiagnosticReport, StudentProfile) | Partial — extend LessonPlan, add VocabCluster, FilmClip, RoleplayScript |
| **Template work** | 7 new components + 2 page templates | 14 new components + 1 page template |
| **Prompt work** | Minimal | Significant — methodology instructions |
| **Pipeline changes** | 2 new pipeline steps | Wire existing step 08 |
| **Estimated effort** | 30-40 days | 25-30 days |
| **Risk** | High (new agent architecture) | Medium (template-heavy, known patterns) |

### Feasibility assessment

| Dimension | Rating | Notes |
|---|---|---|
| **Pedagogical methodology** | 🟡 MEDIUM | Concept-map and contrastive-pairs are well-defined pedagogical patterns. The challenge is encoding them in the Content Creator prompt so the LLM produces the right JSON structure. |
| **Film-based learning** | 🟡 MEDIUM | Novel content type — no existing schema. But it's straightforward: film title + description + hunt sheet chips. |
| **Shy-student design** | 🟢 HIGH | `dialogue_completion` exercise type already supports script-based dialogue. Just needs a template. |
| **"Why wrong" reasoning** | 🟢 HIGH | `QuestionCard.wrong_reasons` already exists. Just needs `question_card.eta` template (also needed for Report 08). |
| **Rich HTML output** | 🟡 MEDIUM | 14 new components needed, but the CSS patterns are fully defined in `learning-vocab-template.html`. Pure template implementation work. |
| **Reference design quality** | 🟢 HIGH | `learning-vocab-template.html` (435 lines) is a complete, functional reference. Every CSS pattern is defined. Slice and implement. |

### Priority recommendation

**Phase 1 (Week 1-2): Content Creator prompt + schema extensions**
- Extend `content_creator/prompts/system.md` with methodology instructions
- Add `VocabCluster`, `PhrasalVerbCluster`, `FilmClip`, `RoleplayScript` schemas
- Extend `LessonPlan` with methodology fields

**Phase 2 (Week 2-4): Template components**
- Build 14 new Eta components (sidebar, hero, concept_box, contrast_cards, vocab_cards, etc.)
- Build `dispatcher.eta` component router
- Build `pages/lesson.eta` page template

**Phase 3 (Week 4-5): Pipeline integration**
- Wire Content Creator into graph (step 08)
- Add pedagogical quality gate
- End-to-end test

### Shared components with Report 08

Several components overlap between this use case and Report 08:

| Component | Report 08 | This Report |
|---|---|---|
| `sidebar.eta` | ✅ Needed for answer key | ✅ Needed for lesson plan |
| `hero.eta` | ✅ Needed for answer key | ✅ Needed for lesson plan |
| `question_card.eta` (with wrong-reasons) | ✅ Core of answer key | ✅ Core of practice questions |
| `dispatcher.eta` | ✅ Component router | ✅ Component router |
| `note_callout.eta` | ✅ Note boxes | ✅ Note boxes |

**Building these shared components first serves both use cases.** The sidebar + hero + question_card + dispatcher = ~6 days of work, and they unblock both the answer key template (Report 08) and the lesson plan template (this report).

### Appendix: File References

| File | Relevance |
|---|---|
| `docs/templates/learning-vocab-template.html` | 435-line reference: the exact output format for this use case |
| `docs/templates/key-template.html` | 1067-line reference: shared design system |
| `docs/templates/path-template.html` | 846-line reference: phase timeline patterns |
| `docs/reports/core/08-usecase-evaluation-answer-key.md` | Prior evaluation with shared components |
| `packages/agents/sub_agents/content_creator/prompts/system.md` | 35-line prompt — needs methodology instructions |
| `packages/agents/sub_agents/content_creator/nodes.py` | Content Creator agent — needs pipeline wiring |
| `packages/agents/graph.py` | Pipeline graph — step 08 is dummy |
| `common/contracts/lesson_plan.py` | LessonPlan schema — needs methodology extensions |
| `common/contracts/components/questions.py` | QuestionCard with wrong_reasons |
| `common/contracts/components/concept.py` | ConceptMap (basic — needs edges/relationships) |
| `common/schemas/src/exercise-types/english.ts` | vocabulary_scaffolded, dialogue_completion, collocation |
| `packages/renderer/templates/pages/lesson.html` | 2-line stub — must rebuild |
| `packages/renderer/templates/components/question_mc.html` | TODO stub — must implement |
| `packages/renderer/templates/components/concept_map.html` | 8-line minimal — must extend |
| `packages/renderer/templates/components/comparison_table.html` | Working — can reuse for contrastive pairs |
| `.scratch/educational-content-research/ISSUE.md` | Planned LessonPhase[] with UbD + Gagné (not implemented) |
| `.scratch/template-library/ISSUE.md` | Planned template library (not implemented) |

---

## 8. Research Findings: Development Directions

> This section synthesizes findings from 5 parallel librarian research sessions covering concept-map pedagogy, film-based learning, roleplay dialogue, distractor explanation, and phrasal verb clustering. Each subsection includes: research evidence, recommended data model, and implementation guidance.

---

### 8.1 Concept-Map / Contrastive-Pairs Pedagogy

#### Research Evidence

**Nation's Four Strands** (2001, 2007, 2008) — the dominant vocabulary pedagogy framework:

| Strand | Time | Role of concept maps |
|--------|------|---------------------|
| Meaning-focused input | ~25% | Encounter words in context |
| **Language-focused learning** | ~25% | **Concept maps live here** — deliberate study of word features |
| Meaning-focused output | ~25% | Production tasks using target vocab |
| Fluency development | ~25% | Speed drills with known words |

**Key insight**: Concept maps serve one strand. Pair each concept-map artifact with a production task in the same lesson.

**Nation's three aspects of word knowledge** — concept map JSON must encode all three:
- **Form**: spelling, pronunciation, syllable count, word family
- **Meaning**: definition, L1 translation, concreteness (1-7 scale), corpus frequency
- **Use**: example sentences, collocations, register, grammatical patterns

**Contrastive pairs research** (Waller et al. 2025, Dutch PMC8290082 2021):
- Semantic similarity is a **double-edged sword**
- Presented simultaneously → **interference errors** (learners confuse them)
- **Contrasted deliberately** with explicit comparison → **sharpens lexical representations**
- Effect strongest for highly skilled readers (metalinguistic awareness matters)

**Practical implication**: Contrastive pairs work only when:
1. The contrast is **explicit** (not incidental co-presentation)
2. The pair is **interleaved** with unrelated items, not massed together
3. A retrieval/decision task forces the learner to **choose** between the pair

**DUCTION → Data model must carry**:
- The **dimension of contrast** (antonymy, synonymy, hyponymy, collocational)
- The **discrimination task** type (MCQ, fill-blank with distractors)
- **Difficulty rating** of discrimination

**LECTOR (2025, state-of-the-art)**: Adds **semantic interference awareness** to spaced repetition. Computes semantic similarity Φ: C × C → [0,1] via LLM, then schedules reviews to **separate semantically similar concepts in time**. Achievement: 90.2% success rate vs 88.4% for prior best.

**DUCTION → Content creator agent should output `contrastivePairs` and `semanticClusters` as first-class data** that the scheduler can consume.

**Duolingo's Half-Life Regression**: Every word has a learned "half-life" — time until recall drops to 50%. Key finding: **decompose words into denser features** (POS, tense, corpus frequency, word length) rather than single difficulty score.

**DUCTION → Concept node should carry decomposed features**: `corpus_frequency`, `concreteness`, `morphological_complexity`, `semantic_cluster_size`.

---

### 8.1 Concept-Map Data Model: Recommended Schema

Based on research, the recommended `ConceptGraph` schema:

```typescript
interface ConceptGraph {
  id: string
  metadata: {
    title: string
    subject: string
    gradeLevel: string
    targetLanguage: string
    cefrLevel: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
    strategyType: 'concept-map' | 'contrastive-pairs' | 'semantic-mapping' | 'frayer-model'
  }
  nodes: ConceptNode[]        // vocabulary items with Nation's 3 aspects
  edges: ConceptEdge[]        // typed semantic relations (52 types from Nesso taxonomy)
  contrastivePairs: ContrastivePair[]  // explicit contrast relationships
  semanticClusters: SemanticCluster[]  // groupable nodes for interleaving
}

interface ConceptNode {
  id: string
  type: 'word' | 'phrase' | 'collocation' | 'root' | 'affix'
  label: string
  partOfSpeech: string
  form: { spelling: string; pronunciation: string; wordFamily: string[]; affixLevel?: number }
  meaning: { definition: string; l1Translation?: string; concreteness: number; corpusFrequency: number }
  use: { exampleSentences: string[]; collocations: string[]; register: string; grammaticalPatterns: string[] }
  fsrs: { stability: number; difficulty: number; state: 0|1|2|3; due: number }  // Spaced repetition
}

interface ContrastivePair {
  id: string
  wordA: string                    // node id
  wordB: string                    // node id
  dimension: 'antonymy' | 'scalar' | 'complementary' | 'converse' | 'synonymy-discrimination' | 'hyponymy' | 'collocational' | 'morphological'
  teachingStrategy: 'explicit-contrast' | 'distractor-mcq' | 'fill-blank' | 'matching'
  discriminationPrompt: string     // forces the comparison
  commonError: string              // typical learner confusion
}

interface SemanticCluster {
  id: string
  label: string
  nodes: string[]                  // node ids
  organizingRelation: 'taxonomy' | 'thematic' | 'word-family' | 'collocational'
  recommendedOrder: string[]       // teaching sequence
  interleavingStrategy: 'blocked' | 'interleaved' | 'gradual'
}
```

**Key libraries**:
- **Nesso** (`@nesso-how/graph`) — MIT, typed semantic edges (52 relation types), FSRS fields, React component
- **React Flow** (`@xyflow/react`) — for teacher editing interface
- **Cytoscape.js** — for graph algorithms if needed

---

## 9. Research Findings: Film-Based Learning

### 9.1 Platform Architecture Patterns

**FluentU** (content wrapper model):
- Overlays interactive features on YouTube/Netflix via Chrome extension
- Core loop: Video → Interactive Captions (clickable words) → Quiz → SRS Review → Progress Tracking
- Tracks `known_words`, `learning_words`, `saved_words` per user
- "Blue bar" per video shows % vocabulary already known

**TED-Ed** (lesson creator platform):
- Template: "Let's Begin…" → "Think" (up to 15 questions) → "Dig Deeper" → "Discuss" → "And Finally…"
- Any YouTube embeddable video can be used
- Teachers can "Flip" existing lessons

**H5P Interactive Video** (canonical ed-tech standard):
- `semantics.json` defines the authoritative data model
- Embeddable content types: MultiChoice, Blanks, MarkTheWords, TrueFalse, DragText, Summary, FreeTextQuestion
- Key for vocabulary: **MarkTheWords** — target words marked with `*asterisks*` in text field → rendered as clickable/highlightable spans

### 9.2 Clip Length Research

| Source | Recommended Length | Context |
|---|---|---|
| Mayer (2009) — Cognitive Theory of Multimedia Learning | Segment longer videos into short clips | Avoid cognitive overload |
| Empirical EFL study (8 clips, 8 weeks) | ~10 minutes per clip | Animated movies, B1-B2 learners |
| A2-level EFL study | ≤ 5 minutes | A2+ learners, authentic film clips |
| TED-Ed best practice | ≤ 6 minutes without interaction | General guidance |
| Vocabulary video study | 2 min 40 sec | Target vocabulary focus (A2-B1) |

**DUCTION → For teaching-pack generation, use 2-5 minute clips** (focused vocabulary segment) to 10-minute clips (comprehension + vocabulary).

### 9.3 Three-Stage Scaffolding Framework (Empirically Validated)

**Pre-Viewing (Advance Organizers)**:
- Question previewing: Show comprehension questions before viewing
- Vocabulary pre-teaching: Introduce target words with definitions
- **Combined approach** yields best results (Herron et al. 1995, Chung 2002)
- Teacher mediation: "Signal which lexical items are worth attending to before the video begins" (Le Nguyen & Le, 2026)

**While-Viewing**:
- English subtitles (not L1) preferred for vocabulary uptake
- Keyword captions (highlighting target words) improve vocabulary learning over full captions
- Teacher decides when to pause vs preserve viewing continuity
- Vocabulary coverage: 70-85% A1-A2, with B1-B2 items to challenge

**Post-Viewing**:
- Fill-in-the-blank exercises from film dialogue — most cited activity
- Comprehension questions containing target words
- Reuse tasks: Students use target vocabulary in new utterances
- Trajectory: Noticing → Interpretive Engagement → Reuse

### 9.4 Vocabulary Hunt Sheet: Data Model

Based on H5P MarkTheWords + VSS (Vocabulary Self-Collection Strategy) research:

```typescript
interface FilmClipActivity {
  clip: {
    source: "youtube" | "vimeo" | "upload"
    url: string
    start_time: number           // seconds
    end_time: number
    duration_seconds: number     // 120-600 recommended
    title: string
    cefr_level: string
    theme: string[]              // ["travel", "weather", "emotions"]
  }
  subtitles: {
    full_transcript: string
    segments: Array<{ start: number; end: number; text: string; words: Array<{ text: string; is_target?: boolean }> }>
  }
  target_vocabulary: Array<{
    word: string
    definition: string
    example_from_clip: { time: number; sentence: string }
    collocations?: string[]
  }>
  pre_viewing: {
    warm_up_question: string
    vocabulary_preview: Array<{ word: string; prompt?: string }>
  }
  while_viewing: Array<{
    type: "comprehension_question" | "vocabulary_hunt" | "mark_the_words" | "fill_blank"
    timestamp: number
    pause_video: boolean
    transcript_segment?: string    // with *target words* marked
    task_instruction?: string
  }>
  post_viewing: {
    comprehension_check: Array<{ question: string; type: string; options?: string[] }>
    vocabulary_practice: Array<{ type: string; prompt: string; target_word: string }>
    discussion_prompts: string[]
  }
}
```

---

## 10. Research Findings: Scripted Roleplay for Shy Learners

### 10.1 Platform Patterns

**FreeCodeCamp's Animated Dialogue Scene** (`challengeType: 21`):
- Dialogue → Task → Task → Dialogue → Task structure
- `alwaysShowDialogue: true` flag — text never disappears (reduces retrieval anxiety)
- Fill-in-the-blank tasks follow narrative dialogue
- Pre-authored audio files + character sprites from curated asset library

**Babbel's Two-Track System**:
- **Guided Conversations** (scripted, A1-A2): Pre-scripted dialogues, listen then repeat
- **Babbel Speak** (AI-powered, B1+): LLM-powered open conversation with guardrails
- Key: `communicative_situation`, `canDo` (CEFR target), `tasks` (2-3 sub-goals)

**Rosetta Stone's Milestone System**:
- Slide-show story context → characters speak → student responds by selecting fill-in-the-blank options
- Three conversation goals create bounded, achievable structure

### 10.2 SLA Research: Scripted vs Unscripted

| Study | Finding |
|---|---|
| ADJES Journal, UAD Yogyakarta | Scripted roleplay increases confidence by providing "clear guidelines and achievable goals" |
| JEASP, UIN Malang | 15/30 students felt nervous performing unscripted; many refused voluntarily |
| IJMOE 2026 | Low-stakes + safe space reduces affective filter (Krashen) |
| JOECY 2026 | Roleplay reduces speaking anxiety: p<0.00, 40% low anxiety post-intervention |
| ETRD, Springer 2025 | AI-GFCA scaffold (Generalization→Formulation→Correction→Appreciation) improved roleplay with fewer L2 errors |

**Key finding**: Predictability reduces anxiety. The fear of "not knowing what to say" outweighs the tedium of scripted repetition.

### 10.3 4-Level Difficulty Scaffold

| Level | Name | Description | Student Anxiety |
|---|---|---|---|
| 1 | **Full Script Read-Aloud** | Word bank present, student selects | Very low |
| 2 | **Partial Hints** | First letter/syllable + some word bank | Low |
| 3 | **Sentence Frames** | Structure provided, content blank | Medium |
| 4 | **Free Production** | Role + scenario only, open response | Higher (but bounded) |

**DUCTION → Default to Level 1-2 for shy students.** Allow teacher to adjust scaffold level.

### 10.4 RoleplayScript Schema

```typescript
interface RoleplayScript {
  id: string
  title: string
  scenario_description: string
  cefr_level: 'A1' | 'A2' | 'B1' | 'B2'
  characters: Array<{ id: string; name: string; role: 'student' | 'partner' | 'narrator' }>
  student_role_id: string
  scaffold_level: 'word_bank' | 'partial_hint' | 'sentence_frame' | 'free_production'
  lines: Array<{
    id: string
    order: number
    character_id: string
    script_template: string         // "I would like {blank:drink} {blank:quantity} please."
    blanks: Array<{
      key: string
      correct_answer: string
      acceptable_answers: string[]
      word_bank_options?: string[]
      partial_hint?: string
      feedback_correct?: string
      feedback_incorrect?: string
    }>
    full_answer: string
    display: { is_student_response: boolean; show_duration_ms?: number }
  }>
  scoring: {
    passing_threshold: number
    blank_weight: number
    allow_retry: boolean            // critical for shy students
  }
}
```

**DUCTION → No ed-tech standard has a first-class roleplay dialogue data model.** You're designing something genuinely new. Build from freeCodeCamp's `FullScene` + `FillInTheBlank` pattern.

---

## 11. Research Findings: "Why Wrong" Reasoning in Assessment

### 11.1 Production Platform Patterns

**Learnosity** (enterprise assessment):
- Two levels: per-question rationale + per-response rationale
- `show_distractor_rationale: { per_question: "incorrect", per_response: "always" }`
- Rationale stored as metadata, display logic decides when to show

**Qwiklabs (Google Cloud)**:
- Per-option: `{ id, title, rationale, is_answer }` — clean, self-contained
- Rationale is locale-dictionary-keyed (HTML content)

**Canvas New Quizzes (Instructure)**:
- UUID-keyed map for per-option feedback
- Three tiers: neutral, correct, incorrect question-level feedback

**QTI 2.1 (1EdTech standard)**:
- `modalFeedback` elements controlled by outcome variables
- Feedback shown/hidden based on response processing

### 11.2 Cognitive Science Research

**The J-Effect (Justification Effect)**:
- Students who answer correctly but can't justify why distractors are wrong → **false understanding**
- JMCQ reduces test anxiety vs. simple correct/incorrect feedback

**Worked Examples vs. Problem Solving** (McLaren et al.):
- Worked examples require **46-69% less study time** than problem solving
- **No difference in learning outcomes**
- But combining correct + incorrect examples with **explanatory feedback** significantly improved **transfer performance**

**Explanation Feedback > Correct Answer Feedback** (Butler, Godbole & Marsh 2013):
- Explanation feedback produces **significantly better transfer** than simply showing the correct answer
- Mechanism: helps learners apply knowledge to **new contexts**

**LLM Distractor Generation** (ACL 2026):
- LLMs naturally follow **solve-first, error-injection strategy**:
  1. ERR_DESC: Identify common error/misconception
  2. ERR_SIM: Simulate the error in an otherwise correct solution
  3. INST: State the incorrect outcome

### 11.3 Essence (Bản chất) and Tip (Mẹo làm bài)

**Bản chất (Essence)**: The **core concept** the question tests. Positive statement of the principle. Answers: "What fundamental concept, if understood, would make the correct answer obvious?"

**Mẹo làm bài (Exam Tip)**: A **recognition pattern** or **heuristic** for quick identification. Cognitive shortcut grounded in deep understanding, not rote memorization.

**Research support**: Maps to cognitive science distinction between **declarative knowledge** ("what" — essence) and **procedural knowledge** ("how" — tip). Both needed for robust learning. Butler et al. (2013) found explanation feedback improves **transfer** — tips are transfer heuristics.

### 11.4 Recommended DistractorExplanation Schema

```typescript
interface DistractorExplanation {
  reason: string                    // Why this specific option is wrong
  commonMisconception?: string      // Underlying misunderstanding this exploits
  guidance?: string                 // Hint pointing toward correct reasoning
  essence?: string                  // Bản chất: core concept (positive statement)
  tip?: string                      // Mẹo làm bài: exam strategy / recognition pattern
  bloomLevel?: string               // Complexity level of explanation
}

interface MCQOption {
  id: string
  text: string
  isCorrect: boolean
  explanation?: DistractorExplanation
  partialScore?: number             // 0-100 for "best answer" questions
}

interface MCQQuestion {
  stem: string
  options: MCQOption[]              // 4-6 options
  explanation: {
    correctAnswer?: string          // Why correct answer is correct
    general?: string                // Shown regardless of answer
    correctFeedback?: string        // Only when student answered correctly
    incorrectFeedback?: string      // Only when student answered incorrectly
  }
}
```

**DUCTION → Extend `QuestionCard` in `common/contracts/components/questions.py`** to add `common_misconception`, `guidance`, `essence`, `tip` fields. The `wrong_reasons` field already exists — enhance it with the full `DistractorExplanation` structure.

**DUCTION → Content creator prompt should instruct**:
> For each distractor option, generate:
> 1. **reason**: Why this specific answer is wrong — point to the exact reasoning error
> 2. **commonMisconception**: The underlying misunderstanding this distractor exploits
> 3. **guidance**: A hint pointing toward the correct reasoning path
> 4. **essence**: The core concept (bản chất) — what the student must understand. State positively.
> 5. **tip**: An exam strategy (mẹo làm bài) — a quick check or recognition pattern.

---

## 12. Research Findings: Phrasal Verb Clustering

### 12.1 SLA Research: Semantic Clustering Debate

Three camps with empirical support:

**Camp A: Semantic Clustering Harms** (Interference Theory):
- Tinkham (1993, 1997): More trials needed for semantically related pseudowords
- Pérez-Serrano et al. (Frontiers 2022): Unrelated categories better recalled in incidental learning
- Nakata & Suzuki (2018): Related items cause more within-set interference errors
- Barclay/Bach (NTU 2023): Semantic + physical similarity → **41.5% increase in learning burden**

**Camp B: Semantic Clustering Helps** (Semantic Field Theory):
- Aksoy (Turkish): 15 semantically related words outperformed on delayed tests
- Serbian engineering students: Semantic sets outperformed on immediate AND delayed tests
- Saudi EFL study (2024): Semantic sets "significantly better on both delayed tests"
- ACCHE 2025 review: "recent scepticism towards semantic clustering is not justified"

**Camp C: Radial Categories** (WINNER for phrasal verbs):
- **Mehrad Sadr et al. (2022)**: Radial categories (one prototypical concept + peripheral members) **significantly outperformed** traditional approaches for PV learning AND retention, while reducing cognitive load
- Why: Particles (up, off, out) have a central prototypical meaning with radial extensions
- **DUCTION → Use radial categories for phrasal verb clusters**

### 12.2 Cluster Size: Cognitive Load Research

| Source | Optimal Size | Notes |
|---|---|---|
| Cognitive Load Theory (Sweller) | 3-5 new items | Intrinsic load limit for novices |
| Radial categories study (2022) | 5-7 PVs per category | 6 particles with ~50 sense extensions |
| Nakata & Suzuki (2018) | 4 items per cluster | 4 semantically related items per set |
| General vocabulary research | 5-9 words per lesson | Working memory: 7±2 chunks |

**DUCTION → Limit each cluster to 4-7 phrasal verbs. Sweet spot: 5 (±2).**

### 12.3 Travel/Transport Phrasal Verb Taxonomy

| Category | Subcategory | Example PVs | CEFR |
|---|---|---|---|
| **Departure** | Journey begins | set off, set out, take off, head off | B1 |
| **Departure** | Boarding | get on, check in | A2-B1 |
| **Arrival** | Landing/stopping | touch down, pull in, get in | B1 |
| **Arrival** | Alighting | get off, get out of, drop off | A2-B1 |
| **Lodging** | Hotel | check in, check out, put up, settle in | B1 |
| **Transport** | Vehicle ops | speed up, slow down, back up, pull over | B1-B2 |
| **Incidents** | Problems | break down, run out of, hold up | B1-B2 |
| **Exploration** | Sightseeing | look around, come across, drop by | B1 |
| **Return** | Going back | get back, head back, turn back | A2-B1 |

**Particle-centered radial categories** (Rudzka-Ostyn 2003, validated 2022):

| Particle | Prototypical Meaning | Travel Extensions |
|---|---|---|
| **up** | upward/completion | speed up, pack up, fill up, pick up |
| **off** | separation/departure | take off, set off, drop off, see off |
| **out** | exiting/removal | get out of, check out, run out of |
| **in** | entering/arrival | get in, check in, pull in, settle in |
| **down** | decreasing/stopping | slow down, touch down, break down |
| **back** | return/reversal | get back, head back, turn back |

### 12.4 PhrasalVerbCluster Schema

```python
class PhrasalVerbCluster(BaseModel):
    id: str
    name: str                        # "Departure: Setting Off"
    description: str
    cluster_type: Literal["thematic", "radial_particle", "semantic_field"]
    anchor_particle: str | None = None  # For radial clusters
    target_cefr_level: str
    phrasal_verbs: list[PhrasalVerb]   # 4-7 items
    narrative_context: str | None = None
    contrast_notes: list[str] = []     # "set off vs set out: nearly identical"
    common_errors: list[str] = []      # "Learners say 'get on the car' (wrong)"

class PhrasalVerb(BaseModel):
    verb: str
    particle: str
    meaning: str
    guideword: str | None = None       # Cambridge-style disambiguator
    transparency: Literal["literal", "aspectual", "semi_transparent", "idiomatic"]
    cefr_level: str
    separability: Literal["separable", "inseparable", "obligatorily_separable"]
    example_sentences: list[ExampleSentence]
    particle_meaning_extension: str | None = None
```

**DUCTION → Design principles**:
1. Cluster by **scenario** (airport loop), not by particle alone
2. Mix **radial and thematic** — inside each thematic cluster, show radial connections
3. Limit to **5±2 per cluster**
4. Surface **contrastive pairs** explicitly (get on/get in, set off/set out)
5. Flag **semantic transparency** — transparent PVs need less scaffolding
6. Use **retrieval + continuation tasks** over rote (Barri 2024: fill-in-blank 3x repetition > sentence writing)

---

## 13. Updated Development Roadmap

### What to build first (research-backed priority)

| Priority | Component | Research Basis | Effort |
|---|---|---|---|
| **P0** | `ConceptGraph` schema + prompt engineering | Nation (2001), LECTOR (2025), Waller (2025) | 3 days |
| **P0** | `DistractorExplanation` schema extension | Butler (2013), J-Effect research, Learnosity patterns | 1 day |
| **P0** | `RoleplayScript` schema + scaffold levels | ADJES, Springer 2025 GFCA model, Babbel patterns | 1 day |
| **P1** | `PhrasalVerbCluster` schema (radial categories) | Mehrad Sadr (2022), Rudzka-Ostyn (2003) | 1 day |
| **P1** | `FilmClipActivity` schema + 3-stage scaffolding | H5P MarkTheWords, Herron (1995), Le Nguyen (2026) | 1 day |
| **P1** | Content Creator prompt with methodology instructions | All above | 2 days |
| **P2** | Template components (14 new Eta partials) | `learning-vocab-template.html` reference | 2 weeks |
| **P2** | Pipeline wiring (step 08) | — | 2 days |

### Shared components with Report 08

| Component | Report 08 | This Report |
|---|---|---|
| `sidebar.eta` | ✅ Needed | ✅ Needed |
| `hero.eta` | ✅ Needed | ✅ Needed |
| `question_card.eta` (with distractor explanations) | ✅ Core | ✅ Core |
| `dispatcher.eta` | ✅ Router | ✅ Router |
| `note_callout.eta` | ✅ Boxes | ✅ Boxes |

**DUCTION → Build shared components first.** Sidebar + hero + question_card + dispatcher = ~6 days, unblocks both use cases.

---

> **Last updated**: 2026-06-24
> **Research agents**: 5 parallel librarian agents (concept-map, film-based, roleplay, distractor-reasoning, phrasal-verb)
> **Next steps**: See Section 13 (Updated Development Roadmap) for research-backed priority order.
> **Key insight**: The research confirms that contrastive pairs, scripted roleplay, distractor explanations, and radial-category phrasal verb clusters are all **evidence-based pedagogical approaches** — not just the teacher's preference. Build the data models to encode these patterns, and the content creator agent can generate them.
