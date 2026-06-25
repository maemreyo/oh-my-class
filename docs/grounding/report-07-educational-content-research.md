# Grounding Report: Report 07 — Educational Content Research

**Date**: 2026-06-24  
**Prepared for**: Implementation of Report 07 tickets  
**Source Report**: `docs/reports/core/07-educational-content-research.md` (853 lines)

---

## 1. Report 07 Summary

**Title**: AI Educational Content Generation — Research Findings  
**Purpose**: Research synthesis on AI in education, pedagogical frameworks, content schemas, quality standards, and export formats.

### Report Structure (5 Sections)

| Section | Topic | Key Contents |
|---------|-------|--------------|
| 1 | AI in Education Frameworks | Khanmigo, Q-Chat, Kahoot! architectures; 8 academic papers; 7 open-source implementations |
| 2 | Pedagogical Frameworks | Bloom's Taxonomy (revised), Backward Design/UbD (WHERETO template), Gagné's Nine Events |
| 3 | Educational Content Schemas | TypeScript interfaces for LessonPlan, Quiz, Worksheet, Infographic, TeachingPack |
| 4 | Quality Standards | TEAS framework, ACIF/FACT protocol, 5-dimension pedagogical rubric, age-appropriate filtering (6 bands), WCAG 2.2 AA |
| 5 | Export Formats | Moodle GIFT, H5P, QTI 2.1, Google Forms API, 5-format comparison matrix |

### Key Pedagogical Frameworks

| Framework | Application in oh-my-class |
|-----------|---------------------------|
| **Backward Design (UbD)** | Lesson plan structure — Stage 1 (Desired Results), Stage 2 (Assessment Evidence), Stage 3 (Learning Plan) |
| **Gagné's Nine Events** | Micro-level lesson phases — 9 sequential events for each lesson segment |
| **Bloom's Taxonomy** | Difficulty levels — remember/understand/apply/analyze/evaluate/create |
| **FACT Protocol** | Hallucination verification — Find → Assess → Cross-reference → Tag (VERIFIED/MODIFIED/REMOVED/UNCERTAIN) |

### Vietnamese Education Context

- **Decision 3439/QĐ-BGDĐT** — Vietnamese curriculum standards
- **Circular 02/2025/TT-BGDĐT** — Assessment regulations
- **6 age bands** for content filtering (preschool → grade 12)
- **Bilingual support** — `language: 'vi' | 'en' | 'bilingual'`

---

## 2. Issues Tagged `report: "07"`

**Only 1 issue found**:

### Issue: Educational Content Research (`educational-content-research`) — P0, `ready`

**Path**: `.scratch/educational-content-research/ISSUE.md`  
**Status**: `ready`  
**Priority**: `p0` (highest)  
**Labels**: `architecture`, `schema`, `education`, `quality`, `export`

**Description**: Core content schemas and supporting systems derived from research synthesis. Covers lesson plan structure, teaching pack bundle, dual quality scoring, multi-format export, bilingual support, age-appropriate filtering, curriculum standards, worksheet block system, diagram rendering, WCAG 2.2 AA upgrade.

#### Design Decisions

| Code | Decision | Rationale |
|------|----------|-----------|
| **PB3** | UbD macro + Gagné micro are complementary | UbD for overall lesson structure, Gagné for individual segment sequencing |
| **TP1** | `teaching_pack` = artifact type 11 | Extends `ArtifactDataMap` with bundle type |
| **QG2** | Dual scoring: G-Eval + 5-dimension pedagogical | Technical quality (automated) + pedagogical quality (LLM judge) |
| **EF4** | 6 export formats | GIFT, H5P, QTI, Google Forms, Flashcard TSV, Anki .apkg |
| **BL2** | Language configurable per artifact | `language: 'vi' | 'en' | 'bilingual'` in all request types |
| **AF4** | 6 age bands + Flesch-Kincaid | Grade-aware prompt injection (preventive) + ReadabilityChecker (detective) |
| **CS2** | `CurriculumStandard` is typed | Agent-generated, no external DB lookup |
| **WC2** | WCAG 2.2 AA upgrade | 3 additions over Report 03 templates |
| **WB1** | `WorksheetBlock` = 11 discriminated union variants | Type-safe block system for worksheets |
| **DF2** | Differentiation guides optional | Not required for all lessons |
| **DG3** | Diagrams: LLM generates SVG | Renderer sanitizes + embeds inline |

