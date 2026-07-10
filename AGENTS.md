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

---

## 3. Pipeline Graphs

The authoritative LangGraph runtime is the teaching-pack stage graph (`packages/agents/teaching_pack/graph.py`). Legacy graph/Lead-Agent surfaces are decommissioned and guarded by deletion tests.

### 3.1 Teaching-Pack Stage Graph — 10 Stages Default (`build_teaching_pack_graph`)

**Status**: Authoritative runtime. Two modes: `generate_pack` (children, default) and `plan_unit` (units).

**Default sequence (`generate_pack` mode, 10 stages):**

```
setup_contract → triage → preplanning_search → planning_blueprint → post_blueprint_research
  → artifact_workflow → render_quality → compliance_gate → teacher_approval → export_finalize → END
```

**Unit mode (`plan_unit` with `FEATURE_COMPONENT_STRATEGIST_V1`, 12 stages):**

```
setup_contract → triage → preplanning_search → planning_blueprint → post_blueprint_research
  → unit_planning → unit_approval → artifact_workflow → render_quality → compliance_gate
  → teacher_approval → export_finalize → END
```

The component-strategist variant reorders `unit_approval` before `artifact_workflow`. This is a structurally different pipeline, not just a longer one.

**Conditional edges** (6):
1. After `triage`: routes to `plan_unit` or `generate_pack` path based on request type
2. After `unit_approval` (plan_unit only): routes to `artifact_workflow` on approve, back to `unit_planning` on reject
3. After `artifact_workflow`: fan-out to render_quality based on artifact types
4. After `render_quality`: routes to `planning_blueprint`, `post_blueprint_research`, `artifact_workflow`, or `compliance_gate` based on quality recovery output
5. After `compliance_gate`: routes to `teacher_approval` on pass, or `artifact_workflow` on fail-closed hard blocks
6. After `teacher_approval`: routes to `export_finalize` on approve, or `artifact_workflow` on reject with scoped feedback

### Gate Nodes (LangGraph `interrupt()`)

| Gate | Graph | Pipeline | Teacher Action | On Reject |
|------|-------|----------|---------------|-----------|
| `unit_approval` | Teaching-pack | `plan_unit` only | approve / reject | Loop back to `unit_planning` |
| `teacher_approval` | Teaching-pack | Both modes | approve / edit / reject / audited fast-lane auto-approve with visible revert window | Loop back to `artifact_workflow` |

Both gates time out after **24 hours** and auto-escalate to admin.

### Gateway Gate Registry

The gateway exposes 6 named gates via `teaching_pack_gate_registry.py`, each with its own allowed actions. These are distinct from the graph-level stage nodes above:

| Gate Name | Allowed Actions |
|-----------|----------------|
| `CLARIFICATION` | respond |
| `CONTRACT_CONFIRMATION` | confirm / edit |
| `SEARCH_PLAN_CONFIRMATION` | approve / edit |
| `BLUEPRINT_APPROVAL` | approve / edit / reject |
| `CONTENT_APPROVAL` | approve / edit / reject |
| `UNIT_APPROVAL` | approve / reject |

Changes to the gate registry must update docs, API contract, and tests in the same PR.

### Conditional Routing

- After `triage`: route to unit-planning or generate-pack path based on request classification.
- After `unit_approval` (plan_unit only): route to `artifact_workflow` on approve; back to `unit_planning` on scoped rejection.
- After `render_quality`: route to `planning_blueprint`, `post_blueprint_research`, `artifact_workflow`, or `compliance_gate` based on quality recovery output.
- After `compliance_gate`: route to `teacher_approval` only when deterministic hard-block checks pass; otherwise return to `artifact_workflow`.
- After `teacher_approval`: route to `export_finalize` on approval or back to `artifact_workflow` on scoped rejection.

### Sync Rule

Every change to `graph.py`, `stages.py`, routing functions, or feature-flag stage variants must update AGENTS.md in the same PR. A snapshot test (`docs/runtime/teaching-pack-graph-contract.json`) enforces stage tuples and conditional routes against runtime code.

