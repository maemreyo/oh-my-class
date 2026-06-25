# Grounding Report: Report 08 — Use Case Evaluation: Personalized Answer Key & Learning Roadmap

**Date**: 2026-06-24  
**Prepared for**: Implementation of Report 08 tickets  
**Source Report**: `docs/reports/core/08-usecase-evaluation-answer-key.md` (2137 lines)

---

## 1. Report 08 Summary

**Title**: Use Case Evaluation: Personalized Answer Key & Learning Roadmap  
**Purpose**: Evaluate whether oh-my-class can handle "teacher inputs wrong answers → personalized learning roadmap + detailed answer key HTML". Research-backed architecture proposal with 6-phase implementation roadmap.

### The Use Case

A teacher describes a student's wrong answers on a practice test and requests:
1. **Diagnostic Analysis** — map wrong answers → knowledge gaps, Bloom level gaps, misconception patterns
2. **Personalized Learning Roadmap** — 6-7 month study plan targeting HSA 40+, book recommendations (Destination B2/C1)
3. **Detailed Answer Key** — per-question explanations with `explain`, `wrongReasons`, `essence`, `tip`
4. **Student Profile Integration** — shy personality, film-based learner, weak vocabulary, 1v1 tutoring context

### Report Structure (15 Sections)

| Section | Topic | Key Contents |
|---------|-------|--------------|
| 1-3 | Use Case + Gap Analysis | 4 deliverables (D1-D4), 12 capabilities audited, 6 critical gaps identified |
| 4 | Template Reference Analysis | `key-template.html` (1067 lines), `path-template.html` (846 lines), shared design system |
| 5 | Template Engine Architecture | Component dispatcher pattern, discriminated union, Eta layout/blocks, page hierarchy |
| 6-7 | Leverage + Build | 12 reusable components, 18 new components to build (~30-40 days) |
| 8 | Implementation Roadmap | 5 phases, week-by-week plan |
| 9 | Recommendation | Feasibility assessment, priority ordering |
| 10-14 | Research Findings | Diagnostic agents, learning roadmaps, answer key reasoning, template engines, student profiles |
| 15 | Updated Roadmap | 6 phases, ~12 weeks (expanded from research) |

### Key Architectural Decisions (from Report)

| Code | Decision | Research Basis |
|------|----------|----------------|
| **AC1** | Component dispatcher pattern | Khan Perseus, Vercel json-render, Strapi Dynamic Zones |
| **AC2** | `ContentComponent` discriminated union (14+ types) | json-render catalog, Perseus widget registry |
| **AC3** | BKT for knowledge tracing (not IRT) | pyBKT — simpler, real-time, sufficient for 15-20 HSA skills |
| **AC4** | 9-code error taxonomy | Carnegie MATHia + ErrorRadar + MalruleLib consolidation |
| **AC5** | Verification pipeline (L1-L4) | Correct Answer Trap research (57% → 84% detection) |
| **AC6** | SM-2 spacing for roadmap | Proven algorithm, DRL-SRS is future upgrade |
| **AC7** | Felder-Silverman + Big 5 for student profile | PATS (EACL 2026), EduGenome AI |
| **AC8** | AQ gating for roadmap progression | DeepTutor Trace Forest |

---

## 2. Issues Tagged `report: "08"`

**1 issue found**:

### Issue: Answer Key + Learning Roadmap (`answer-key-roadmap`) — P0, `ready`

**Path**: `.scratch/answer-key-roadmap/ISSUE.md` (if exists)  
**Status**: `ready`  
**Priority**: `p0`  
**Labels**: `template`, `schema`, `agent`, `diagnostic`, `roadmap`

---

## 3. Implementation Status

### 3.1 Acceptance Criteria Matrix

