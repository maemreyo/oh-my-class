# Topic Decomposition in K-12 Teaching — Research Findings

> Compiled for "oh-my-class" architecture & schema design.
> Date: 2026-06-30
> Trigger: Investigation into whether oh-my-class has a mechanism to split teaching topics into individual sub-lessons/sessions, and what standardized frameworks exist for doing so.

---

## TABLE OF CONTENTS

- [Topic Decomposition in K-12 Teaching — Research Findings](#topic-decomposition-in-k-12-teaching--research-findings)
  - [TABLE OF CONTENTS](#table-of-contents)
  - [1. Codebase Audit — Current State](#1-codebase-audit--current-state)
    - [1.1 LessonPlan Schema — Single-Session Hardwired](#11-lessonplan-schema--single-session-hardwired)
    - [1.2 RunContract — One Run = One Topic = One Pack](#12-runcontract--one-run--one-topic--one-pack)
    - [1.3 RoadmapAgent — Exists, But Different Purpose](#13-roadmapagent--exists-but-different-purpose)
    - [1.4 The 12-Step Pipeline — Linear, Not Fan-Out](#14-the-12-step-pipeline--linear-not-fan-out)
    - [1.5 Search Results — Zero Hits for Decomposition Vocabulary](#15-search-results--zero-hits-for-decomposition-vocabulary)
    - [1.6 Verdict Table](#16-verdict-table)
  - [2. Pedagogical Frameworks for Decomposition](#2-pedagogical-frameworks-for-decomposition)
    - [2.1 Backward Design (UbD) — The Macro Layer](#21-backward-design-ubd--the-macro-layer)
    - [2.2 Gagné's Nine Events — The Meso Layer](#22-gagnés-nine-events--the-meso-layer)
    - [2.3 Cognitive Load Theory — The Micro Layer](#23-cognitive-load-theory--the-micro-layer)
    - [2.4 Bloom's Taxonomy — Sequencing Constraint](#24-blooms-taxonomy--sequencing-constraint)
    - [2.5 Knowledge Component Analysis](#25-knowledge-component-analysis)
  - [3. Vietnamese Curriculum Standards](#3-vietnamese-curriculum-standards)
    - [3.1 Chương trình GDPT 2018 — Structure](#31-chương-trình-gdpt-2018--structure)
    - [3.2 Standard Time Allocations](#32-standard-time-allocations)
    - [3.3 Topic-to-Lesson Mapping](#33-topic-to-lesson-mapping)
    - [3.4 QĐ 764/QĐ-BGDDT — Assessment Constraints](#34-qđ-764qđ-bgddt--assessment-constraints)
  - [4. AI/LLM Research on Topic Decomposition (2023–2026)](#4-aillm-research-on-topic-decomposition-20232026)
    - [4.1 Key Papers \& Systems](#41-key-papers--systems)
    - [4.2 Proven Prompting Strategy: Curricular CoT](#42-proven-prompting-strategy-curricular-cot)
    - [4.3 Knowledge Graph + LLM Approaches](#43-knowledge-graph--llm-approaches)
    - [4.4 Production Platform Patterns](#44-production-platform-patterns)
    - [4.5 Open-Source Tools](#45-open-source-tools)
  - [5. Age-Band Guidelines](#5-age-band-guidelines)
    - [5.1 Attention Span \& Duration by Age](#51-attention-span--duration-by-age)
    - [5.2 Vietnamese Session Standards](#52-vietnamese-session-standards)
  - [6. Actionable Suggestions for oh-my-class](#6-actionable-suggestions-for-oh-my-class)
    - [6.1 Schema Extension — LessonSequence](#61-schema-extension--lessonsequence)
    - [6.2 Pipeline Integration Points](#62-pipeline-integration-points)
    - [6.3 Planner Agent Decomposition Prompt](#63-planner-agent-decomposition-prompt)
    - [6.4 Middleware — Prerequisite Validator](#64-middleware--prerequisite-validator)
    - [6.5 Splitting Triggers](#65-splitting-triggers)
    - [6.6 Framework Composition Map](#66-framework-composition-map)
  - [7. References](#7-references)
    - [Academic Papers](#academic-papers)
    - [Pedagogical Frameworks](#pedagogical-frameworks)
    - [Vietnamese Standards](#vietnamese-standards)
    - [Production Platforms](#production-platforms)

---

## 1. Codebase Audit — Current State

### 1.1 LessonPlan Schema — Single-Session Hardwired

**File:** `common/contracts/lesson_plan.py`

```python
class LessonPlan(BaseModel):
    topic: str                          # singular, max 200 chars
    grade_level: str                    # e.g. "Grade 5", "Lớp 5"
    subject: str                        # e.g. "math", "english", "science"
    duration_minutes: int               # 10–180  ← one class period
    learning_objectives: list[LearningObjective]   # 1–10 objectives
    prerequisite_knowledge: list[str]   # flat list — no ordering, no DAG
    learning_plan: dict[str, Any]       # Gagné 9-event phases (ONE cycle)
    assessment_checkpoints: list[AssessmentCheckpoint]
    methodology: MethodologyMetadata | None = None
```

**Key signals this is one session, not a sequence:**

| Field | Signal | Why It Matters |
|-------|--------|---------------|
| `topic: str` | Singular | Not a list of sub-topics or session titles |
| `duration_minutes: int` | Hard cap at 180 min (3 hours) | One class period, not a multi-week unit |
| `prerequisite_knowledge: list[str]` | Flat strings | No dependency chain, no ordering, no DAG |
| `learning_plan: dict` | Gagné 9 events = ONE instructional cycle | Events don't span multiple sessions |
| `assessment_checkpoints` | No `session_index` or `lesson_id` | Per-session, not cross-session |
| Missing fields | No `sessions`, `sub_topics`, `modules`, `lesson_sequence` | Absence is the evidence |

### 1.2 RunContract — One Run = One Topic = One Pack

**File:** `common/contracts/run_contract.py`

```python
class RunContract(BaseModel):
    topic: str                          # singular
    grade_band: str
    subject: str
    locale: str
    artifact_types: list[ArtifactType]  # ["lesson", "worksheet", "quiz", ...]
    export_formats: list[ExportFormat]
    research_policy: ResearchPolicy
    # ... no session_id, no sequence_position, no unit_id
```

The contract defines a single run producing one pack of artifacts for one topic. There is no concept of "session 3 of 5" or "part 2 of the Fractions unit."

**Artifact types (from `run_contract.py`):**

```python
ArtifactType = Literal["lesson", "worksheet", "quiz", "drill", "recap", "infographic"]
```

These are **views/materials derived from one lesson**, not a sequence of lessons.

### 1.3 RoadmapAgent — Exists, But Different Purpose

**Files:** `packages/agents/sub_agents/roadmap_agent/`

The `RoadmapAgent` generates a **personalized learning roadmap** from `DiagnosticReport` + `StudentProfile`. It is:

| Aspect | What It Does | What It Does NOT Do |
|--------|-------------|---------------------|
| **Input** | DiagnosticReport + StudentProfile | Topic decomposition request |
| **Focus** | Exam-prep milestones (HSA, IELTS, TOEIC) | Sub-lesson sequencing |
| **Output** | Monthly milestones, book recommendations, CEFR-based progression | Session-by-session lesson plans |
| **Granularity** | Month-scale targets | Lesson-scale sequencing |
| **Tools** | `book_recommender()`, `milestone_calculator()` | Prerequisite graph builder |

The `RoadmapContent` schema has `sections: list[RoadmapSection]` where each section contains `ContentComponent` items — but these are visual sections of a roadmap page, not lesson sequences.

**`RoadmapAgentState`:**

```python
class RoadmapAgentState(MessagesState):
    diagnostic_report: dict[str, Any]
    student_profile: dict[str, Any] | None
    run_id: str
    current_step: int
    roadmap_artifact: dict[str, Any] | None
```

No `topic`, no `session_count`, no `prerequisite_graph`. This agent is for long-horizon exam prep, not topic decomposition.

### 1.4 The 12-Step Pipeline — Linear, Not Fan-Out

```
Step 03 → One LessonPlan
Step 04 → Teacher Gate 1 (approve/edit/reject ONE plan)
Step 05 → Pack Scope (artifact types for 1 run)
Step 08 → One set of ArtifactContent[] for ONE plan
Step 11 → Teacher Gate 2 (approve/edit/reject ONE pack)
```

No fan-out node, no "for each session" loop, no session index cursor. The conditional routing after review (Step 10) loops back to `generate` (Step 08), not to a new sub-lesson.

**Routing logic (from `packages/agents/graph.py`):**

```python
def route_after_content_review(state) -> str:
    if state["quality_scores"]["overall"] >= 7.0:
        return "human_review"
    if state.get("revision_count", 0) >= 3:
        return "escalate"
    return "repair"

def route_after_human_review(state) -> str:
    return "validate" if state["teacher_approved"] else "generate"
```

Both routes operate on a single lesson. No session iteration.

### 1.5 Search Results — Zero Hits for Decomposition Vocabulary

| Term | Hits in Codebase |
|------|-----------------|
| `split` / `divide` / `decompose` (lesson context) | 0 |
| `session` (lesson context) | 0 |
| `sub_topic` / `subtopic` | 0 |
| `module` / `unit` / `chapter` (curriculum context) | 0 |
| `LessonSequence` / `MultiSession` / `UnitPlan` | 0 |
| `curriculum` | 1 — `RunContract.curriculum: str | None` (a label, not a planner) |
| `LearningPath` / `PrerequisiteGraph` / `DependencyDAG` | 0 |

The only mention of `session` anywhere in the codebase is in LangGraph infrastructure language (e.g., "checkpoint per session"), not in the lesson domain.

### 1.6 Verdict Table

| Question | Answer | Evidence |
|----------|--------|----------|
| Can the system split a topic into sub-lessons? | **No** | `LessonPlan.topic: str` (singular), no `sessions` field |
| Is there a curriculum/unit-level planner? | **No** | No `UnitPlan` / `CurriculumPlan` in `common/contracts/` |
| Is there a lesson sequencing mechanism? | **No** | Pipeline is linear; no fan-out over sessions |
| Is there a prerequisite dependency graph? | **No** | `prerequisite_knowledge: list[str]` is flat |
| Does the RoadmapAgent handle topic decomposition? | **No** | It handles exam-prep milestones |
| Could the architecture support splitting? | **Yes** | Clean contracts, extensible pipeline, teacher gates |

---

## 2. Pedagogical Frameworks for Decomposition

### 2.1 Backward Design (UbD) — The Macro Layer

**Source:** Wiggins & McTighe, *Understanding by Design* (2005)

UbD provides the **highest-level decomposition structure**. The inversion principle: never start from content, start from the Transfer Goal and work backwards.

**Decomposition hierarchy:**

```
Transfer Goal (1 per unit)
  → Enduring Understandings (3–5 per unit)
    → Essential Questions (1–3 per EU)
      → Knowledge + Skills (5–12 per EU)
        → Performances of Understanding (2–4 per EU)
          → Lessons (3–5 per UbD unit, McREL standard)
```

**Granularity rules:**

| Layer | Count Rule | Time Allocation |
|-------|-----------|----------------|
| Transfer Goal | 1 per unit | — |
| Enduring Understandings | 3–5 per unit | — |
| Essential Questions | 1–3 per EU | — |
| Knowledge items | 5–12 per EU | — |
| Skills/procedures | 2–6 per EU | — |
| Performances of Understanding | 2–4 per EU | Each = 1 lesson |
| Lessons | 3–5 per unit | 45–90 min each |

**The Six Facets as decomposition lens:**

When a single EU is "too big" for one lesson, apply the Six Facets — each is a defensible standalone lesson:

- **Explain** → justification lesson
- **Interpret** → meaning-making lesson
- **Apply** → transfer lesson
- **Have Perspective** → critique/compare lesson
- **Empathize** → role/stakeholder lesson
- **Self-Knowledge** → metacognitive reflection lesson

**Decision rule:** If a Transfer Goal cannot be written cleanly, the topic is either too broad (split it) or too narrow (merge with another). This gives the AI a validity check on the input topic itself.

**Transfer Goal formula:**

> *"Students will be able to [verb in Apply/Create Bloom level] [concept] in order to [authentic context beyond the classroom]."*

### 2.2 Gagné's Nine Events — The Meso Layer

**Source:** Gagné, *The Conditions of Learning* (1985)

oh-my-class already uses Gagné's 9 events in `learning_plan: dict`. The key insight for decomposition: **one Gagné cycle = one lesson**. Events don't span multiple sessions. What spans multiple sessions is **multiple stacked Gagné cycles**.

**Time allocation for a 45-min Vietnamese tiết:**

| Event | Minutes | Function | AI Implementation |
|-------|---------|----------|-------------------|
| 1. Gain attention | 2–3 | Hook, arousal | `engagement_hook` |
| 2. State objective | 1–2 | Goal priming | `lesson_objective_card` |
| 3. Recall prerequisites | 3–5 | Schema activation | `prerequisite_warmup` |
| 4. Present content | 10–12 | New material | `direct_instruction_segment` |
| 5. Provide guidance | 5–7 | Scaffolding | `worked_examples` / `modeling` |
| 6. Elicit performance | 8–10 | Practice | `graduated_practice` |
| 7. Provide feedback | 2–3 | Correction | `inline_feedback` |
| 8. Assess performance | 3–5 | Formative check | `formative_check` |
| 9. Enhance retention/transfer | 3–5 | Generalization | `transfer_prompt` |

**When one event "spans" multiple sessions:**

It doesn't — but Event 6 (Elicit Performance) has sub-structures:

- *Near transfer* (same context) → same session
- *Far transfer* (new context) → next session
- *Over-learning/spaced practice* → distributed sessions

**Rule:** If practice requires >10 minutes, the topic was decomposed too finely OR the lesson duration was set too short. Re-plan, don't stretch one event.

**Micro-session variant (10–15 min):** Collapse events 1–3 to 1 min, keep 4–6, skip 7–9 (delegate to next session or homework).

### 2.3 Cognitive Load Theory — The Micro Layer

**Source:** Sweller, *Cognitive Load Theory* (2011); Cowan, *The Magical Number 4±1* (2001)

**Working memory facts (primary, replicated, non-negotiable):**

- Working memory holds **5–9 chunks** at once (Miller, 1956; Cowan, 2001)
- When information must be **processed** (compared, contrasted, combined) — not merely held — practical capacity is only **2–4 elements** simultaneously
- Unrehearsed novel information decays in **~20 seconds** (Peterson & Peterson, 1959)
- Schemas in long-term memory are **unlimited**; the goal of instruction is to convert new elements into schemas via chunking

**Three types of load — additive:**

| Load | What It Is | Teaching Action |
|------|-----------|----------------|
| Intrinsic | Inherent complexity of the topic | Split the topic to keep this low per session |
| Extraneous | Wasted load from bad presentation | Remove; this is a "must-do zero" |
| Germane | Productive load from schema construction | Maximize via worked examples, self-explanation |

**Hard constraints per session:**

- Introduce **2–4 new "elements"** per session (not 7)
- Each session should end with the student able to name **one cohesive schema**
- Stop rule for splitting: when the next sub-concept requires more than ~4 unmastered prerequisite elements to be active in working memory simultaneously
- Use the **"worked-example → completion → independent problem"** gradient for the first 30–50% of practice when intrinsic load is high

**Splitting triggers (from CLT research):**

1. More than 4 new interactive elements
2. Cannot explain the concept in 10 minutes
3. Requires more than 3 distinct competencies
4. Spans more than 2 content strands
5. Prerequisite DAG depth > 3 unmastered levels

### 2.4 Bloom's Taxonomy — Sequencing Constraint

**Source:** Anderson & Krathwohl, *A Taxonomy for Learning* (2001)

Bloom levels provide a **hard sequencing constraint**, not just labeling:

```
Remember → Understand → Apply → Analyze → Evaluate → Create
```

**Hard sequencing rule:** A lesson at Bloom level X cannot precede mastery of all prerequisite levels.

**Typical lesson decomposition pattern per UbD unit:**

| Lesson | Bloom Primary | Bloom Secondary | Function |
|--------|---------------|-----------------|----------|
| 1 | Remember | — | Vocabulary, facts, definitions |
| 2 | Understand | — | Concepts, principles, categorization |
| 3 | Apply | (Remember) | Procedural practice |
| 4 | Analyze | (Apply) | Compare, distinguish, decompose |
| 5 | Evaluate | (Analyze) | Critique, judge, defend |
| 6 | Create | (all) | Synthesis project (Performance of Understanding) |

**Vietnamese Bloom mapping (per QĐ 764/QĐ-BGDDT):**

| Vietnamese | English | Bloom Level |
|-----------|---------|-------------|
| Nhận biết | Recognize | Remember |
| Thông hiểu | Understand | Understand |
| Vận dụng | Apply | Apply + Analyze |
| Vận dụng cao | Advanced Apply | Evaluate + Create |

**Assessment distribution:** Nhận biết 40% / Thông hiểu 30% / Vận dụng 20% / Vận dụng cao 10%

### 2.5 Knowledge Component Analysis

**Source:** Koedinger et al., *Knowledge Component* (ACT-R framework)

A **Knowledge Component (KC)** is the atomic learnable unit. Sizing rules:

| Property | Rule |
|----------|------|
| Definition | One KC = one statement: *"Student will be able to [verb] [object]"* |
| Cognitive load | A lesson segment teaches **2–4 new KCs** (working memory: 4±1 chunks) |
| Time per KC | 5–15 minutes of direct instruction |
| Prerequisite mapping | Each KC must list its prerequisite KCs (DAG) |
| Mastery threshold | 80–90% accuracy on first independent attempt |

**KC Types:**

| Type | Definition | Example |
|------|-----------|---------|
| Fact | Discrete information | "H₂O = water" |
| Concept | Categorization rule | "Mammal = warm-blooded, etc." |
| Procedure | Step sequence | "Long division algorithm" |
| Principle | Causal/relational | "Force = mass × acceleration" |
| Strategy | Meta-procedure | "When to use procedure A vs B" |

**Decomposition algorithm using KCs:**

```
1. Enumerate all KCs needed for the Transfer Goal
2. Build prerequisite DAG
3. Topologically sort
4. Group consecutive KCs into lesson segments (≤ 4 new per segment)
5. Each segment becomes a Gagné Events 4–5 block
```

---

## 3. Vietnamese Curriculum Standards

### 3.1 Chương trình GDPT 2018 — Structure

**Source:** Bộ GD&ĐT, Thông tư 32/2020/TT-BGDDT; Decision 2499/QĐ-BGDDT

The 2018 General Education Curriculum organizes each subject as:

```
Môn học (Subject)
  └── Khối lớp (Grade level)
        └── Chủ đề (Topic/Theme)        ← primary decomposition unit
              └── Bài (Lesson)            ← secondary unit (≈ 1–3 tiết)
                    └── Tiết (Period, 45 min)  ← smallest scheduling unit
```

**Key terminology:**

| Vietnamese | English | Role in Segmentation |
|-----------|---------|---------------------|
| Chủ đề | Topic / Chapter | Top-level unit (e.g., "Phân số") |
| Bài | Lesson | A single 45-min teaching unit |
| Tiết | Period | 45-minute class session |
| PPCT | Phân phối chương trình | School-level mapping of chủ đề → tiết |
| Kế hoạch bài giảng | Lesson plan | Single tiết lesson plan |
| Phân chia chủ đề | Topic decomposition | Splitting a chủ đề into bài |
| Mạch nội dung | Content strand | Cross-cutting thread (e.g., "số học → đại số") |
| Yêu cầu cần đạt | Required outcomes | Competency-based learning goals |

### 3.2 Standard Time Allocations

**Session standards by grade:**

| Grade | Periods/week per subject | Minutes/period |
|-------|------------------------|----------------|
| 1–2 (Tiểu học) | 4–10 (varies) | 35–40 min |
| 3–5 (Tiểu học) | 4–10 | 40–45 min |
| 6–7 (THCS) | 4–5 | 45 min |
| 8–9 (THCS) | 4–5 | 45 min |
| 10–12 (THPT) | 3–5 | 45 min |

**Default lesson length:** 45 min (1 tiết). Double tiết (90 min) allowed only for integrated lab/project work.

### 3.3 Topic-to-Lesson Mapping

**From official sample PPCTs (Phân phối chương trình):**

| Subject | Chủ đề per year | Bài per chủ đề | Tiết per bài |
|---------|-----------------|----------------|--------------|
| Toán (Math) | 6–10 | 2–4 | 2–4 |
| Ngữ văn (Literature) | 9–12 | 2–6 | 2–6 |
| TNXH (Grade 1–3) | 8–10 | 3–4 | 3–4 |
| Khoa học TN (Science) | 7–9 | 3–5 | 3–5 |
| Lịch sử & Địa lý | 6–8 | 2–4 | 2–4 |
| KHTN (Grade 6–7) | — | 1–2 tiết/bài | 3–6 bài/chủ đề |

**Specific examples from official plans:**

- **Toán 5:** ~35 chủ đề/năm, average ~9 tiết/tuần, 35 tuần ≈ 175–180 periods/year. Single chủ đề ≈ 4–6 tiết.
- **Ngữ văn 6:** organized into chủ đề đọc hiểu + chủ đề viết, each ≈ 2–4 tiết.
- **KHTN 6–7:** organized into chủ đề + bài, each bài = 1–2 tiết, each chủ đề = 3–6 bài.
- **Lịch sử & Địa lí 6–9:** mỗi bài = 1–2 tiết, mỗi chương = 4–10 bài.

**Decomposition rule from MOET sample plans:** A chủ đề is split when it covers >3 distinct competencies (năng lực) or >2 mạch nội dung (content strands).

### 3.4 QĐ 764/QĐ-BGDDT — Assessment Constraints

**Source:** Ministry of Education, Decision 764/QĐ-BGDDT (2014)

This decision governs assessment format for Math and Literature at THCS/THPT level. Key constraint for topic decomposition:

**TF 4-item scoring:**

| Correct items | Score |
|--------------|-------|
| 1 | 0.1đ |
| 2 | 0.25đ |
| 3 | 0.5đ |
| 4 | 1.0đ |

**Difficulty distribution guideline for Vietnamese K-12:**

| Level | Practice | Tests |
|-------|----------|-------|
| Dễ (Easy) | 30% | 20% |
| Trung bình (Medium) | 50% | 60% |
| Khó (Hard) | 20% | 20% |

**Bloom-mapped distribution for VN exams:**

| Level | Vietnamese | Percentage |
|-------|-----------|-----------|
| Nhận biết | Remember | 40% |
| Thông hiểu | Understand | 30% |
| Vận dụng | Apply | 20% |
| Vận dụng cao | Evaluate/Create | 10% |

---

## 4. AI/LLM Research on Topic Decomposition (2023–2026)

### 4.1 Key Papers & Systems

| Paper | Year | Core Contribution | Use Case |
|-------|------|-------------------|----------|
| **LessonPlanLM** (Nature HSS) | Nov 2025 | RAG over 100k lesson plans, step-by-step component generation | Single lesson from topic + grade |
| **COMA** | Apr 2026 | Multi-role agent collaboration (objectives→activities→assessment) | Full lesson plan with role specialization |
| **TeachPlanAlign** | Apr 2026 | Dual-profile (teacher + class) + curriculum grounding + self-refinement | Personalized, curriculum-compliant |
| **Curricular CoT** | Jan 2026 | Extraction→synthesis→scoring for competency mapping | Curriculum analysis |
| **PSI-KT** (ICLR) | 2024 | Bayesian + prerequisite discovery + continual learning | Adaptive sequencing |
| **SINKT** | Jul 2024 | LLM-generated concept-question graphs + inductive KT | Cold-start KT |
| **ZPDES-KS** | 2024 | Zone of Proximal Development + prerequisite graphs | Adaptive item selection |
| **Hierarchical MAB** | 2024 | Multi-armed bandit for concept + problem selection | Open-source tutoring |

**Key empirical finding** (LessonPlanLM, Nature HSS 2025):

> "To improve the relevance and coherence of these components, this work first generates the lesson objective and lesson key & difficult points, then creates the lesson procedure with the generation of the lesson objective... Similarly, the specific materials are prepared with the generated lesson procedure."

This validates oh-my-class's Step 03 (Blueprint) → Step 08 (Generate) pipeline — generate dependencies first, then specifics.

### 4.2 Proven Prompting Strategy: Curricular CoT

**Source:** Xu et al., Curricular CoT (2026)

Three-phase decomposition outperforms zero-shot and monologic CoT:

| Phase | Action | Output |
|-------|--------|--------|
| **1. Extraction** | Answer guided pedagogical questions | Prerequisites, core concepts, misconceptions, Bloom levels |
| **2. Synthesis** | Organize into dependency graph | Concept DAG + difficulty progression + time estimates |
| **3. Scoring/Decomposition** | Apply rubric, return structured JSON | Lesson sequence with objectives, KCs, assessments |

**Why this beats naive prompts:**

| Strategy | Verifiable? | Pedagogy-grounded? | Reference |
|----------|------------|-------------------|-----------|
| Zero-shot "split into 5 lessons" | ❌ | ❌ | ChatGPT case study, PLOS ONE 2024 |
| Monologic CoT ("think step by step") | Partial | ❌ | Zhao 2026 (CoT reasoning mirage) |
| **Structured extraction-synthesis-scoring** | ✅ | ✅ | Curricular CoT, Xu et al. 2026 |
| Knowledge-grounded + iterative refinement | ✅ | ✅ | LessonPlanLM 2025, TeachPlanAlign 2026 |

**Critical finding:** "The more specific the prompt, the less accurate the result" (Rutecka 2025). Solution: **incremental decomposition** — break one topic into 5 lessons, then optionally expand each lesson into sub-micro-lessons.

**Curricular CoT prompt template:**

```python
PLANNER_PROMPT_TEMPLATE = """
You are decomposing a K-12 topic into a lesson sequence.

TOPIC: {topic}
GRADE: {grade_level}
DURATION_MINUTES: {duration}

PHASE 1 - EXTRACTION (answer each, quote/cite source):
- What are the prerequisites?
- What are the core concepts?
- What are common misconceptions?
- What Bloom levels are needed?

PHASE 2 - SYNTHESIS (organize):
- Concept dependency graph (what must come before what)
- Difficulty progression (concrete → abstract, simple → complex)
- Estimated minutes per micro-concept (typical 8-15 min/lesson)
- Prerequisites that must be assumed vs. taught

PHASE 3 - DECOMPOSITION (return JSON only):
{
  "lessons": [
    {
      "id": "L01",
      "title": "...",
      "duration_min": 12,
      "prerequisites": [],
      "learning_objectives": [
        {"verb": "identify", "bloom_level": "remember"},
        {"verb": "apply",    "bloom_level": "apply"}
      ],
      "core_concepts": ["..."],
      "misconceptions_to_address": ["..."],
      "assessment_checkpoints": [...]
    }
  ],
  "rationale": "why this sequence respects Bloom + ZPD"
}

CONSTRAINTS:
- Return JSON only
- Bloom coverage ≥ 2 levels across the sequence
- Total duration ≈ {duration} ± 10%
- Each lesson has 1-3 objectives (verbs from Bloom taxonomy)
"""
```

### 4.3 Knowledge Graph + LLM Approaches

**Source:** SINKT (2024), PSI-KT (ICLR 2024)

| Approach | Strength | Limitation |
|----------|----------|-----------|
| Pure LLM | Flexible, no cold-start | Hallucinates dependencies |
| Pure KG (expert-built) | Interpretable, accurate | Expensive, brittle |
| **KG-augmented LLM** | Best of both | More complex |
| **LLM-discovered KG** | Learns from data | Needs interaction logs |

**For oh-my-class (cold-start, single-shot generation):** Bootstrap with LLM-generated graph, then refine with user data.

**LLM-generated prerequisite graph:**

```python
async def build_initial_graph(topic: str, grade: int) -> dict:
    """LLM proposes prerequisite graph; validate later."""
    prompt = f"""
    For grade-{grade} topic "{topic}", list 5-15 core concepts
    in dependency order.

    Return JSON:
    {{
      "concepts": [
        {{"id": "c1", "name": "...", "prerequisites": []}},
        {{"id": "c2", "name": "...", "prerequisites": ["c1"]}}
      ]
    }}

    Rules:
    - Acyclic (no concept depends on itself, even transitively)
    - Each concept teachable in 5-20 minutes
    - Prerequisites are concepts taught in earlier grades
      OR earlier in this unit
    """
    return await llm_call(prompt, response_format="json")
```

**Prerequisite discovery from learner data** (PSI-KT):

```python
def discover_prerequisites(
    interactions: list[tuple[str, str, int]],  # (student, KC, 0/1)
    n_concepts: int,
    max_edges: int = 50,
) -> np.ndarray:
    """Returns adjacency matrix A where A[i,j]=1 means
    concept j is prerequisite for i."""
    A = np.eye(n_concepts)
    for _ in range(max_edges):
        best_edge, best_gain = None, -np.inf
        for i in range(n_concepts):
            for j in range(n_concepts):
                if i == j or A[j, i] == 1:
                    continue
                A[i, j] = 1
                if creates_cycle(A):
                    A[i, j] = 0
                    continue
                gain = predictive_likelihood(interactions, A)
                if gain > best_gain:
                    best_gain, best_edge = gain, (i, j)
                A[i, j] = 0
        if best_edge is None:
            break
        A[best_edge] = 1
    return A
```

### 4.4 Production Platform Patterns

All major platforms converge on a **three-tier metadata structure:**

```
Course (3–5 units)
  → Unit (3–7 lessons, week-scale)
    → Lesson (1–3 concepts, 10–20 min)
      → Concept (3–5 min teachable chunk)
        → Exercise (5–20 per concept)
```

| Platform | Decomposition Unit | Granularity | Key Method |
|----------|-------------------|-------------|------------|
| **Khan Academy** | Skill (1 "I can…" statement) | ~10–25 min | Skill graph (DAG of 8,000+ skills); mastery gating |
| **Duolingo** | Skill (5–15 items) | ~3–7 min | Half-life spaced repetition + mastery gating |
| **ALEKS** | Knowledge State | ~20–40 states | Bayesian mastery model; ZPD-based selection |
| **Squirrel AI** | Atomic micro-lesson | ~3 min | Knowledge graph + Bayesian; real-time difficulty adjustment |
| **Carnegie MATHia** | One concept per session | Branching | Real-time cognitive model drives next item selection |

**Universal pattern across all platforms:**

1. **Atomic skill definition** — each session teaches exactly one "I can …" statement
2. **Mastery gating** — student cannot move on until a measurable threshold is met
3. **Prerequisite DAG** — explicit edges prevent teaching something the student isn't ready for
4. **Adaptive granularity** — break a session into smaller micro-sessions if the student struggles; combine if they breeze through

**Per-lesson metadata schema (universal across platforms):**

```yaml
lesson:
  id: "alg2.unit3.lesson2"
  title: "Solving Quadratic Equations by Factoring"
  estimated_minutes: 14
  video_minutes: 6
  exercise_minutes: 8
  prerequisites: ["alg2.unit2.lesson5"]  # IDs, not names
  learning_objectives:
    - verb: "factor"
      bloom_level: "apply"
      measurable: true
  checkpoints:
    - type: "formative"
      question_count: 3
      mastery_threshold: 0.8
  difficulty_tier: 2  # 1-5
  accessibility:
    reading_level: "grade-8"
    languages: ["en", "vi"]
```

**Sequencing heuristics from production systems:**

1. **Spiral sequencing** (Khan Academy): revisit concepts at increasing depth
2. **Mastery-based gating** (Coursera): can't advance until ≥80% on checkpoint
3. **Zone of Proximal Development** (edX, ASSISTments): difficulty = mastery + 0.2–0.3
4. **Interleaving** (Duolingo, Codecademy): mix topics from previous units

### 4.5 Open-Source Tools

| Repository | What It Does | URL |
|-----------|-------------|-----|
| **PSI-KT** | Interpretable KT with prerequisite discovery | github.com/mlcolab/psi-kt |
| **pyBKT** | Bayesian Knowledge Tracing implementations | github.com/CAHLR/pyBKT-family |
| **Hierarchical MAB** | Open-source MAB-based concept selection | arXiv 2408.07208 (code in paper) |
| **SINKT** | LLM-augmented inductive KT | arXiv 2407.01245 |
| **LangChain** | Multi-step curriculum chains | github.com/langchain-ai/langchain |

**Practical recommendation:** Don't fine-tune from scratch. Use GPT-5.4 or Claude Sonnet 4.6 with Curricular CoT prompting. Fine-tuning only pays off at >10k runs/month.

---

## 5. Age-Band Guidelines

### 5.1 Attention Span & Duration by Age

**Source:** Cognitive Load Theory research; microlearning meta-analyses (2020–2024)

| Age | Grade | Attention Span | New Concept Time | Optimal Lesson Length |
|-----|-------|---------------|-----------------|----------------------|
| 5–7 | K–2 | 10–15 min | 5–10 min | 30–40 min |
| 7–9 | 3–4 | 15–20 min | 8–12 min | 40–45 min |
| 9–11 | 5–6 | 20–30 min | 10–15 min | 45 min |
| 11–13 | 7–8 | 25–35 min | 12–18 min | 45 min |
| 13–15 | 9–10 | 30–40 min | 15–20 min | 45 min |
| 15–18 | 11–12 | 40–50 min | 15–25 min | 45–60 min |

**The "10-minute rule":** A single novel concept should be introducible and explained in ≤10 min when the learner is at age-appropriate prior knowledge. If the micro-explanation runs longer, the topic is actually 2+ topics.

**Evidence-based duration ranges:**

| Duration | Use Case | Evidence Base |
|----------|---------|--------------|
| **5–7 min** | Micro-skill, single concept, vocabulary item | Duolingo lessons; microlearning meta-analyses |
| **10–15 min** | Single focused topic, one schema | TED-Ed; Khan Academy video norm; sustained-attention threshold |
| **20–25 min** | Standard instructional block (model + guided practice) | Common K-12 period; matches ultradian rhythm |
| **35–45 min** | Full session including practice + formative check | Vietnamese 45-min tiết; widely replicated effect sizes |
| >60 min | Workshop/lab/integrated project only | Attention reliably degrades after 45 min in 12–18yr olds |

### 5.2 Vietnamese Session Standards

| Rule | Value | Source |
|------|-------|--------|
| Default session length | 45 min (1 tiết) | MOET standard |
| Double session | 90 min (2 tiết) | Lab/project work only |
| Primary (Grade 1–2) | 35–40 min | Thông tư 32/2020 |
| Primary (Grade 3–5) | 40–45 min | Thông tư 32/2020 |
| Secondary + High School | 45 min | Thông tư 32/2020 |
| Chủ đề decomposition rule | Split when >3 competencies or >2 content strands | MOET sample PPCTs |
| Typical chủ đề size | 2–8 tiết | Subject-dependent |

---

## 6. Actionable Suggestions for oh-my-class

### 6.1 Schema Extension — LessonSequence

**New file:** `common/contracts/lesson_sequence.py`

```python
"""LessonSequence Pydantic models — multi-session topic decomposition.

Extends LessonPlan to support splitting a topic into individual
sub-lessons/sessions, with prerequisite DAG and per-session structure.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from common.contracts.lesson_plan import (
    AssessmentCheckpoint,
    LearningObjective,
)


class KnowledgeComponent(BaseModel):
    """Atomic learnable unit within a session."""

    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=200)
    kc_type: str = Field(
        ...,
        pattern=r"^(fact|concept|procedure|principle|strategy)$",
    )
    estimated_minutes: int = Field(..., ge=2, le=20)
    prerequisites: list[str] = Field(
        default_factory=list,
        description="KC IDs that must be mastered first",
    )
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)


class SessionPlan(BaseModel):
    """One session within a topic decomposition."""

    session_index: int = Field(..., ge=0)
    title: str = Field(..., min_length=1, max_length=200)
    sub_topic: str = Field(..., min_length=1, max_length=200)
    duration_minutes: int = Field(..., ge=10, le=90)
    learning_objectives: list[LearningObjective] = Field(
        ..., min_length=1, max_length=5
    )
    bloom_level_primary: str = Field(
        ...,
        pattern=r"^(remember|understand|apply|analyze|evaluate|create)$",
    )
    prerequisite_sessions: list[int] = Field(
        default_factory=list,
        description="Session indices that must complete first",
    )
    knowledge_components: list[KnowledgeComponent] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="2–4 new KCs per session (CLT constraint)",
    )
    gagne_events: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-session Gagné 9-event cycle",
    )
    assessment_checkpoints: list[AssessmentCheckpoint] = Field(
        default_factory=list
    )


class PrerequisiteEdge(BaseModel):
    """Edge in the prerequisite dependency graph."""

    source: str = Field(..., description="Source KC ID")
    target: str = Field(..., description="Target KC ID")
    strength: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="How strongly source is a prerequisite for target",
    )


class LessonSequence(BaseModel):
    """Multi-session decomposition of a topic.

    Produced by the Planner Agent when a topic requires more than
    one session. Consumed by the pipeline to fan-out generation
    across sessions.
    """

    topic: str = Field(..., min_length=1, max_length=200)
    grade_level: str
    subject: str
    total_sessions: int = Field(..., ge=1, le=20)
    total_duration_minutes: int = Field(..., ge=10, le=1800)
    sessions: list[SessionPlan] = Field(
        ..., min_length=1, max_length=20
    )
    prerequisite_edges: list[PrerequisiteEdge] = Field(
        default_factory=list,
        description="Cross-session KC dependency graph",
    )
    rationale: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Why this decomposition respects Bloom + CLT + curriculum",
    )
```

### 6.2 Pipeline Integration Points

| Step | Current Behavior | With Decomposition |
|------|-----------------|-------------------|
| **03 Blueprint** | Planner → 1 LessonPlan | Planner → 1 LessonSequence (N SessionPlans) |
| **04 Teacher Gate 1** | Approve 1 plan | Approve sequence + optionally edit/reorder sessions |
| **05 Pack Scope** | Artifact types for 1 run | Artifact types per session |
| **06 Visual Engine** | Theme/layout for 1 pack | Theme consistency across all session packs |
| **07 Research** | 1 ResearchBundle | 1 shared bundle (or per-session if topics diverge) |
| **08 Generate** | 1 set of ArtifactContent[] | N sets (one per session, iterating over sessions) |
| **09–10 Quality** | Review 1 pack | Review each session pack (or batch) |
| **11 Teacher Gate 2** | Approve 1 pack | Approve packs sequentially or in batch |
| **13 Export** | Export 1 pack | Export N packs (or combined unit pack) |

**State schema extension:**

```python
class OhMyClassState(TypedDict):
    # ... existing fields ...

    # ── Decomposition (new) ────────────────
    lesson_sequence: NotRequired[dict]    # LessonSequence JSON
    current_session_index: int            # 0-based cursor for fan-out
    total_sessions: int                   # for progress tracking
    session_artifacts: Annotated[
        dict[int, list[dict]], merge_session_artifacts
    ]  # session_index → artifacts
```

### 6.3 Planner Agent Decomposition Prompt

```
Given topic T, grade G, subject S, total duration D minutes:

STEP 1 — TRANSFER_ANCHOR
  Generate 1 Transfer Goal (Bloom: Apply/Create)
  Validate: contains real-world context beyond classroom
  If fails → ASK_TEACHER (Teacher Gate 1 candidate)

STEP 2 — EU_EXPANSION
  Generate 3–5 Enduring Understandings
  Each EU must be expressible as a generalization
  ("X is important because Y")

STEP 3 — KC_EXTRACTION
  For each EU:
    - Extract 5–12 KCs (type-tagged: fact/concept/procedure/principle/strategy)
    - Build KC prerequisite DAG
    - Estimate difficulty (0.0–1.0) per KC

STEP 4 — LESSON_PARTITIONING
  Given total_duration and lesson_length (per grade table):
    n_sessions = ceil(total_duration / lesson_length)
  Distribute EUs across sessions, weighted by KC difficulty sum
  Validate: each session has ≤ 4 new KCs (CLT constraint)

STEP 5 — BLOOM_SEQUENCING
  Within each session, order KCs by Bloom level
  Validate: no Apply-level KC without prerequisite
  Remember-level KC in this unit

STEP 6 — GAGNE_FILLING
  For each session:
    - Allocate minutes per Gagné event (use age-band table)
    - Map KCs to Events 4–5 (Present + Guide)
    - Generate Assessment checkpoints for Event 8

STEP 7 — STANDARDS_INJECTION
  If locale=vi-VN:
    - Inject QĐ 764 TF 4-item format into assessments
    - Apply Bloom distribution: 40/30/20/10
    - Ensure session duration = 45 min (1 tiết)
  If locale=en-US:
    - Inject CCSS alignment labels

STEP 8 — VALIDATION
  - ≥2 Bloom levels covered across sequence
  - No KC > 20 min direct instruction
  - Each session has Transfer hook (Event 9)
  - Cognitive load per segment ≤ 4±1 schemas
  - Total duration ≈ D ± 10%
  - Acyclic prerequisite graph

STEP 9 — HUMAN_GATE
  Emit LessonSequence JSON to Teacher Gate 1
  On reject → loop back to STEP 2 with feedback
```

### 6.4 Middleware — Prerequisite Validator

**New file:** `packages/agents/middleware/prereq_validator.py`

```python
"""Prerequisite Graph Validator — middleware for pipeline.

Validates concept graph acyclicity, Bloom coverage, and KC load
per session before generation begins.
"""

from typing import Any


def has_cycle(edges: list[dict]) -> bool:
    """Check if prerequisite edges form a cycle (DFS)."""
    graph: dict[str, list[str]] = {}
    for e in edges:
        graph.setdefault(e["source"], []).append(e["target"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    for node in graph:
        if color[node] != WHITE:
            continue
        stack = [(node, False)]
        while stack:
            v, processed = stack.pop()
            if processed:
                color[v] = BLACK
                continue
            if color[v] == GRAY:
                continue
            color[v] = GRAY
            stack.append((v, True))
            for w in graph.get(v, []):
                if color[w] == GRAY:
                    return True  # cycle
                if color[w] == WHITE:
                    stack.append((w, False))
    return False


class PrerequisiteValidator:
    """Validates lesson sequence before generation."""

    async def before_model(self, state: dict, context: Any) -> dict:
        sequence = state.get("lesson_sequence")
        plan = state.get("lesson_plan")

        if not sequence and not plan:
            return state

        # If using LessonSequence
        if sequence:
            errors = []

            # 1. Acyclicity
            if has_cycle(sequence.get("prerequisite_edges", [])):
                errors.append("Cyclic prerequisites detected in KC graph")

            # 2. Bloom coverage ≥ 2 levels
            all_bloom = set()
            for session in sequence.get("sessions", []):
                for obj in session.get("learning_objectives", []):
                    all_bloom.add(obj.get("bloom_level", ""))
            if len(all_bloom) < 2:
                errors.append(
                    f"Only {all_bloom} Bloom levels covered, need ≥2"
                )

            # 3. KC load per session ≤ 4
            for session in sequence.get("sessions", []):
                kcs = session.get("knowledge_components", [])
                if len(kcs) > 4:
                    errors.append(
                        f"Session '{session.get('title', '?')}' has "
                        f"{len(kcs)} KCs (max 4 per CLT)"
                    )

            # 4. Duration realism
            total_estimated = sum(
                s.get("duration_minutes", 0)
                for s in sequence.get("sessions", [])
            )
            target = sequence.get("total_duration_minutes", 0)
            if target > 0 and abs(total_estimated - target) > target * 0.15:
                errors.append(
                    f"Time drift: estimated {total_estimated}min vs "
                    f"target {target}min (>{15}% drift)"
                )

            if errors:
                return {**state, "errors": errors}

        return state
```

### 6.5 Splitting Triggers

| Trigger | Detection Method | Action |
|---------|-----------------|--------|
| Teacher says "across X days/weeks" | NLP parsing of `raw_request` | Auto-decompose into X sessions |
| `duration_minutes > 90` | Schema validation in Step 01 | Suggest decomposition to teacher |
| Topic contains >3 competencies | LLM analysis in Step 03 | Decompose |
| Vietnamese `chủ đề` > 4 tiết | PPCT lookup or LLM | Decompose per MOET guidelines |
| Teacher explicitly requests | `raw_request` keyword match | Decompose |
| KC count > 12 for one topic | LLM extraction in Step 03 | Must decompose (CLT violation) |
| Prerequisite depth > 3 unmastered | DAG analysis | Must decompose |

### 6.6 Framework Composition Map

| Decision | Use Framework |
|----------|--------------|
| What is the unit of decomposition? | **UbD** (Enduring Understandings) |
| How many sessions in the unit? | **UbD** (3–5) + duration math |
| What's inside each session? | **Gagné** (9 events) |
| What cognitive level is each segment? | **Bloom's Taxonomy** |
| What is each learnable atom? | **KC analysis** (Cognitive Load Theory) |
| How long is each segment? | **Age-band attention tables** |
| How is each session assessed? | **Locale standards** (QĐ 764 / CCSS / NGSS) |
| How are revisions handled? | **Layer 4 self-heal** + Teacher Gate |

**The frameworks compose, not compete:**

```
UbD          →  macro structure  (unit → lessons)
Gagné        →  meso structure   (lesson → events)
Bloom + KC   →  micro structure  (event → knowledge components)
CLT          →  sizing constraints (4±1 KCs, 10-min rule)
Age-bands    →  duration bounds   (30–60 min per session)
Locale stds  →  assessment format (QĐ 764, CCSS, NGSS)
```

**Mapping to oh-my-class architecture:**

| Layer | Framework | oh-my-class Component |
|-------|-----------|----------------------|
| Macro | UbD | `LessonSequence` (new) |
| Meso | Gagné | `LessonPlan.learning_plan` (existing) |
| Micro | Bloom + KC | `SessionPlan.knowledge_components` (new) |
| Constraints | CLT | `PrerequisiteValidator` middleware (new) |
| Sizing | Age-bands | Planner Agent prompt (updated) |
| Assessment | Locale standards | `SessionPlan.assessment_checkpoints` (existing pattern) |

---

## 7. References

### Academic Papers

| Paper | Year | URL |
|-------|------|-----|
| LessonPlanLM (Nature HSS) | 2025 | https://doi.org/10.1057/s41599-025-06004-2 |
| Curricular CoT | 2026 | https://www.emergentmind.com/topics/curricular-cot |
| TeachPlanAlign | 2026 | https://www.mdpi.com/2227-7390/14/9/1492 |
| COMA (Multi-Agent Lesson Plans) | 2026 | Referenced in lesson planning literature |
| PSI-KT (ICLR) | 2024 | https://github.com/mlcolab/psi-kt |
| SINKT | 2024 | https://arxiv.org/html/2407.01245 |
| ZPDES-KS | 2024 | https://arxiv.org/html/2402.01672v1 |
| Hierarchical MAB | 2024 | https://doi.org/10.48550/arxiv.2408.07208 |
| Theory-guided prompting | 2025 | https://ejournal.abcollab.id/index.php/JAAIE/article/view/493 |
| GenAI curriculum empirical | 2025 | https://webm.ue.katowice.pl/strzelecki/papers/rutecka-ieee-2025.pdf |
| Causal Graph CoT | 2025 | https://exa.ai/library/publication/qj8xq11mv1h |
| BKT 25-year review | 2023 | https://doi.org/10.1007/s11257-023-09389-4 |

### Pedagogical Frameworks

| Framework | Source |
|-----------|--------|
| Backward Design (UbD) | Wiggins & McTighe, *Understanding by Design* (2005) |
| Gagné's Nine Events | Gagné, *The Conditions of Learning* (1985) |
| Cognitive Load Theory | Sweller (2011); Cowan (2001); Miller (1956) |
| Bloom's Taxonomy (Revised) | Anderson & Krathwohl, *A Taxonomy for Learning* (2001) |
| Knowledge Components (ACT-R) | Koedinger et al., *Knowledge Component* framework |
| Zone of Proximal Development | Vygotsky (1978) |

### Vietnamese Standards

| Document | Source |
|----------|--------|
| Chương trình GDPT 2018 | Bộ GD&ĐT, Thông tư 32/2020/TT-BGDDT |
| QĐ 764/QĐ-BGDDT (2014) | Ministry of Education and Training |
| Decision 2499/QĐ-BGDDT | Bộ GD&ĐT curriculum framework |
| PPCT sample plans | Provincial Departments of Education |

### Production Platforms

| Platform | Reference |
|----------|-----------|
| Khan Academy / Khanmigo | https://blog.khanacademy.org/how-we-built-ai-tutoring-tools/ |
| Quizlet Q-Chat | https://quizlet.com/blog/meet-q-chat |
| Kahoot! AI | https://trust.kahoot.com/ai-powered-features-in-kahoot/ |
| ALEKS | Knowledge Space Theory (Doignon & Falmagne, 1999) |
| Squirrel AI | Adaptive learning platform (China) |
| Carnegie MATHia | Cognitive tutoring system |

---

> **Last updated:** 2026-06-30
> **Status:** Research complete. Ready for ADR if topic decomposition is approved as a feature.
> **Next step:** If approved, create ADR in `docs/adr/` for the `LessonSequence` schema extension and pipeline fan-out architecture.