#### Files to Create

**Contracts** (`contracts/schemas/`):
```
contracts/schemas/
├── teaching-pack.ts     — TeachingPackData, QualityScore
├── lesson-plan.ts       — LessonPlan (UbD + Gagné), LearningObjective, AssessmentEvidence
├── worksheet.ts         — Worksheet, WorksheetSection, WorksheetBlock (11 variants)
└── infographic.ts       — Infographic with diagram data model
```

**Contracts** (root):
```
contracts/
├── artifact-data-map.ts — Add teaching_pack as type 11
└── curriculum-standard.ts — CurriculumFramework enum (7 frameworks)
```

**Quality modules** (`packages/agents/quality/`):
```
packages/agents/quality/
├── __init__.py
├── age_band.py          — AgeBand dataclass, 6 bands, build_grade_prompt_section()
├── readability_checker.py — check_readability() with Flesch-Kincaid
└── pedagogical_scorer.py — score_pedagogical() with 5-dimension LLM scoring
```

**Renderer additions** (`packages/renderer/src/`):
```
packages/renderer/src/
├── diagrams/
│   ├── index.ts
│   └── svg-sanitizer.ts — sanitizeSVG() reuses allowlist
└── exporters/
    ├── gift/
    │   └── index.ts     — GIFTExporter for choice/text types
    ├── h5p/
    │   ├── index.ts
    │   ├── content-types/*.ts — 5 H5P content types
    │   └── packager.ts  — .h5p ZIP creation
    ├── google-forms/
    │   ├── index.ts
    │   ├── auth.ts      — OAuth 2.0 flow
    │   ├── question-mapper.ts
    │   └── client.ts    — batchUpdate API
    ├── flashcard-tsv/
    │   └── index.ts     — Tab-separated for Quizlet + Anki
    └── anki-apkg/
        └── index.py     — .apkg via genanki
```

#### Acceptance Criteria (16)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `LessonPlan` schema — UbD Stage 1/2/3 with Gagné `lessonPhases[]` (all 9 events) | ❌ Pending |
| 2 | `TeachingPackData` — artifact type 11, `QualityScore` included | ❌ Pending |
| 3 | `QualityScore.passed` — `technical.total >= 70 AND pedagogical.total >= 3.5` | ❌ Pending |
| 4 | `WorksheetBlock` — all 11 variants | ❌ Pending |
| 5 | `CurriculumStandard` — typed `CurriculumFramework` enum | ❌ Pending |
| 6 | `language: 'vi' | 'en' | 'bilingual'` — in all artifact request types | ❌ Pending |
| 7 | `AgeBand` config — 6 bands, `build_grade_prompt_section()` works | ❌ Pending |
| 8 | `check_readability(text, grade)` — Flesch-Kincaid, warns at \|deviation\| > 2 | ❌ Pending |
| 9 | `score_pedagogical(content)` — 5 dimensions, passed at total >= 3.5 | ❌ Pending |
| 10 | `GIFTExporter` — valid Moodle GIFT for choice/text question types | ❌ Pending |
| 11 | `FlashcardTSVExporter` — tab-separated, importable by Quizlet + Anki | ❌ Pending |
| 12 | `AnkiApkgExporter` — valid `.apkg` via `genanki` | ❌ Pending |
| 13 | `H5PExporter` — valid `.h5p` ZIP for 5 content types | ❌ Pending |
| 14 | `GoogleFormsExporter` — OAuth flow documented, `batchUpdate` payload valid | ❌ Pending |
| 15 | `renderDiagram(data)` — LLM generates SVG, `sanitizeSVG()` reuses allowlist | ❌ Pending |
| 16 | WCAG 2.2 AA: `scroll-margin-top`, `lang="vi"` default | ❌ Pending |

#### Dependencies

| Dependency | Status | Report |
|------------|--------|--------|
| `llm-client` | ❌ Not implemented | Report 04 |
| `sanitizer-module` | ✅ **Implemented** | Report 03 |
| `exercise-types-catalog` | ❌ Not implemented | Report 06 |