| # | Acceptance Criterion | Status | Evidence |
|---|---------------------|--------|----------|
| AC-01 | `ContentComponent` discriminated union with 14+ types | ✅ DONE | `common/contracts/components/__init__.py` — 16 union members, Pydantic `Field(discriminator="type")` |
| AC-02 | `QuestionCard` has `essence`, `tip`, `wrong_reasons` fields | ✅ DONE | `common/contracts/components/questions.py:17-19` |
| AC-03 | `AnswerKeyContent` Pydantic model with sections + metadata | ✅ DONE | `common/contracts/answer_key.py` — full schema |
| AC-04 | `RoadmapContent` Pydantic model with hero + sidebar + sections | ✅ DONE | `common/contracts/roadmap.py` — full schema |
| AC-05 | `answer_key` in `ArtifactType` enum | ✅ DONE | `common/contracts/artifact.py:24` |
| AC-06 | `roadmap` in `ArtifactType` enum | ✅ DONE | `common/contracts/artifact.py:24` |
| AC-07 | `answer_key.html` page template | ✅ DONE | `packages/renderer/templates/pages/answer_key.html` (45 lines) |
| AC-08 | `renderer.ts` uses Eta dispatch | ✅ DONE | `packages/renderer/src/renderer.ts:40` — `eta.renderAsync('pages/${type}')` |
| AC-09 | 69 component + roadmap tests passing | ✅ DONE | `common/contracts/tests/test_components.py` (401 lines) + `test_roadmap.py` (155 lines) |
| AC-10 | `AnswerKeyData` TypeScript interface | ✅ DONE | `packages/renderer/src/contracts/answer_key.ts` |
| AC-11 | `ContentComponentSchema` (Zod/TS equivalent) | ❌ NOT DONE | No TS-side discriminated union; Python Pydantic is sole source of truth |
| AC-12 | `dispatcher.eta` component router template | ❌ NOT DONE | Dispatch is in `renderer.ts` code, not a template file |
| AC-13 | `question_card.eta` component partial | ❌ NOT DONE | Question rendering is inline in page templates |
| AC-14 | `roadmap.html` page template | ❌ NOT DONE | `RoadmapContent` schema exists but no renderer template |
| AC-15 | `sidebar.eta` + `hero.eta` shared components | ❌ NOT DONE | No sidebar/hero templates |
| AC-16 | 7 roadmap component partials (stat_grid, pattern_grid, trait_grid, taxonomy_grid, phase_timeline, flow_step, alert) | ❌ NOT DONE | Python schemas exist (cards.py, timeline.py) but no Eta templates |
| AC-17 | `DiagnosticAgent` implementation | ❌ NOT DONE | No agent class file |
| AC-18 | `RoadmapAgent` implementation | ❌ NOT DONE | Only docstring reference in `roadmap.py` |
| AC-19 | `StudentProfile` schema | ❌ NOT DONE | No Pydantic or TypeScript model |
| AC-20 | `StudentResponse` schema | ❌ NOT DONE | No Pydantic or TypeScript model |
| AC-21 | `DiagnosticReport` schema | ❌ NOT DONE | No Pydantic or TypeScript model |
| AC-22 | Pipeline integration (diagnostic + roadmap steps) | ❌ NOT DONE | No graph.py changes |
| AC-23 | Theme extension with group colors (`--c-a` through `--c-e`) | ❌ NOT DONE | `theme.json` not extended |
| AC-24 | Dark mode CSS (`@media (prefers-color-scheme: dark)`) | ❌ NOT DONE | — |
| AC-25 | Print styles (`@media print`) | ❌ NOT DONE | — |

**Score: 10/25 ACs done (40%)**

### 3.2 Component-Level Status

#### ✅ DONE — Schema Layer (Python)

