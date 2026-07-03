# Báo Cáo Kiến Trúc: Module packages/agents

> **Dự án**: oh-my-class
> **Module**: packages/agents
> **Phiên bản**: 1.0
> **Ngày tạo**: 2026-07-02
> **Trạng thái**: Phiên bản chính thức

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Sơ Đồ Kiến Trúc Tổng](#2-sơ-đồ-kiến-trúc-tổng)
3. [Định Nghĩa Agent](#3-định-nghĩa-agent)
   - 3.1 [Lead Agent (Đã Nghỉ Hưởng)](#31-lead-agent-supervisor--đã-nghỉ-hưởng)
   - 3.2 [Planner Agent](#32-planner-agent-thiết-kế-kế-hoạch-bài-học)
   - 3.3 [Researcher Agent](#33-researcher-agent-thu-thập-nguồn-tài-liệu)
   - 3.4 [Content Creator Agent](#34-content-creator-agent-tạo-nội-dung-bài-học)
   - 3.5 [Reviewer Agent](#35-reviewer-agent-đánh-giá-chất-lượng)
4. [Kiến Trúc Đồ Thị](#4-kiến-trúc-đồ-thị)
   - 4.1 [Legacy Graph (Đã Xóa)](#41-legacy-graph-đã-xóa)
   - 4.2 [Teaching-Pack Stage Graph](#42-teaching-pack-stage-graph-authoritative)
5. [State Schema](#5-state-schema)
6. [Hệ Thống Middleware (31 Lớp)](#6-hệ-thống-middleware-31-lớp)
7. [Quality Gates (6 Lớp)](#7-quality-gates-6-lớp)
8. [Hệ Thống Self-Healing](#8-hệ-thống-self-healing)
9. [Agent Tools](#9-agent-tools)
10. [Framework LangGraph — Các Pattern Sử Dụng](#10-framework-langgraph--các-pattern-sử-dụng)
11. [Bảng Tra Cứu File Chính](#11-bảng-tra-cứu-file-chính)
12. [Ghi Chú Kỹ Thuật](#12-ghi-chú-kỹ-thuật)

---

## 1. Tổng Quan

oh-my-class là hệ thống AI-powered teaching pack generator cho giáo dục K-12. Giáo viên mô tả bài học; hệ thống tạo ra bộ tài liệu giảng dạy hoàn chỉnh, sẵn sàng in và sử dụng, ở định dạng HTML độc lập. Module `packages/agents` chứa toàn bộ pipeline đa agent sử dụng LangGraph 1.x.

### Ngăn xếp công nghệ

| Tầng | Công nghệ | Lý do chọn |
|------|-----------|------------|
| Orchestration | LangGraph 1.x | Pipeline tuần tự + native `interrupt()` cho teacher gates |
| Backend | FastAPI (Python 3.12) | Async, type-safe, OpenAPI auto-docs |
| Frontend | Next.js 15 (TypeScript) | SSR + App Router; teacher dashboard |
| Template Engine | Eta (JS/TS) | 3.5 KB, TypeScript-native, standalone HTML output |
| LLM Gateway L1 | LiteLLM Proxy (port 4000) | Virtual keys, budget control, cost tracking, fallback chains |
| LLM Gateway L2 | 9Router sidecar (port 20128) | RTK token compression (20-40%), free-tier aggregation, fusion routing |
| Cache | Redis 7 | LiteLLM exact-match cache; LangGraph shared state |
| Persistence | PostgreSQL 16 | LangGraph checkpoints; cost logs; artifact metadata |
| Validation | Pydantic v2 (Python) + Zod v4 (TS) | Bi-directional schema enforcement |
| Testing | pytest + Vitest | Python agents + TypeScript template renderer |

### Nguyên Tắc Thiết Kế (bất khả xâm phạm)

- **SoC (Separation of Concerns)**: Mỗi agent có một trách nhiệm. Lead Agent không bao giờ tạo nội dung trực tiếp.
- **Modular**: Mỗi tầng (middleware, gate, template, agent) là đơn vị riêng, test độc lập.
- **Standalone HTML**: Mọi đầu ra đều tự chứa, không CDN, không tài nguyên bên ngoài, hoạt động offline.
- **Config-driven**: Hành vi kiểm soát qua YAML/JSON, không magic trong code.
- **Fail closed**: Mọi gate failure đều chặn export. Không có silent pass.
- **Typed end-to-end**: Python dùng Pydantic v2. TypeScript dùng strict mode + Zod schemas.

---

## 2. Sơ Đồ Kiến Trúc Tổng

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Giáo Viên (Trình Duyệt)                            │
│                   Next.js 15 Dashboard :3000                             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ REST / WebSocket (SSE)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   FastAPI Gateway  :8001                                  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              LangGraph Runtime (Embedded)                         │  │
│  │                                                                    │  │
│  │    ┌─────────────────────────────────────────────────────────┐    │  │
│  │    │       Teaching-Pack Stage Graph (8 stages)               │    │  │
│  │    │                                                          │    │  │
│  │    │  setup_contract → triage → preplanning_search            │    │  │
│  │    │    → planning_blueprint → post_blueprint_research        │    │  │
│  │    │    → artifact_workflow → render_quality                  │    │  │
│  │    │    → teacher_approval → export_finalize → END            │    │  │
│  │    └──────────────────────────────┬──────────────────────────┘    │  │
│  │                                   │                                │  │
│  │    ┌─────────────┬────────────────┼────────────────┬────────┐    │  │
│  │    ▼             ▼                ▼                ▼        ▼    │  │
│  │  Planner    Researcher    Content Creator    Reviewer   Gate     │  │
│  │  Agent      Agent         Agent              Agent      Nodes    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────┐  ┌──────────────────────────────┐   │
│  │  PostgreSQL :5432             │  │  Redis :6379                 │   │
│  │  (Checkpoints, cost logs)     │  │  (LiteLLM cache, state)     │   │
│  └───────────────────────────────┘  └──────────────────────────────┘   │
│                                                                          │
│  LiteLLM Proxy :4000 ──────────────────────────────► 9Router :20128    │
│  (budget, fallback chains, cache)        (RTK, free tiers, fusion)     │
│                                                │                        │
│                                    ┌───────────┼───────────┐           │
│                                    ▼           ▼           ▼           │
│                                 Kiro AI    OpenCode   Vertex AI       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mô Hình Tương Tác Agent

```
Teaching-Pack Stage Graph
  │
  ├─► preplanning_search ──► web_search(topic)
  │
  ├─► planning_blueprint ──► planner_node()
  │     └─► task(Planner, "Design learning plan")     → LessonPlan JSON
  │
  ├─► post_blueprint_research ──► researcher_node()
  │     └─► task(Researcher, "Gather sources")         → ResearchBundle JSON
  │
  ├─► artifact_workflow ──► content_creator_node()
  │     └─► task(ContentCreator, "Generate HTML")     → ArtifactContent JSON
  │
  └─► render_quality ──► reviewer_node()
        └─► task(Reviewer, "QA check")               → JudgeOutput JSON
```

---

## 3. Định Nghĩa Agent

### 3.1 Lead Agent (Supervisor) — ĐÃ NGHỈ HƯỞNG

**Trạng thái**: DECOMMISSIONED (dead code removed theo td-004, commit 4800383)

Lead Agent ban đầu là một LangGraph `create_react_agent` ReAct orchestrator, giờ đã bị xóa. Phần còn lại là các helper đã được parked:

| File | Nội dung | Trạng thái |
|------|----------|------------|
| `config.py` | LeadAgentConfig (model="gpt-5.4", tools, max_turns) | Parked |
| `tools.py` | 4 @tool wrappers (run_planner, run_researcher, run_content_creator, run_reviewer) | Parked |
| `recovery.py` | build_recovery_context() cho retry guidance | Parked |
| `prompts/system.md` | System prompt 38 dòng | Parked |

**INVARIANT-01 enforcement**: Lead Agent KHÔNG BAO GIỜ gọi LLM trực tiếp, chỉ qua `task()`. Nhưng `task()` hiện là stub (`NotImplementedError` tại `tools/task.py:41`).

**Thay thế bởi**: Teaching-Pack Stage Graph (state machine tuần tự thay thế ReAct agent).

### 3.2 Planner Agent (Thiết Kế Kế Hoạch Bài Học)

**Vị trí**: `packages/agents/sub_agents/planner/`
**Điểm vào**: `planner_node()` async function
**Model**: "4omc" (medium tier), temperature 0.7/0.3 retry, max_tokens=8192

#### Ba đường dẫn thực thi

1. **Staged Engine (MẶC ĐỊNH SẢN XUẤT)**: `build_staged_lesson_plan()` — tuần tự, không LLM, sử dụng Gagné plan builder + Bloom level selector
2. **Seed Expansion**: mở rộng unit planner seeds thành LessonPlan đầy đủ
3. **LLM Call**: single chat completion với compiled prompt

#### System Prompt

Triết lý: UbD (Backward Design) + Gagné 9-event instruction model.

#### Đầu Ra

`LessonPlan` (Pydantic v2):
- `topic`: str
- `grade_level`: str (ví dụ "Grade 5")
- `subject`: str
- `duration_minutes`: int (10-180)
- `learning_objectives`: list[LearningObjective] (min 1, max 10, >=2 Bloom levels)
- `prerequisite_knowledge`: list[str]
- `learning_plan`: dict (Gagné 9-event phases)
- `assessment_checkpoints`: list[dict]
- `methodology`: MethodologyMetadata (optional)

#### Vòng Lặp Chất Lượng Nội Bộ

`LessonConsistencyValidator` (6 rules) + `critique_lesson()` → repair loop tối đa 3 lần.

#### 9 Sự Kiện Gagné

| # | Sự kiện | Mô tả |
|---|---------|-------|
| 1 | gain_attention | Thu hút sự chú ý |
| 2 | inform_objectives | Thông báo mục tiêu |
| 3 | recall_prior | Nhắc lại kiến thức trước |
| 4 | present_content | Trình bày nội dung |
| 5 | provide_guidance | Cung cấp hướng dẫn |
| 6 | elicit_performance | Yêu cầu thực hành |
| 7 | provide_feedback | Cung cấp phản hồi |
| 8 | assess_performance | Đánh giá thực hành |
| 9 | enhance_retention | Tăng cường ghi nhớ |

#### Các File Chính

| File | Nội dung | Dòng |
|------|----------|------|
| `nodes.py` | planner_node(), expand_lesson_plan_from_seed(), ensure_seed_alignment() | — |
| `staged_engine.py` | Staged/deterministic planner | — |
| `lesson_consistency_validator.py` | 6 rules + repair() | — |
| `lesson_critic.py` | objective coverage, prerequisite gap, misconception gap | — |
| `state.py` | PlannerNodeState, PlannerState | — |
| `tools.py` | web_search (delegated), read_file (stub) | — |

**Schema**: `common/contracts/lesson_plan.py` — LessonPlan, LearningObjective, AssessmentCheckpoint, MethodologyMetadata

### 3.3 Researcher Agent (Thu Thập Nguồn Tài Liệu)

**Vị trí**: `packages/agents/sub_agents/researcher/`
**Điểm vào**: `researcher_node()` async function
**Model**: "4omc" (medium tier), temperature 0.7/0.3 retry, max_tokens=8192

#### FACT Protocol

```
Find → Assess → Cross-reference → Tag (VERIFIED/MODIFIED/REMOVED/UNCERTAIN)
```

#### Luồng Thực Thi

```
1. Load system prompt
2. Kiểm tra RESEARCH_MEMORY_CACHE (in-memory, không persistent)
3. web_search(topic) qua 9Router
4. build_research_evidence() — fetch từng URL, truncate 4000 chars
5. LLM call qua complete_json_chat()
6. finalize_bundle() — attach excerpts → deterministic triangulation → override verification_status
7. remember_verified_sources() — cache cho các lần chạy sau
8. Retry tối đa 3 lần khi thất bại
```

#### Chính Sách Nghiên Cứu

| Chính sách | Số nguồn tối thiểu | Coverage | Số nguồn tối đa |
|-----------|-------------------|----------|-----------------|
| `basic` | 2 | 0.5 | 3 |
| `standard` | 2 | 0.8 | 5 |
| `rigorous` | 3 | 0.9 | 10 |

#### Deterministic Triangulation

`triangulation.py` — xác minh nguồn bằng independent-domain corroboration. Independence = distinct registrable domain.

#### Đầu Ra

`ResearchBundle`:
- `topic`: str
- `sources`: list[ResearchSource] (title, url, excerpt, credibility_score, verification_status)
- `key_findings`: list[str]
- `cross_references`: list[dict]
- `research_policy`: str

#### Các File Chính

| File | Nội dung | Dòng |
|------|----------|------|
| `nodes.py` | researcher_node() | 236 |
| `triangulation.py` | triangulate() | 134 |
| `grounding.py` | policy_rigor(), ResearchMemoryCache | — |
| `evidence.py` | build_research_evidence() | — |
| `runtime_grounding.py` | finalize_bundle(), attach_excerpts() | — |
| `lexical_evidence.py` | Vocabulary-specific evidence | — |
| `lexical_grounding.py` | Vocabulary-specific grounding | — |
| `tools.py` | web_search (delegated), web_fetch (NineRouter), read_file | — |

**Schema**: `common/contracts/research_bundle.py` — ResearchBundle, ResearchSource

### 3.4 Content Creator Agent (Tạo Nội Dung Bài Học)

**Vị trí**: `packages/agents/sub_agents/content_creator/`
**Điểm vào**: `content_creator_node()` async function
**Model**: "4omc" (medium tier), max_tokens=16384 (NGÂN SÁCH CAO NHẤT), streaming only

#### System Prompt

262 dòng — RCM (Rich Component Model) catalog, vocabulary methodology, present-tenses inverse-thinking.

#### Ràng Buộc Bắt Buộc

| Ràng buộc | Chi tiết |
|-----------|---------|
| JSON only | Không bao giờ raw HTML — `_JSON_ONLY_SUFFIX` được append |
| Không CDN | `validate_no_cdn` kiểm tra |
| Không PII | `validate_no_pii` kiểm tra |
| Answer keys | Chỉ trong sections `teacher_only` |
| Không placeholder | TBD, lorem ipsum bị chặn |
| Nội dung tối thiểu | `ARTIFACT_RICHNESS` dict theo từng artifact type |

#### Quy Trình Tạo Theo Artifact Type

```
1. Xây user prompt qua build_single_artifact_prompt() với COMPONENT_CONTRACT + ARTIFACT_RICHNESS
2. Chọn prompt module: content_creator_mcq_v1 cho quiz, content_creator_lesson_v1 cho các loại khác
3. Gọi compiled_json_chat() — streaming transport (agent DUY NHẤT dùng streaming)
4. Parse JSON → ArtifactContent.model_validate()
5. 3 retry attempts với error-feedback prompt
```

#### Hai Đường Dẫn Rendering

**A. Python snapshots** (`snapshots.py`): nhanh, synchronous, cho preview
**B. TypeScript Eta renderer** (`packages/renderer/`): production đầy đủ, standalone HTML

#### Hierarchical Path

`hierarchical.py`: deterministic outline-based generation, không LLM per section.

#### Đầu Ra

`ArtifactContent`:
- `artifact_type`: Literal["lesson"|"worksheet"|"quiz"|"drill"|"recap"|"infographic"|"answer_key"|"roadmap"|"flashcard_deck"]
- `theme`: str
- `title`: str (min 3, max 200 chars)
- `sections`: list[dict] (min 1)
- `metadata`: dict
- `accessibility`: dict (language, reading_level, alt_texts)

#### Các File Chính

| File | Nội dung | Dòng |
|------|----------|------|
| `nodes.py` | content_creator_node() | 238 |
| `hierarchical.py` | Deterministic artifact builder | 261 |
| `prompt_contract.py` | COMPONENT_CONTRACT, ARTIFACT_RICHNESS | — |
| `summarizers.py` | Condenses lesson_plan + research_bundle | — |
| `semantic_anchor_synthesis.py` | Vocabulary lesson sub-profile | — |
| `tools.py` | read_file, write_file | — |

**Schema**: `common/contracts/artifact.py` — ArtifactContent

### 3.5 Reviewer Agent (Đánh Giá Chất Lượng)

#### Hai Triển Khai

**A. Legacy step_10b** (`gates/llm_judge.py`): heuristic scoring, không LLM, MVP stub
**B. Teaching-pack reviewer**: full LLM-as-Judge với G-Eval

**Model**: "4omc", max_tokens=4096

#### G-Eval Scoring (3 Lớp)

| Lớp | Trọng số | Tiêu chí |
|-----|---------|---------|
| format_compliance | 15% | DOCTYPE, không CDN, brand string, viewport |
| content_quality | 55% | Accuracy, completeness, relevance, reasoning |
| presentation | 30% | Readability, engagement, accessibility |

#### Quy Trình Đánh Giá

```
3 judge calls độc lập với temperatures lệch (0.3, 0.4, 0.5)
  → majority_vote() aggregation
  → Pass nếu score >= 7.0 VÀ không có critical issues
```

#### 4 Biện Pháp Chống Thiên Lệch (Bias Mitigations)

| # | Biện pháp | Mô tả |
|---|----------|-------|
| 1 | Think-before-score | Viết rationale TRƯỚC khi chấm điểm |
| 2 | 3 judge độc lập + majority vote | Giảm thiên kiến cá nhân |
| 3 | Generator ≠ Judge model | Tránh tự đánh giá |
| 4 | Anti-length bias | "Do NOT rate longer answers higher" |

#### 9 Hard Blocks (Auto-fail)

| # | Hard Block | Mô tả |
|---|-----------|-------|
| 1 | missing_doctype | Không có `<!DOCTYPE html>` |
| 2 | external_assets | Bất kỳ link CDN/http nào |
| 3 | answer_key_leakage | Đáp án trong bản sinh viên |
| 4 | pii_leakage | Thông tin cá nhân |
| 5 | native_radio_inputs | `<input type="radio">` hiển thị cho sinh viên |
| 6 | unmanaged_js_runtime | External JS framework |
| 7 | missing_brand_string | "oh-my-class" không có mặt |
| 8 | schema_invalid | Schema validation fail |
| 9 | teacher_gate_not_approved | Gate giáo viên chưa approve |

#### Hai Đường Dẫn Scoring

- **GEvalScorer** (được dùng bởi reviewer_node)
- **LiveReviewerQualityGate**: deterministic lenses (format, content, pedagogy, presentation) với ReviewerCalibration

**AdaptiveJudge**: pipeline đầy đủ với RubricSelector + hard-block enforcement (đã export nhưng chưa wired vào graph nodes).

#### Đầu Ra

`JudgeOutput`:
- `overall_score`: float
- `layer_scores`: list[LayerScore]
- `critical_issues`: list[str]
- `passed`: bool
- `rationale`: str

#### Các File Chính

| File | Vị trí | Vai trò |
|------|--------|--------|
| `nodes.py` | `sub_agents/reviewer/` | reviewer_node() |
| `live_quality_gate.py` | `sub_agents/reviewer/` | LiveReviewerQualityGate |
| `geval.py` | `packages/quality/layer4_judge/` | GEvalScorer |
| `majority_vote.py` | `packages/quality/layer4_judge/` | majority_vote() |
| `judge_interface.py` | `packages/quality/layer4_judge/` | AdaptiveJudge |
| `hard_blocks.py` | `packages/quality/layer4_judge/` | enforce_hard_blocks() |
| `rubric_selector.py` | `packages/quality/layer4_judge/` | RubricSelector |

**Schema**: `common/contracts/judge_output.py` — JudgeOutput, LayerScore

---

## 4. Kiến Trúc Đồ Thị

### 4.1 Legacy Graph (ĐÃ XÓA)

Đồ thị legacy 18-node (`packages/agents/graph.py`) đã bị **XÓA VẬT LÝ**.

- Guard test: `test_no_legacy_runtime.py` assert module không tồn tại
- Legacy routes trả HTTP 410 Decommissioned

### 4.2 Teaching-Pack Stage Graph (AUTHORITATIVE)

**Vị trí**: `packages/agents/teaching_pack/`
**Điểm vào**: `build_teaching_pack_graph()` → `CompiledStateGraph`

#### 9 Stage (Linear Wiring)

```
setup_contract ──► triage ──► preplanning_search ──► planning_blueprint
    ──► post_blueprint_research ──► artifact_workflow ──► render_quality
    ──► teacher_approval ──► export_finalize ──► END
```

#### Sơ Đồ Chuyển Trạng Thái Chi Tiết

```
                              ┌─────────────────────┐
                              │    setup_contract    │
                              │  (Khởi tạo contract) │
                              └──────────┬──────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │       triage          │
                              │  (Phân loại mode)    │
                              └──────────┬──────────┘
                                         │
                          ┌──────────────┴──────────────┐
                          │                              │
                   mode=plan_unit                  mode=generate_pack
                          │                              │
                          ▼                              ▼
                 ┌──────────────────┐        ┌───────────────────────┐
                 │  unit_planning   │        │  preplanning_search   │
                 │  (Side-branch)   │        │  (Tìm kiếm sơ bộ)    │
                 └────────┬─────────┘        └───────────┬───────────┘
                          │                              │
                          ▼                              ▼
                 ┌──────────────────┐        ┌───────────────────────┐
                 │  unit_approval   │        │  planning_blueprint   │
                 │  Gate: interrupt │        │  (Kế hoạch bài học)   │
                 └────────┬─────────┘        └───────────┬───────────┘
                          │                              │
                   approve│                    reject    │
                          │                    ↻ loop    │
                          │                              ▼
                          │                ┌───────────────────────────┐
                          │                │ post_blueprint_research    │
                          │                │ (Nghiên cứu sau blueprint)│
                          │                └───────────┬───────────────┘
                          │                            │
                          └──────────┬─────────────────┘
                                     │
                                     ▼
                        ┌───────────────────────────┐
                        │     artifact_workflow       │
                        │  (Tạo nội dung artifact)   │
                        │                             │
                        │  Fan-out 3 waves:           │
                        │  Wave 1: ("lesson")         │
                        │  Wave 2: ("worksheet",      │
                        │           "quiz", "drill")  │
                        │  Wave 3: ("recap")          │
                        └──────────────┬──────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────┐
                        │      render_quality         │
                        │  (Đánh giá chất lượng)     │
                        └──────────────┬──────────────┘
                                       │
                         ┌─────────────┼─────────────┐
                         │             │              │
                    PASS │        FAIL │         FAIL │
                         │  (recovery) │  (recovery)  │
                         │             │              │
                         ▼             ▼              ▼
              ┌──────────────┐  ┌──────────┐  ┌──────────────┐
              │   teacher    │  │ 回到     │  │ 回到         │
              │   _approval  │  │ blueprint│  │ artifacts    │
              └──────┬───────┘  └──────────┘  └──────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
    approve│              reject│
          │              (scoped)│
          ▼                     ▼
  ┌──────────────┐    ┌──────────────────┐
  │export_finalize│    │artifact_workflow  │
  │ (Xuất file)  │    │ (Tạo lại với     │
  └──────┬───────┘    │  feedback)       │
         │            └──────────────────┘
         ▼
       ┌─────┐
       │ END │
       └─────┘
```

#### 4 Conditional Seams

| # | Vị trí | Điều kiện | Kết quả |
|---|--------|-----------|---------|
| 1 | Sau triage | `mode=plan_unit` → unit_planning side-branch, `mode=generate_pack` → preplanning_search | Phân nhánh theo chế độ |
| 2 | Sau artifact_workflow | Send-based fan-out (3 waves) → render_quality | Parallel artifact generation |
| 3 | Sau render_quality | Recovery routes đến blueprint/research/artifacts/approval | Tự phục hồi khi fail |
| 4 | Sau teacher_approval | approve → export_finalize, scoped_reject → artifact_workflow | Phân nhánh theo quyết định |

#### 2 interrupt() Gates

| Gate | Mục đích | Hành động |
|------|---------|----------|
| `unit_approval` | Duyệt lesson sequence | approve/reject/edit |
| `teacher_approval` | Duyệt nội dung artifact | approve với fast-lane (trust-score auto-approve), reject, edit |

#### Artifact Fan-Out (Send API)

```
Wave 1: ("lesson")
         │
         ├──► worksheet  (phụ thuộc lesson)
         │
Wave 2: ├──► quiz       (phụ thuộc lesson)
         │
         └──► drill      (phụ thuộc lesson)
         
Wave 3: └──► recap      (phụ thuộc lesson + quiz)
```

- **Parallelism cap**: mặc định 2
- **generate_one_artifact node**: gọi content_creator_node cho single artifact type

---

## 5. State Schema

### TeachingPackState (AUTHORITATIVE)

```python
class TeachingPackState(TypedDict):
    # ── Input ──────────────────────────────
    contract: dict                        # RunContract
    teacher_id: str
    run_id: str
    theme: str                            # "default" | "ocean" | "forest"

    # ── Planning ───────────────────────────
    lesson_plan: NotRequired[dict]
    blueprint_approved: bool
    revision_feedback: NotRequired[str]

    # ── Research ───────────────────────────
    research_bundle: NotRequired[dict]
    research_policy: str                  # "basic" | "standard" | "rigorous"

    # ── Content ────────────────────────────
    artifact_types: list[str]
    artifact_chunks: Annotated[list[dict], stable_merge_artifacts]      # accumulate by artifact_id
    artifact_workflow_states: Annotated[list[dict], stable_merge_workflow_states]  # accumulate by workflow_id

    # ── Quality ────────────────────────────
    quality_scores: NotRequired[dict]
    quality_passed: bool
    teacher_approved: bool
    revision_count: int
    quality_recovery_route: NotRequired[str]

    # ── Gate Tracking ──────────────────────
    fail_layer: NotRequired[str | None]     # "schema" | "content" | "judge" | "human"
    fail_count: NotRequired[int]
    fail_type: NotRequired[str | None]      # "validation" | "content" | "score" | "timeout"
    fail_context: NotRequired[dict[str, Any] | None]

    # ── Healing ────────────────────────────
    escalate: NotRequired[bool]
    escalate_reason: NotRequired[str | None]
    healing_strategy: NotRequired[str | None]

    # ── Export ─────────────────────────────
    exported_files: Annotated[list[dict[str, Any]], stable_merge_files]

    # ── Metadata ───────────────────────────
    current_step: int                      # 1-13
    tokens_used: int
    cost_usd: float
```

### Custom Reducers (3)

| Reducer | Hành vi | Dùng cho |
|---------|---------|----------|
| `stable_merge_artifacts` | Tích lũy theo artifact_id, giữ thứ tự | artifact_chunks |
| `stable_merge_workflow_states` | Tích lũy theo workflow_id | artifact_workflow_states |
| `stable_merge_files` | Deduplicated union | exported_files |

### OhMyClassState (LEGACY)

`OhMyClassState` vẫn tồn tại để tương thích với healing/middleware. Không phải state chính.

---

## 6. Hệ Thống Middleware (31 Lớp)

**Vị trí**: `packages/agents/middleware/`

### BaseMiddleware ABC

```python
class BaseMiddleware:
    name: str
    order: int           # 1-31; Clarification PHẢI LUÔN là 31

    async def before_model(self, state, context) -> state: ...
    async def after_model(self, state, context) -> state: ...
```

**Invariant**: Clarification (order=31) LUÔN là lớp cuối cùng.

### Safety Tier (orders 1-12)

| # | Middleware | Mô tả |
|---|-----------|-------|
| 1 | input_sanitization | Validate raw_request, grade 1-12, subject |
| 2 | token_budget | Per-run token ceiling (100K mặc định) |
| 3 | thread_data | Populate run_dir + thread_id |
| 4 | uploads | Validate file attachment paths |
| 5 | content_safety | Block K-12 inappropriate content (regex) |
| 6 | dangling_tool_call | Detect/recover interrupted tool calls |
| 7 | llm_error_handling | Mark llm_error_handled |
| 8 | guardrail | PII detection (email/phone/score) + harmful content |
| 9 | teacher_audit_log | Log teacher decisions |
| 10 | tool_error_handling | Mark tool_error_handled |
| 11 | loop_detection | Hash-based + frequency-based infinite loop detection |
| 12 | safety_finish_reason | Suppress length/content_filter finish reasons |

### Context Tier (orders 13-22)

| # | Middleware | Mô tả |
|---|-----------|-------|
| 13 | dynamic_context | Inject date + class summary |
| 14 | skill_activation | Inject CCSS curriculum skill files |
| 15 | summarization | Context compression tại 80K tokens |
| 16 | todo_list | Track lesson plan objective count |
| 17 | token_usage | Record step_start_tokens |
| 18 | title | Derive run_title |
| 19 | memory | Persist teacher_id |
| 20 | view_image | Track uploaded image count |
| 21 | deferred_tool_filter | Set tools_filtered flag |
| 22 | system_message_coalescing | Set system_messages_coalesced flag |

### Quality Tier (orders 23-29)

| # | Middleware | Mô tả |
|---|-----------|-------|
| 23 | subagent_limit | Block LLM khi active_subagents >= 5 |
| 24 | curriculum_alignment | Warn on curriculum mismatch |
| 25 | readability_level | Basic readability check |
| 26 | pedagogical_quality | Count Bloom's taxonomy levels |
| 27 | bias_detection | Scan gendered bias patterns |
| 28 | artifact_coherence | Record artifact count + diversity |
| 29 | learning_objective_alignment | Alignment check |

### Terminal Tier (orders 30-31)

| # | Middleware | Mô tả |
|---|-----------|-------|
| 30 | sequence_consistency_validator | DAG cycle, Bloom, cognitive load, duration (networkx) |
| 31 | clarification | INVARIANT-08 — LUÔN CUỐI CÙNG |

### Middleware Registry Groupings cho Teaching-Pack

| Grouping | Middleware | Số lớp |
|----------|-----------|--------|
| RUN_ENTRY | InputSanitization, Uploads, ThreadData, Title, Memory, TokenBudget | 6 |
| GENERATION_CONTEXT | DynamicContext + SkillActivation (per-agent) | 2 |
| GATE_LAYER | TeacherAuditLog + Clarification | 2 |
| QUALITY_GATE_CONSOLIDATED | CurriculumAlignment → LearningObjectiveAlignment | 6 |
| PARKED_REACT | Không active trong deterministic teaching-pack graph | 8 |

---

## 7. Quality Gates (6 Lớp)

**Vị trí**: `packages/agents/gates/`

### Lớp 1 — Schema Validation

**File**: `gates/schema_validator.py`
**Nhiệm vụ**: required keys, valid types, non-empty

### Lớp 2-3 — Content + HTML

**File**: `gates/content_reviewer.py`
**Nhiệm vụ**: FACT fact-check, HTML validation, age-appropriateness, answer key leakage

### Lớp 4 — LLM Judge

**Legacy**: `gates/llm_judge.py` — heuristic scoring, MVP stub
**Teaching-pack**: `GEvalScorer` — G-Eval 3-layer scoring

### Lớp 5a — Blueprint Gate

**File**: `gates/gate_01_blueprint.py`
**Cơ chế**: HITL interrupt cho lesson plan

### Lớp 5b — Content Gate

**File**: `gates/gate_02_content_approval.py`
**Cơ chế**: HITL interrupt cho artifacts

### Lớp 6 — Export Readiness

**File**: `gates/export_readiness.py`
**Nhiệm vụ**: format support, artifact coverage, judge score

### Bảng Tổng Hợp

| Lớp | File | Cơ chế | Kích hoạt |
|-----|------|--------|----------|
| 1 - Schema | `schema_validator.py` | Pydantic validation | Mỗi artifact |
| 2-3 - Content/HTML | `content_reviewer.py` | Regex + HTML parse | Mỗi artifact |
| 4 - LLM Judge | `llm_judge.py` / `geval.py` | Heuristic / G-Eval | Sau content gen |
| 5a - Blueprint | `gate_01_blueprint.py` | `interrupt()` | Sau planning |
| 5b - Content | `gate_02_content_approval.py` | `interrupt()` | Sau rendering |
| 6 - Export | `export_readiness.py` | Checklist | Trước export |

---

## 8. Hệ Thống Self-Healing

**Vị trí**: `packages/agents/healing/`

### HealingOrchestrator.heal()

Chọn healing strategy dựa trên `fail_count`:

| fail_count | fail_type | Strategy | Hiệu ứng |
|-----------|-----------|----------|----------|
| 1 | transient | **retry** | exponential backoff + jitter |
| 1 | validation/score/content | **rewrite** | inject error context, cùng model |
| 2 | any | **reroute** | đổi model (f.light ↔ 4omc) |
| 3 | any | **replan** | clear toàn bộ downstream state |
| >3 | any | **escalate** | mark escalate=True → teacher gate |

### CircuitBreaker

3 trạng thái: **closed** → **open** → **half-open**.
Threshold-based: chuyển trạng thái khi vượt ngưỡng lỗi.

### HTML Healer

- DOCTYPE injection (thêm `<!DOCTYPE html>` nếu thiếu)
- External asset URL removal (loại bỏ CDN links)

### Sơ Đ� Healing Flow

```
Node fail
  │
  ▼
HealingOrchestrator.heal()
  │
  ├── fail_count=1, transient ──► retry (backoff + jitter)
  │
  ├── fail_count=1, content ──► rewrite (inject feedback, cùng model)
  │
  ├── fail_count=2 ──► reroute (đổi model: f.light ↔ 4omc)
  │
  ├── fail_count=3 ──► replan (clear downstream state)
  │
  └── fail_count>3 ──► escalate (→ teacher gate, timeout 24h)
```

---

## 9. Agent Tools

| Tool | Trạng thái | Sử dụng bởi |
|------|-----------|-------------|
| `task(agent_name, prompt, ...)` | STUB (NotImplementedError) | Lead Agent (decommissioned) |
| `read_file(path)` | Mixed (researcher+content_creator=implemented, planner+reviewer=stub) | Tất cả agents |
| `write_file(path, content)` | Implemented | Content Creator |
| `web_search(query)` | Implemented (NineRouterWebClient) | Planner, Researcher |
| `web_fetch(url)` | Implemented (NineRouterWebClient) | Researcher |

### Chi Tiết Từng Tool

#### task() — STUB

```python
# tools/task.py:41
def task(agent_name, prompt, ...):
    raise NotImplementedError("task() is a stub — use direct node calls")
```

#### read_file()

- **Researcher**: implemented (đọc file từ filesystem)
- **Content Creator**: implemented (đọc file template, prompts)
- **Planner**: stub
- **Reviewer**: stub

#### write_file()

Implement đầy đủ, sử dụng bởi Content Creator để ghi artifact output.

#### web_search()

Triển khai qua `NineRouterWebClient`. Sử dụng bởi Planner và Researcher.

#### web_fetch()

Triển khai qua `NineRouterWebClient`. Fetch URL content, truncate 4000 chars. Sử dụng bởi Researcher.

---

## 10. Framework LangGraph — Các Pattern Sử Dụng

### 10.1 StateGraph + Compile

Teaching-Pack graph sử dụng `StateGraph(TeachingPackState)` với `.compile()` tạo `CompiledStateGraph`.

```python
# packages/agents/teaching_pack/graph.py
def build_teaching_pack_graph() -> CompiledStateGraph:
    graph = StateGraph(TeachingPackState)
    # Thêm nodes
    graph.add_node("setup_contract", setup_contract_node)
    graph.add_node("triage", triage_node)
    # ... các nodes khác
    # Thêm edges
    graph.add_edge("setup_contract", "triage")
    graph.add_conditional_edges("triage", route_after_triage)
    # ... các edges khác
    return graph.compile()
```

### 10.2 Custom State Reducers

```python
from typing import Annotated

# 3 reducers tùy chỉnh
artifact_chunks: Annotated[list[dict], stable_merge_artifacts]
artifact_workflow_states: Annotated[list[dict], stable_merge_workflow_states]
exported_files: Annotated[list[dict[str, Any]], stable_merge_files]
```

Mỗi reducer đảm bảo state accumulation đúng cách, không mất dữ liệu từ các parallel branches.

### 10.3 interrupt() cho HITL

```python
# Teacher Gate
response = interrupt({
    "gate": "teacher_approval",
    "artifacts": state["artifact_chunks"],
    "quality_scores": state["quality_scores"],
    "actions": ["approve", "edit", "reject"]
})
```

Hai gates sử dụng `interrupt()`:
- `unit_approval`: lesson sequence approval
- `teacher_approval`: content approval với fast-lane

Timeout: 24 giờ → auto-escalate.

### 10.4 Send API cho Dynamic Parallelism

```python
# Artifact fan-out
from langgraph.types import Send

# Sau artifact_workflow
wave_1 = [Send("generate_one_artifact", {"artifact_type": "lesson"})]
wave_2 = [Send("generate_one_artifact", {"artifact_type": t}) 
          for t in ["worksheet", "quiz", "drill"]]
wave_3 = [Send("generate_one_artifact", {"artifact_type": "recap"})]

# Tất cả waves converge về render_quality
```

### 10.5 Conditional Routing

4 conditional seams điều khiển luồng:

```python
# Seam 1: Sau triage
def route_after_triage(state) -> str:
    mode = state.get("contract", {}).get("mode", "generate_pack")
    return "unit_planning" if mode == "plan_unit" else "preplanning_search"

# Seam 3: Sau render_quality
def route_after_quality(state) -> str:
    if state.get("quality_passed"):
        return "teacher_approval"
    return state.get("quality_recovery_route", "artifact_workflow")
```

### 10.6 Checkpointing

| Môi trường | Checkpointer | Ghi chú |
|-----------|-------------|---------|
| `development` | `MemorySaver` | Mất khi restart |
| `staging` | `SqliteSaver` | File: `omc_checkpoints.db` |
| `production` | `PostgresSaver` | Multi-instance safe |

`run_id` được dùng làm `thread_id` cho checkpointing.

### 10.7 Streaming

Content Creator là **agent DUY NHẤT** sử dụng streaming transport.

```python
# Content Creator — streaming only
async for chunk in compiled_json_chat(
    model="4omc",
    messages=messages,
    stream=True  # ONLY streaming agent
):
    process_chunk(chunk)
```

Các agent khác sử dụng non-streaming (sync completion).

---

## 11. Bảng Tra Cứu File Chính

### Teaching-Pack Core

| Thành phần | File path |
|-----------|-----------|
| Teaching-Pack Graph | `packages/agents/teaching_pack/graph.py` |
| Stage Enum | `packages/agents/teaching_pack/stages.py` |
| All Stage Nodes | `packages/agents/teaching_pack/nodes.py` |
| Artifact Fan-Out | `packages/agents/teaching_pack/artifact_fanout.py` |
| Quality Runtime | `packages/agents/teaching_pack/quality_runtime.py` |
| State Schema (authoritative) | `packages/agents/teaching_pack/nodes.py` (TeachingPackState) |

### Sub-Agents

| Agent | File path |
|-------|-----------|
| Planner Agent | `packages/agents/sub_agents/planner/nodes.py` |
| Researcher Agent | `packages/agents/sub_agents/researcher/nodes.py` |
| Content Creator Agent | `packages/agents/sub_agents/content_creator/nodes.py` |
| Reviewer Agent | `packages/agents/sub_agents/reviewer/nodes.py` |

### Infrastructure

| Thành phần | File path |
|-----------|-----------|
| Healing Orchestrator | `packages/agents/healing/orchestrator.py` |
| Middleware Registry | `packages/agents/middleware/registry.py` |
| Legacy State | `packages/agents/state.py` (OhMyClassState) |
| Model Config | `packages/agents/config/models.py` |
| Gate Config | `packages/agents/config/gate_config.py` |
| Event Bus | `packages/agents/events.py` |
| Observability | `packages/agents/observability/` |

### Schemas (common/contracts)

| Schema | File path |
|--------|-----------|
| LessonPlan | `common/contracts/lesson_plan.py` |
| ResearchBundle | `common/contracts/research_bundle.py` |
| ArtifactContent | `common/contracts/artifact.py` |
| JudgeOutput | `common/contracts/judge_output.py` |
| RunContract | `common/contracts/run_contract.py` |
| Auth | `common/contracts/auth.py` |

### Gateway

| Thành phần | File path |
|-----------|-----------|
| Gateway Entry | `services/gateway/main.py` |
| Teaching Pack Router | `services/gateway/routers/teaching_packs.py` |
| Recovery Sweeper | `services/gateway/recovery_sweeper.py` |

### Đồ Thị Legacy (ĐÃ XÓA)

| Thành phần | File path | Trạng thái |
|-----------|-----------|-----------|
| Legacy Graph | `packages/agents/graph.py` | ĐÃ XÓA VẬT LÝ |
| Guard Test | `tests/.../test_no_legacy_runtime.py` | Active (ngăn hồi sinh) |

---

## 12. Ghi Chú Kỹ Thuật

### 1. Legacy Graph Đã Bị Xóa

Đồ thị legacy 18-node đã bị xóa vật lý. Guard test `test_no_legacy_runtime.py` assert module không tồn tại, ngăn việc vô tình hồi sinh code đã deprecated.

### 2. Lead Agent Đã Nghỉ Hưởng

Lead Agent (Supervisor) đã bị decommissioned theo ticket td-004 (commit 4800383). `task()` hiện là stub với `NotImplementedError`. Các helper tools (run_planner, run_researcher, run_content_creator, run_reviewer) vẫn còn trong codebase nhưng không được sử dụng.

### 3. Documentation Drift — AGENTS.md

AGENTS.md mô tả Lead Agent là active. Đây là documentation drift cần được cập nhật. Lead Agent đã bị thay thế bởi Teaching-Pack Stage Graph (deterministic state machine).

### 4. Hai State Schema Đồng Tồn

- **TeachingPackState**: state chính, authoritative cho teaching-pack pipeline
- **OhMyClassState**: legacy compat, vẫn được sử dụng bởi healing/middleware layers

Hai state này có nhiều field trùng lặp nhưng cấu trúc khác nhau.

### 5. Per-Agent Tool Access Bất Đối Xứng

| Agent | read_file | write_file | web_search | web_fetch | task |
|-------|-----------|------------|------------|-----------|------|
| Planner | stub | — | implemented | — | — |
| Researcher | implemented | — | implemented | implemented | — |
| Content Creator | implemented | implemented | — | — | — |
| Reviewer | stub | — | — | — | — |
| Lead Agent | — | — | — | — | stub |

### 6. Middleware Layers Đang PARKED

8 middleware layers thuộc `PARKED_REACT` grouping không active trong deterministic teaching-pack graph. Chúng thuộc về ReAct architecture đã decommissioned.

### 7. AdaptiveJudge Chưa Wired

`AdaptiveJudge` (tại `packages/quality/layer4_judge/judge_interface.py`) đã được export nhưng chưa wired vào graph nodes. Nó cung cấp RubricSelector + hard-block enforcement đầy đủ nhưng hiện chưa được sử dụng trong luồng chính.

### 8. Quality Gate 6-Lớp Partially Wired

Hệ thống 6-layer quality gate được thiết kế đầy đủ nhưng wiring vào graph nodes mới ở mức cơ bản. ADR-018 đề cập đến "capability cliffs" giữa các lớp.

### 9. pedagogical_scorer.py

File `pedagogical_scorer.py` tồn tại như một kênh scoring 5-dimension riêng biệt, tách rời khỏi GEvalScorer chính. Kênh này đo lường các khía cạnh pedagogical chi tiết hơn.

### 10. Streaming Asymmetry

Content Creator là agent duy nhất sử dụng streaming transport. Tất cả các agent khác (Planner, Researcher, Reviewer) sử dụng non-streaming completion. Đây là quyết định thiết kế có chủ đích vì Content Creator tạo output dài nhất (max_tokens=16384).

### 11. Model Routing Summary

| Agent | Model | Tier | max_tokens |
|-------|-------|------|------------|
| Lead Agent | gpt-5.4 | High | — |
| Planner | 4omc | Medium | 8192 |
| Researcher | 4omc | Medium | 8192 |
| Content Creator | 4omc | Medium | 16384 |
| Reviewer | 4omc | Medium | 4096 |

### 12. Invariant Reference

| Invariant | Mô tả | Trạng thái |
|-----------|-------|-----------|
| INVARIANT-01 | Lead Agent NEVER calls LLM directly | ✅ Enforced (task() is stub) |
| INVARIANT-02 | packages/agents NEVER imports from services/* or apps/* | ✅ CI enforced |
| INVARIANT-03 | Every node is pure function (state) → partial_state | ✅ |
| INVARIANT-04 | HTML output MUST NOT contain http(s):// asset | ✅ Layer 3 enforcement |
| INVARIANT-05 | Answer keys in teacher_only sections | ✅ Layer 2 enforcement |
| INVARIANT-06 | Teacher Gate cannot be silently bypassed: trust-score auto-approval is audited, visibly labelled, revertible, and allowed only after `compliance_gate_node` passes (ADR-026) | ⚠️ ADR decided; dedicated invariant test + compliance gate wiring tracked in Phase 3/5 |
| INVARIANT-07 | All LLM calls include metadata.tags | ✅ Per-agent cost attribution |
| INVARIANT-08 | Clarification middleware is always last (order=31) | ✅ Registry enforced |
| INVARIANT-09 | theme.json is single source of truth | ✅ Renderer enforced |
| INVARIANT-10 | Pydantic models in common/contracts | ✅ |

---

> **Bản quyền**: Báo cáo này thuộc dự án oh-my-class. Sử dụng nội bộ.
> **Cập nhật lần cuối**: 2026-07-02
> **Tác giả**: AI Architecture Analysis