**Blocks**: `content-creator-agent`, `template-library`, `quality-gate-nodes`

---

## 3. Current Codebase State (Relevant to Report 07)

### What Exists (Already Implemented)

| Component | Status | Location | Relevance |
|-----------|--------|----------|-----------|
| **LessonPlan Pydantic model** | ✅ Complete | `common/contracts/lesson_plan.py` | 72 lines — basic structure, needs UbD + Gagné expansion |
| **ArtifactContent Pydantic model** | ✅ Complete | `common/contracts/artifact.py` | 48 lines — needs `teaching_pack` type |
| **JudgeOutput Pydantic model** | ✅ Complete | `common/contracts/judge_output.py` | 50 lines — G-Eval scoring |
| **Quality gates** | ✅ Complete | `packages/quality/` | 6 layers — needs pedagogical scorer |
| **G-Eval scorer** | ✅ Complete | `packages/quality/layer4_judge/geval.py` | 130 lines — technical scoring |
| **Sanitizer** | ✅ Complete | `packages/renderer/src/sanitizer/` | SVG sanitizer can reuse allowlist |
| **Renderer contracts** | ✅ Complete | `packages/renderer/src/contracts/` | 10 artifact types — needs `teaching_pack` |
| **Exercise type schemas** | ✅ Complete | `common/schemas/src/exercise-types/` | ~1,000 lines — foundation for question types |
| **Zod schemas** | ✅ Complete | `common/schemas/src/` | Generated from Pydantic |
| **Gateway routers** | ✅ Complete | `services/gateway/routers/` | Runs, approvals, webhooks |

### What's Missing (Report 07 Scope)

| Component | Status | Impact |
|-----------|--------|--------|
| **`LessonPlan` UbD expansion** | ❌ Not implemented | No backward design structure |
| **`TeachingPackData` schema** | ❌ Not implemented | No bundle type for artifact type 11 |
| **`QualityScore` dual scoring** | ❌ Not implemented | No pedagogical quality dimension |
| **`WorksheetBlock` 11 variants** | ❌ Not implemented | No typed block system |
| **`CurriculumStandard` enum** | ❌ Not implemented | No curriculum framework typing |
| **`AgeBand` module** | ❌ Not implemented | No age-appropriate filtering |
| **Readability checker** | ❌ Not implemented | No Flesch-Kincaid scoring |
| **Pedagogical scorer** | ❌ Not implemented | No 5-dimension LLM scoring |
| **GIFT exporter** | ❌ Not implemented | No Moodle export |
| **Flashcard TSV exporter** | ❌ Not implemented | No Quizlet/Anki export |
| **Anki .apkg exporter** | ❌ Not implemented | No Anki export |
| **H5P exporter** | ❌ Not implemented | No interactive export |
| **Google Forms exporter** | ❌ Not implemented | No Google Forms API |
| **SVG sanitizer** | ❌ Not implemented | No diagram rendering |
| **WCAG 2.2 AA** | ❌ Not implemented | Still on 2.1 AA |

### Existing Contracts vs Report 07 Requirements

| Existing Contract | Report 07 Addition |
|-------------------|-------------------|
| `lesson_plan.py` (72 lines) | → Expand with UbD Stage 1/2/3 + Gagné 9 events |
| `artifact.py` (48 lines) | → Add `teaching_pack` as type 11 |
| `judge_output.py` (50 lines) | → Add `QualityScore` with dual scoring |
| `components/` (various) | → Add `WorksheetBlock` 11-variant union |

**Key insight**: Report 07 **extends** existing contracts — doesn't replace them. The `LessonPlan` model needs UbD expansion, `ArtifactContent` needs `teaching_pack` type, `JudgeOutput` needs pedagogical dimension.

---

## 4. Dependencies & Blockers

### Report 07 Internal Dependencies

```
Core schemas (lesson-plan, teaching-pack, worksheet, curriculum-standard)
    ├── Quality modules (age_band, readability_checker, pedagogical_scorer)
    ├── Exporters (gift, h5p, google-forms, flashcard-tsv, anki-apkg)
    ├── Diagram renderer (svg-sanitizer)
    └── WCAG 2.2 AA updates
```