| Component | Location | Lines | Tests |
|-----------|----------|-------|-------|
| `ContentComponent` union (16 types) | `common/contracts/components/__init__.py` | 100 | `test_components.py` — 401 lines, 39 tests |
| `Heading`, `Paragraph`, `Callout`, `OrderedList`, `UnorderedList` | `common/contracts/components/textual.py` | ~80 | Covered in `test_components.py` |
| `Table` | `common/contracts/components/tabular.py` | ~30 | Covered in `test_components.py` |
| `StatGrid`, `PatternGrid`, `TraitGrid`, `TaxonomyGrid` | `common/contracts/components/cards.py` | ~120 | Covered in `test_components.py` |
| `PhaseTimeline`, `FlowStep`, `RoadmapPhase`, `PhaseBlock` | `common/contracts/components/timeline.py` | ~80 | Covered in `test_components.py` |
| `QuestionCard`, `QuestionList` | `common/contracts/components/questions.py` | 31 | Covered in `test_components.py` |
| `ConceptMap`, `TimelineComponent` | `common/contracts/components/concept.py` | ~40 | Covered in `test_components.py` |
| `AnswerKeyContent` | `common/contracts/answer_key.py` | 37 | `test_answer_key.py` |
| `RoadmapContent` | `common/contracts/roadmap.py` | 56 | `test_roadmap.py` — 155 lines, 20 tests |

#### ✅ DONE — Renderer Layer (TypeScript)

| Component | Location | Lines | Notes |
|-----------|----------|-------|-------|
| `renderer.ts` (Eta dispatch) | `packages/renderer/src/renderer.ts` | 113 | `renderArtifact<T>()` uses `eta.renderAsync('pages/${type}')` |
| `answer_key.html` template | `packages/renderer/templates/pages/answer_key.html` | 45 | Basic: MCQ-only, no wrongReasons/essence/tip, no sidebar, no color groups |
| `AnswerKeyData` TS interface | `packages/renderer/src/contracts/answer_key.ts` | 20 | Basic: `MCQuestion[]` + `teachingNotes` + `rubric` |

#### ❌ NOT DONE — Missing Components

| Component | Priority | Effort | Blocks |
|-----------|----------|--------|--------|
| `StudentProfile` schema | P0 | 2 days | D4 (student profile integration) |
| `StudentResponse` schema | P0 | 1 day | D1 (diagnostic analysis) |
| `DiagnosticReport` schema | P0 | 2 days | D1 (diagnostic analysis) |
| `DiagnosticAgent` | P0 | 5 days | D1 (diagnostic analysis) |
| `RoadmapAgent` | P1 | 5 days | D2 (learning roadmap) |
| `roadmap.html` template | P1 | 2 days | D2 (learning roadmap) |
| `sidebar.eta` + `hero.eta` | P1 | 2 days | D2, D3 |
| 7 roadmap component partials | P1 | 5 days | D2 |
| `question_card.eta` (rich version) | P1 | 3 days | D3 (answer key) |
| `dispatcher.eta` (template-based) | P2 | 1 day | Architectural cleanup |
| `ContentComponentSchema` (Zod/TS) | P2 | 2 days | TS-side validation |
| Theme extension (group colors) | P2 | 1 day | D2, D3 |
| Pipeline integration | P2 | 4 days | All |
| Dark mode + print styles | P3 | 2 days | Polish |
| `StudentProfile` UI in dashboard | P3 | 5 days | D4 |

---

## 4. Key Gaps

### 4.1 Answer Key Template is Minimal

The existing `answer_key.html` (45 lines) is a basic MCQ answer list. The reference `key-template.html` (1067 lines) has:
- Sidebar with navigation, jump-to-question grid, hide/reveal toggle
- Color-coded groups (`--c-a` through `--c-e`)
- Per-question cards with `explain`, `wrongReasons`, `essence`, `tip`
- Section headers with range badges
- Hero section with stamp and stats

**Gap**: The template needs a complete rewrite to match the reference design.

### 4.2 No Roadmap Template

`RoadmapContent` schema exists (Python) but there's no `roadmap.html` template to render it. The reference `path-template.html` (846 lines) has:
- Sidebar with stats, nav, legend
- Hero with eyebrow, stamp, stat grid
- Diagnostic table with error rates
- Pattern grid, trait grid, taxonomy grid
- Phase timeline with vertical rail
- Flow steps with time badges

