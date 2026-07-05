# AGENTS.md — oh-my-class

> **Purpose**: Single source of truth for every AI agent, developer, and tool working in this codebase.
> Read this file before touching any code. All architectural decisions flow from here.
>
> **Version**: 1.2 | **Date**: 2026-07-03

---

## Table of Contents

1. [Project Identity](#1-project-identity)
2. [Architecture Overview](#2-architecture-overview)
3. [Pipeline Graphs](#3-pipeline-graphs)
4. [Agent Definitions](#4-agent-definitions)
5. [State Schema](#5-state-schema)
6. [LLM Routing](#6-llm-routing)
7. [Quality Gates — 6 Layers](#7-quality-gates--6-layers)
8. [Template System](#8-template-system)
9. [Exercise Types — Quick Reference](#9-exercise-types--quick-reference)
10. [Export Formats](#10-export-formats)
11. [Project Structure](#11-project-structure)
12. [Coding Conventions](#12-coding-conventions)
13. [Testing](#13-testing)
14. [Hard Invariants](#14-hard-invariants)

---

## 1. Project Identity

**oh-my-class** is an AI-powered **teaching pack generator** for K-12 education. A teacher describes a lesson; the system produces a complete, print-and-use HTML teaching pack — lesson, worksheet, quiz, drill, recap, infographic — tailored to their students.

### Core Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Orchestration | LangGraph 1.x | Sequential pipeline + native `interrupt()` for teacher gates |
| Backend | FastAPI (Python 3.12) | Async, type-safe, OpenAPI auto-docs |
| Frontend | Next.js 15 (TypeScript) | SSR + App Router; teacher dashboard |
| Template Engine | Eta (JS/TS) | 3.5 KB, TypeScript-native, standalone HTML output |
| LLM Gateway L1 | LiteLLM Proxy (port 4000) | Virtual keys, budget control, cost tracking, fallback chains |
| LLM Gateway L2 | 9Router sidecar (port 20128) | RTK token compression (20–40%), free-tier aggregation, fusion routing |
| Cache | Redis 7 | LiteLLM exact-match cache; LangGraph shared state |
| Persistence | PostgreSQL 16 | LangGraph checkpoints; cost logs; artifact metadata |
| Validation | Pydantic v2 (Python) + Zod v4 (TS) | Bi-directional schema enforcement |
| Testing | pytest + Vitest | Python agents + TypeScript template renderer |

### Design Principles (non-negotiable)

- **SoC** — Each stage/sub-agent has one responsibility. The stage graph orchestrates; content generation stays inside content-creator nodes.
- **Modular** — Every layer (middleware, gate, template, agent) is a standalone unit, independently testable.
- **Standalone HTML** — All output is self-contained: no CDN, no external assets, works offline.
- **Config-driven** — Behavior controlled via YAML/JSON; no magic in code.
- **Fail closed** — Any gate failure blocks export. No silent passes.
- **Typed end-to-end** — Python: Pydantic v2. TypeScript: strict mode, Zod schemas.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher (Browser)                         │
│              Next.js 15 Dashboard                           │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST / WebSocket (SSE)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Gateway  :8001                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         LangGraph Runtime (Embedded)                 │    │
│  │  ┌──────────────────────────────────────────┐    │    │
│  │  │        Teaching-Pack Stage Graph          │    │    │
│  │  │ setup_contract → planning → artifacts     │    │    │
│  │  │ → render_quality → teacher_approval       │    │    │
│  │  └──────────────────────────────────────────┘    │    │
│  │       │                                              │    │
│  │  ┌────┴────────────────────────────────────┐        │    │
│  │  ▼           ▼             ▼            ▼           │    │
│  │  Planner  Researcher  ContentCreator  Reviewer      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  LiteLLM Proxy :4000 ──► 9Router sidecar :20128            │
│  PostgreSQL :5432 │ Redis :6379                             │
└─────────────────────────────────────────────────────────────┘
```

### Stage Interaction Pattern

```
Teaching-Pack Stage Graph
  ├─► planning_blueprint        → Planner node → LessonPlan JSON
  ├─► post_blueprint_research   → Researcher node → ResearchBundle JSON
  ├─► artifact_workflow         → ContentCreator node → ArtifactContent JSON
  └─► render_quality            → Reviewer/quality gate → JudgeOutput / quality reports
```

The decommissioned Lead Agent and `task()` delegation stub are not runtime surfaces.

---

## 3. Pipeline Graphs

The authoritative LangGraph runtime is the teaching-pack stage graph (`packages/agents/teaching_pack/graph.py`). Legacy graph/Lead-Agent surfaces are decommissioned and guarded by deletion tests.

### 3.1 Teaching-Pack Stage Graph — 9 Stages (`build_teaching_pack_graph`)

**Status**: Authoritative runtime. Single-lesson runs use this path.

```
setup_contract → preplanning_search → planning_blueprint → post_blueprint_research
  → artifact_workflow → render_quality → compliance_gate → teacher_approval → export_finalize → END
```

**Conditional seams** (3):
- After `render_quality`: routes to `planning_blueprint`, `post_blueprint_research`, `artifact_workflow`, or `compliance_gate`
- After `compliance_gate`: routes to `teacher_approval` on pass or `artifact_workflow` on fail-closed hard blocks
- After `teacher_approval`: routes to `export_finalize` (approve) or `artifact_workflow` (reject with scoped feedback)

**ADR-017 extension** (proposed, not yet implemented):
- `mode="plan_unit"` → `TRIAGE → UNIT_PLANNING → UNIT_APPROVAL → UNIT_PREP → END`
- `mode="generate_pack"` → existing stage sequence above (children take this path)

### Gate Nodes (LangGraph `interrupt()`)

| Gate | Graph | Teacher Action | On Reject |
|------|-------|---------------|-----------|
| `teacher_approval` | Teaching-pack | approve / edit / reject / audited fast-lane auto-approve with visible revert window | Loop back to `artifact_workflow` |

Gates time out after **24 hours** and auto-escalate to admin.

### Conditional Routing

- After `render_quality`: route to `planning_blueprint`, `post_blueprint_research`, `artifact_workflow`, or `compliance_gate` based on quality recovery output.
- After `compliance_gate`: route to `teacher_approval` only when deterministic hard-block checks pass; otherwise return to `artifact_workflow`.
- After `teacher_approval`: route to `export_finalize` on approval or back to `artifact_workflow` on scoped rejection.

---

## 4. Agent Definitions

### 4.1 Planner Agent

```
Model:   deepseek-v4-flash  (via LiteLLM)
Tools:   web_search, read_file
Role:    Backward design (UbD) lesson planning.
         Output: LessonPlan JSON (see §5).
Turns:   max 80
Schema:  LessonPlan (Pydantic v2)
```

**Output contract:**
```python
class LessonPlan(BaseModel):
    topic: str
    grade_level: str          # e.g. "Grade 5"
    subject: str
    duration_minutes: int     # 10–180
    learning_objectives: list[LearningObjective]   # min 1, max 10, ≥2 Bloom levels
    prerequisite_knowledge: list[str]
    learning_plan: dict       # Gagné 9-event phases
    assessment_checkpoints: list[dict]
```

### 4.2 Researcher Agent

```
Model:   deepseek-v4-flash  (via LiteLLM)
Tools:   web_search, web_fetch, read_file
Role:    Gather, cross-reference, synthesize sources.
         Verify every factual claim against ≥2 sources (FACT protocol).
Turns:   max 80
Schema:  ResearchBundle (Pydantic v2)
```

**Research policies:**

| Policy | Minimum Sources | Cross-ref Required |
|--------|----------------|-------------------|
| `basic` | 2–3 | factual accuracy only |
| `standard` | 5+ | citations required |
| `rigorous` | 10+ | peer-reviewed preferred |

Default policy: `standard`.

### 4.3 Content Creator Agent

```
Model:   deepseek-v4-flash  (via LiteLLM, fallback: deepseek-compressed)
Tools:   read_file, write_file
Role:    Generate structured JSON content for each artifact type.
         Output rendered via Eta templates — never raw HTML directly.
Turns:   max 120
Schema:  ArtifactContent (Pydantic v2)
```

**Output contract:**
```python
class ArtifactContent(BaseModel):
    artifact_type: Literal["lesson","worksheet","quiz","drill","recap","infographic"]
    theme: str                 # "default" | "ocean" | "forest"
    title: str                 # min 3, max 200 chars
    sections: list[dict]       # min 1
    metadata: dict
    accessibility: dict        # language, reading_level, alt_texts
```

**Hard constraints:**
- Return JSON only — never raw HTML
- No CDN references in data
- No student PII (name, email, score) in output
- Answer keys must be absent from student-facing output; deterministic compliance fails closed on English/Vietnamese answer-key leakage markers.

### 4.4 Reviewer Agent

```
Model:   gpt-5.4  (via LiteLLM; different model from generator = bias mitigation)
Tools:   read_file
Role:    LLM-as-Judge. 3-layer G-Eval scoring.
Turns:   max 40
Schema:  JudgeOutput (Pydantic v2)
```

**Scoring weights:**

| Layer | Weight | Criteria |
|-------|--------|---------|
| Format compliance | 15% | DOCTYPE, no CDN, brand strings, responsive |
| Content quality | 55% | Accuracy, completeness, relevance, reasoning |
| Presentation | 30% | Readability, engagement, accessibility |

**Pass threshold:** `overall_score ≥ 7.0`

**Bias mitigations:**
- Rationale written before score (think-before-score)
- 3 independent judge calls → majority vote
- Generator model ≠ judge model
- Explicit guard: "Do not rate longer answers higher"

---

## 5. State Schema

The live teaching-pack runtime uses `TeachingPackState` in `packages/agents/teaching_pack/nodes.py`, with boundary-local state shapes for middleware, gates, and node adapters. The deleted legacy state module is not a runtime contract.

```python
from typing import Annotated, NotRequired
from langgraph.graph import StateGraph

class TeachingPackState(TypedDict):
    # ── Input ──────────────────────────────
    raw_request: str
    teacher_id: str
    class_info: dict          # {grade, subject, student_count, language}
    run_id: str

    # ── Planning ───────────────────────────
    lesson_plan: NotRequired[dict]
    blueprint_approved: bool
    revision_feedback: NotRequired[str]

    # ── Research ───────────────────────────
    research_bundle: NotRequired[dict]
    research_policy: str      # "basic" | "standard" | "rigorous"

    # ── Content ────────────────────────────
    artifact_types: list[str]
    theme: str
    artifacts: Annotated[list[dict], merge_artifacts]   # deduplicated

    # ── Quality ────────────────────────────
    quality_scores: NotRequired[dict]
    quality_passed: bool
    teacher_approved: bool
    revision_count: int

    # ── Gate tracking (written by gate nodes) ───────────────────────────────────
    fail_layer: NotRequired[str | None]       # "schema" | "content" | "judge" | "human"
    fail_count: NotRequired[int]              # incremented by healing_node
    fail_type: NotRequired[str | None]        # "validation" | "content" | "score" | "timeout"
    fail_context: NotRequired[dict[str, Any] | None]    # error details for healing strategy

    # ── Gate scores ──────────────────────────────────────────────────────────────
    schema_valid: NotRequired[bool | None]
    content_review_passed: NotRequired[bool | None]
    judge_score: NotRequired[float | None]    # overall G-Eval score
    export_ready: NotRequired[bool | None]

    # ── Healing / model override ─────────────────────────────────────────────────
    escalate: NotRequired[bool]              # set True to trigger escalation
    escalate_reason: NotRequired[str | None]
    healing_strategy: NotRequired[str | None]  # "retry" | "rewrite" | "reroute" | "replan" | "escalate"
    healing_note: NotRequired[str | None]
    healing_context: NotRequired[dict[str, Any] | None]
    generation_model: NotRequired[str | None]  # overrides default model for generation

    # ── HITL Gate ────────────────────────────────────────────────────────────────
    teacher_decision: NotRequired[str]   # "approve" | "reject" | "edit"
    gate_payload: NotRequired[dict[str, Any]]   # data shown to teacher at gate

    # ── Error ────────────────────────────────────────────────────────────────────
    error: NotRequired[str]   # set by any node on unrecoverable failure

    # ── Review ───────────────────────────────────────────────────────────────────
    review_results: NotRequired[dict[str, Any] | None]   # output from reviewer agent

    # ── Diagnostic ───────────────────────────────────────────────────────────────
    student_responses: NotRequired[dict[str, Any] | None]   # StudentResponse JSON
    diagnostic_report: NotRequired[dict[str, Any] | None]   # DiagnosticReport JSON
    student_profile: NotRequired[dict[str, Any] | None]     # StudentProfile JSON

    # ── Export ─────────────────────────────
    export_formats: list[str]  # ["html", "gift", "h5p"]
    exported_files: Annotated[list[dict[str, Any]], merge_exported_files]

    # ── Metadata ───────────────────────────
    current_step: int          # 1–13
    tokens_used: int
    cost_usd: float
```

### Custom Reducers

```python
def merge_artifacts(prev: list, new: list) -> list:
    """Deduplicated union preserving insertion order."""
    seen = set()
    result = []
    for item in (prev or []) + (new or []):
        key = item if isinstance(item, str) else item.get("id", str(item))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
```

### Persistence Strategy

| Environment | Checkpointer | Notes |
|------------|-------------|-------|
| `development` | `MemorySaver` | Lost on restart |
| `staging` | `SqliteSaver` | File: `omc_checkpoints.db` |
| `production` | `PostgresSaver` | Multi-instance safe |

---

## 6. LLM Routing

All agents call **LiteLLM Proxy** at `http://litellm:4000`. LiteLLM routes to providers or to 9Router.

### 6.1 Model Assignment per Agent

| Agent / Task | Primary Model | Fallback | ~Cost/call |
|-------------|--------------|----------|-----------|
| Planner | `deepseek-v4-flash` | `deepseek-v4-pro` | $0.0017 |
| Researcher | `deepseek-v4-flash` | `deepseek-v4-pro` | $0.0010 |
| Content Creator | `deepseek-free` → `deepseek-compressed` → `deepseek-direct` | `gpt-4.1-mini` | $0 → $0.0017 |
| Reviewer (Judge) | `content-fusion` | `gpt-5.4` | $0.015 |
| Code Generation | `claude-sonnet-4-6` | `gpt-5.4` | $0.033 |

### 6.1.1 9Router Combo Mapping

| LiteLLM Model Name | 9Router Combo | Providers | Cost |
|---|---|---|---|
| `gpt-5.4` | `f.pro` | Kiro AI, OpenCode, Vertex AI | $0 (free tier) |
| `deepseek-v4-flash` | `f.light` | Kiro AI, OpenCode | $0 (free tier) |
| `deepseek-free` | `f.light` | Kiro AI, OpenCode | $0 (free tier) |
| `content-fusion` | `f.pro` (fusion) | Kiro AI + OpenCode parallel | $0 (free tier) |
| `deepseek-compressed` | `f.light` (RTK) | Kiro AI, OpenCode | $0 (free tier) |

> **All traffic routes through 9Router sidecar (port 20128).**
> Model names are LiteLLM virtual routes — NOT direct API calls.
> When 9Router is unreachable → fail safely (queue/run or error).
> NO paid fallbacks. Budget cap = $0 for all virtual keys.

### 6.2 2-Layer Proxy Architecture

```
Agent
  └─► LiteLLM :4000      (budget control, cost tracking, fallback chains, Redis cache)
        ├─► Direct        (DeepSeek API, OpenAI API, Anthropic API)
        └─► 9Router :20128  (RTK compression, free tiers, fusion combo)
              ├─► Kiro AI   (Claude 4.5 free tier)
              ├─► OpenCode  (free tier)
              └─► Vertex AI ($300 credits)
```

### 6.3 9Router Combos

| Combo Name | Strategy | Use Case |
|-----------|----------|---------|
| `deepseek-free` | free-tier → Kiro AI | High-volume drafting, zero cost |
| `deepseek-compressed` | RTK compress → DeepSeek API | Tool-heavy content gen (20–40% token savings) |
| `content-fusion` | fusion (parallel GPT-5.4 + Claude → judge) | Quality gate, max accuracy |

### 6.4 Fallback Chains (LiteLLM config)

```yaml
litellm_settings:
  fallbacks:
    - deepseek-free:      ["deepseek-compressed", "deepseek-direct"]
    - content-fusion:     ["gpt-5.4"]
    - gpt-5.4:            ["claude-sonnet-4-6"]
    - claude-sonnet-4-6:  ["gpt-5.4"]
  context_window_fallbacks:
    - deepseek-v4-flash:  ["gpt-4.1-mini"]
  num_retries: 3
  request_timeout: 120
  allowed_fails: 3
  cooldown_time: 30
```

### 6.5 Per-Agent Cost Attribution

```python
# Every LLM call must include metadata tags
extra_body={
    "metadata": {
        "tags": [
            f"agent:{agent_name}",
            f"step:{current_step}",
            f"run:{run_id}",
            "pipeline:oh-my-class"
        ]
    }
}
```

---

## 7. Quality Gates — 6 Layers

Gates run sequentially. Any `CRITICAL` failure at any layer blocks progress.

### Layer 1 — JSON Schema Validation

- **Tool**: Pydantic v2 model validators
- **Self-healing**: `ModelRetry` up to 3 times, then `CircuitBreaker(threshold=3)`
- **Key checks**: Required fields, format patterns, no placeholder content (`[TBD]`, `lorem ipsum`), Bloom coverage ≥2 levels, no answer key in student fields

### Layer 2 — Content-Type Rules

- **FACT Hallucination Protocol**: Find → Assess → Cross-reference → Tag (`VERIFIED`/`MODIFIED`/`REMOVED`/`UNCERTAIN`)
- **Minimum verification**: 2 independent sources for every HIGH-risk claim
- **Age-appropriateness**: Flesch-Kincaid grade level check; forbidden content per age band
- **Binary pedagogical metrics** (all 7 must pass): prompt_alignment, factual_correctness, clarity, contextual_relevance, engagement, harmful_content_avoidance, solution_accuracy

### Layer 3 — Presentation Contract

- **DOCTYPE** present
- **No external assets** (CDN links, external images, `@import url(http...)`)
- **Answer key separation** — no visible answer data in student-facing artifacts
- **Viewport meta** present
- **Brand strings** (`oh-my-class`) present
- **Responsive check** via Playwright at 375/768/1280/1920px (staging/prod only)

### Layer 4 — LLM-as-Judge (G-Eval)

```
Score = Layer1×0.15 + Layer2×0.55 + Layer3×0.30
Pass if score ≥ 7.0 AND no critical issues
Majority vote: 3 independent judge calls
```

Self-heal strategies on failure:

| Attempt | Strategy | When |
|---------|----------|------|
| 1st | Rewrite (same model, new prompt with error feedback) | Validation failure |
| 2nd | Reroute (different model) | Model-specific failure |
| 3rd | Replan (new content plan) | Structural failure |
| 4th | Escalate to teacher | Budget exhausted |

### Layer 5 — Human-in-the-Loop

```python
# LangGraph interrupt at Teacher Gate 2
response = interrupt({
    "gate": "content_approval",
    "artifacts": state["artifacts"],
    "quality_scores": state["quality_scores"],
    "actions": ["approve", "edit", "reject"]
})
```

- Notification via webhook (Telegram/Zalo/email)
- Timeout: 24 hours → auto-escalate
- Max revisions: 3 cycles before full replan

### Layer 6 — Export Readiness

- 3 independent judges (different models) — 2/3 must pass
- Format-specific required artifacts check (`html` requires `lesson`, `gift` requires `quiz`)
- Skip threshold: if ≥20% items fail → stop + ask teacher

### Hard Blocks (auto-fail regardless of score)

`packages/quality/compliance_policy.py` is the single owner for deterministic hard-block policy. Layer-3 HTML validation, Layer-4 judge hard-block checks, presentation gate compatibility wrappers, and the teaching-pack `compliance_gate` all delegate to that policy. Violations fail closed before teacher approval and emit `hard_block_violation` observability events with non-sensitive code/reason/location payloads.

---

## 8. Template System

### 8.1 Overview

```
ArtifactContent JSON
        │
        ▼
   Eta Template Engine (TypeScript)
        │  templates/pages/{artifact_type}.html
        │  templates/components/*.html
        │  templates/branding/theme_{name}.css  (auto-generated from theme.json)
        ▼
   Standalone HTML
   (all CSS inlined, no CDN, works offline)
```

### 8.2 Template Directory

```
templates/
├── base.html                  # Shell: DOCTYPE, head, header, footer, inline JS
├── pages/
│   ├── lesson.html
│   ├── worksheet.html
│   ├── quiz.html
│   ├── drill.html
│   ├── recap.html
│   └── infographic.html
├── components/
│   ├── question_mc.html       # Multiple choice
│   ├── question_fill.html     # Fill-in-blank
│   ├── question_match.html    # Matching
│   ├── question_order.html    # Ordering
│   ├── hint_box.html
│   ├── feedback.html
│   ├── progress_bar.html
│   ├── math_block.html        # LaTeX via KaTeX (inlined)
│   └── data_chart.html
└── branding/
    ├── theme_default.css      # Auto-generated — do not edit manually
    ├── theme_ocean.css
    └── theme_forest.css
```

### 8.3 Three-Tier CSS Token System

```
PRIMITIVES         →  SEMANTIC TOKENS   →  COMPONENT TOKENS
(raw hex values)      (meaning)             (scoped to component)

--color-blue-500      --color-primary       .quiz-option { border-color: var(--color-primary) }
--space-4             --space-md
```

Theme is driven by `common/branding/kits/{name}/theme.json` — single source of truth.

### 8.4 Standalone HTML Invariants

- All CSS inlined in `<style>` — no `<link rel="stylesheet">`
- System font stack only (zero weight): `system-ui, -apple-system, 'Segoe UI', Roboto, ...`
- Images: inline SVG preferred; small bitmaps as base64 data URIs; large images → omit or host separately
- JS: minimal, inline, vanilla; no frameworks; no `eval()`
- Print styles: `@media print` with `.no-print { display:none }` and `.page-break`
- Dark mode: `@media (prefers-color-scheme: dark)` via CSS vars

### 8.5 Security Layers

1. Eta auto-escaping (`<%= %>` escapes HTML entities)
2. DOMPurify server-side sanitization post-render
3. `<iframe sandbox="allow-scripts">` for previews (never combine with `allow-same-origin`)
4. CSP header: `default-src 'self'; script-src 'none'` on export endpoint

---

## 9. Exercise Types — Quick Reference

Full schemas in `common/schemas/src/exercise-types/`.

### Core Assessment (§1)

| Type | Key | Supported Artifacts |
|------|-----|-------------------|
| Multiple Choice Single | `multiple_choice_single` | lesson, worksheet, quiz, drill, recap |
| Multiple Choice Multiple | `multiple_choice_multiple` | worksheet, quiz, drill |
| True/False 4-item | `true_false_4item` | quiz, drill, recap |
| Short Answer | `short_answer` | worksheet, quiz, drill, recap |
| Essay | `essay` | lesson, worksheet, quiz |
| Fill Blank (word bank) | `fill_blank_wordbank` | lesson, worksheet, drill |
| Cloze (free) | `cloze` | worksheet, drill, quiz |
| Matching | `matching` | lesson, worksheet, drill |
| Ordering | `ordering` | worksheet, drill, quiz |
| Drag and Drop | `drag_and_drop` | lesson, drill, quiz |

### English Language (§2) — 19 types

`vocabulary_scaffolded`, `cloze_mixed`, `reading_comprehension`, `grammar_transformation`,
`error_correction`, `sentence_manipulation`, `paraphrase`, `dialogue_completion`,
`phonics`, `dictation`, `translation`, `idioms`, `collocation`, `word_analysis`,
`tense_timeline`, `conditional_builder`, `reported_speech`, `passive_voice`, `matching_vocabulary`

### Math/Science (§3) — 7 types

`step_by_step_math` (CGI types), `geometric_proof`, `data_interpretation`,
`lab_report`, `measurement`, `coding_exercise`, `financial_literacy`

### Multimedia Homework (§4) — 7 types

`multimedia_video`, `multimedia_audio`, `multimedia_photo`,
`experiment_documentation`, `parent_child_activity`, `field_trip_journal`, `art_project`

### Gamified (§6) — key types

`timed_challenge`, `streak_system`, `adaptive_difficulty`, `branching_scenario`, `collaborative_activity`

### Vietnamese Exam Specifics

- **TF 4-item scoring** (per QĐ 764/QĐ-BGDDT): 1 correct=0.1đ, 2=0.25đ, 3=0.5đ, 4=1.0đ
- **Difficulty distribution**: nhận biết 40% / thông hiểu 30% / vận dụng 20% / vận dụng cao 10%
- **Bloom mapping**: nhận biết=remember, thông hiểu=understand, vận dụng=apply+analyze, vận dụng cao=evaluate+create

---

## 10. Export Formats

All formats generated from the same `ArtifactContent` JSON — format-agnostic internal model.

### Moodle GIFT (`.txt`)

- Simplest. Line-oriented. Start here for new export implementations.
- Supports: MCQ, TF, short answer, matching, numerical, essay, missing word
- Partial credit via `%50%` syntax
- Category: `$CATEGORY: oh-my-class/{subject}/{topic}`

### H5P (`.h5p` ZIP)

- Richest interactivity. Bundle: `h5p.json` + `content/content.json` + library files.
- Key types: `H5P.MultiChoice`, `H5P.Blanks`, `H5P.DragText`, `H5P.Summary`, `H5P.Flashcards`
- Generate only `content/content.json` — pre-built libraries handle rendering.

### QTI 2.1 (XML ZIP)

- Most interoperable standard (1EdTech). Export-only (not import).
- Structure: `imsmanifest.xml` + `assessments/test.xml` + `items/*.xml`
- Use for LMS integrations beyond Moodle.

### Google Forms (REST API)

- OAuth 2.0 (`forms.body` scope). Two-step: create → `batchUpdate`.
- Auto-gradable types: radio, checkbox, dropdown, short answer (exact match).
- Limitation: no partial credit, no math/LaTeX.

### Format Selection Guide

```
Teacher wants to use Moodle?         → GIFT + H5P
Teacher wants interactive homework?  → H5P
Teacher wants to share a Google Form? → Google Forms API
Teacher just wants printable files?  → Standalone HTML
Maximum portability?                 → QTI 2.1
```

---

## 11. Project Structure

```
oh-my-class/
├── packages/
│   ├── agents/                  # LangGraph multi-agent pipeline (Python)
│   │   ├── sub_agents/          # planner, researcher, content_creator, reviewer, diagnostician, roadmap_agent
│   │   ├── teaching_pack/       # Authoritative stage graph (ADR-017 runtime)
│   │   │   ├── graph.py         # build_teaching_pack_graph — 8-stage StateGraph
│   │   │   ├── stages.py        # TeachingPackStage StrEnum (8 values)
│   │   │   ├── nodes.py         # Stage node implementations + routing
│   │   │   ├── ports.py         # Port/interface contracts
│   │   │   ├── quality.py       # Quality gate wiring
│   │   │   ├── quality_routing.py
│   │   │   ├── scoped_regeneration.py
│   │   │   ├── snapshots.py
│   │   │   ├── checkpointing.py
│   │   │   ├── artifacts.py
│   │   │   └── config.py
│   │   ├── middleware/          # 23 active single-concern layers
│   │   │   ├── base.py          # BaseMiddleware ABC (order 1–23)
│   │   │   ├── registry.py      # Middleware chain registration
│   │   │   ├── context/         # Context middleware (dynamic_context, memory, etc.)
│   │   │   ├── quality/         # Quality middleware
│   │   │   ├── safety/          # Safety middleware
│   │   │   └── terminal/        # Terminal middleware
│   │   ├── tools/
│   │   ├── gates.py             # interrupt() gate node implementations
│   │   ├── healing.py           # Self-heal orchestrator
│   │   ├── events.py            # In-memory event bus (SSE/observability only)
│   │   ├── checkpointer.py      # get_checkpointer factory
│   │   └── observability.py     # Langfuse tracing
│   ├── quality/                 # 6-layer quality gate system (Python)
│   │   ├── layer1_schema/
│   │   ├── layer2_content/
│   │   ├── layer3_html/
│   │   ├── layer4_judge/
│   │   ├── layer5_human/
│   │   └── layer6_export/
│   ├── renderer/                # Eta template engine → standalone HTML (TypeScript)
│   │   ├── src/renderer.ts
│   │   ├── src/inline-assets.ts
│   │   └── templates/          # see §8.2
│   └── exporters/               # Export format generators (TypeScript)
│       ├── src/gift/
│       ├── src/h5p/
│       └── src/qti/
├── common/
│   ├── contracts/               # Pydantic models (Python) — source of truth for schemas
│   │   ├── run_contract.py      # RunContract, PipelineMode, ArtifactType, etc.
│   │   ├── lesson_plan.py
│   │   ├── artifact.py
│   │   ├── judge_output.py
│   │   └── auth.py
│   ├── schemas/                 # TypeScript types + Zod schemas (generated from Pydantic)
│   │   └── src/
│   │       ├── exercise-types/  # One file per exercise type
│   │       ├── questions.ts
│   │       └── generated/       # Auto-generated from Pydantic — do not edit
│   └── branding/
│       └── kits/
│           ├── default/theme.json  # Single source of truth for all themes
│           ├── ocean/
│           └── forest/
├── services/
│   ├── gateway/                 # FastAPI + embedded agent runtime :8001
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── teaching_packs.py   # Teaching-pack endpoints
│   │   │   └── health.py
│   │   ├── teaching_pack_models.py # TeachingPack SQLAlchemy models
│   │   ├── teaching_pack_store.py  # TeachingPackJobStore
│   │   ├── recovery_sweeper.py     # Stuck job + gate escalation sweeper
│   │   ├── middleware/
│   │   ├── auth/
│   │   ├── webhooks/
│   │   ├── observability/
│   │   ├── models.py            # Run, RunStatus, RunEvent SQLAlchemy models
│   │   └── alembic/
│   ├── proxy/                   # LiteLLM proxy :4000
│   │   └── config.yaml
│   └── router/                  # 9Router sidecar :20128
│       └── config.yaml
├── apps/
│   └── web/                     # Next.js 15 teacher dashboard :3000
│       └── src/app/
├── skills/                      # Markdown skills injected into agent prompts
│   ├── blueprint-designer/SKILL.md
│   ├── pack-generator/SKILL.md
│   ├── artifact-reviewer/SKILL.md
│   └── export-assistant/SKILL.md
├── infra/
│   └── compose/docker-compose.yml
├── scripts/                     # Utility scripts (generate_zod_schemas, typecheck, etc.)
├── tests/                       # Cross-package integration + E2E tests
└── AGENTS.md                    # ← this file
```

### Package Boundaries (enforced by CI)

```
packages/agents     →  MUST NOT import from  services/* or apps/*
packages/quality    →  MUST NOT import from  services/* or apps/*
packages/renderer   →  MUST NOT import from  services/* or apps/*
packages/exporters  →  MUST NOT import from  services/* or apps/*
common/contracts    →  MUST NOT import from  packages/* or services/* or apps/*
services/*          →  MAY import from       packages/* and common/*
apps/*              →  MAY import from       packages/* and common/* and services/*
```

---

## 12. Coding Conventions

### Python (agents, gateway)

```python
# ✅ DO: one agent = one file = one responsibility
# packages/agents/sub_agents/planner/agent.py

# ✅ DO: typed function signatures with Pydantic models
def design_lesson_plan(state: TeachingPackState) -> dict[str, Any]:
    ...

# ✅ DO: explicit return types for LangGraph nodes
def quality_review_node(state: TeachingPackState) -> TeachingPackState:
    return {"quality_scores": scores, "quality_passed": passed}

# ❌ DON'T: raise bare exceptions — use typed domain exceptions
class ValidationGateError(Exception):
    def __init__(self, layer: int, issues: list[str]):
        ...

# ❌ DON'T: put business logic in __init__.py
```

### TypeScript (template renderer, frontend)

```typescript
// ✅ DO: strict mode, explicit return types
function renderArtifact(data: ArtifactContent): string { ... }

// ✅ DO: Zod schemas co-located with types
const ArtifactContentSchema = z.object({ ... });
type ArtifactContent = z.infer<typeof ArtifactContentSchema>;

// ❌ DON'T: use `any`
// ❌ DON'T: import from `app/` in renderer package
```

### Middleware (Python)

Every middleware is a single Python file `~200 lines` implementing one `BaseMiddleware` interface:

```python
class BaseMiddleware:
    name: str
    order: int                # 1–23; Clarification MUST be 23

    async def before_model(self, state: ThreadState, context: MiddlewareContext) -> ThreadState: ...
    async def after_model(self, state: ThreadState, context: MiddlewareContext) -> ThreadState: ...
```

Middleware execution order is fixed. **Clarification (23) must always be last.**

### Parked-status TTL policy

Parked code is temporary, not a permanent state. Any component intentionally parked in the repo must carry this marker in the file that owns the component or in the closest component README:

```text
Status: Parked
Parked-Until: YYYY-MM-DD
```

`Parked-Until` must be no more than 90 days after the parking decision. `tests/test_parked_status_ttl.py` scans live component paths in CI and fails when a parked marker has no date or the date is expired. The same test includes an intentionally expired fixture to prove the policy catches expiry.

### LangGraph Nodes

- One Python file per node in `packages/agents/` or `services/gateway/`
- Legacy graph naming: `step_01_preflight.py` through `step_13_export.py`
- Teaching-pack graph: `nodes.py` with `make_stage_node()` dispatch per `TeachingPackStage`
- Every node is a pure function: `(state) → partial_state`
- No I/O except via state — nodes never write to disk directly

### Configuration over Code

```yaml
# config/agents-config.yaml — change model assignment here, not in code
agents:
  planner:
    model: deepseek-v4-flash
    fallback: deepseek-v4-pro
    max_turns: 80
    research_policy: standard
  content_creator:
    model: deepseek-free
    fallback_chain: [deepseek-compressed, deepseek-direct]
    max_turns: 120
```

---

## 13. Testing

> **Runbook** (commands, tiers, REST walkthrough, artifact verification): [`docs/testbook/runbook.md`](docs/testbook/runbook.md)

### Test Pyramid

```
Unit Tests         packages/agents/tests/              pytest
                   packages/renderer/__tests__/        Vitest
                   common/contracts/tests/             pytest

Integration Tests  tests/integration/                  pytest + TestClient
                   (real LangGraph graph, mock LLMs)

E2E Tests          tests/e2e/                          pytest
                   (real pipeline, real LiteLLM sandbox keys)
```

### Agent Testing Pattern

```python
# Unit-test each agent node in isolation
def test_planner_node():
    state = TeachingPackState(
        raw_request="Toán lớp 5 — Phân số",
        teacher_id="t-001",
        class_info={"grade": 5, "subject": "math", "student_count": 30}
    )
    result = design_lesson_plan(state)

    assert "lesson_plan" in result
    plan = LessonPlan(**result["lesson_plan"])  # validates via Pydantic
    assert len(plan.learning_objectives) >= 1
    bloom_levels = {lo.bloom_level for lo in plan.learning_objectives}
    assert len(bloom_levels) >= 2, "Must cover ≥2 Bloom levels"
```

### Quality Gate Testing Pattern

```python
# Test each gate layer independently
def test_layer1_rejects_placeholder_content():
    artifact = {"title": "[TBD]", "sections": []}
    with pytest.raises(ValidationError, match="placeholder"):
        ArtifactContent(**artifact)

def test_layer3_rejects_cdn_link():
    html = '<!DOCTYPE html><link href="https://cdn.tailwindcss.com">'
    issues = PresentationValidator().validate_external_assets(html)
    assert any("CDN" in i for i in issues)
```

### Mock LLM Pattern (integration tests)

```python
# Use LiteLLM's built-in mock mode — no real API calls in CI
os.environ["LITELLM_MOCK_RESPONSE"] = "true"
```

### Template Renderer Tests

```typescript
// Vitest: test every artifact type renders valid HTML
describe("quiz template", () => {
  it("outputs standalone HTML with no external assets", () => {
    const html = renderArtifact(mockQuizData);
    expect(html).toMatch(/<!DOCTYPE html>/);
    expect(html).not.toMatch(/href="https?:\/\//);
    expect(html).not.toMatch(/src="https?:\/\//);
    expect(html).toContain("oh-my-class");
  });
});
```

### Coverage Targets

| Package | Line Coverage |
|---------|--------------|
| `packages/agents` | ≥ 85% |
| `common/contracts` | ≥ 95% |
| `packages/renderer` | ≥ 90% |
| `packages/quality` | ≥ 90% |

---

## 14. Hard Invariants

These rules are never negotiable. CI enforces them.

```
INVARIANT-01  The stage graph owns orchestration; content is generated only by
              the content-creator node, not by a supervisor/Lead Agent surface.

INVARIANT-02  packages/agents NEVER imports from services/* or apps/*.
              packages/quality NEVER imports from services/* or apps/*.
              Enforced by CI import boundary check.

INVARIANT-03  Every LangGraph node is a pure function (state) → partial_state.
              No global side effects, no filesystem writes.

INVARIANT-04  HTML output MUST NOT contain any http(s):// asset reference.
              Zero exceptions. Violations trigger Layer 3 CRITICAL failure.

INVARIANT-05  Answer keys MUST be in teacher_only sections.
              Student-facing artifacts MUST NOT contain correct answers in any
              parseable or scrapeable form.

INVARIANT-06  Teacher Gate cannot be silently bypassed. Trust-score auto-approval
              is audited, visibly labelled, revertible, and permitted only after
              `compliance_gate_node` passes (ADR-026).

INVARIANT-07  All LLM calls MUST include metadata.tags with agent and run_id.
              Required for cost attribution.

INVARIANT-08  Clarification middleware is always the last active middleware (order=23).
              All other active middleware order values must be 1–22.

INVARIANT-09  theme.json is the single source of truth for all brand tokens.
              theme_*.css files are auto-generated — never edit them manually.

INVARIANT-10  Every Pydantic model that validates agent output MUST be in
              common/contracts, not in packages/agents or services/gateway/*.
              Contracts are the canonical schema — code references them, not the reverse.
```

---

---

## Agent skills

### Issue tracker

Local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Two labels: `needs-info` and `ready-for-agent`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` at repo root + `docs/adr/` for ADRs. See `docs/agents/domain.md`.

---

> **Last updated**: 2026-07-03
> **Maintained by**: Core team. PRs that violate any Hard Invariant will be rejected.
> **Source docs**: Technical Reports 01–07 (multi-agent blueprint, quality gates,
>   template system, LLM proxy, 9Router integration, exercise catalog, content research)
