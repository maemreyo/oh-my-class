# 08 — Use Case Evaluation: Personalized Answer Key & Learning Roadmap

> **Date**: 2026-06-23
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

> **Last updated**: 2026-06-23
> **Next steps**: See Section 8 (Implementation Roadmap) for phased build plan.
> **Key deliverable**: The template engine (dispatcher + component partials) is the product — not the individual templates.

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