**Gap**: Entire template needs to be built from scratch.

### 4.3 No Agent Implementation

The report proposes `DiagnosticAgent` and `RoadmapAgent`. Neither exists:
- No `packages/agents/sub_agents/diagnostician/` directory
- No `packages/agents/sub_agents/roadmap/` directory
- No `StudentProfile`, `StudentResponse`, or `DiagnosticReport` schemas

**Gap**: Entire agent layer is missing.

### 4.4 TS Side Lacks ContentComponentSchema

The Python `ContentComponent` discriminated union is comprehensive (16 types). But the TypeScript side has no equivalent Zod schema. This means:
- No runtime validation on the TS side
- No type-safe component dispatch in templates
- The `AnswerKeyData` TS interface uses `MCQuestion[]`, not `ContentComponent[]`

**Gap**: Need Zod `ContentComponentSchema` in `common/schemas/src/components.ts`.

---

## 5. Test Status

### Python Tests

| Package | Tests | Status |
|---------|-------|--------|
| `common/contracts/tests/` | **94** | ✅ ALL PASSING |
| `packages/quality/` | **156** | ✅ ALL PASSING |
| `packages/agents/` | **433** | ✅ ALL PASSING |
| Full Python suite | **683** passed, 6 pre-existing failures | ✅ NO NEW FAILURES |

### TypeScript Tests

| Package | Tests | Status |
|---------|-------|--------|
| `packages/renderer/` | **209** | ✅ ALL PASSING |
| `packages/exporters/` | **41** | ✅ ALL PASSING |

### Report 08-Specific Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_components.py` | **39** | All 16 ContentComponent types + discriminated union + unknown type rejection |
| `test_roadmap.py` | **20** | RoadmapContent, RoadmapHero, RoadmapSidebar, RoadmapSection, NavItem, LegendItem |
| `test_answer_key.py` | **10** | AnswerKeyContent, AnswerKeySection, AnswerKeyMetadata |

**Total: 69 Report 08-specific tests passing.**

---

## 6. File Inventory

### Files Created (Report 08)

```
common/contracts/
├── components/
│   ├── __init__.py          — ContentComponent discriminated union (16 types)
│   ├── textual.py           — Heading, Paragraph, Callout, OrderedList, UnorderedList
│   ├── tabular.py           — Table
│   ├── cards.py             — StatGrid, PatternGrid, TraitGrid, TaxonomyGrid
│   ├── timeline.py          — PhaseTimeline, FlowStep, RoadmapPhase, PhaseBlock
│   ├── questions.py         — QuestionCard, QuestionList
│   └── concept.py           — ConceptMap, TimelineComponent
├── answer_key.py            — AnswerKeyContent model
├── roadmap.py               — RoadmapContent model
└── tests/
    ├── test_components.py   — 39 tests for ContentComponent union
    ├── test_roadmap.py      — 20 tests for RoadmapContent
    └── test_answer_key.py   — 10 tests for AnswerKeyContent

packages/renderer/
├── templates/pages/
│   └── answer_key.html      — Basic answer key template (45 lines)
└── src/contracts/
    └── answer_key.ts        — AnswerKeyData TypeScript interface
```

### Files Referenced but NOT Created

```
packages/renderer/templates/
├── pages/roadmap.html              — MISSING (RoadmapContent has no template)
├── components/dispatcher.eta       — MISSING (dispatch is in renderer.ts code)
├── components/question_card.eta    — MISSING (inline in page templates)
├── components/sidebar.eta          — MISSING
├── components/hero.eta             — MISSING
├── components/stat_grid.eta        — MISSING
├── components/pattern_grid.eta     — MISSING
├── components/trait_grid.eta       — MISSING
├── components/taxonomy_grid.eta    — MISSING
├── components/phase_timeline.eta   — MISSING
├── components/flow_step.eta        — MISSING
└── components/alert.eta            — MISSING

packages/agents/sub_agents/
├── diagnostician/                  — MISSING (DiagnosticAgent)
└── roadmap/                        — MISSING (RoadmapAgent)

common/contracts/
├── student_profile.py              — MISSING (StudentProfile)
├── student_response.py             — MISSING (StudentResponse)
└── diagnostic_report.py            — MISSING (DiagnosticReport)

common/schemas/src/
└── components.ts                   — MISSING (ContentComponentSchema Zod)
```

