# 08 — Use Case Evaluation: Personalized Answer Key & Learning Roadmap

> **Date**: 2026-06-23
> **Evaluated by**: Sisyphus (multi-agent exploration)
> **Scope**: Can oh-my-class handle "teacher inputs wrong answers → personalized learning roadmap + detailed answer key HTML"?
> **Reference**: `docs/templates/key-template.html` (1067-line static HTML answer key mockup)

---

## Table of Contents

1. [The Use Case](#1-the-use-case)
2. [Current System Capabilities](#2-current-system-capabilities)
3. [Gap Analysis](#3-gap-analysis)
4. [Can We Generate key-template.html?](#4-can-we-generate-key-templatehtml)
5. [What Exists That We Can Leverage](#5-what-exists-that-we-can-leverage)
6. [What Needs to Be Built](#6-what-needs-to-be-built)
7. [Recommendation](#7-recommendation)

---

## 1. The Use Case

The teacher's workflow (verbatim):

```
Đây là bản kiểm tra đầu vào
Nếu học sinh của tôi sai các câu: 2,6,7,10,12,13,14,18,19-23,27,32,34,37,39,41,44,49,50.
thì theo bạn chương trình học sẽ nên thi theo hướng nào để:

- Target 40+ cho kỳ thi đánh giá năng lực của Đại học quốc gia (HSA)
- Kết hợp sách Destination nào (B2 ? C1?)
- xây dựng lộ trình chi tiết trong 6-7 tháng thế nào?
- Học sinh là 1 người nhút nhát, học qua film, yếu từ vựng, thích hiểu bản chất,
  có kiến thức nền tảng, nhưng chỉ học công thức -> nên không hiểu được bản chất,
  context, nuance ở các câu > 35
- từ vựng/collocation/idiom yếu
- đọc sai đề bài do chưa hiểu cấu trúc đề thi
- học 1v1 trực tiếp tại phòng học, tool quản lý BTVN, lớp là google classroom

Viết 1 bản HTML chi tiết để lên chương trình học giúp tôi.
```

**Decomposed into 4 deliverables:**

| # | Deliverable | Description |
|---|---|---|
| D1 | **Diagnostic Analysis** | Map wrong answers → identify knowledge gaps, weak Bloom levels, misconception patterns |
| D2 | **Personalized Learning Roadmap** | 6-7 month study plan targeting HSA 40+, with book recommendations (Destination B2/C1) |
| D3 | **Detailed Answer Key** | Per-question explanations with correct answer, why wrong answers are wrong, "essence" (bản chất), test-taking tips |
| D4 | **Student Profile Integration** | Factor in: shy personality, learns via film, weak vocabulary, understands depth not formulas, 1v1 tutoring context |

---

## 2. Current System Capabilities

### What oh-my-class CAN do today

| Capability | Evidence | Maturity |
|---|---|---|
| Generate standalone HTML | `packages/renderer/` — Eta templates, CSS inlining, no CDN | Scaffolded (stubs) |
| 6 artifact types | `common/contracts/artifact.py` — lesson, worksheet, quiz, drill, recap, infographic | Schema defined |
| 50+ exercise types | `common/schemas/src/exercise-types/` — MC, TF, cloze, reading comprehension, etc. | Schema defined |
| Per-question `explanation` field | Every exercise type schema includes `explanation: z.string().optional()` | Schema defined |
| Per-answer `feedback` | MCQ options have `feedback?: string`; quiz has `feedbackCorrect`, `feedbackIncorrect` | Schema defined |
| `answer_key.html` page template | `.scratch/template-library/ISSUE.md` — spec'd with `AnswerKeyData` contract | Spec ready |
| Teacher approval gates | LangGraph `interrupt()` at 2 points | Implemented |
| Quality gate system (6 layers) | `packages/quality/` — schema, content, HTML, judge, human, export | Partially implemented |
| Answer key separation (INVARIANT-05) | Layer 3 HTML validator enforces `teacher_only` sections | Implemented |
| Bloom's Taxonomy tagging | Every `LearningObjective` has `bloom_level` enum | Schema defined |
| Differentiation guides | `DifferentiationGuide` with `forStruggling`, `forAdvanced`, `forELL` | Schema defined |
| Vietnamese language support | First-class: VN curriculum standards, bilingual output | Documented |

### What oh-my-class CANNOT do today

| Missing Capability | Evidence | Impact |
|---|---|---|
| **Accept student wrong answer input** | `OhMyClassState` has no `student_responses` field | Blocks D1 |
| **Diagnostic/error analysis** | No agent, node, skill, or model for analyzing wrong answers | Blocks D1 |
| **Personalized learning roadmap** | No roadmap artifact type, no student model, no adaptive routing | Blocks D2 |
| **Per-student content generation** | Pipeline generates one pack per class, not per student | Blocks D4 |
| **`key-template.html`-quality answer key** | `answer_key.html` is spec'd but not implemented; page templates are stubs | Blocks D3 |
| **Student profile modeling** | No personality, learning style, or weakness tracking | Blocks D4 |

---

## 3. Gap Analysis

### D1: Diagnostic Analysis of Wrong Answers

**What the teacher needs:**
- Input: list of wrong question IDs (e.g., "2,6,7,10,12...")
- Output: categorized weakness analysis (grammar, vocabulary, reading comprehension, etc.)
- Output: Bloom level gaps (nhận biết vs. vận dụng)
- Output: misconception patterns (e.g., "only learns formulas → doesn't understand nuance in Q>35")

**What exists:**
- `AssessmentCheckpoint` model in `lesson_plan.py` — but this describes *planned* assessments, not *actual* student responses
- Exercise type schemas have `bloom_level` and `difficulty` fields —可用于 mapping wrong answers to knowledge gaps
- Vietnamese Bloom mapping exists: nhận biết=remember, thông hiểu=understand, vận dụng=apply+analyze, vận dụng cao=evaluate+create

**Gap: 🔴 CRITICAL — No diagnostic pipeline exists**

The system has zero infrastructure for accepting student answer data, let alone analyzing it. This requires:
1. A new input schema for student responses (question_id, student_answer, correct_answer, is_correct)
2. A new "Diagnostic Agent" that maps wrong answers to knowledge gaps
3. A new output model for diagnostic reports (weakness categories, Bloom gaps, misconception patterns)

---

### D2: Personalized Learning Roadmap

**What the teacher needs:**
- 6-7 month study plan targeting HSA 40+
- Book recommendations (Destination B2/C1)
- Weekly/monthly milestones
- Tailored to student profile (shy, film-based learner, weak vocabulary)

**What exists:**
- `LessonPlan` model with `learning_objectives`, `learning_plan` (Gagné's 9 Events), `assessment_checkpoints`
- `DifferentiationGuide` with `forStruggling` array — closest to personalization
- `DifferentiationGuide` schema in `common/contracts/lesson_plan.py`

**Gap: 🔴 CRITICAL — No roadmap generation**

The `LessonPlan` is a single-session lesson plan, not a multi-month study roadmap. There's no:
- Multi-session sequencing
- Book/adriculum mapping
- Progress milestone tracking
- Student profile integration

---

### D3: Detailed Answer Key with Explanations

**What the teacher needs (from `key-template.html`):**
- Per-question card with: question text, 4 options, correct answer highlighted
- `explain` — detailed explanation of why correct answer is correct
- `wrongReasons` — why each wrong option is wrong (A/B/C/D breakdown)
- `essence` — the core knowledge point being tested ("Bản chất")
- `tip` — test-taking strategy ("Mẹo làm bài")
- Sidebar with: section navigation, jump-to-question grid, hide/reveal toggle
- Color-coded groups (grammar=violet, dialogue=amber, etc.)

**What exists:**
- Exercise type schemas support `explanation` field
- MCQ schema has per-option `feedback` field
- `answer_key.html` template is spec'd in `.scratch/template-library/ISSUE.md`
- `AnswerKeyData` contract is defined in `.scratch/html-template-system/ISSUE.md`
- `key-template.html` is a 1067-line reference implementation showing the exact design

**Gap: 🟡 PARTIAL — Schema exists, template not implemented**

The data model can represent everything in `key-template.html`:
- `explanation` → `explain`
- Per-option `feedback` → `wrongReasons`
- Need new fields for `essence` and `tip` (not in current schema)
- Need to implement `answer_key.html` Eta template

---

### D4: Student Profile Integration

**What the teacher needs:**
- Shy personality → avoid high-pressure activities
- Learns via film → incorporate multimedia/video resources
- Weak vocabulary → prioritize vocabulary building
- Understands depth, not formulas → focus on conceptual understanding
- 1v1 tutoring → no group activities

**What exists:**
- `class_info` dict: `{grade, subject, student_count, language}` — class-level only
- `DifferentiationGuide` with `forStruggling`, `forAdvanced`, `forELL` — closest to student profiles
- `AgeBand` config for age-appropriate content filtering

**Gap: 🔴 CRITICAL — No student profile model**

The system operates at class level, not student level. There's no:
- Student profile schema (personality, learning style, strengths, weaknesses)
- Adaptive content selection based on student profile
- 1v1 tutoring mode

---

## 4. Can We Generate `key-template.html`?

### Short answer: **Not automatically. Yes manually (with significant work).**

### Detailed analysis:

`key-template.html` is a **1067-line static HTML file** with:
- **10 question sections** (sentence completion, synonyms, antonyms, dialogue, sentence rewriting, sentence combination, cloze, reading comprehension ×2, logical thinking)
- **50 questions** each with: question text, 4 options, correct answer, `explain`, `wrongReasons` (per distractor), `essence`, `tip`
- **Rich UI**: sidebar navigation, jump-to-question grid, hide/reveal toggle, color-coded groups, responsive design
- **Vietnamese language** throughout (bản chất, mẹo làm bài, giải thích)
- **External fonts** (Google Fonts: Spectral, Be Vietnam Pro, IBM Plex Mono) — violates INVARIANT-04

### What the system CAN generate today:

| Element | Can Generate? | How |
|---|---|---|
| Question text + options | ✅ Yes | MCQ schema fields |
| Correct answer highlight | ✅ Yes | `options.correct` styling |
| `explain` text | ✅ Yes | `explanation` field in schema |
| `wrongReasons` per distractor | 🟡 Partial | Per-option `feedback` exists, but not structured as `wrongReasons` object |
| `essence` (Bản chất) | ❌ No | Not in any schema — needs new field |
| `tip` (Mẹo làm bài) | ❌ No | Not in any schema — needs new field |
| Sidebar navigation | ❌ No | `answer_key.html` template not implemented |
| Jump-to-question grid | ❌ No | Same — template not implemented |
| Hide/reveal toggle | ❌ No | Same — template not implemented |
| Color-coded groups | ❌ No | Same — template not implemented |
| Standalone HTML (no CDN) | 🟡 Partial | Renderer enforces no CDN, but `key-template.html` uses Google Fonts |

### What needs to change:

1. **Extend exercise schemas** — Add `essence` and `tip` fields to exercise type definitions
2. **Implement `answer_key.html` Eta template** — Full template matching `key-template.html` design
3. **Add `wrongReasons` structure** — Per-distractor explanation object (not just flat `feedback`)
4. **Replace Google Fonts** — Use system font stack to comply with INVARIANT-04
5. **Wire into pipeline** — New pipeline step or artifact type for answer key generation

### Estimated effort:

| Task | Effort | Dependencies |
|---|---|---|
| Add `essence` + `tip` to schemas | 1 day | None |
| Add `wrongReasons` structure to MCQ schema | 0.5 days | None |
| Implement `answer_key.html` Eta template | 3-5 days | Schema changes |
| Add answer key as pipeline artifact type | 2-3 days | Template + schema |
| **Total** | **~7-10 days** | — |

---

## 5. What Exists That We Can Leverage

### Reusable components:

| Component | Location | Reuse for |
|---|---|---|
| Exercise type schemas | `common/schemas/src/exercise-types/` | Question data model for answer key |
| `ArtifactContent` model | `common/contracts/artifact.py` | Base for new answer key artifact type |
| `DifferentiationGuide` | `common/contracts/lesson_plan.py` | Student profile scaffolding |
| `LearningObjective` + `bloom_level` | `common/contracts/lesson_plan.py` | Mapping wrong answers to Bloom gaps |
| `AssessmentCheckpoint` | `common/contracts/lesson_plan.py` | Planned assessment structure |
| Feedback component | `packages/renderer/templates/components/feedback.html` | Correct/incorrect display |
| Question components | `packages/renderer/templates/components/question_*.html` | Question rendering |
| Quality gate system | `packages/quality/` | Validate answer key quality |
| `key-template.html` design | `docs/templates/key-template.html` | Direct reference for template implementation |
| Vietnamese Bloom mapping | `docs/reports/core/06-exercise-types-catalog.md` | HSA-specific gap analysis |

### Architectural patterns to follow:

| Pattern | From | Apply to |
|---|---|---|
| Supervisor + `task()` delegation | Lead Agent architecture | New Diagnostic Agent |
| LangGraph `interrupt()` for teacher gates | Teacher Gate 1/2 | Roadmap approval gate |
| Eta template + CSS inlining | Renderer pipeline | Answer key template |
| Pydantic v2 validation | Contracts layer | New schemas |
| FACT protocol (Find→Assess→Cross-ref→Tag) | Researcher Agent | Wrong answer analysis |
| G-Eval scoring | Reviewer Agent | Answer key quality validation |

---

## 6. What Needs to Be Built

### New components (in priority order):

| # | Component | Type | Effort | Blocks |
|---|---|---|---|---|
| 1 | `StudentResponse` schema | Contract | 0.5 days | D1, D2, D4 |
| 2 | `DiagnosticReport` schema | Contract | 1 day | D1 |
| 3 | `LearningRoadmap` schema | Contract | 1.5 days | D2 |
| 4 | `StudentProfile` schema | Contract | 1 day | D4 |
| 5 | `DiagnosticAgent` | Agent | 3-5 days | D1 |
| 6 | `RoadmapAgent` | Agent | 3-5 days | D2 |
| 7 | `answer_key.html` Eta template | Template | 3-5 days | D3 |
| 8 | `pages/roadmap.html` Eta template | Template | 2-3 days | D2 |
| 9 | New pipeline step(s) | Graph | 2-3 days | All |
| 10 | Extend exercise schemas (`essence`, `tip`, `wrongReasons`) | Schema | 1-2 days | D3 |
| 11 | Student profile UI in dashboard | Frontend | 3-5 days | D4 |
| **Total** | | | **~20-30 days** | |

### New pipeline flow (proposed):

```
Teacher Input (wrong answers + student profile)
    │
    ▼
┌─ Step 01: Preflight ─────────────────────────────┐
│  Validate: wrong answer IDs, student profile       │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 02: Diagnostic ────────────────────────────┐
│  Diagnostic Agent → DiagnosticReport JSON          │
│  - Map wrong answers → knowledge gaps              │
│  - Identify Bloom level weaknesses                 │
│  - Detect misconception patterns                   │
│  - Factor in student profile (shy, film-based...)  │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 03: Teacher Gate (approve diagnostic) ─────┐
│  interrupt() — teacher reviews gap analysis        │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 04: Roadmap Generation ────────────────────┐
│  RoadmapAgent → LearningRoadmap JSON               │
│  - 6-7 month plan targeting HSA 40+                │
│  - Book recommendations (Destination B2/C1)        │
│  - Weekly milestones                               │
│  - Tailored to student profile                     │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 05: Answer Key Generation ─────────────────┐
│  Content Creator Agent → AnswerKey JSON            │
│  - Per-question: explain, wrongReasons, essence, tip│
│  - Grouped by knowledge category                   │
│  - Vietnamese language                             │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 06: Quality Review ────────────────────────┐
│  LLM-as-Judge validates: accuracy, completeness    │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 07: Teacher Gate (approve content) ────────┐
│  interrupt() — teacher reviews roadmap + key       │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ Step 08: Export ────────────────────────────────┐
│  Render via Eta → standalone HTML                  │
│  (answer_key.html + roadmap.html)                  │
└────────────────────────────────────────────────────┘
```

---

## 7. Recommendation

### Verdict: The system **cannot** handle this use case today. But it **can** be extended to do so.

### Feasibility assessment:

| Dimension | Rating | Notes |
|---|---|---|
| **Technical feasibility** | 🟢 HIGH | Existing architecture (LangGraph + Eta + Pydantic) supports extension. No architectural blockers. |
| **Schema readiness** | 🟡 MEDIUM | Exercise schemas have `explanation` and `feedback`, but lack `essence`, `tip`, `wrongReasons`. Easy to extend. |
| **Template readiness** | 🟡 MEDIUM | `answer_key.html` is fully spec'd in `.scratch/` with `AnswerKeyData` contract. `key-template.html` provides exact design reference. But neither is implemented yet. |
| **Agent readiness** | 🔴 LOW | No diagnostic or roadmap agents exist. Would need to build from scratch, though the Supervisor + `task()` pattern is well-established. |
| **Pipeline readiness** | 🟡 MEDIUM | The 13-step pipeline is scaffolded (dummy nodes). Adding new steps follows existing patterns. But the pipeline currently assumes class-level generation, not student-level. |
| **Estimated effort** | 🟠 20-30 days | Including schema, agents, templates, pipeline, and frontend. |

### Priority recommendation:

**Phase 1 (MVP — 2 weeks):** Build the answer key generator
- Extend schemas (`essence`, `tip`, `wrongReasons`)
- Implement `answer_key.html` Eta template based on `key-template.html`
- Add answer key as a new artifact type in the pipeline
- This alone would be valuable: teacher inputs an exam → gets a detailed answer key with explanations

**Phase 2 (Full use case — 3-4 weeks):** Add diagnostic + roadmap
- Build `DiagnosticAgent` and `RoadmapAgent`
- Add student profile model
- Create new pipeline flow (diagnostic → roadmap → answer key)
- Implement `roadmap.html` template

**Phase 3 (Polish — 2 weeks):** Frontend integration
- Student profile UI in Next.js dashboard
- Wrong answer input interface
- Roadmap visualization

### Key insight:

The `key-template.html` reference file is the **most valuable artifact** in this evaluation. It demonstrates:
1. The exact data model needed (question + options + answer + explain + wrongReasons + essence + tip)
2. The exact UI design needed (sidebar, grid, color groups, hide/reveal)
3. The exact interaction pattern needed (jump-to-question, mode toggle)

**Building the `answer_key.html` Eta template to match `key-template.html` is the highest-impact first step.** It unblocks D3 (answer key) immediately and provides a concrete deliverable the teacher can use while D1/D2/D4 are being built.

---

## Appendix: File References

| File | Relevance |
|---|---|
| `docs/templates/key-template.html` | 1067-line reference design for answer key HTML |
| `docs/reports/core/01-multi-agent-blueprint.md` | Pipeline architecture, state schema |
| `docs/reports/core/02-quality-gate-harnessing.md` | Quality validation patterns |
| `docs/reports/core/03-html-template-skills.md` | Template system, branding, Eta engine |
| `docs/reports/core/06-exercise-types-catalog.md` | 50+ exercise types with explanation/feedback fields |
| `docs/reports/core/07-educational-content-research.md` | Pedagogical frameworks, Vietnamese support |
| `.scratch/template-library/ISSUE.md` | `answer_key.html` template spec |
| `.scratch/html-template-system/ISSUE.md` | `AnswerKeyData` TypeScript contract |
| `common/contracts/artifact.py` | `ArtifactContent` model (current artifact types) |
| `common/contracts/lesson_plan.py` | `LessonPlan`, `LearningObjective`, `DifferentiationGuide` |
| `common/schemas/src/exercise-types/core.ts` | MCQ schema with `explanation` and `feedback` |
| `packages/agents/state.py` | `OhMyClassState` (current state fields) |
| `packages/agents/graph.py` | 13-step pipeline with conditional routing |
| `packages/renderer/src/renderer.ts` | Core HTML renderer |
| `packages/renderer/templates/pages/` | 6 page template stubs |

---

> **Last updated**: 2026-06-23
> **Next steps**: See Section 7 (Recommendation) for phased implementation plan.