---

## 4. Agent Definitions

**Model source of truth:** `packages/agents/config/models.py`. All agents default to `"4omc"`. Per-task overrides via `MODEL_STRONG_DEFAULT`, `MODEL_FAST_DEFAULT`, `MODEL_<TASK>` env vars. Model assignment changes require docs update.

### 4.1 Planner Agent

```
Model:   4omc  (override: MODEL_FAST_DEFAULT)
Tools:   web_search, read_file
Role:    Backward design (UbD) lesson planning.
         Output: LessonPlan JSON (see §5).
Config:  max_retries=3, MaxTokensConfig per agent
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
Model:   4omc  (override: MODEL_FAST_DEFAULT)
Tools:   web_search, web_fetch, read_file
Role:    Gather, cross-reference, synthesize sources.
         Verify every factual claim against ≥2 sources (FACT protocol).
Config:  max_retries=3, MaxTokensConfig per agent
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
Model:   4omc  (override: MODEL_STRONG_DEFAULT)
Tools:   read_file, write_file
Role:    Generate structured JSON content for each artifact type.
         Output rendered via Eta templates — never raw HTML directly.
Config:  max_retries=3, MaxTokensConfig per agent
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

### 4.4 Reviewer Agent (AdaptiveJudge)

```
Model:   4omc  (different model from generator = bias mitigation)
Tools:   read_file
Role:    LLM-as-Judge. Constructs AdaptiveJudge with num_judges=3 (wired from GateConfig.judge_n).
         3-layer G-Eval scoring per judge; majority vote determines pass/fail.
Config:  max_retries=3, GateConfig.judge_n=3
Schema:  JudgeOutput (Pydantic v2)
```

The reviewer never calls an LLM directly. It constructs `AdaptiveJudge(num_judges=gate_config.judge_n)` and delegates transport back through the same `AgentRuntime`, adding multi-judge dispatch and deterministic hard-block override on top.

**Layer 4 rubric weights** (internal to each judge):

| Criterion | Weight | What it checks |
|-----------|--------|---------------|
| Format compliance | 15% | DOCTYPE, no CDN, brand strings, responsive |
| Content quality | 55% | Accuracy, completeness, relevance, reasoning |
| Presentation | 30% | Readability, engagement, accessibility |

**Pass threshold:** `overall_score ≥ 7.0`

**Bias mitigations:**
- Rationale written before score (think-before-score)
- 3 independent judge calls → majority vote (`GateConfig.judge_n=3`)
- Generator model ≠ judge model
- Explicit guard: "Do not rate longer answers higher"

### 4.5 Additional Agents

| Agent | Model | Role |
|-------|-------|------|
| `unit_planner` | 4omc (`MODELS.blueprint_design` alias) | Unit-level lesson sequencing |
| `practice_generator` | 4omc | Drill/practice set generation |
| `coherence_judge` | 4omc | Cross-artifact coherence check |
| `roadmap_agent` | 4omc (`MODELS.blueprint_design` alias) | Curriculum roadmap generation |
| `diagnostician` | 4omc | Student performance diagnostics |

---

## 5. State Schema

The live teaching-pack runtime uses `TeachingPackState` in `packages/agents/teaching_pack/nodes.py`, with boundary-local state shapes for middleware, gates, and node adapters. The deleted legacy state module is not a runtime contract. Generated `ArtifactContent` never belongs in LangGraph checkpoints: graph state keeps compact `artifact_references` and snapshot metadata only; `ArtifactContentStore` hydrates projections for quality, compliance, scoped edits, and the gateway completion boundary persists snapshots/exports.

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
    artifact_references: Annotated[list[dict], stable_merge_artifact_references]
        # document_id, artifact_id, artifact_type, generation_id, version, title

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
def stable_merge_artifact_references(prev: list, new: list) -> list:
    """Deduplicate compact durable references by document_id."""
    by_document_id = {item["document_id"]: item for item in prev or []}
    by_document_id.update({item["document_id"]: item for item in new or []})
    return sorted(by_document_id.values(), key=lambda item: item["document_id"])
```