---

## 7. Dependency Graph

```
Phase 1: Schema Layer (DONE ✅)
  │
  ├──> Phase 2: Answer Key Template (PARTIAL — basic template exists, rich version missing)
  │       │
  │       └──> Phase 4: Roadmap Template (shares sidebar/hero components)
  │
  ├──> Phase 3: Diagnostic Agent (NOT STARTED — needs StudentResponse, DiagnosticReport schemas)
  │       │
  │       └──> Phase 4: Roadmap Agent (consumes DiagnosticReport)
  │
  └──> Phase 5: Student Profile (NOT STARTED — needs StudentProfile schema)
          │
          └──> Phase 6: Integration (everything comes together)
```

**Critical path**: Schema Layer ✅ → Answer Key Template → Roadmap Template (template chain)  
**Parallel path**: Schema Layer ✅ → Diagnostic Agent → Roadmap Agent (agent chain)

---

## 8. Implementation Roadmap (from Report 08, updated)

### Phase 1: Schema Layer — ✅ DONE

| Step | Component | Status |
|------|-----------|--------|
| 1.1 | `ContentComponent` discriminated union | ✅ 16 types in `common/contracts/components/` |
| 1.2 | `AnswerKeyContent` schema | ✅ `common/contracts/answer_key.py` |
| 1.3 | `RoadmapContent` schema | ✅ `common/contracts/roadmap.py` |
| 1.4 | `QuestionCard` with essence/tip/wrongReasons | ✅ `common/contracts/components/questions.py` |
| 1.5 | 69 tests | ✅ All passing |

### Phase 2: Answer Key Template — ⏳ PARTIAL

| Step | Component | Status | Effort |
|------|-----------|--------|--------|
| 2.1 | `question_card.eta` (rich version) | ❌ | 3 days |
| 2.2 | `sidebar.eta` + `hero.eta` | ❌ | 2 days |
| 2.3 | `answer_key.html` (rewrite to match key-template.html) | ⏳ Basic exists | 3 days |
| 2.4 | Theme extension (group colors) | ❌ | 1 day |
| 2.5 | `ContentComponentSchema` (Zod/TS) | ❌ | 2 days |

### Phase 3: Diagnostic Agent — ❌ NOT STARTED

| Step | Component | Status | Effort |
|------|-----------|--------|--------|
| 3.1 | `StudentResponse` schema | ❌ | 1 day |
| 3.2 | `DiagnosticReport` schema | ❌ | 2 days |
| 3.3 | `DiagnosticAgent` (verify → diagnose → analyze_bloom → synthesize) | ❌ | 5 days |
| 3.4 | Pipeline integration | ❌ | 2 days |

### Phase 4: Roadmap Template + Agent — ❌ NOT STARTED

| Step | Component | Status | Effort |
|------|-----------|--------|--------|
| 4.1 | 7 roadmap component partials | ❌ | 5 days |
| 4.2 | `roadmap.html` page template | ❌ | 2 days |
| 4.3 | `RoadmapAgent` (BKT + resequencing + spacing) | ❌ | 5 days |
| 4.4 | Pipeline integration | ❌ | 2 days |

### Phase 5: Student Profile — ❌ NOT STARTED

| Step | Component | Status | Effort |
|------|-----------|--------|--------|
| 5.1 | `StudentProfile` schema | ❌ | 2 days |
| 5.2 | Student profile UI in dashboard | ❌ | 5 days |

### Phase 6: Integration + Polish — ❌ NOT STARTED