### Cross-Report Dependencies

| Report 07 Task | Depends On | Report | Status |
|-----------------|------------|--------|--------|
| `LessonPlan` expansion | — | — | Can start |
| `TeachingPackData` | `ArtifactDataMap` | Report 03 | ✅ Done |
| `QualityScore` | `JudgeOutput` | Report 02 | ✅ Done |
| `WorksheetBlock` | Exercise types | Report 06 | ❌ Blocked |
| `CurriculumStandard` | — | — | Can start |
| `AgeBand` | — | — | Can start |
| Readability checker | — | — | Can start |
| Pedagogical scorer | `llm-client` | Report 04 | ❌ Blocked |
| `GIFTExporter` | Exercise types | Report 06 | ❌ Blocked |
| `H5PExporter` | Exercise types | Report 06 | ❌ Blocked |
| `GoogleFormsExporter` | Exercise types | Report 06 | ❌ Blocked |
| `FlashcardTSVExporter` | Exercise types | Report 06 | ❌ Blocked |
| `AnkiApkgExporter` | Exercise types | Report 06 | ❌ Blocked |
| SVG sanitizer | `sanitizer-module` | Report 03 | ✅ Done |
| WCAG 2.2 AA | `html-template-system` | Report 03 | ✅ Done |

### What Blocks Report 07

| Blocker | Report | Status |
|---------|--------|--------|
| `llm-client` | Report 04 | ❌ Not implemented |
| `exercise-types-catalog` | Report 06 | ❌ Not implemented (1/12 done) |

### What Report 07 Blocks

| Blocked Item | Impact |
|--------------|--------|
| `content-creator-agent` | Can't generate lesson plans with UbD structure |
| `template-library` | Can't render worksheet blocks |
| `quality-gate-nodes` | Can't score pedagogical quality |

---

## 5. Implementation Plan (Recommended Order)

### Wave 1: Core Schemas (No Dependencies)

1. **Expand `lesson_plan.py`** — Add UbD Stage 1/2/3 + Gagné 9 events + `LessonPhase[]`
2. **Create `teaching_pack.py`** — `TeachingPackData` with `QualityScore`
3. **Create `worksheet.py`** — `Worksheet`, `WorksheetSection`, `WorksheetBlock` (11 variants)
4. **Create `curriculum_standard.py`** — `CurriculumFramework` enum (7 frameworks)
5. **Update `artifact.py`** — Add `teaching_pack` as type 11 in `ArtifactDataMap`

### Wave 2: Quality Modules (No Dependencies)

1. **Implement `age_band.py`** — `AgeBand` dataclass, 6 bands, `build_grade_prompt_section()`
2. **Implement `readability_checker.py`** — `check_readability()` with Flesch-Kincaid formula
3. **Implement `pedagogical_scorer.py`** — `score_pedagogical()` with 5-dimension LLM scoring
4. **Write tests** — each module with edge cases

### Wave 3: Diagram Renderer (Depends on Report 03)

1. **Implement `svg-sanitizer.ts`** — Reuse sanitizer allowlist for SVG
2. **Implement `diagrams/index.ts`** — `renderDiagram(data)` entry point
3. **Write tests** — SVG sanitization, inline embedding

### Wave 4: WCAG 2.2 AA Updates (Depends on Report 03)

1. **Update `base.html`** — Add `scroll-margin-top`, `lang="vi"` default
2. **Update page templates** — WCAG 2.2 AA compliance checks
3. **Write tests** — Accessibility validation

### Wave 5: Exporters (Depends on Report 06)

1. **Implement `gift/index.ts`** — GIFTExporter for choice/text types
2. **Implement `flashcard-tsv/index.ts`** — Tab-separated for Quizlet + Anki
3. **Implement `anki-apkg/index.py`** — `.apkg` via genanki
4. **Implement `h5p/`** — 5 content types + packager
5. **Implement `google-forms/`** — OAuth + batchUpdate + question mapper
6. **Write tests** — each exporter with sample data

### Wave 6: Integration & Verification

