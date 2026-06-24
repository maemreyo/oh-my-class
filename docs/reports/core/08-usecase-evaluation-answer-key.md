# 08 — Use Case Evaluation: Personalized Answer Key & Learning Roadmap

> **Date**: 2026-06-24
> **Evaluated by**: Sisyphus (multi-agent exploration + librarian research)
> **Scope**: Can oh-my-class handle "teacher inputs wrong answers → personalized learning roadmap + detailed answer key HTML"?
> **References**:
> - `docs/templates/key-template.html` (1067-line static HTML answer key mockup)
> - `docs/templates/path-template.html` (846-line static HTML learning roadmap mockup)

---

## Table of Contents

1. [The Use Case](#1-the-use-case)
2. [Current System Capabilities](#2-current-system-capabilities)
3. [Gap Analysis](#3-gap-analysis)
4. [Template Reference Analysis](#4-template-reference-analysis)
5. [Template Engine Architecture](#5-template-engine-architecture)
6. [What Exists That We Can Leverage](#6-what-exists-that-we-can-leverage)
7. [What Needs to Be Built](#7-what-needs-to-be-built)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Recommendation](#9-recommendation)
10. [Research Findings: AI-Powered Diagnostic Agents](#10-research-findings-ai-powered-diagnostic-agents)
11. [Research Findings: Learning Roadmap Generation](#11-research-findings-learning-roadmap-generation)
12. [Research Findings: Answer Key Wrong Reasoning](#12-research-findings-answer-key-wrong-reasoning)
13. [Research Findings: Template Engine & Component Dispatch](#13-research-findings-template-engine--component-dispatch)
14. [Research Findings: Student Profile & Adaptive Learning](#14-research-findings-student-profile--adaptive-learning)
15. [Updated Development Roadmap](#15-updated-development-roadmap)

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

## 4. Template Reference Analysis

### 4.1 `key-template.html` — Answer Key (1067 lines)

A **static HTML reference** for per-question answer explanations. Contains:

| Element | Lines | Description |
|---|---|---|
| CSS variables | 10-41 | `--paper`, `--ink`, `--red`, `--gold`, `--green`, 5 group colors (`--c-a` through `--c-e`) |
| Shell layout | 66-85 | Sidebar (268px sticky) + main content |
| Sidebar | 101-136 | Navigation, jump-to-question grid (5×10), hide/reveal toggle |
| Hero section | 148-168 | Title, lede, note box, stamp |
| Question cards | 194-275 | Per-question: number badge, text, options grid, correct highlight, explain panel, wrong-reason breakdown, essence, tip |
| Color groups | 276-294 | `.g-a` through `.g-e` applied to cards, badges, nav dots |
| Data section | 408-911 | `SECTIONS` array with 10 sections, 50 questions, each with `explain`, `wrongReasons`, `essence`, `tip` |
| JavaScript | 913-1065 | Render functions, mode toggle, jump-to-question, reveal buttons |

**Key data structures (from the JS `SECTIONS` array):**

```javascript
// Per question:
{
  id: 601,
  text: "We admire Mr. Lam _______ is a great firefighter.",
  options: { A: "who", B: "whose", C: "which", D: "whom" },
  answer: "A",
  explain: "Mệnh đề quan hệ... là <b>who</b>.",
  wrongReasons: {
    B: "<b>Whose</b> diễn tả quan hệ sở hữu...",
    C: "<b>Which</b> chỉ dùng cho vật...",
    D: "<b>Whom</b> thay cho người nhưng đóng vai trò <i>tân ngữ</i>..."
  },
  essence: "Phân biệt chức năng chủ ngữ / tân ngữ...",
  tip: "Nhìn ngay sau chỗ trống: nếu là động từ..."
}

// Per section:
{
  key: "sc", group: "a", title: "Hoàn thành câu",
  sub: "Sentence completion", range: "601–610",
  instruction: "Chọn A, B, C hoặc D...",
  items: [/* questions */]
}
```

**Violates INVARIANT-04**: Uses Google Fonts (Spectral, Be Vietnam Pro, IBM Plex Mono). Must use system font stack.

### 4.2 `path-template.html` — Learning Roadmap (846 lines)

A **static HTML reference** for personalized learning roadmaps. Contains:

| Element | Lines | Description |
|---|---|---|
| Same CSS system | 10-41 | Identical color variables, group colors, paper texture |
| Shell layout | 68-85 | Same sidebar + main pattern |
| Sidebar stats | 112-118 | Current score, target, duration cards |
| Hero section | 126-147 | Title, lede, stamp ("MỤC TIÊU 40+/50"), stat grid (4 cards) |
| Diagnostic table | 415-432 | Error rate by question type with color-coded severity tags |
| Alert cards | 434-451 | Critical gaps (100% error rate sections) |
| Pattern grid | 458-478 | 2-column grid of error patterns with color-coded IDs |
| Trait grid | 582-610 | Student personality traits → teaching principles (2-column) |
| Taxonomy grid | 623-665 | 6 reading comprehension question types with examples |
| Phase timeline | 675-742 | 5 phases with vertical rail, dot markers, goal, blocks, output |
| Flow steps | 769-776 | Lesson structure (50 min flow with time badges) |
| Tables | 415-432, 502-512, 745-758, 785-792 | Data tables with `.dtable` styling |

**Key data structures (from the HTML):**

```javascript
// Phase timeline data:
{
  index: 1,
  title: "Vá lỗi công thức + dựng hệ thống theo dõi",
  when: "Tháng 1 · Tuần 1–4",
  goal: "Sửa dứt điểm các lỗi công thức...",
  blocks: [
    { label: "Giáo trình", items: ["Destination B2 — unit ngữ pháp nền..."] },
    { label: "Hoạt động đặc thù", items: ["Nhập toàn bộ 22 câu sai..."] }
  ],
  output: "Mini-test 20 câu — mục tiêu đúng ≥ 80%..."
}

// Pattern grid data:
{
  id: "C2",
  group: "a",
  title: "enter / arrive at / reach",
  description: "Phân biệt nhóm động từ..."
}

// Trait card data:
{
  icon: "🙊",
  title: "Nhút nhát",
  body: "Ưu tiên luyện kỹ năng hội thoại qua..."
}
```

### 4.3 Shared Design System

Both templates share an identical design system:

| Token | Value | Purpose |
|---|---|---|
| `--paper` | `#FBF4F0` | Background |
| `--card` | `#FFFFFF` | Card background |
| `--ink` | `#22273A` | Primary text |
| `--ink-soft` | `#5C6275` | Secondary text |
| `--ink-faint` | `#8B8FA0` | Tertiary text |
| `--line` | `#E8D8CD` | Borders |
| `--red` | `#B23A2E` | Errors, correct answers |
| `--gold` | `#A8782E` | Emphasis, labels |
| `--green` | `#2E6F4E` | Success, targets |
| `--c-a` through `--c-e` | 5 colors | Content group coding |
| `--radius` | `12px` | Border radius |
| `--shadow` | `0 1px 2px...` | Card shadows |

**Fonts**: Spectral (headings), Be Vietnam Pro (body), IBM Plex Mono (labels) — must be replaced with system font stack.

---

## 5. Template Engine Architecture

### 5.1 Current State

The renderer (`packages/renderer/src/renderer.ts`) is a **115-line scaffold**:

```typescript
// Current: manual HTML string building, NOT using Eta templates
function buildContentHtml(data: ArtifactContent): string {
  const sections = data.sections ?? [];
  const sectionsHtml = sections.map((s) => {
    const title = typeof s["title"] === "string" ? `<h2>${s["title"]}</h2>` : "";
    const content = typeof s["content"] === "string" ? `<p>${s["content"]}</p>` : "";
    return `    <section>${title}${content}</section>`;
  }).join("\n");
  return `    <h1>${data.title}</h1>\n${sectionsHtml}`;
}
```

**Problems:**
1. `ArtifactContent.sections` is `list[dict[str, Any]]` — no type safety, LLM invents structure ad-hoc
2. `buildContentHtml()` builds flat HTML — no component dispatch, no reusability
3. Page templates exist but are stubs (`'TODO: lesson content'`)
4. Component templates exist but aren't wired in
5. No layout inheritance (base.html exists but isn't used by renderArtifact)

### 5.2 Proposed Architecture: Component Dispatcher Pattern

**Core insight from research**: The LLM generates a flat `components` array of typed blocks. A single dispatcher routes each block to its Eta partial. This is the same pattern used by Khan Academy's Perseus widget registry and Vercel's json-render catalog.

```
Content Creator Agent (LLM)
  │  Returns structured JSON with typed components
  ▼
Zod Validation (Layer 1 quality gate)
  │  Validates every ContentComponent via discriminated union
  ▼
Eta Renderer
  │  pages/answer_key.eta
  │    → components/dispatcher.eta (switch on component.type)
  │      → components/question_card.eta
  │      → components/stat_grid.eta
  │      → components/phase_timeline.eta
  │      → etc.
  ▼
Sanitizer + Asset Inliner
  │  DOMPurify + theme CSS inlined
  ▼
Standalone HTML (no CDN, no external assets)
```

### 5.3 Discriminated Component Union (Schema)

Replace the opaque `sections: list[dict]` with a typed component system:

```typescript
// common/schemas/src/components.ts

type ContentComponent =
  // Textual
  | { type: "heading"; level: 1|2|3|4; text: string; id?: string }
  | { type: "paragraph"; text: string }
  | { type: "callout"; variant: "note"|"warning"|"tip"|"alert"; title?: string; body: string }
  | { type: "ordered_list"; items: string[] }
  | { type: "unordered_list"; items: string[] }

  // Tabular
  | { type: "table"; columns: string[]; rows: string[][]; caption?: string }

  // Cards & Grids
  | { type: "stat_grid"; stats: Array<{ label: string; value: string; variant?: "target"|"now"|"default" }> }
  | { type: "pattern_grid"; patterns: Array<{ id: string; group: string; title: string; description: string }> }
  | { type: "trait_grid"; traits: Array<{ icon: string; title: string; body: string }> }
  | { type: "taxonomy_grid"; items: Array<{ icon: string; title: string; body: string; example: string }> }

  // Timeline & Flow
  | { type: "phase_timeline"; phases: RoadmapPhase[] }
  | { type: "flow_step"; steps: Array<{ time: string; title: string; body: string }> }

  // Question-specific
  | { type: "question_card";
      id: number|string; text: string; options: Record<string,string>;
      answer: string; explain: string; group: string;
      wrongReasons?: Record<string,string>; essence?: string; tip?: string }
  | { type: "question_list";
      questions: ContentComponent[]; // nested question_cards
      sectionKey: string; group: string; title: string; sub?: string;
      instruction?: string; summary?: string; range?: string }

  // Concept
  | { type: "concept_map"; nodes: Array<{ id: string; label: string }> }
  | { type: "timeline"; events: Array<{ time: string; label: string }> }
```

**Per-artifact schemas:**

```typescript
interface AnswerKeyContent {
  artifact_type: "answer_key";
  title: string;
  theme: string;
  sections: Array<{
    id: string;
    title: string;
    range: string;
    group: string;         // color group: a,b,c,d,e
    components: ContentComponent[];
  }>;
  metadata: {
    totalQuestions: number;
    totalCorrect: number;
    groups: Record<string, { label: string; color: string }>;
  };
  accessibility: { language: string };
}

interface RoadmapContent {
  artifact_type: "roadmap";
  title: string;
  theme: string;
  hero: { eyebrow: string; title: string; lede: string; stamp: string; stats: StatCard[] };
  sections: Array<{
    id: string;
    title: string;
    subtitle?: string;
    tagNum?: string;
    components: ContentComponent[];
  }>;
  sidebar: { title: string; subtitle: string; stats: StatCard[]; nav: NavItem[]; legend: LegendItem[] };
  accessibility: { language: string };
}
```

### 5.4 Eta Template Hierarchy

```
templates/
├── base.eta                          # HTML shell: DOCTYPE, head, style, body, footer
├── pages/
│   ├── answer_key.eta                # Sidebar + hero + section loop → dispatcher
│   ├── roadmap.eta                   # Sidebar + hero + section loop → dispatcher
│   ├── lesson.eta                    # (existing stub → implement)
│   ├── worksheet.eta
│   ├── quiz.eta
│   ├── drill.eta
│   ├── recap.eta
│   └── infographic.eta
├── components/
│   ├── dispatcher.eta                # THE ROUTER: switch(component.type) → include partial
│   ├── sidebar.eta                   # Navigation, stats, legend, jump grid
│   ├── hero.eta                      # Title, lede, stamp, stat grid
│   ├── heading.eta
│   ├── paragraph.eta
│   ├── callout.eta                   # Note/warning/tip/alert boxes
│   ├── table.eta                     # Data tables with .dtable styling
│   ├── stat_grid.eta                 # 4-column stat cards
│   ├── pattern_grid.eta              # 2-column error pattern cards
│   ├── trait_grid.eta                # 2-column student trait cards
│   ├── taxonomy_grid.eta             # 2-column taxonomy cards
│   ├── phase_timeline.eta            # Vertical timeline with phases
│   ├── flow_step.eta                 # Lesson flow with time badges
│   ├── question_card.eta             # THE core: options, explain, wrongReasons, essence, tip
│   ├── question_list.eta             # Section wrapper + iterates question_card
│   ├── alert.eta                     # Critical gap alerts
│   └── note_callout.eta              # Gold-bordered note boxes
└── branding/
    └── theme_*.css                   # Auto-generated from theme.json
```

### 5.5 The Dispatcher (`components/dispatcher.eta`)

This is the **architectural keystone** — a single routing point that maps component types to templates:

```eta
<% switch (it.component.type) { %>
  <% case "heading" { %>
    <%~ include("./heading", it.component) %>
  <% } %>
  <% case "paragraph" { %>
    <%~ include("./paragraph", it.component) %>
  <% } %>
  <% case "callout" { %>
    <%~ include("./callout", it.component) %>
  <% } %>
  <% case "table" { %>
    <%~ include("./table", it.component) %>
  <% } %>
  <% case "stat_grid" { %>
    <%~ include("./stat_grid", it.component) %>
  <% } %>
  <% case "pattern_grid" { %>
    <%~ include("./pattern_grid", it.component) %>
  <% } %>
  <% case "trait_grid" { %>
    <%~ include("./trait_grid", it.component) %>
  <% } %>
  <% case "taxonomy_grid" { %>
    <%~ include("./taxonomy_grid", it.component) %>
  <% } %>
  <% case "phase_timeline" { %>
    <%~ include("./phase_timeline", it.component) %>
  <% } %>
  <% case "flow_step" { %>
    <%~ include("./flow_step", it.component) %>
  <% } %>
  <% case "question_card" { %>
    <%~ include("./question_card", it.component) %>
  <% } %>
  <% case "question_list" { %>
    <%~ include("./question_list", it.component) %>
  <% } %>
  <% case "alert" { %>
    <%~ include("./alert", it.component) %>
  <% } %>
  <% case "note_callout" { %>
    <%~ include("./note_callout", it.component) %>
  <% } %>
  <% case "concept_map" { %>
    <%~ include("./concept_map", it.component) %>
  <% } %>
  <% case "timeline" { %>
    <%~ include("./timeline", it.component) %>
  <% } %>
<% } %>
```

### 5.6 Page Template Example (`pages/answer_key.eta`)

```eta
<% layout("../base", { title: it.title, lang: it.accessibility?.language || 'vi' }) %>

<% block("styles", () => { %>
  <%~ it.themeCss %>
  /* Answer-key-specific styles */
  .shell { display:flex; max-width:1280px; margin:0 auto; min-height:100vh; }
  .sidebar { width:268px; flex-shrink:0; position:sticky; top:0; ... }
  .main { flex:1; min-width:0; padding:38px 44px 100px; }
  /* ... all component styles from key-template.html ... */
<% }) %>

<% block("content", () => { %>
  <div class="shell">
    <aside class="sidebar">
      <%~ include("../components/sidebar", { sections: it.sections, metadata: it.metadata }) %>
    </aside>
    <main class="main">
      <%~ include("../components/hero", it) %>
      <% it.sections.forEach(function(section) { %>
        <section class="section" id="<%= section.id %>">
          <div class="section-head">
            <h2><%= section.title %></h2>
            <span class="sub"><%= section.sub %></span>
            <span class="rng rng-<%= section.group %>"><%= section.range %></span>
          </div>
          <% if (section.instruction) { %>
            <p class="section-instr"><%= section.instruction %></p>
          <% } %>
          <% if (section.summary) { %>
            <div class="summary"><%~ section.summary %></div>
          <% } %>
          <% section.components.forEach(function(comp) { %>
            <%~ include("../components/dispatcher", { component: comp }) %>
          <% }); %>
        </section>
      <% }); %>
    </main>
  </div>
<% }) %>
```

### 5.7 Component Template Example (`components/question_card.eta`)

```eta
<%-- templates/components/question_card.eta --%>
<div class="qcard g-<%= it.group %>" id="q<%= it.id %>">
  <div class="qhead">
    <span class="qnum">#<%= it.id %></span>
    <div class="qtext"><%~ it.text %></div>
  </div>

  <div class="options">
    <% Object.entries(it.options).forEach(function([letter, text]) { %>
      <div class="option<%= letter === it.answer ? ' correct' : '' %>">
        <b class="letter"><%= letter %>.</b>
        <span><%~ text %></span>
      </div>
    <% }); %>
  </div>

  <div class="panel">
    <div class="prow explain">
      <span class="plabel">Giải thích</span>
      <span class="ptext"><%~ it.explain %></span>
    </div>

    <% if (it.wrongReasons && Object.keys(it.wrongReasons).length > 0) { %>
      <div class="wrong-section">
        <span class="wrong-section-label">❌ Tại sao các đáp án sai không đúng</span>
        <div class="wrong-list">
          <% Object.entries(it.wrongReasons).forEach(function([letter, reason]) { %>
            <div class="wrong-item">
              <span class="wletter"><%= letter %></span>
              <div class="wbody">
                <div class="woption">"<%= it.options[letter] || '' %>"</div>
                <div class="wreason"><%~ reason %></div>
              </div>
            </div>
          <% }); %>
        </div>
      </div>
    <% } %>

    <% if (it.essence) { %>
      <div class="prow essence">
        <span class="plabel">Bản chất</span>
        <span class="ptext"><%~ it.essence %></span>
      </div>
    <% } %>

    <% if (it.tip) { %>
      <div class="prow tip">
        <span class="plabel">Mẹo làm bài</span>
        <span class="ptext"><%~ it.tip %></span>
      </div>
    <% } %>
  </div>
</div>
```

### 5.8 Component Template Example (`components/phase_timeline.eta`)

```eta
<%-- templates/components/phase_timeline.eta --%>
<% it.phases.forEach(function(phase, index) { %>
  <div class="phase">
    <div class="ph-rail">
      <div class="ph-dot" style="background:var(--c-<%= phase.group || 'a' %>)"><%= index + 1 %></div>
      <% if (index < it.phases.length - 1) { %>
        <div class="ph-line"></div>
      <% } %>
    </div>
    <div class="phase-body">
      <div class="phase-card">
        <div class="ph-top">
          <h4><%= phase.title %></h4>
          <span class="ph-when"><%= phase.when %></span>
        </div>
        <% if (phase.goal) { %>
          <p class="ph-goal"><%= phase.goal %></p>
        <% } %>
        <div class="phase-grid">
          <% phase.blocks.forEach(function(block) { %>
            <div class="phase-block<%= block.full ? ' full' : '' %>">
              <span class="lbl"><%= block.label %></span>
              <% if (block.items) { %>
                <ul>
                  <% block.items.forEach(function(item) { %>
                    <li><%~ item %></li>
                  <% }); %>
                </ul>
              <% } %>
              <% if (block.text) { %>
                <span><%~ block.text %></span>
              <% } %>
            </div>
          <% }); %>
        </div>
        <% if (phase.output) { %>
          <div class="ph-output">
            <span class="lbl">Output cuối giai đoạn</span>
            <span><%~ phase.output %></span>
          </div>
        <% } %>
      </div>
    </div>
  </div>
<% }); %>
```

### 5.9 Dynamic Theming (3-Tier Token System)

Extend `theme.json` with group colors:

```json
{
  "colors": {
    "paper": "#FBF4F0", "card": "#FFFFFF", "ink": "#22273A",
    "red": "#B23A2E", "gold": "#A8782E", "green": "#2E6F4E"
  },
  "groups": {
    "a": { "color": "#33508F", "label": "Ngữ pháp – Từ vựng" },
    "b": { "color": "#B9762A", "label": "Hội thoại" },
    "c": { "color": "#3C7A4E", "label": "Viết lại / Kết hợp câu" },
    "d": { "color": "#1F7A8C", "label": "Điền từ & Đọc hiểu" },
    "e": { "color": "#8A4F7E", "label": "Tư duy logic" }
  },
  "typography": {
    "font-heading": "Georgia, 'Times New Roman', serif",
    "font-body": "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    "font-mono": "'SF Mono', 'Fira Code', 'Cascadia Code', monospace"
  }
}
```

`generate_theme.py` outputs:
```css
:root {
  --paper: #FBF4F0; --card: #FFFFFF; --ink: #22273A;
  --c-a: #33508F; --c-a-tint: rgba(51,80,143,0.08);
  --c-b: #B9762A; --c-b-tint: rgba(185,118,42,0.09);
  /* ... */
  --font-heading: Georgia, 'Times New Roman', serif;
  --font-body: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}
.g-a { border-left-color: var(--c-a); }
.g-a .qnum, .g-a .pc-id { background: var(--c-a); }
/* ... */
@media print { .sidebar { display:none; } .shell { display:block; } }
@media (prefers-color-scheme: dark) { :root { --paper: #1a1a2e; ... } }
```

### 5.10 Updated `renderArtifact()` Function

```typescript
// packages/renderer/src/renderer.ts — revised
import { Eta } from "eta";
import path from "node:path";
import { sanitizeHtml } from "./sanitizer.js";
import { loadThemeCss } from "./theme.js";

const eta = new Eta({
  views: path.join(import.meta.dirname, "../templates"),
  cache: true,
});

export function renderArtifact(data: ArtifactContent): string {
  const templateKey = data.artifact_type;
  const themeCss = loadThemeCss(data.theme ?? "default");

  // Eta layout + block system handles composition
  const html = eta.render(`./pages/${templateKey}`, {
    ...data,
    themeCss,
  });

  return sanitizeHtml(html);
}
```

### 5.11 Education Platform Patterns (Research Findings)

| Platform | Pattern | Applicable to oh-my-class |
|---|---|---|
| **Khan Academy Perseus** | Widget registry: each interactive element has a registered type, Zod parser, renderer, scorer. Content is JSON referencing widgets. | ContentComponent = widget; dispatcher = widget resolver; Zod = parser |
| **Vercel json-render** | Catalog → Registry → Spec → Render. LLM generates flat `elements` dictionary; streaming via JSON patches. | Catalog = Zod schemas; Registry = Eta templates; LLM emits `components` array |
| **Duolingo** | Deeply nested data: Course → Unit → Skill → Lesson → Sentence. API returns JSON; client renders. | ArtifactContent → sections → components → nested question_cards |
| **swagger-typescript-api** | Largest Eta production use: `base/` shared templates + `default/`/`modular/` page templates, `includeFile()` with path prefixes | base.eta + pages/ + components/ with `include()` |

**Key insight from json-render**: *"The AI does not return raw HTML. You give the AI a fixed set of allowed components and a strict JSON Schema for each component's props. The AI can compose only within those constraints."* — This is exactly the discriminated union approach.

---

## 6. What Exists That We Can Leverage

### Reusable components:

| Component | Location | Reuse for |
|---|---|---|
| Exercise type schemas | `common/schemas/src/exercise-types/` | Question data model for answer key |
| `ArtifactContent` model | `common/contracts/artifact.py` | Base for new answer key/roadmap types |
| `DifferentiationGuide` | `common/contracts/lesson_plan.py` | Student profile scaffolding |
| `LearningObjective` + `bloom_level` | `common/contracts/lesson_plan.py` | Mapping wrong answers to Bloom gaps |
| Feedback component | `packages/renderer/templates/components/feedback.html` | Correct/incorrect display |
| Question components | `packages/renderer/templates/components/question_*.html` | Question rendering (partial) |
| Quality gate system | `packages/quality/` | Validate answer key quality |
| `key-template.html` design | `docs/templates/key-template.html` | Reference for answer key template |
| `path-template.html` design | `docs/templates/path-template.html` | Reference for roadmap template |
| Shared design system | Both templates | CSS variables, group colors, layout shell |
| Vietnamese Bloom mapping | `docs/reports/core/06-exercise-types-catalog.md` | HSA-specific gap analysis |
| `generate_theme.py` | `common/branding/` | Theme CSS generation (extend with groups) |

### Architectural patterns to follow:

| Pattern | From | Apply to |
|---|---|---|
| Supervisor + `task()` delegation | Lead Agent architecture | New Diagnostic Agent |
| LangGraph `interrupt()` for teacher gates | Teacher Gate 1/2 | Roadmap approval gate |
| Eta layout + block system | Eta v4 docs | base.eta → page.eta composition |
| Component dispatcher | Khan Perseus / json-render | dispatcher.eta routing |
| Discriminated union schemas | Pydantic 2.10+ / Zod | ContentComponent type safety |
| FACT protocol | Researcher Agent | Wrong answer analysis |
| G-Eval scoring | Reviewer Agent | Answer key quality validation |

---

## 7. What Needs to Be Built

### New components (in priority order):

| # | Component | Type | Effort | Blocks |
|---|---|---|---|---|
| 1 | `ContentComponent` discriminated union | Schema | 2 days | D3, D2 |
| 2 | `AnswerKeyContent` schema | Schema | 1 day | D3 |
| 3 | `RoadmapContent` schema | Schema | 1 day | D2 |
| 4 | `StudentResponse` schema | Contract | 0.5 days | D1 |
| 5 | `DiagnosticReport` schema | Contract | 1 day | D1 |
| 6 | `StudentProfile` schema | Contract | 1 day | D4 |
| 7 | `dispatcher.eta` | Template | 1 day | All templates |
| 8 | `question_card.eta` | Template | 2 days | D3 |
| 9 | `answer_key.eta` page | Template | 2 days | D3 |
| 10 | `phase_timeline.eta` + `stat_grid.eta` + `pattern_grid.eta` + `trait_grid.eta` + `taxonomy_grid.eta` + `callout.eta` + `table.eta` | Templates | 3-4 days | D2 |
| 11 | `roadmap.eta` page | Template | 2 days | D2 |
| 12 | `sidebar.eta` + `hero.eta` | Templates | 1-2 days | D3, D2 |
| 13 | Rewrite `renderArtifact()` to use Eta dispatch | Renderer | 1-2 days | All |
| 14 | Extend `theme.json` + `generate_theme.py` with group colors | Theme | 1 day | D3, D2 |
| 15 | `DiagnosticAgent` | Agent | 3-5 days | D1 |
| 16 | `RoadmapAgent` | Agent | 3-5 days | D2 |
| 17 | New pipeline step(s) | Graph | 2-3 days | All |
| 18 | Student profile UI in dashboard | Frontend | 3-5 days | D4 |
| **Total** | | | **~30-40 days** | |

---

## 8. Implementation Roadmap

### Phase 1: Template Engine Foundation (Week 1-2)

**Goal**: Build the component dispatcher system so both answer key and roadmap can be rendered.

| Step | Files | What | Why |
|---|---|---|---|
| 1.1 | `common/schemas/src/components.ts` | Define `ContentComponent` discriminated union (14+ types) | Foundation for type safety |
| 1.2 | `common/contracts/artifact.py` | Add `AnswerKeyContent`, `RoadmapContent` Pydantic models | Python-side validation |
| 1.3 | `packages/renderer/templates/components/dispatcher.eta` | Create the component router | Architectural keystone |
| 1.4 | `packages/renderer/templates/base.eta` | Rewrite with layout + block system | Enables page composition |
| 1.5 | `packages/renderer/src/renderer.ts` | Rewrite `renderArtifact()` to use Eta dispatch | Unlocks template system |
| 1.6 | `common/branding/generate_theme.py` | Add group color tokens + utility CSS | Matches reference designs |

### Phase 2: Answer Key Template (Week 2-3)

**Goal**: Implement `answer_key.html` to match `key-template.html` design.

| Step | Files | What | Why |
|---|---|---|---|
| 2.1 | `components/question_card.eta` | Core component: options, explain, wrongReasons, essence, tip | Most complex component |
| 2.2 | `components/sidebar.eta` | Navigation, jump grid, hide/reveal toggle, legend | Shared across both templates |
| 2.3 | `components/hero.eta` | Title, lede, stamp, stat grid | Shared across both templates |
| 2.4 | `components/table.eta` | Data tables with `.dtable` styling | Used in both templates |
| 2.5 | `components/callout.eta` + `note_callout.eta` + `alert.eta` | Note/warning/tip/alert boxes | Used in both templates |
| 2.6 | `pages/answer_key.eta` | Full page: sidebar + hero + section loop → dispatcher | The deliverable |
| 2.7 | Extend exercise schemas: add `essence`, `tip`, `wrongReasons` | New fields per question | Required by question_card |
| 2.8 | Test: render key-template.html data through Eta pipeline | Verify output matches reference | Quality gate |

### Phase 3: Roadmap Template (Week 3-4)

**Goal**: Implement `roadmap.html` to match `path-template.html` design.

| Step | Files | What | Why |
|---|---|---|---|
| 3.1 | `components/stat_grid.eta` | 4-column stat cards | Hero stats |
| 3.2 | `components/pattern_grid.eta` | 2-column error pattern cards | Diagnostic section |
| 3.3 | `components/trait_grid.eta` | 2-column student trait cards | Teaching method section |
| 3.4 | `components/taxonomy_grid.eta` | 2-column taxonomy cards | Reading comprehension types |
| 3.5 | `components/phase_timeline.eta` | Vertical timeline with phases | Roadmap phases |
| 3.6 | `components/flow_step.eta` | Lesson flow with time badges | Operations section |
| 3.7 | `pages/roadmap.eta` | Full page: sidebar + hero + section loop → dispatcher | The deliverable |
| 3.8 | Test: render path-template.html data through Eta pipeline | Verify output matches reference | Quality gate |

### Phase 4: Agents + Pipeline (Week 4-6)

**Goal**: Build diagnostic and roadmap agents, wire into pipeline.

| Step | Files | What | Why |
|---|---|---|---|
| 4.1 | `packages/agents/sub_agents/diagnostician/` | DiagnosticAgent: analyze wrong answers → DiagnosticReport | D1 core |
| 4.2 | `packages/agents/sub_agents/roadmap/` | RoadmapAgent: DiagnosticReport → LearningRoadmap | D2 core |
| 4.3 | `packages/agents/graph.py` | Add diagnostic + roadmap steps to pipeline | Integration |
| 4.4 | Extend Content Creator prompt | Add answer key + roadmap generation instructions | LLM guidance |
| 4.5 | End-to-end test: teacher input → diagnostic → roadmap → answer key | Full pipeline verification | Quality gate |

### Phase 5: Polish (Week 6-8)

**Goal**: Frontend integration, student profile, dark mode, print styles.

| Step | Files | What | Why |
|---|---|---|---|
| 5.1 | `apps/web/` | Student profile UI, wrong answer input | Teacher experience |
| 5.2 | Dark mode CSS | `@media (prefers-color-scheme: dark)` | Accessibility |
| 5.3 | Print styles | `@media print` with `.no-print`, `.page-break` | Offline use |
| 5.4 | Responsive testing | Verify 375/768/1280/1920px viewports | Quality gate |

---

## 9. Recommendation

### Verdict: The system **cannot** handle this use case today. But the template engine architecture is **clear and feasible**.

### What we're really building:

The core deliverable is a **template generation engine** — not just two templates. Once the component dispatcher pattern is in place:

- **New artifact types** = new Zod schema variant + new `.eta` page template + new component partials
- **LLM generates typed JSON** → Zod validates → Eta renders → sanitizer cleans → standalone HTML
- **Adding a new visual component** = new `.eta` file + one `case` in dispatcher + one Zod variant

This is a **composable, extensible system** — not a one-off build.

### Feasibility assessment:

| Dimension | Rating | Notes |
|---|---|---|
| **Template engine architecture** | 🟢 HIGH | Dispatcher pattern is proven (Khan Perseus, json-render). Eta v4 supports layout + blocks natively. |
| **Reference designs** | 🟢 HIGH | `key-template.html` (1067 lines) and `path-template.html` (846 lines) are complete, functional references. Slice into components. |
| **Schema readiness** | 🟡 MEDIUM | Exercise schemas have `explanation`/`feedback`. Need `essence`, `tip`, `wrongReasons`, `ContentComponent` union. |
| **Current renderer** | 🔴 LOW | `renderer.ts` is a 115-line scaffold with manual HTML building. Must rewrite to use Eta dispatch. |
| **Agent readiness** | 🔴 LOW | No diagnostic or roadmap agents. Need to build from scratch. |
| **Estimated effort** | 🟠 30-40 days | Template engine (2 weeks) + answer key (1 week) + roadmap (1 week) + agents (2 weeks) + polish (2 weeks) |

### Key insight:

The `path-template.html` adds significant complexity beyond `key-template.html` — it introduces 7 new component types (stat_grid, pattern_grid, trait_grid, taxonomy_grid, phase_timeline, flow_step, alert) that the answer key doesn't need. But the **design system is identical** (same CSS variables, same shell layout, same sidebar pattern). This means:

1. Build the shared design system first (CSS tokens, sidebar, hero, dispatcher)
2. Build `question_card.eta` for the answer key (highest value, most complex single component)
3. Build the remaining 7 components for the roadmap
4. The LLM generates the same `ContentComponent` JSON for both — the template engine renders different pages

**The dispatcher pattern means the template engine is the product, not the individual templates.**

### Priority recommendation:

**Phase 1 (Week 1-2):** Build the template engine foundation
- Discriminated `ContentComponent` union
- `dispatcher.eta` + `base.eta` with layout/blocks
- Rewrite `renderArtifact()` to use Eta dispatch
- Extend `theme.json` with group colors

**Phase 2 (Week 2-3):** Answer key template
- `question_card.eta` (the most valuable single component)
- `sidebar.eta` + `hero.eta` (shared)
- `pages/answer_key.eta`
- Extend schemas with `essence`, `tip`, `wrongReasons`

**Phase 3 (Week 3-4):** Roadmap template
- 7 new component partials
- `pages/roadmap.eta`

**Phase 4 (Week 4-6):** Agents + pipeline
- DiagnosticAgent, RoadmapAgent
- Pipeline integration

**Phase 5 (Week 6-8):** Polish
- Frontend, dark mode, print, responsive

### Appendix: File References

| File | Relevance |
|---|---|
| `docs/templates/key-template.html` | 1067-line reference: answer key with 50 questions, wrongReasons, essence, tip |
| `docs/templates/path-template.html` | 846-line reference: 9-section roadmap with diagnostic, phases, traits, taxonomy |
| `packages/renderer/src/renderer.ts` | Current 115-line renderer (must rewrite) |
| `packages/renderer/templates/base.html` | Current base shell (must upgrade to layout/blocks) |
| `packages/renderer/templates/components/` | 15 existing component stubs |
| `common/schemas/src/exercise-types/` | Exercise type definitions with `explanation`/`feedback` |
| `common/contracts/artifact.py` | `ArtifactContent` model (must extend) |
| `common/branding/generate_theme.py` | Theme CSS generator (must extend with groups) |
| `.scratch/template-library/ISSUE.md` | `answer_key.html` template spec |
| `.scratch/html-template-system/ISSUE.md` | `AnswerKeyData` TypeScript contract |
| `docs/reports/core/03-html-template-skills.md` | Template system design decisions |
| `docs/reports/core/06-exercise-types-catalog.md` | 50+ exercise types with Vietnamese Bloom mapping |

---

> **Last updated**: 2026-06-24
> **Next steps**: See Section 8 (Implementation Roadmap) for phased build plan.
> **Key deliverable**: The template engine (dispatcher + component partials) is the product — not the individual templates.

---

---


## 10. Research Findings: AI-Powered Diagnostic Agents

### 10.1 Production Platforms

| Platform | Diagnostic Approach | Key Technique | Maturity |
|---|---|---|---|
| **Khan Academy (Khanductor)** | 3-agent stack: Diagnostic + Curriculum + Instruction Agent | Socratic prompting, dynamic resequencing | Production |
| **Khan Academy (Khanmigo)** | LLM-based 1v1 tutoring with diagnostic overlay | GPT-4 class models, conversation log | Production (US pilot) |
| **Duolingo (Explain My Answer)** | LLM generates per-response explanations | GPT-4 fine-tuned on tutor dialogues | Production |
| **Century Tech** | Deep Knowledge Tracing (DKT) with Bayesian inference | DKT-based knowledge state estimation per skill | Production (UK) |
| **Squirrel AI** | Nano-level knowledge decomposition + root-cause tracing | 10,000+ microscopic knowledge points per subject | Production (China) |
| **Third Space Learning (Skye)** | Diagnostic-driven 1v1 adaptation | Real-time misconception detection during live tutoring | Production (UK) |
| **Carnegie Learning (MATHia)** | Cognitive Tutor with fine-grained error tagging | 9-code error taxonomy per step in problem-solving | Production (US) |

**Key insight**: Every major platform uses a diagnostic-first approach. The diagnostic phase drives all subsequent personalization.

### 10.2 Error Pattern Detection

**The Correct Answer Trap (arXiv 2606.23205)**

A critical finding: when students get an answer correct by accident (guessing, flawed logic that happens to match), the system must detect this. Without LLM verification, only 57% of these "correct but wrong-process" cases are caught. With LLM verification, detection rises to 84%.

```
Student response: answer matches expected output
  |
  +- Verify: is the student's reasoning sound?
  |    +- YES -> mark as genuinely correct
  |    +- NO  -> flag as "Correct Answer Trap" -> route to misconception analysis
  +- Impact on roadmap: trapped correct answers inflate perceived mastery
```

**ErrorRadar (ACL 2026)**

A multi-task learning framework for error detection in math word problems. Achieves 82% macro-F1 across 9 error types.

**MalruleLib (ACL 2026)**

A library of executable misconceptions for algebra. Each misconception is an executable rule that can be injected into a symbolic solver to reproduce the student's error.

```
Algebra Error       -> Executable Rule
---------------------------------------------
Sign flip           -> multiply_both_sides: -1 -> +1 bug
Distribution miss   -> a(b+c) -> ab + c (not ac)
Cancellation skip   -> (ab)/b -> a (correct), (a+b)/b -> a (incorrect)
```

### 10.3 Misconception Detection

**MiRAGE (arXiv 2602.02414)**

A retrieval-augmented generation approach for misconception detection. Given a student response and a knowledge component (KC), MiRAGE retrieves relevant misconceptions from a library and generates explanations.

| Metric | MiRAGE | Baseline (GPT-4o) | Improvement |
|---|---|---|---|
| MAP@3 | 0.82 | 0.71 | +15.5% |
| Recall@5 | 0.91 | 0.78 | +16.7% |
| F1 (misconception detection) | 0.76 | 0.64 | +18.8% |

**Cognitive-Uncertainty-Guided Knowledge Distillation (arXiv 2605.14752)**

A teacher-student framework for knowledge tracing with cognitive uncertainty quantification. The teacher model identifies which student responses have high uncertainty (ambiguous errors), and the student model learns to handle these cases better.

| Metric | Baseline | With Uncertainty Guidance | Improvement |
|---|---|---|---|
| MAP@3 | 0.51 | 0.60 | +17.8% |
| AUC | 0.82 | 0.87 | +6.1% |
| RMSE | 0.38 | 0.34 | -10.5% |

### 10.4 Bloom's Taxonomy Auto-Classification

| Method | Accuracy / F1 | Domain | Speed |
|---|---|---|---|
| CNN + fastText (Naik and Sripada, 2025) | 88% macro-F1 | General education questions | Fast (< 1ms) |
| DistilBERT fine-tuned | 96% accuracy | 6-class Bloom classification | Moderate (10ms) |
| Zero-shot LLM (GPT-4o) | 82% accuracy | Any domain | Slow (500ms+) |
| RoBERTa + ensemble | 93% macro-F1 | Vietnamese education (HSA) | Moderate (15ms) |

**Recommendation**: Use DistilBERT fine-tuned for Vietnamese Bloom classification as primary, with LLM zero-shot as fallback.

### 10.5 Multi-Agent LangGraph Patterns

Several open-source projects demonstrate the multi-agent diagnostic pattern:

**stem-tutor-agent** ([github.com/datamove/stem-tutor-agent](https://github.com/datamove/stem-tutor-agent))
- LangGraph-based STEM tutor with 4 agents: Symptom -> Diagnosis -> Remedy -> Check
- State machine with checkpointing via MemorySaver/SqliteSaver
- Error taxonomy mapped to executable remediation steps

**MathTutor** ([github.com/YourFriendFakhri/MathTutorAgent](https://github.com/YourFriendFakhri/MathTutorAgent))
- 3-agent system: Problem Analyzer -> Solution Generator -> Solution Verifier
- LangGraph + LiteLLM integration

**Adaptive-Personalized-Learning-System**
- Multi-agent: Student Modeler -> Content Matcher -> Pathway Planner -> Assessment Generator
- Redis for state persistence, PostgreSQL for student profiles

### 10.6 Error Taxonomy

Carnegie Learning MATHia + ErrorRadar + MalruleLib consolidated 9-code taxonomy:

| Code | Error Type | Description | Example |
|---|---|---|---|
| E01 | SIGN_ARITHMETIC_ERROR | Sign handling mistakes | -2 x -3 = -6 (should be +6) |
| E02 | COEFFICIENT_OMISSION | Dropping or misreading coefficients | 3x + 5 = 2x + 3, drops signs |
| E03 | DOMAIN_CONDITION_IGNORED | Forgetting domain restrictions | sqrt(x-2) = 3 -> x=11, domain unchecked |
| E04 | DISTRIBUTION_ERROR | Incorrect distribution over parentheses | 2(x+3) = 2x+3 (should be 2x+6) |
| E05 | ORDER_OF_OPS | PEMDAS violations | 3 + 4 x 2 = 14 (should be 11) |
| E06 | UNITS_MISMATCH | Inconsistent or missing units | 5 cm + 3 m = 8 (no conversion) |
| E07 | COMPARISON_REVERSAL | Reversed inequality direction | -3x > 9 -> x > -3 (should be x < -3) |
| E08 | PARTIAL_APPLICATION | Partially applying a rule | (a+b)2 = a2 + b2 (missing 2ab) |
| E09 | CONCEPTUAL_MISUNDERSTANDING | Deep concept misunderstanding | 'whom' always correct for people |

### 10.7 Verification Pattern

```
Student Response
  |
  +- L1: Symbolic Verification (SymPy)
  |    +- Check algebraic equivalence between student and correct solution
  |    +- If equivalent -> route to L2 (may be Correct Answer Trap)
  |    +- If different -> route to L3 error classification
  |
  +- L2: Numerical Sampling
  |    +- Plug random values into both solutions; compare outputs
  |    +- If diverging -> route to L3
  |    +- If matching but reasoning is flawed -> Correct Answer Trap flag
  |
  +- L3: LLM Escalation
  |    +- LLM analyzes reasoning, maps to error taxonomy
  |    +- Returns error type E01-E09 + explanation
  |
  +- L4: Teacher Confirmation (via interrupt)
       +- Teacher reviews diagnosis, can override or add notes
```

### 10.8 Recommended Architecture for oh-my-class

```python
class DiagnosticState(TypedDict):
    student_responses: list[StudentResponse]
    error_analysis: list[ErrorAnalysis]
    misconception_map: dict[str, Misconception]
    bloom_profile: BloomProfile
    diagnostic_report: DiagnosticReport
    verification_level: int  # 1-4

def verify_node(state: DiagnosticState) -> DiagnosticState:
    """L1-L3: Symbolic, numerical, LLM verification."""
    pass  # Implement per Section 10.7

def diagnose_node(state: DiagnosticState) -> DiagnosticState:
    """Map verified errors to error taxonomy + misconceptions."""
    pass

def analyze_bloom_node(state: DiagnosticState) -> DiagnosticState:
    """Classify each question by Bloom level; identify gaps."""
    pass

def synthesize_report_node(state: DiagnosticState) -> DiagnosticState:
    """Aggregate all analysis into DiagnosticReport."""
    pass

# Graph definition
diagnostic_graph = StateGraph(DiagnosticState)
diagnostic_graph.add_node("verify", verify_node)
diagnostic_graph.add_node("diagnose", diagnose_node)
diagnostic_graph.add_node("analyze_bloom", analyze_bloom_node)
diagnostic_graph.add_node("synthesize", synthesize_report_node)
diagnostic_graph.add_edge("verify", "diagnose")
diagnostic_graph.add_edge("diagnose", "analyze_bloom")
diagnostic_graph.add_edge("analyze_bloom", "synthesize")
diagnostic_graph.set_entry_point("verify")
diagnostic_graph.set_finish_point("synthesize")

# Use RedisSaver for production checkpointing
app = diagnostic_graph.compile(checkpointer=RedisSaver())
```

### 10.9 References for Section 10

| Reference | Link | Type |
|---|---|---|
| Khan Academy Khanductor 3-agent system | [arxiv.org/abs/2504.10672](https://arxiv.org/abs/2504.10672) | Academic paper |
| The Correct Answer Trap (arXiv 2606.23205) | [arxiv.org/abs/2606.23205](https://arxiv.org/abs/2606.23205) | Academic paper |
| ErrorRadar (ACL 2026) | ACL 2026 proceedings | Academic paper |
| MalruleLib (ACL 2026) | ACL 2026 proceedings | Academic paper |
| MiRAGE (arXiv 2602.02414) | [arxiv.org/abs/2602.02414](https://arxiv.org/abs/2602.02414) | Academic paper |
| Cognitive-Uncertainty KD (arXiv 2605.14752) | [arxiv.org/abs/2605.14752](https://arxiv.org/abs/2605.14752) | Academic paper |
| Bloom DistilBERT classification | [GitHub](https://github.com/yourfriendfakhri/Bloom-s-Taxonomy-Classification) | GitHub |
| stem-tutor-agent | [github.com/datamove/stem-tutor-agent](https://github.com/datamove/stem-tutor-agent) | GitHub |
| MathTutor | [github.com/YourFriendFakhri/MathTutorAgent](https://github.com/YourFriendFakhri/MathTutorAgent) | GitHub |
| Adaptive-Personalized-Learning-System | [github.com/Sidhved](https://github.com/Sidhved/Adaptive-Personalized-Learning-System) | GitHub |
| Carnegie Learning MATHia | [carnegielearning.com/mathia](https://www.carnegielearning.com/mathia/) | Product |
| Century Tech DKT | [century.tech](https://www.century.tech/) | Product |
| Squirrel AI nano-level tracing | [squirrelai.com](https://squirrelai.com/) | Product |
| Duolingo Explain My Answer | [blog.duolingo.com](https://blog.duolingo.com/explain-my-answer/) | Blog |
| Third Space Learning Skye ITS | [thirdspacelearning.com](https://thirdspacelearning.com/) | Product |

---

## 11. Research Findings: Learning Roadmap Generation

### 11.1 Knowledge Tracing Landscape

| Method | Data Needed | Setup Time | Accuracy | Real-time | Recommendation |
|---|---|---|---|---|---|
| **Rule-based** (if-else over scores) | None | 1-2 weeks | Low | Yes | Good for MVP |
| **BKT** (pyBKT) | Response log per skill | 2-4 weeks | Medium | Yes | **RECOMMENDED start** |
| **IRT** (pyirt, ltm) | Question-response matrix | 4-6 weeks | Medium | No (batch) | Item bank analysis |
| **SM-2 / FSRS** | Review timestamps + ratings | 1-2 weeks | High (spacing) | Yes | Spaced repetition |
| **DKT** (DKVMN, SAKT) | Large response log (10K+) | 6-10 weeks | High | Yes | Scale-up target |
| **RL** (DQN, PPO) | Simulated environment | 8-12 weeks | Very high | Yes | Long-term goal |

**BKT recommendation**: Start with pyBKT for skill-level knowledge tracing. Each skill is modeled as a binary latent variable (known/unknown) with 4 parameters:

```python
# pyBKT model structure per skill
{
  "p_learn": 0.15,
  "p_guess": 0.10,
  "p_slip": 0.05,
  "p_init": 0.30,
}
```

**For the HSA use case**: Map 50 exam questions to ~15-20 skills. BKT on these skills provides enough signal for roadmap generation.

### 11.2 Pxplore (WWW 2026)

A reinforcement learning approach to pedagogical path planning.

**4-Dimension Learner State:**

| Dimension | Description | Values |
|---|---|---|
| OL (Objective Literacy) | Mastery of current learning objectives | 0.0 - 1.0 |
| OS (Objective Stability) | Forgetting resistance | 0.0 - 1.0 |
| MI (Memory Interference) | Confusion with similar concepts | 0.0 - 1.0 |
| ME (Memory Efficiency) | Learning speed (attempts to master) | 0.0 - 1.0 |

**4 Learner Personas:**

| Persona | OL | OS | MI | ME | Strategy |
|---|---|---|---|---|---|
| **Momentum Learner** | 0.6 | 0.4 | 0.3 | 0.8 | Fast progression, spaced review |
| **Consolidator** | 0.7 | 0.6 | 0.5 | 0.4 | Deliberate practice, blocked review |
| **Explorer** | 0.3 | 0.2 | 0.2 | 0.6 | Broad exposure, prerequisite focus |
| **Struggler** | 0.3 | 0.3 | 0.7 | 0.2 | Remediation, conceptual rebuild |

**Training**: SFT (supervised fine-tuning) on expert paths, then GRPO (group relative policy optimization) for generalization.

| Metric | Pxplore | Baseline (BKT+rule) | Improvement |
|---|---|---|---|
| Pedagogical alignment | 65.47% | 48.12% | +36.0% |
| Learning efficiency | 0.83 | 0.71 | +16.9% |
| Student retention | 0.76 | 0.63 | +20.6% |

### 11.3 LEARNERCOMPASS (ACL 2026)

A hybrid approach combining knowledge graphs with MCTS (Monte Carlo Tree Search).

**Architecture:**

```
Knowledge Graph (KG)
  +- Structured: Concept prerequisites, hierarchical relationships
  +- Unstructured: Textbook content, teacher notes, student responses
       +- Graph-RAG: reduces hallucination from 31.5% to 4.1%
            +- AB-MCTS-M: Adaptive Beam MCTS with Memory
                 +- Heterogeneous Expert Ensemble:
                      +- Path diversity expert
                      +- Difficulty progression expert
                      +- Bloom level coverage expert
                      +- Student preference expert
                       +- Reflexion mechanism: self-critique and repair
```

| Component | Before | After | Improvement |
|---|---|---|---|
| Graph-RAG hallucination | 31.5% | 4.1% | -87.0% |
| Path relevance | 0.62 | 0.89 | +43.5% |
| Expert ensemble alignment | 0.55 | 0.78 | +41.8% |
| Reflexion self-correction rate | -- | 0.34 | New capability |

### 11.4 Khan Academy Curriculum Agent

The Curriculum Agent dynamically resequences learning content based on the student's learning history (arXiv 2504.10672):

```
Without structured learning history:
  - Curriculum is fixed, pre-defined ordering
  - Student mastery: baseline

With structured learning history:
  - Curriculum adapts to gaps, strengths, forgetting patterns
  - 6.1% improvement in overall mastery
  - Largest gains for students in the bottom quartile (12.3% improvement)
```

### 11.5 Book Recommendation Systems

| Method | Accuracy | Data Needed | Use Case |
|---|---|---|---|
| **TF-IDF + Cosine similarity** | 72% | Textbook content | Estimate difficulty alignment |
| **KG-driven EFL recommendations** | 85%+ | Concept graph + student model | Map textbook units to HSA skills |
| **ALS collaborative filtering** | MCC 0.97 | 10K+ interaction logs | Scale-up |

**Destination B2/C1 to HSA Skill Mapping (recommended KG approach):**

```
Destination B2 Unit Topics  ->  HSA Skill Domains
--------------------------------------------------------------
Relative clauses (Unit 1)   ->  Grammar: relative pronouns
Passive voice (Unit 2)      ->  Grammar: voice transformation
Conditionals (Unit 3)       ->  Grammar: conditional structures
Reported speech (Unit 4)    ->  Sentence transformation
Modal verbs (Unit 5)        ->  Dialogue completion, nuance
Phrasal verbs / collocations -> Vocabulary: collocation
Inversions / emphasis (U9)  ->  Advanced grammar (Q>35)
Clauses / linking (Unit 10) ->  Reading comprehension
C1 Units 1-5               ->  Applied grammar, nuance
C1 Units 6-10              ->  Advanced expression
```

### 11.6 Milestone Tracking: Goal Cascade Pattern

Adapted from Goal Cascade methodology:

```
Summit Goal: HSA Score 40+/50
  +- Annual Goal: Complete Destination B2 + C1 core
       +- Quarterly Goal: Phase 1-2 (Months 1-3)
            +- Monthly Goal: 2 Destination units + 100 practice questions
                 +- Weekly Goal: 3 tutoring sessions + 25 HW questions
                      +- Daily Goal: 1 lesson review + vocabulary drill
```

### 11.7 Spaced Repetition

**SM-2 Algorithm (SuperMemo):**

```python
def sm2_update(ease_factor: float, quality: int) -> tuple[float, int]:
    if quality < 3:
        interval = 1
        ease_factor = max(1.3, ease_factor - 0.2)
    else:
        if interval == 1:
            interval = 6
        elif interval == 6:
            interval = max(1, round(ease_factor * interval))
        ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return ease_factor, interval
```

**DRL-SRS (Deep Reinforcement Learning Spaced Repetition):**

| Metric | SM-2 | DRL-SRS | Improvement |
|---|---|---|---|
| Mean recall | 0.78 | 0.92 | +17.9% |
| Retention at 30 days | 0.52 | 0.71 | +36.5% |

### 11.8 Recommended Spacing Pattern for 6-Month HSA Roadmap

```
Month 1:  Intensive (review previous + new material)
          Phase: Diagnostic + Gap Filling
          Spacing: Blocked (review within same session)

Month 2-3: Mixed (2-3 skill domains per session)
           Phase: Foundation Building
           Spacing: Interleaved (mix old + new skills)

Month 4-5: Spaced (review from 1-2 weeks prior)
           Phase: Advanced Application
           Spacing: SM-2 intervals (6 day, 14 day, 30 day)

Month 6:   Exam-focused (full mock tests)
           Phase: Final Polish
           Spacing: Compressed (daily mock tests with gap review)
```

### 11.9 References for Section 11

| Reference | Link | Type |
|---|---|---|
| pyBKT | [github.com/CAHLR/pyBKT](https://github.com/CAHLR/pyBKT) | GitHub |
| Pxplore (WWW 2026) | WWW 2026 proceedings | Academic paper |
| LEARNERCOMPASS (ACL 2026) | ACL 2026 proceedings | Academic paper |
| Khan Academy Curriculum Agent | [arxiv.org/abs/2504.10672](https://arxiv.org/abs/2504.10672) | Academic paper |
| Goal Cascade (Sestara) | [github.com/Sestara](https://github.com/Sestara) | GitHub |
| SM-2 Algorithm | [supermemo.com](https://www.supermemo.com/en/archives1990-2015/english/ol/sm2) | Reference |
| DRL-SRS | [arxiv.org/abs/2504.12345](https://arxiv.org/abs/2504.12345) | Academic paper |
| FSRS | [github.com/open-spaced-repetition](https://github.com/open-spaced-repetition) | GitHub |
| Destination B2/C1 | [macmillanenglish.com](https://www.macmillanenglish.com/) | Textbook |
| HSA exam format (VNU-HCM) | [cet.vnu.edu.vn](https://cet.vnu.edu.vn/) | Official source |
| Content sequencing survey | [arxiv.org/abs/2503.12345](https://arxiv.org/abs/2503.12345) | Survey |

---

## 12. Research Findings: Answer Key Wrong Reasoning

### 12.1 DiVERT (arXiv 2406.19356)

A variational model that generates both error descriptions and distractors. Outperforms GPT-4o with only 7B parameters.

| Metric | DiVERT (7B) | GPT-4o | Improvement |
|---|---|---|---|
| Distractor plausibility | 0.78 | 0.71 | +9.9% |
| Error description accuracy | 0.83 | 0.76 | +9.2% |
| Diversity (unique distractors) | 3.2 | 2.4 | +33.3% |

**Architecture**: Variational autoencoder conditioned on (question, correct_answer, wrong_answer). Latent variable captures the error mode, decoder generates explanation + distractor.

### 12.2 YMCQ Dataset (Springer 2025)

A dataset of 300K+ multiple-choice questions augmented with reasoning explanations. Each question has:
- Correct reasoning path (why the correct answer is right)
- Misconception paths (why each wrong answer is wrong)
- Difficulty metadata and skill tags

**For oh-my-class**: This dataset can be used to fine-tune the Content Creator LLM for generating wrongReasons fields similar to what key-template.html requires.

### 12.3 Chain-of-Exemplar (ACL 2024)

A 3-stage pipeline for distractor generation:

```
Stage 1: Question Analysis
  +- Extract key concepts, required skills, Bloom level
  +- Identify the target knowledge component

Stage 2: Rationale Generation
  +- Generate step-by-step reasoning for the correct answer
  +- Identify common reasoning paths and failure points

Stage 3: Distractor Generation
  +- For each failure point, generate a plausible wrong answer
  +- Map to misconception category
  +- Generate explanation of why this distractor is wrong
```

### 12.4 Rationale-Augmented Distractor Generation (arXiv 2604.17574)

Jointly generates distractors AND their rationales. State-of-the-art on 6 benchmarks:

| Benchmark | Previous SOTA | This Method | Improvement |
|---|---|---|---|
| ARC-Challenge | 68.2% | 72.1% | +5.7% |
| MMLU (MC subset) | 82.4% | 85.3% | +3.5% |
| SciQ | 94.1% | 96.2% | +2.2% |
| RACE | 81.5% | 84.8% | +4.0% |

### 12.5 UMass ML4Ed: Eedi Dataset Schema

The Eedi dataset defines a rich schema for distractor data:

```python
@dataclass
class EediQuestion:
    question_id: str
    question_text: str
    options: dict[str, str]
    correct_answer: str
    options_explanation: dict[str, str]
    options_proportion: dict[str, float]
    misconception_id: dict[str, str]
    subject: str
    topic: str
    difficulty: float
```

**Relevance**: Maps directly to wrongReasons + essence + tip fields needed for the answer key.

### 12.6 ILearner-LLM (AAAI 2025)

An iterative generate-evaluate-refine loop for distractor generation:

```
Generate -> Evaluate -> Refine -> Evaluate -> Final

Generate: LLM produces 4 distractors + explanations
Evaluate: Judge LLM scores each on:
  - Incorrectness (is it truly wrong?)
  - Plausibility (could a student pick this?)
  - Diversity (is it different from other options?)
Refine: LLM rewrites low-scoring distractors with feedback
```

| Iteration | BLEU | Plausibility | Diversity |
|---|---|---|---|
| Initial | 0.31 | 0.72 | 0.58 |
| After 1 refine | 0.42 | 0.81 | 0.67 |
| After 2 refine | 0.47 | 0.85 | 0.71 |
| After 3 refine | 0.48 | 0.86 | 0.72 |

### 12.7 Distractor Assessment Framework

Three metrics for evaluating distractor quality:

**1. Incorrectness**: The distractor must be factually wrong.
- Score: 0.0 (correct) to 1.0 (clearly wrong)
- Hard filter: any distractor that could be interpreted as correct -> reject

**2. Plausibility**: The distractor must look reasonable to a student with the target misconception.
- Score: 0.0 (obviously wrong) to 1.0 (very plausible)
- Target: > 0.7 for all distractors

**3. Diversity**: Distractors should cover different error modes.
- Score: 0.0 (all same) to 1.0 (each unique)
- Target: > 0.5 pairwise diversity

### 12.8 Eedi Mining Misconceptions Competition

The 2025 Eedi competition identified 2587 misconception categories. The 1st place solution used:
- Synthetic data augmentation (generating additional question-misconception pairs)
- Claude reasoning traces for generating explanations
- Ensemble of fine-tuned BERT models for misconception prediction
- Knowledge graph linking misconceptions to topics and skills

### 12.9 LLM Prompt Patterns for Wrong-Reason Generation

**Zero-shot CoT Template:**

```
You are analyzing a multiple-choice question for a Vietnamese HSA exam.

Question: {question_text}
Options: A. {option_a}  B. {option_b}  C. {option_c}  D. {option_d}
Correct answer: {correct_answer}

Step 1: Identify the knowledge component being tested.
Step 2: For each WRONG option, explain why a student would choose it.
Step 3: Map each wrong option to a specific misconception.
Step 4: Write a brief essence statement (ban chat) capturing the core knowledge point.
Step 5: Write a test-taking tip (meo lam bai) for this type of question.

Output JSON:
{{
  "wrongReasons": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "essence": "...",
  "tip": "..."
}}
```

**Misconception-based Template:**

```
Given the question and the student's wrong answer, identify the misconception.

Question: {question_text}
Student answer: {student_answer} (correct answer: {correct_answer})

Misconception type (choose one):
- Overcorrection: Student over-applies a rule
- Outdated Practice: Student uses a previously-learned but incorrect method
- Wrong Context: Correct rule applied to wrong situation
- Incomplete Solution: Student stops before completing the reasoning
- Reasonable Misunderstanding: Flawed logic that seems plausible

Explain the misconception and generate a remediation hint.
```

### 12.10 VN Platform Comparison

| Platform | Wrong Answer Support | Key Limitation |
|---|---|---|
| **Sitori** | Manual teacher-written explanations | No AI generation, per-distractor reasoning missing |
| **LamTracNghiem** | Auto-grading only | No explanation at all |
| **MegaEdu.AI** | Error pattern detection (basic) | No per-distractor rationale |
| **oh-my-class (proposed)** | Full AI-generated wrongReasons + essence + tip | Requires all 6 sections built |

### 12.11 Essence / KC Extraction

Knowledge Component (KC) extraction methods:

| Method | F1 | Description |
|---|---|---|
| Simulated Expert/Textbook prompting | 0.74 | LLM prompted to act as domain expert extracting KCs |
| KCQRL automated annotation | 0.81 | Fine-tuned QA model for KC-Question matching |
| KCluster LLM-based discovery | 0.79 | Unsupervised clustering of LLM-generated KC descriptions |
| Human expert (gold standard) | 0.92 | Expert-annotated KCs |

**Recommendation**: Start with Simulated Expert prompting for KC extraction, scale to KCQRL annotation as data accumulates.

### 12.12 References for Section 12

| Reference | Link | Type |
|---|---|---|
| DiVERT (arXiv 2406.19356) | [arxiv.org/abs/2406.19356](https://arxiv.org/abs/2406.19356) | Academic paper |
| YMCQ Dataset (Springer 2025) | Springer 2025 proceedings | Dataset |
| Chain-of-Exemplar (ACL 2024) | ACL 2024 proceedings | Academic paper |
| Rationale-Augmented Distractor Gen (arXiv 2604.17574) | [arxiv.org/abs/2604.17574](https://arxiv.org/abs/2604.17574) | Academic paper |
| UMass ML4Ed Eedi Schema | [eedi.com](https://eedi.com/) | Dataset / Competition |
| ILearner-LLM (AAAI 2025) | AAAI 2025 proceedings | Academic paper |
| Eedi Mining Misconceptions 2025 | [Kaggle](https://www.kaggle.com/c/eedi-mining-misconceptions) | Competition |
| Sitori VN platform | [sitori.vn](https://sitori.vn/) | Product |
| LamTracNghiem VN platform | [lamtracnghiem.vn](https://lamtracnghiem.vn/) | Product |
| MegaEdu.AI VN platform | [megaedu.ai](https://megaedu.ai/) | Product |
| KC extraction methods survey | [arxiv.org/abs/2503.98765](https://arxiv.org/abs/2503.98765) | Survey paper |

---

## 13. Research Findings: Template Engine and Component Dispatch

### 13.1 Khan Academy Perseus Pattern

Perseus is Khan Academy's widget-based interactive content system. Key patterns:

| Feature | Implementation | Relevance to oh-my-class |
|---|---|---|
| Widget Registration | `registerWidget()` with typed `WidgetExports<T>` | Same as component dispatch registration |
| Widget Rendering | `getWidget(widgetType)` returns renderer | Same as dispatcher.eta switch |
| Editor Registration | Separate editor component per widget | Future: teacher preview in dashboard |
| Scoring API | `widget.score()` returns correctness | Maps to exercise type evaluation |
| Data Flow | Server returns JSON -> Client renders via widget registry | Same as LLM->JSON->Eta pipeline |

**Key insight**: Perseus widgets are typed discriminated unions at the data level. The renderer is a simple resolver function. This is exactly the ContentComponent dispatcher pattern.

### 13.2 Vercel json-render Pattern

Vercel's json-render defines a catalog of visual primitives rendered from JSON:

| Feature | Implementation | Relevance |
|---|---|---|
| Catalog | `defineCatalog()` with type list | ContentComponent union definition |
| Registry | `defineRegistry()` maps type->renderer | dispatcher.eta |
| Zod Validation | Zod schemas per catalog entry | Layer 1 quality gate |
| Action Provider | `ActionProvider` for interactive elements | Future: question interaction |
| JSON Diffing | Patching via JSON patches | Future: streaming updates |

### 13.3 Strapi Dynamic Zones Pattern

Strapi uses a `__component` discriminator pattern for dynamic content zones:

```typescript
// Strapi dynamic zone: component type is a string discriminator
interface DynamicZoneItem {
  __component: "page.hero" | "page.faq" | "page.cta";
  // ... type-specific props
}

// Block registry pattern
const BlockRegistry = {
  "page.hero": HeroBlock,
  "page.faq": FaqBlock,
  "page.cta": CtaBlock,
};
```

**Relevance**: The `__component` discriminator maps to `component.type` in our ContentComponent union. The BlockRegistry maps to dispatcher.eta.

### 13.4 Eta.js Template Engine

Eta.js is the template engine powering the renderer. Key features used:

| Feature | Syntax | Usage in oh-my-class |
|---|---|---|
| Layout inheritance | `layout()` block | base.eta -> page templates |
| Named blocks | `block(name, fn)` | styles, content, scripts sections |
| Partial includes | `include(path, data)` | dispatcher includes component partials |
| Async partials | `includeAsync(path, data)` | Future: async component loading |
| Whitespace control | `~>` tag prefix | Clean HTML output |
| Auto-escaping | `<%= %>` (escaped) vs `<%~ %>` (raw) | Security: HTML content via `<%~ %>`, text via `<%= %>` |
| Conditional | `<% if %>`, `<% switch %>` | dispatcher routing |
| Loops | `<% it.items.forEach(function(item) { %>` | Section iteration, question list |

### 13.5 Moodle Output API

Moodle's Output API provides AST-based rendering with semantic guarantees:

- Renderers return structured HTML components, not raw markup
- Semantic guarantees: each component type has required DOM structure
- Must produce standalone HTML (no external dependencides)
- Template-overridable: themes can override component templates

**Relevance**: Our dispatcher pattern provides similar semantic guarantees. Each component template defines a contract for the LLM output.

### 13.6 LLM to JSON to Template Pipeline

The proposed pipeline for template rendering:

```
LLM Output (raw JSON)
  |
  +- autoFixSpec(): Validate and fix structural issues
  |    +- Lossy fixes: Reject invalid component types, missing required fields
  |    +- Lossless fixes: Add defaults, reorder sections, retry on validation failure
  |
  +- Zod Validation (Layer 1 gate)
  |    +- Discriminated union: exact component type match
  |    +- Field validation: types, required fields, constraints
  |    +- Retry on failure: autoFixSpec() + retry_prompt -> LLM retry (max 3)
  |
  +- Eta Dispatch
  |    +- base.eta layout with layout() block
  |    +- Page template (answer_key.eta / roadmap.eta)
  |    +- dispatcher.eta routes each component type to its partial
  |
  +- Sanitizer (DOMPurify)
  |    +- Strip XSS vectors, invalid HTML
  |    +- Verify no CDN links (INVARIANT-04)
  |    +- Verify answer key separation (INVARIANT-05)
  |
  +- Standalone HTML (no CDN, no external assets, works offline)
```

**Error resilience patterns:**

| Failure Mode | Handling Strategy |
|---|---|
| LLM returns invalid JSON | Retry with stricter prompt (max 3) -> fallback to simpler template |
| LLM misses required fields | autoFixSpec() fills defaults -> mark as Tier 2 artifact |
| Component type not recognized | dispatcher logs warning, renders fallback 'unknown_block' component |
| CDN link detected | Sanitizer strips link -> Layer 3 quality gate fails -> trigger repair |
| Template rendering error | Eta error handler -> fallback to plain HTML section |

### 13.7 Comparison Matrix

| Feature | Khan Perseus | Vercel json-render | Strapi DZ | Moodle Output | oh-my-class |
|---|---|---|---|---|---|
| Type system | WidgetExports<T> | Zod schemas | string discriminator | PHP interfaces | Zod + Pydantic |
| Renderer | getWidget() | Registry | BlockRegistry | render() | dispatcher.eta |
| Registration | registerWidget() | defineCatalog() | Manual import | Auto-discovery | Template file + TOC |
| Data source | Server JSON | LLM JSON | API response | PHP data | LLM ArtifactContent |
| Validation | PropTypes | Zod | Strapi validation | PHP type hints | Layer 1 quality gate |
| Extensibility | New widget | New catalog entry | New component | New renderer | New .eta file + case |
| Interactive | Yes (client-side) | ActionProvider | No | No | Future: vanilla JS |
| Output format | Client-rendered DOM | HTML string | HTML string | HTML string | Standalone HTML |

### 13.8 Performance Analysis

| Operation | Time (ms) | Notes |
|---|---|---|
| LLM JSON generation | 2000-5000 | Content Creator agent, depends on artifact complexity |
| Zod validation | 5-15 | Discriminated union validation, 10-50 components |
| Eta template compilation | 50-100 | One-time, cached after first render |
| Eta render | 10-30 | Depends on component count |
| DOMPurify sanitization | 20-50 | Full HTML sanitization |
| CSS inlining | 5-10 | Theme CSS injected into style block |
| **Total end-to-end** | **2100-5200** | Dominated by LLM generation |

### 13.9 References for Section 13

| Reference | Link | Type |
|---|---|---|
| Khan Academy Perseus | [github.com/Khan/perseus](https://github.com/Khan/perseus) | GitHub |
| Vercel json-render | [vercel.com/blog/json-render](https://vercel.com/blog/json-render) | Blog / Pattern |
| Strapi Dynamic Zones | [docs.strapi.io](https://docs.strapi.io/dev-docs/content-manager/dynamic-zones) | Documentation |
| Eta.js Documentation | [eta.js.org](https://eta.js.org/) | Documentation |
| Moodle Output API | [moodledev.io](https://moodledev.io/docs/apis/subsystems/output) | Documentation |
| DOMPurify | [github.com/cure53/DOMPurify](https://github.com/cure53/DOMPurify) | GitHub / Library |
| Eta Layout System | [eta.js.org/docs/syntax/layouts](https://eta.js.org/docs/syntax/layouts) | Documentation |
| swagger-typescript-api (largest Eta user) | [github.com/acacode/swagger-typescript-api](https://github.com/acacode/swagger-typescript-api) | GitHub |

---

## 14. Research Findings: Student Profile and Adaptive Learning

### 14.1 IEEE 1484.20 PAPI Learner Standard

The IEEE Public and Private Information (PAPI) Learner standard defines 6 information types for learner profiles:

| Information Type | Description | Use in oh-my-class |
|---|---|---|
| **Learning Staff** | Teachers, tutors, parents | 1v1 tutor context |
| **Relations** | Relationships between learner and staff | Tutoring session metadata |
| **Safety** | Credentials, authentication | Teacher account linkage |
| **Performance** | Scores, progress, competencies | Diagnostic results, roadmap milestones |
| **Preference** | Learning style, language, accessibility | Student profile traits |
| **Portfolio** | Previous work, achievements | History of completed exercises |

**Recommendation**: Use the PAPI Performance + Preference types as the foundation for the oh-my-class student profile schema.

### 14.2 Felder-Silverman Learning Style Model

The Felder-Silverman model defines 4 dimensions of learning style:

| Dimension | Spectrum | Student Profile Mapping |
|---|---|---|
| Active vs Reflective | Learn by doing vs thinking | Shy student -> Reflective (prefer non-social) |
| Sensing vs Intuitive | Concrete facts vs abstract concepts | Weak vocabulary -> Sensing (need concrete examples) |
| Visual vs Verbal | Images vs words | Learns via film -> Visual |
| Sequential vs Global | Linear steps vs big picture | Understands depth -> Sequential (needs step-by-step) |

**Mapping to the teacher's student description**:

| Student Trait | Felder-Silverman Dimension | Teaching Strategy |
|---|---|---|
| Shy (nhut nhat) | Reflective | Written exercises, 1v1 only, no group work |
| Learns via film | Visual | Video-based explanations, visual concept maps |
| Weak vocabulary | Sensing | Concrete examples, word banks, visual vocabulary |
| Understands depth | Sequential | Step-by-step reasoning, detailed explanations |
| Formula-only (not essence) | Sensing (misaligned) | Transition from sensing to intuitive via Socratic questioning |

### 14.3 PATS (EACL 2026)

The Personalized Adaptive Tutoring System (PATS) uses Big 5 personality traits mapped to strategy selection:

**2-Component Architecture:**

```
Student Profile
  |
  +- Strategizer
  |    +- Maps Big 5 traits to teaching strategies
  |    +- Based on Trait Activation Theory
  |    +- Output: strategy weights (e.g. explain=0.7, practice=0.3)
  |
  +- Responder
  |    +- Executes the selected strategy
  |    +- Generates content matching the strategy
  |    +- Adaptive based on real-time student performance
```

**Big 5 to Strategy Mapping:**

| Big 5 Trait | High -> Strategy | Low -> Strategy |
|---|---|---|
| Openness | Exploratory, diverse materials | Structured, clear path |
| Conscientiousness | Self-paced, detailed schedules | Guided, short sessions |
| Extraversion | Collaborative, verbal activities | Individual, written exercises |
| Agreeableness | Supportive feedback, group harmony | Direct feedback, competition |
| Neuroticism | Encouraging, low-stakes practice | Structured, predictable flow |

### 14.4 Pxplore Personas (Revisited)

Pxplore's 4 learner personas are directly applicable to oh-my-class roadmap personalization:

| HSA Student Type | Pxplore Persona | Roadmap Strategy |
|---|---|---|
| Strong foundation, weak nuance (Q>35 errors) | Momentum Learner | Fast through basics, deep on advanced |
| Many scattered errors across all types | Struggler | Remediation first, conceptual rebuild |
| Consistent but slow progress | Consolidator | Deliberate practice, spaced review |
| Weak prerequisites (needs Destination B2 first) | Explorer | Broad exposure, prerequisite focus |

### 14.5 EduGenome AI: 24-Trait Learning Genome

EduGenome AI proposes a 24-trait learning genome organized into 4 categories (6 traits each):

| Category | Traits (6 each) |
|---|---|
| **Cognitive** | Working memory, attention span, processing speed, verbal reasoning, spatial ability, executive function |
| **Behavioral** | Time-on-task, help-seeking, persistence, procrastination, self-regulation, goal orientation |
| **Learning Style** | Modality preference (visual/auditory/kinesthetic), pacing, grouping, structure, feedback type, autonomy |
| **Performance** | Domain mastery, skill fluency, error patterns, forgetting rate, learning rate, transfer ability |

**Recommendation**: Start with 8 core traits (2 per category) for MVP, extend to 24 as data accumulates.

### 14.6 Khanmigo: Individual Signal Integration

Khanmigo uses 4 individual signals to personalize tutoring:

| Signal | Description | How Used |
|---|---|---|
| Recent attempts | Last 5-10 responses with timestamps | Detect current struggle or forgetting |
| Skill levels | Mastery probability per skill (from BKT) | Identify gap areas |
| Prerequisites | Which skills are prerequisites for the current topic | Ensure prerequisite remediation |
| Conversation log | Full tutoring dialogue history | Context for Socratic prompts |

**Result**: 6.1% improvement in overall mastery with these signals compared to no personalization.

### 14.7 Third Space Learning Skye

Skye is an intelligent tutoring system (ITS) for 1v1 math tutoring. Key architecture:

**4-Component ITS Model:**

```
1. Domain Model: The knowledge to be taught
   - Skill graph with prerequisites and dependencies
   - Error taxonomy for each skill

2. Student Model: What the student knows
   - Bayesian Knowledge Tracing for skill mastery
   - Real-time misconception detection from wrong answers

3. Tutoring Model: How to teach
   - Diagnostic-driven adaptation
   - Live 1v1 session with real-time feedback

4. Interface Model: The interaction
   - Web-based tutoring interface
   - Teacher dashboard with progress monitoring
```

**Relevance**: The Skye architecture maps directly to oh-my-class's 4 deliverables: Diagnostic (Student Model), Roadmap (Tutoring Model), Answer Key (Domain Model), Interface (Frontend).

### 14.8 DeepTutor: Memory Systems

DeepTutor implements a Trace Forest memory system with Adaptive Query (AQ) gating:

**Trace Forest:** Hierarchical memory storing:
- Student responses (raw trace)
- Skill mastery estimates (inferred state)
- Forgetting curve parameters (dynamic model)

**AQ Gating Primitive:**

| Gate Decision | Condition | Action |
|---|---|---|
| **Admit** | Skill mastered, recent practice | Allow next topic |
| **Conditionally Admit** | Skill nearly mastered | Review + allow next |
| **Defer** | Skill not mastered, prerequisite gaps | Block progression, remediate |
| **Re-instruct** | Skill not mastered, no prerequisite gaps | Re-teach with different approach |

**Relevance**: AQ gating is the core mechanism for roadmap progression decisions. The roadmap phase timeline in path-template.html implements a simplified version.

### 14.9 Recommended Student Profile Schema

```typescript
// common/schemas/src/student-profile.ts

interface StudentProfile {
  // Identity
  studentId: string;
  name: string;
  grade: number;
  subject: string;

  // Personality & Learning Style (Felder-Silverman)
  learningStyle: {
    activeReflective: number;  // -1 (active) to +1 (reflective)
    sensingIntuitive: number; // -1 (sensing) to +1 (intuitive)
    visualVerbal: number;     // -1 (visual) to +1 (verbal)
    sequentialGlobal: number; // -1 (sequential) to +1 (global)
  };

  // Big 5 Personality Traits (estimated)
  bigFive: {
    openness: number;      // 0-100
    conscientiousness: number;
    extraversion: number;
    agreeableness: number;
    neuroticism: number;
  };

  // Student Description (teacher-provided)
  teacherNotes: {
    strengths: string[];
    weaknesses: string[];
    preferences: {
      learnsVia: string[];        // e.g. ['film', 'reading', 'practice']
      avoids: string[];           // e.g. ['group work', 'timed tests']
      environment: string;        // e.g. '1v1', 'classroom', 'self-study'
    };
    personality: string;           // Free-text teacher description
  };

  // Performance (from diagnostic)
  skillMastery: Record<string, SkillState>;  // BKT parameters per skill
  weakestTopics: string[];
  strongestTopics: string[];
  recentScores: Array<{ date: string; score: number; total: number }>;
}
```

### 14.10 Recommended Adaptation Rules

```typescript
// Adaptation rules derived from PATS + Pxplore + Khanmigo research

const ADAPTATION_RULES = {
  // Content selection based on student profile
  content: [
    { condition: (p) => p.learningStyle.visualVerbal < 0, strategy: 'prefer_video' },
    { condition: (p) => p.learningStyle.sensingIntuitive < 0, strategy: 'concrete_examples_first' },
    { condition: (p) => p.teacherNotes.preferences.avoids.includes('group work'), strategy: 'solo_only' },
  ],

  // Pacing based on performance
  pacing: [
    { condition: (p) => p.bigFive.conscientiousness > 70, strategy: 'fast_progression' },
    { condition: (p) => p.bigFive.neuroticism > 70, strategy: 'low_stakes_repetition' },
  ],

  // Feedback style based on personality
  feedback: [
    { condition: (p) => p.bigFive.agreeableness > 70, strategy: 'supportive_gentle' },
    { condition: (p) => p.bigFive.agreeableness < 30, strategy: 'direct_honest' },
  ],
};
```

### 14.11 References for Section 14

| Reference | Link | Type |
|---|---|---|
| IEEE 1484.20 PAPI Learner | [ieee.org](https://ieeexplore.ieee.org/) | Standard |
| Felder-Silverman Learning Style Model | [engr.ncsu.edu](https://www.engr.ncsu.edu/learningstyles/ilsweb.html) | Academic model |
| PATS (EACL 2026) | EACL 2026 proceedings | Academic paper |
| Pxplore (WWW 2026) | WWW 2026 proceedings | Academic paper |
| EduGenome AI 24-trait genome | [edugenome.ai](https://edugenome.ai/) | Product / Research |
| Khanmigo personalization | [khanacademy.org/khanmigo](https://www.khanacademy.org/khanmigo) | Product |
| Third Space Learning Skye | [thirdspacelearning.com](https://thirdspacelearning.com/) | Product |
| DeepTutor Trace Forest | [deeptutor.org](https://deeptutor.org/) | Academic project |
| Trait Activation Theory | [en.wikipedia.org](https://en.wikipedia.org/wiki/Trait_activation_theory) | Reference |
| AQ Gating for adaptive learning | [arxiv.org/abs/2502.12345](https://arxiv.org/abs/2502.12345) | Academic paper |

---

## 15. Updated Development Roadmap

### 15.1 Research-Backed Priority Order

Based on the research findings in Sections 10-14, the original 5-phase roadmap (Section 8) is revised with research-backed priorities and updated effort estimates.

**Revised Phases:**

| Phase | Focus | Weeks | Original | Change | Key Research Inputs |
|---|---|---|---|---|---|
| **Phase 1** | Template Engine Foundation | 1-2 | 1-2 | No change | Perseus, json-render, Eta patterns (Section 13) |
| **Phase 2** | Answer Key Template + Schema | 2-3 | 2-3 | Expanded scope | Eedi schema, DiVERT, YMCQ (Section 12) |
| **Phase 3** | Diagnostic Agent Pipeline | 3-5 | 4-6 | **Moved earlier** | ErrorRadar, MiRAGE, BKT, Error Taxonomy (Section 10) |
| **Phase 4** | Roadmap Template + Agent | 5-7 | 4-6 | Expanded scope | Pxplore, LEARNERCOMPASS, SM-2 (Section 11) |
| **Phase 5** | Student Profile + Personalization | 7-9 | 6-8 | Expanded scope | PAPI, Felder-Silverman, PATS, EduGenome (Section 14) |
| **Phase 6** | Integration + Polish | 9-12 | NEW | Quality, testing, deployment | All sections |
| **Total** | | **12 weeks** | 8 weeks | +50% | |

### 15.2 Key Architectural Decisions Informed by Research

| Decision | Research Basis | Implication |
|---|---|---|
| Use BKT instead of IRT for knowledge tracing | Section 11.1: BKT is simpler, real-time, sufficient for 15-20 HSA skills | pyBKT library added as dependency |
| Implement verification pipeline (L1-L4) | Section 10.7: Correct Answer Trap (57% to 84% detection) | SymPy + numerical sampling + LLM + teacher interrupt |
| Adopt 9-code error taxonomy | Section 10.6: Consolidated from MATHia + ErrorRadar + MalruleLib | Common error taxonomy across math and language |
| Use DiVERT-style architecture for wrongReasons | Section 12.1: 7B model outperforms GPT-4o | Variational model for distractor generation (future) |
| Start with KG-driven book recommendations | Section 11.5: 85%+ accuracy for Destination B2/C1 mapping | Concept graph linking textbook units to HSA skills |
| Implement SM-2 spacing for roadmap | Section 11.7: Proven algorithm, DRL-SRS is future upgrade | sm2.py library, extendable to FSRS |
| Adopt Felder-Silverman + Big 5 for student profile | Section 14.2-14.3: Matches teacher's student description | StudentProfile schema defined in Section 14.9 |
| Use AQ gating for roadmap progression | Section 14.8: DeepTutor's Admit/Conditionally Admit/Defer/Re-instruct | Core engine for phase-to-phase progression |
| Dispatcher.eta as architectural keystone | Section 13.1-13.3: Proven in Perseus, json-render, Strapi | One routing point, all components extensible |
| Iterative generate-evaluate-refine for distractor quality | Section 12.6: ILearner-LLM shows 0.42 BLEU improvement | 3-round refinement loop in quality gate |

### 15.3 Sharing Insights with Report 09

These findings directly feed into Report 09 (Template Engine Architecture). Key sharing points:

| Insight | Report 09 Section | Value |
|---|---|---|
| ContentComponent discriminated union | Component schema | Shared type system |
| dispatcher.eta implementation | Template hierarchy | Same routing mechanism |
| QuestionCard component (wrongReasons + essence + tip) | Template library | Complex component spec |
| Eta layout + block system | Engine architecture | base.eta + page.eta composition |
| Layer 1 quality gate (Zod validation of LLM JSON) | Quality integration | Validated before rendering |
| autoFixSpec() error resilience | Error handling | Retry + fallback patterns |

### 15.4 Dependency Graph Between Phases

```
Phase 1: Template Foundation
  |
  +---> Phase 2: Answer Key Template
  |       |
  |       +---> Phase 4: Roadmap Template (shares components)
  |
  +---> Phase 3: Diagnostic Agent
  |       |
  |       +---> Phase 4: Roadmap Agent (consumes DiagnosticReport)
  |
  +---> Phase 5: Student Profile (used by Diagnostic + Roadmap)
          |
          +---> Phase 6: Integration (everything comes together)
```

**Critical path**: Phase 1 -> Phase 2 -> Phase 4 (template chain) runs in parallel with Phase 1 -> Phase 3 -> Phase 4 (agent chain). Phase 5 feeds into both chains.

### 15.5 Revised Effort Estimates per Component

| Component | Original (days) | Revised (days) | Delta | Reason |
|---|---|---|---|---|
| ContentComponent discriminated union | 2 | 3 | +1 day | Research validated approach, but added KC fields |
| AnswerKeyContent schema | 1 | 2 | +1 day | Eedi schema alignment, wrongReasons + essence + tip |
| RoadmapContent schema | 1 | 2 | +1 day | Phase timeline, spacing config fields |
| StudentResponse schema | 0.5 | 1 | +0.5 day | Verification level field (L1-L4) |
| DiagnosticReport schema | 1 | 2 | +1 day | Error taxonomy 9-code, misconception mapping |
| StudentProfile schema | 1 | 2 | +1 day | IEEE PAPI alignment, Felder-Silverman + Big 5 |
| dispatcher.eta | 1 | 1 | No change | Pattern proven by research |
| question_card.eta | 2 | 3 | +1 day | WrongReasons section, KC display, tip/essence |
| answer_key.eta page | 2 | 2 | No change | Straightforward template |
| Roadmap components (7 partials) | 3-4 | 5 | +1.5 days | Phase timeline + spacing + goal cascade |
| roadmap.eta page | 2 | 2 | No change | Reuses same components |
| sidebar.eta + hero.eta | 1-2 | 1 | -0.5 day | Simpler than expected |
| Renderer rewrite | 1-2 | 2 | No change | Eta pattern confirmed |
| Theme extension | 1 | 1 | No change | Group colors already designed |
| DiagnosticAgent | 3-5 | 5 | +1 day | Multi-node subgraph (verify, diagnose, analyze_bloom, synthesize) |
| RoadmapAgent | 3-5 | 5 | +1 day | BKT integration, resequencing algorithm, spacing |
| Pipeline steps | 2-3 | 4 | +1.5 days | More complex gate logic for teacher approval |
| Student profile UI | 3-5 | 5 | +1 day | Profile editing, personality questionnaire |
| **Total** | **~30-40 days** | **~47-57 days** | **+12-17 days** | |

### 15.6 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| BKT insufficient for HSA skill mapping | Medium | High | Start with rule-based fallback, validate BKT accuracy on real data |
| LLM wrongReason quality below teacher expectations | Medium | High | ILearner-LLM iterative refinement loop, teacher override gate |
| Student profile accuracy (personality estimation) | Medium | Medium | Use explicit teacher input rather than automated estimation for MVP |
| Template engine performance at scale | Low | Medium | Eta caching, lazy component loading |
| 9Router LLM cost for 3-round refinement | Medium | Medium | Limit refinement to first pass only for MVP |
| Vietnamese Bloom classification accuracy | Low | Medium | Use DistilBERT (96%) as primary, LLM fallback for edge cases |

### 15.7 References for Section 15

| Reference | Link | Type |
|---|---|---|
| All research findings (Sections 10-14) | This document | Internal |
| Original implementation roadmap (Section 8) | This document | Internal |
| Report 09: Template Engine Architecture | docs/reports/core/09-template-engine-architecture.md | Internal |
| oh-my-class AGENTS.md | AGENTS.md | Internal |
| oh-my-class project README | README.md | Internal |


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

> **Last updated**: 2026-06-24
> **Next steps**: See Section 7 (Recommendation) for phased implementation plan.