### Persistence Strategy

| Environment | Checkpointer | Notes |
|------------|-------------|-------|
| `development` | `MemorySaver` | Lost on restart |
| `staging` | `SqliteSaver` | File: `omc_checkpoints.db` |
| `production` | `PostgresSaver` | Multi-instance safe |

---

## 6. LLM Routing

Default dev/staging path: **Agent → 9Router** (`LLM_BASE_URL=http://localhost:20228/v1`). LiteLLM proxy (`http://litellm:4000`) is optional, production-only, for budget control and fallback chains. The model source of truth is `packages/agents/config/models.py` (see §4).

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
  └─► 9Router :20128      (RTK compression, free tiers, fusion combo)
        ├─► Kiro AI   (Claude 4.5 free tier)
        ├─► OpenCode  (free tier)
        └─► Vertex AI ($300 credits)

  └─► LiteLLM :4000      [OPTIONAL, prod-only] (budget control, cost tracking, fallback chains)
        ├─► Direct        (DeepSeek API, OpenAI API, Anthropic API)
        └─► 9Router :20128  (same sidecar as above)
```

In dev/staging, agents hit 9Router directly. LiteLLM adds a budget-control layer only when `LITELLM_PROXY_URL` is set in production compose profiles.

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
- **Binary pedagogical metrics** (10 defined, 5 active): prompt_alignment, factual_correctness, clarity, contextual_relevance, engagement, harmful_content_avoidance, solution_accuracy. Remaining 5 deferred to post-delivery loop.

### Layer 3 — Presentation Contract

- **DOCTYPE** present
- **No external assets** (CDN links, external images, `@import url(http...)`)
- **Answer key separation** — no visible answer data in student-facing artifacts
- **Viewport meta** present
- **Brand strings** (`oh-my-class`) present
- **Responsive check** via Playwright at 375/768/1280/1920px (staging/prod only)

### Layer 4 — LLM-as-Judge (G-Eval)

```
Layer 4 uses internal rubric weights (not a cross-layer weighted score):
  Format compliance (15%) + Content quality (55%) + Presentation (30%)
Pass if score ≥ 7.0 AND no critical issues
3 independent judges (AdaptiveJudge, num_judges=3 from GateConfig); majority vote
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