1. **Update Zod schemas** — Regenerate from Pydantic models
2. **Verify all 16 acceptance criteria**
3. **Integration tests** — Full pipeline with new schemas

---

## 6. Key Files to Reference

| Purpose | File | Why |
|---------|------|-----|
| Existing LessonPlan | `common/contracts/lesson_plan.py` | 72 lines — needs UbD expansion |
| Existing ArtifactContent | `common/contracts/artifact.py` | 48 lines — needs `teaching_pack` type |
| Existing JudgeOutput | `common/contracts/judge_output.py` | 50 lines — needs pedagogical dimension |
| G-Eval scorer | `packages/quality/layer4_judge/geval.py` | 130 lines — technical scoring pattern |
| Sanitizer | `packages/renderer/src/sanitizer/` | SVG sanitizer can reuse allowlist |
| Renderer contracts | `packages/renderer/src/contracts/` | Zod schemas — needs `teaching_pack` |
| Report 03 grounding | `docs/grounding/report-03-html-template-skills.md` | Template system reference |
| Report 06 grounding | `docs/grounding/report-06-exercise-types-catalog.md` | Exercise types foundation |
| AGENTS.md §8-10 | `AGENTS.md` | Template system, exercise types, export formats |

---

## 7. Risks & Considerations

| Risk | Mitigation |
|------|------------|
| `LessonPlan` expansion may break existing planner agent | Expand incrementally — add optional fields first |
| `TeachingPackData` adds type 11 to `ArtifactDataMap` | Verify renderer handles unknown types gracefully |
| Dual scoring (G-Eval + pedagogical) increases complexity | Start with G-Eval only, add pedagogical in follow-up |
| 6 exporters is large scope | Implement in order: GIFT (simplest) → Flashcard TSV → Anki → H5P → Google Forms |
| WCAG 2.2 AA may require template changes | Audit existing templates against 2.2 checklist |
| SVG sanitization security | Reuse existing allowlist — no new attack surface |
| `genanki` Python dependency | Add to `pyproject.toml` — verify compatibility |

---

## 8. Verification Checklist

Before starting implementation:

- [ ] Verify `common/contracts/lesson_plan.py` has `LessonPlan` model
- [ ] Check `packages/quality/layer4_judge/geval.py` for scoring pattern
- [ ] Confirm `packages/renderer/src/sanitizer/` has reusable allowlist
- [ ] Review AGENTS.md §8-10 for template, exercise, and export specs
- [ ] Check `llm-client` status (Report 04 — blocker for pedagogical scorer)

After implementation:

- [ ] `LessonPlan` — UbD Stage 1/2/3 with Gagné `lessonPhases[]` (all 9 events)
- [ ] `TeachingPackData` — artifact type 11, `QualityScore` included
- [ ] `QualityScore.passed` — `technical.total >= 70 AND pedagogical.total >= 3.5`
- [ ] `WorksheetBlock` — all 11 variants
- [ ] `CurriculumStandard` — typed `CurriculumFramework` enum
- [ ] `language: 'vi' | 'en' | 'bilingual'` — in all artifact request types
- [ ] `AgeBand` config — 6 bands, `build_grade_prompt_section()` works
- [ ] `check_readability(text, grade)` — Flesch-Kincaid, warns at \|deviation\| > 2
- [ ] `score_pedagogical(content)` — 5 dimensions, passed at total >= 3.5
- [ ] `GIFTExporter` — valid Moodle GIFT for choice/text question types
- [ ] `FlashcardTSVExporter` — tab-separated, importable by Quizlet + Anki
- [ ] `AnkiApkgExporter` — valid `.apkg` via `genanki`
- [ ] `H5PExporter` — valid `.h5p` ZIP for 5 content types
- [ ] `GoogleFormsExporter` — OAuth flow documented, `batchUpdate` payload valid
- [ ] `renderDiagram(data)` — LLM generates SVG, `sanitizeSVG()` reuses allowlist
- [ ] WCAG 2.2 AA: `scroll-margin-top`, `lang="vi"` default
- [ ] All 16 acceptance criteria pass

---

**Last updated**: 2026-06-24  
**Status**: Ready for implementation (blocked by Report 04 + Report 06)