| Step | Component | Status | Effort |
|------|-----------|--------|--------|
| 6.1 | Dark mode CSS | ❌ | 1 day |
| 6.2 | Print styles | ❌ | 1 day |
| 6.3 | Responsive testing | ❌ | 1 day |
| 6.4 | End-to-end test | ❌ | 2 days |

---

## 9. Design Decisions

| Code | Decision | Rationale | Status |
|------|----------|-----------|--------|
| **AC1** | Component dispatcher pattern | Khan Perseus, json-render, Strapi — proven in production | ✅ Schema done, ❌ Template not done |
| **AC2** | `ContentComponent` = 16-type discriminated union | Type-safe LLM output validation | ✅ Done (Python), ❌ Missing Zod (TS) |
| **AC3** | BKT for knowledge tracing | pyBKT — simpler, real-time, sufficient for 15-20 skills | ❌ Not started |
| **AC4** | 9-code error taxonomy | MATHia + ErrorRadar + MalruleLib consolidation | ❌ Not started |
| **AC5** | Verification pipeline (L1-L4) | Correct Answer Trap: 57% → 84% detection | ❌ Not started |
| **AC6** | SM-2 spacing for roadmap | Proven algorithm, extendable to FSRS | ❌ Not started |
| **AC7** | Felder-Silverman + Big 5 for student profile | PATS (EACL 2026), matches teacher's description | ❌ Not started |
| **AC8** | AQ gating for roadmap progression | DeepTutor: Admit/Conditionally Admit/Defer/Re-instruct | ❌ Not started |
| **AR1** | `roadmap` as artifact_type literal | Extends ArtifactType enum alongside lesson, quiz, etc. | ✅ Done |
| **AR2** | `answer_key` as artifact_type literal | Teacher-only view, answers always visible | ✅ Done |

---

## 10. Recommendations

### What to Implement Next

**Priority 1 (unblocks most work):**
1. `ContentComponentSchema` (Zod) — enables TS-side validation
2. `question_card.eta` (rich version) — the core answer key component
3. `sidebar.eta` + `hero.eta` — shared across answer key and roadmap
4. Rewrite `answer_key.html` to match `key-template.html` design

**Priority 2 (enables roadmap):**
5. `roadmap.html` template
6. 7 roadmap component partials
7. Theme extension with group colors

**Priority 3 (enables agents):**
8. `StudentResponse` + `DiagnosticReport` schemas
9. `DiagnosticAgent` implementation
10. `RoadmapAgent` implementation

**Priority 4 (enables student profile):**
11. `StudentProfile` schema
12. Pipeline integration

### Effort Estimate

| Phase | Days | Cumulative |
|-------|------|------------|
| Phase 1: Schema Layer | 0 (done) | 0 |
| Phase 2: Answer Key Template | 11 | 11 |
| Phase 3: Diagnostic Agent | 10 | 21 |
| Phase 4: Roadmap Template + Agent | 14 | 35 |
| Phase 5: Student Profile | 7 | 42 |
| Phase 6: Integration + Polish | 5 | 47 |

**Total remaining: ~47 days (9.4 weeks)**

---

## 11. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Answer key template doesn't match reference quality | Medium | High | Use key-template.html as pixel-perfect reference, test with Playwright |
| BKT insufficient for HSA skill mapping | Medium | High | Start with rule-based fallback, validate on real data |
| LLM wrongReason quality below teacher expectations | Medium | High | ILearner-LLM iterative refinement, teacher override gate |
| Missing Zod schema causes TS/Python drift | High | Medium | Generate Zod from Pydantic (existing `scripts/generate_zod_schemas.py`) |
| Roadmap template complexity exceeds estimate | Medium | Medium | Build component partials incrementally, test each in isolation |

---

> **Last updated**: 2026-06-24  
> **Test counts**: 69 Report 08-specific tests (Python), 683 total Python tests, 250 total TS tests  
> **Next steps**: See Section 9 (Recommendations) for priority ordering  
> **Key deliverable**: The template engine (dispatcher + component partials) is the product — not the individual templates.