- 3 independent judges (different models) — 2/3 must pass (`export_consensus_threshold=0.67`)
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
        │  branding/themes/*.json → runtime CSS generation
        ▼
   Standalone HTML
   (all CSS inlined, no CDN, works offline)
```

### 8.2 Template Directory

```
templates/
├── base.html                  # Shell: DOCTYPE, head, header, footer, inline JS
├── pages/                     # 13 page templates (6 original + 7 extensions)
│   ├── lesson.html
│   ├── worksheet.html
│   ├── quiz.html
│   ├── drill.html
│   ├── recap.html
│   ├── infographic.html
│   ├── teaching_pack.html
│   ├── slide_deck.html
│   ├── reading_passage.html
│   ├── exit_ticket.html
│   ├── answer_key.html
│   ├── roadmap.html
│   └── flashcard_deck.html
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
    └── themes/                # Canonical: ThemeTokens JSON files
        ├── default.json
        ├── ocean.json
        └── forest.json
```

### 8.3 Three-Tier CSS Token System

```
PRIMITIVES         →  SEMANTIC TOKENS   →  COMPONENT TOKENS
(raw hex values)      (meaning)             (scoped to component)

--color-blue-500      --color-primary       .quiz-option { border-color: var(--color-primary) }
--space-4             --space-md
```

**Canonical source:** `packages/renderer/src/theme/themes/*.json` (ThemeTokens, 3-tier).
Legacy flat `common/branding/kits/*/theme.json` is deprecated and will be deleted after migration.
CSS is generated at runtime by the renderer, not from pre-built CSS files.

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
- Coverage note: real TS `gift-impl` covers all listed types except `numerical`.

### H5P (`.h5p` ZIP)

- Richest interactivity. Bundle: `h5p.json` + `content/content.json` + library files.
- Key types: `H5P.MultiChoice`, `H5P.Blanks`, `H5P.DragText`, `H5P.Summary`, `H5P.Flashcards`
- Generate only `content/content.json` — pre-built libraries handle rendering.

### QTI 2.1 (XML ZIP)

- **Currently unsupported.** QTI skeleton exists but no real implementation.
- Full QTI support is a separate workstream.

### Google Forms

- Live OAuth + REST client, but **not an offline export format**.
- Split into external `PublishTarget` contract (not `ExportFormat`).
- Requires separate implementation for pipeline integration.

### Format Selection Guide

```
Teacher wants to use Moodle?         → GIFT + H5P
Teacher wants interactive homework?  → H5P
Teacher wants to share a Google Form? → PublishTarget (separate pipeline)
Teacher just wants printable files?  → Standalone HTML
Maximum portability?                 → QTI 2.1 (not yet available)
```

### Export Subprocess Bridging

GIFT and H5P formats are bridged from the gateway to the TS CLI via subprocess
(same pattern as Anki/TSV). The Python skeletons in the gateway are replaced
by real TS exporter output at request time. QTI returns an explicit unsupported
error rather than fake XML.

---

## 11. Project Structure

```
oh-my-class/
├── packages/
│   ├── agents/                  # LangGraph multi-agent pipeline (Python)
│   │   ├── sub_agents/          # planner, researcher, content_creator, reviewer, diagnostician, roadmap_agent
│   │   ├── teaching_pack/       # Authoritative stage graph (ADR-017 runtime)
│   │   │   ├── graph.py         # build_teaching_pack_graph — 10-stage StateGraph
│   │   │   ├── stages.py        # TeachingPackStage StrEnum (10 values)
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
│   │   ├── gates/               # interrupt() gate node implementations
│   │   ├── healing/             # Self-heal orchestrator
│   │   ├── events.py            # In-memory event bus (SSE/observability only)
│   │   ├── checkpointer.py      # get_checkpointer factory
│   │   └── observability/       # Langfuse tracing
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
│   └── branding/                # DEPRECATED — migrate to packages/renderer/src/theme/ then delete
│       └── kits/
│           ├── default/theme.json
│           ├── ocean/
│           └── forest/
├── services/
│   ├── gateway/                 # FastAPI + embedded agent runtime :8001
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── teaching_pack_runs.py  # Teaching-pack endpoints
│   │   │   └── health.py
│   │   ├── teaching_pack_models.py # TeachingPack SQLAlchemy models
│   │   ├── teaching_pack_job_store.py  # TeachingPackJobStore
│   │   ├── recovery_sweeper.py     # Stuck job + gate escalation sweeper
│   │   ├── middleware/
│   │   ├── auth/
│   │   ├── webhooks/
│   │   ├── observability/
│   │   ├── models.py            # Run, RunStatus, RunEvent SQLAlchemy models
│   │   └── alembic/
├── apps/
│   └── web/                     # 
│       └── src/app/
├── skills/                      # Empty (4 dead dirs deleted per grill session G3)
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

### Port Configuration (gateway)

The gateway runs on **different ports in local dev vs Docker — this is INTENTIONAL, not a bug.** There is no reverse proxy mapping `8101 → 8001`.

| Environment | Gateway port | Source |
|-------------|-------------|--------|
| Local dev (`make dev`) | `:8101` | `Makefile:39` `LOCAL_GATEWAY_PORT := 8101` |
| Docker (`compose up`) | `:8001` | `infra/compose/docker-compose.yml:40` `8001:8001` |

The web client targets the gateway via `NEXT_PUBLIC_GATEWAY_URL` — defaults to `http://localhost:8101` in local dev (`apps/web/src/lib/api-client.ts:7`), overridden to `:8001` for the Docker web service. Keep both ports as-is and document any change.

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

