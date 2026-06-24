---
title: "Diagnostic Agent: StudentResponse Schema + Wrong Answer Analysis"
status: ready
labels: [agents, schema, diagnostic]
created: 2026-06-24
priority: p1
report: "08"
---

## What to build

A `DiagnosticAgent` sub-agent that takes student wrong answers → produces a `DiagnosticReport` with knowledge gaps, Bloom level gaps, and misconception patterns. New state fields in `OhMyClassState`. New contracts: `StudentResponse`, `DiagnosticReport`.

**Design decision:** Follows same sub-agent pattern as planner/researcher/content_creator. Modular files — orchestrator, nodes, state, prompts/, tools.

## File Structure

```
common/contracts/
├── student_response.py      # StudentResponse, StudentAnswerItem
└── diagnostic_report.py     # DiagnosticReport, KnowledgeGap, BloomGap, MisconceptionPattern

packages/agents/
├── state.py                 # ADD: student_responses, diagnostic_report fields
└── sub_agents/
    └── diagnostician/
        ├── __init__.py
        ├── agent.py         # make_diagnostician_agent() + diagnostician_graph_node()
        ├── nodes.py         # diagnostician_node() async fn
        ├── state.py         # DiagnosticianState TypedDict
        ├── tools.py         # bloom_taxonomy_lookup(), question_type_classifier()
        └── prompts/
            ├── __init__.py  # load_system_prompt()
            └── system.md    # system prompt for diagnostic analysis
```

## Implementation Spec

### `common/contracts/student_response.py`
```python
from __future__ import annotations
from pydantic import BaseModel, Field

class StudentAnswerItem(BaseModel):
    question_id: int | str
    student_answer: str | None = None    # None = unanswered
    correct_answer: str
    is_correct: bool
    section: str | None = None           # question section/category
    bloom_level: str | None = None       # populated during analysis

class StudentResponse(BaseModel):
    student_id: str
    test_id: str = "unknown"
    wrong_question_ids: list[int | str]  # teacher input
    answers: list[StudentAnswerItem] = []
    total_questions: int = 0
    context: dict = Field(default_factory=dict)  # raw_request, personality, etc.
```

### `common/contracts/diagnostic_report.py`
```python
from __future__ import annotations
from pydantic import BaseModel

class KnowledgeGap(BaseModel):
    category: str           # "grammar", "vocabulary", "reading_comprehension", etc.
    error_count: int
    error_rate: float       # 0.0–1.0
    severity: str           # "critical" | "moderate" | "minor"
    question_ids: list[int | str]

class BloomGap(BaseModel):
    bloom_level: str        # "remember" | "understand" | "apply" | "analyze" | ...
    vn_name: str            # "nhận biết" | "thông hiểu" | etc.
    error_count: int
    error_rate: float

class MisconceptionPattern(BaseModel):
    id: str                 # "C1", "C2", etc.
    group: str              # color group a-e
    title: str
    description: str
    question_ids: list[int | str]

class DiagnosticReport(BaseModel):
    student_id: str
    knowledge_gaps: list[KnowledgeGap] = []
    bloom_gaps: list[BloomGap] = []
    misconception_patterns: list[MisconceptionPattern] = []
    critical_sections: list[str] = []    # 100% error rate sections
    overall_error_rate: float = 0.0
    recommended_level: str = "B2"        # "B1" | "B2" | "C1"
    summary: str = ""
```

### New `OhMyClassState` fields
```python
# ── Diagnostic ──────────────────────────────────────────────────────────────
student_responses: NotRequired[dict | None]    # StudentResponse JSON
diagnostic_report: NotRequired[dict | None]   # DiagnosticReport JSON
student_profile: NotRequired[dict | None]     # StudentProfile JSON (from roadmap-agent)
```

### `sub_agents/diagnostician/state.py`
```python
from typing import TypedDict, Any, NotRequired
from langgraph.graph import MessagesState

class DiagnosticianState(MessagesState):
    student_responses: dict
    diagnostic_report: NotRequired[dict | None]
```

### `sub_agents/diagnostician/tools.py`
```python
from langchain_core.tools import tool

@tool
def bloom_taxonomy_lookup(bloom_level: str) -> dict:
    """Map Bloom level to Vietnamese name and typical question characteristics."""
    ...

@tool
def question_type_classifier(question_ids: list[str], section_map: dict) -> dict:
    """Classify question IDs by type based on section groupings."""
    ...
```

## Graph Integration

Add optional `step_00_diagnostic` node before `step_01_preflight`. Runs only when `state.get("student_responses")` is set.

## Prompt

`prompts/system.md` — instructs agent to:
1. Map wrong question IDs to knowledge categories
2. Identify Bloom level gaps (Vietnamese mapping: nhận biết → remember, etc.)
3. Detect misconception patterns (formula-only learner, nuance blindness, etc.)
4. Return structured `DiagnosticReport` JSON

## Tests

```
packages/agents/tests/sub_agents/test_diagnostician.py
common/contracts/tests/test_diagnostic_report.py
```

## Acceptance Criteria

- [ ] `StudentResponse` and `DiagnosticReport` contracts defined and tested
- [ ] `DiagnosticAgent` follows same compiled-graph pattern as other sub-agents
- [ ] `diagnostician_node()` returns dict with `diagnostic_report` key
- [ ] `OhMyClassState` has `student_responses`, `diagnostic_report`, `student_profile` fields
- [ ] `bloom_taxonomy_lookup` tool covers 6 Bloom levels with Vietnamese names
- [ ] `step_00_diagnostic` node added to graph, skipped when no student_responses

## Dependencies

- Blocked by: `agent-state-schema` (OhMyClassState extensions)
- Blocks: `roadmap-agent` (needs DiagnosticReport as input)
- Priority: p1

## Research Findings

**Source**: Report 08 Section 10 — AI-Powered Diagnostic Agents

### Error Taxonomy (Production)
The Eedi/MathTutor 9-code taxonomy provides a concrete error classification:
- E01: SIGN_ARITHMETIC_ERROR, E02: COEFFICIENT_OMISSION, E03: DOMAIN_CONDITION_IGNORED
- E04: OPERATOR_MISAPPLICATION, E05: UNIT_CONVERSION, E06: LOGICAL_REASONING
- E07: READING_COMPREHENSION, E08: VOCABULARY_KNOWLEDGE, E09: FORMULA_MEMORIZATION

### Verification Pipeline (Research-Backed)
4-level verification: L1 Symbolic (SymPy) → L2 Numerical (sampling) → L3 LLM escalation (confidence < 0.9) → L4 Teacher review

### Bloom Auto-Classification
- CNN+fastText: 88% macro-F1 (Neural Comput & Applic 2026)
- DistilBERT + synonym augmentation: 96% accuracy (Electronics 2025)
- Zero-shot LLM: 82% correctness (no fine-tuning needed)

### Multi-Agent Pattern (LangGraph)
Production repos: stem-tutor-agent, MathTutor, Adaptive-Personalized-Learning-System
Architecture: parse_student_solution → verify_steps → diagnose_error → generate_feedback
Checkpointer: MemorySaver or RedisSaver, human-in-the-loop via interrupt()

### Key References
- "The Correct Answer Trap" (arXiv 2606.23205): 57%→84% with LLM verification
- MiRAGE (arXiv 2602.02414): 0.82 MAP@3 on algebra misconception detection
- stem-tutor-agent (GitHub): https://github.com/ZelinZhou-THU/stem-tutor-agent
- MathTutor (GitHub): https://github.com/dikshant182004/MathTutor