**6 quality middlewares** (`QUALITY_GATE_CONSOLIDATED_MIDDLEWARE` group: curriculum, readability, pedagogical, bias, artifact coherence, LO alignment) run as advisory signals in `render_quality` (warning-only, not hard-block). `SkillActivationMiddleware` uses `SkillLoader` from `packages/agents/skills/registry.py` as its path resolution source.

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

INVARIANT-09  ThemeTokens (3-tier JSON in packages/renderer/src/theme/) is the
              single source of truth for all brand tokens. Legacy flat
              common/branding/kits/*/theme.json is deprecated.

INVARIANT-10  Every Pydantic model that validates agent output MUST be in
              common/contracts, not in packages/agents or services/gateway/*.
              Contracts are the canonical schema — code references them, not the reverse.
```

### Small Docs Fixes (W19)

The following minor corrections were applied during the grill-session docs sync:

| Ref | Section | Fix |
|-----|---------|-----|
| 3.1 | Pipeline Graphs | Stage count corrected from "9" / "8" to **10** default, **12** with component strategist |
| 4.1 | Agent Definitions | Model names updated from stale `deepseek-v4-flash` / `gpt-5.4` to `"4omc"` (source: `models.py`) |
| 4.1 | Agent Definitions | Removed fabricated `max_turns` config; documented actual `max_retries` + `MaxTokensConfig` |
| 4.4 | Reviewer | Updated description from "direct LLM judge call" to AdaptiveJudge + multi-judge dispatch |
| 6.2 | LLM Routing | Topology inverted: 9Router direct is default; LiteLLM proxy is optional/prod-only |
| 6.4 | LLM Routing | Fallback chains documented as LiteLLM-only, not primary path |
| 8.2 | Template System | Template count updated from 6 to **13** pages (added teaching_pack, slide_deck, reading_passage, exit_ticket, answer_key, roadmap, flashcard_deck) |
| 8.2 | Template System | Removed `inlineCss()` reference; CSS inlined natively via `<%~ it.themeCSS %>` |
| 8.3 | Template System | Canonical source updated to `packages/renderer/src/theme/themes/*.json` (ThemeTokens) |
| 8.2 | Template System | `branding/theme_*.css` files replaced with `branding/themes/*.json` ThemeTokens |
| 9.1–9.3 | Project Structure | Gateway file names corrected: `teaching_packs.py` → `teaching_pack_runs.py`, `teaching_pack_store.py` → `teaching_pack_job_store.py` |
| 10.3–10.4 | Project Structure | Removed `services/proxy/` and `services/router/` (9Router is external sidecar); `skills/` marked empty |
| 7.4 | Export Formats | GIFT coverage note added: `numerical` type not supported by TS `gift-impl` |
| 5.1 | Quality Gates | Removed misleading cross-layer weighted score formula; 15/55/30 = Layer 4 internal rubric only |
| 5.2 | Quality Gates | Pedagogical metrics corrected from "7" to "10 defined, 5 active" |

---

## Agent skills

### Issue tracker

GitHub Issues on `github.com/maemreyo/oh-my-class` (uses `gh` CLI). No external PRs. Supports Wayfinder map/child/blocking operations. See `docs/agents/issue-tracker.md`.

### Triage labels

Five standard labels: `needs-triage` → `needs-info` → `ready-for-agent` / `ready-for-human` / `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at repo root + `docs/adr/` for ADRs. See `docs/agents/domain.md`. Use the `/anatomy` skill (located in `.agents/skills/anatomy`) to update or generate architecture documentation dynamically from the codebase.

---

> **Last updated**: 2026-07-03
> **Maintained by**: Core team. PRs that violate any Hard Invariant will be rejected.
> **Source docs**: Technical Reports 01–07 (multi-agent blueprint, quality gates,
>   template system, LLM proxy, 9Router integration, exercise catalog, content research)

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
