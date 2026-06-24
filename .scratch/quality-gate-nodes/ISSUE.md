---
title: "Quality Gate Nodes: B-pattern — 6 Gate Layers as Dedicated Graph Nodes"
status: ready
labels: [architecture, agents, quality, langgraph]
created: 2026-06-24
priority: p0
report: "02"
---

## What to build

Wire the 6-layer quality gate system from Report 02 into the graph as dedicated nodes — one node per gate group. Each node has ONE responsibility and can be tested, retried, and swapped independently.

**Design decision (grilling Q1-B):** Dedicated node per gate group, not monolithic reviewer. Clear mapping, easy to change individual layers without touching others.

## Graph Mapping

```
step_08_generate
    │ artifacts[]
    ▼
step_09_schema_validate        ← Layer 1: JSON Schema (Pydantic v2 + Circuit Breaker)
    │ pass ──────────────────────────────────────────────────────────────────► step_10_content_review
    │ fail → writes: fail_layer="schema", fail_count++, fail_context={errors} ► healing_node
    ▼
step_10_content_review         ← Layer 2+3: FACT hybrid + HTML validate + Age-appropriateness
    │ pass ──────────────────────────────────────────────────────────────────► step_10b_llm_judge
    │ fail → writes: fail_layer="content", fail_count++                      ► healing_node
    ▼
step_10b_llm_judge             ← Layer 4: G-Eval (f.pro judge, single judge K4)
    │ score ≥ 7.0 ───────────────────────────────────────────────────────────► gate_02_content_approval
    │ score < 7.0 → writes: fail_layer="judge", fail_count++, score=X        ► healing_node
    ▼
gate_02_content_approval       ← Layer 5: interrupt() — HITL (from hitl-gate-wrapper issue)
    │ approve ───────────────────────────────────────────────────────────────► step_11_export_readiness
    │ reject  → writes: fail_layer="human", teacher_feedback                 ► step_08_generate
    │ timeout ───────────────────────────────────────────────────────────────► escalate_node
    ▼
step_11_export_readiness       ← Layer 6: Multi-judge assembly (f.pro, 1 judge MVP)
    │ pass ──────────────────────────────────────────────────────────────────► step_12_finalize
    │ fail ──────────────────────────────────────────────────────────────────► escalate_node
    ▼
step_12_finalize
```

## State Fields Added

```python
# packages/agents/state.py additions
class OhMyClassState(TypedDict):
    # ... existing fields ...

    # Gate tracking (written by gate nodes, read by healing_node + router)
    fail_layer: str | None       # "schema" | "content" | "judge" | "human"
    fail_count: int              # incremented by healing_node
    fail_type: str | None        # "validation" | "content" | "score" | "timeout"
    fail_context: dict | None    # error details for healing strategy

    # Gate scores
    schema_valid: bool | None
    content_review_passed: bool | None
    judge_score: float | None    # overall G-Eval score
    export_ready: bool | None
```

## File Structure

```
packages/agents/gates/
├── __init__.py
├── schema_validator.py         # Layer 1 node function
├── content_reviewer.py         # Layer 2-3 node function
├── llm_judge.py                # Layer 4 node function
├── gate_01_blueprint.py        # Layer 5a (from hitl-gate-wrapper)
├── gate_02_content.py          # Layer 5b (from hitl-gate-wrapper)
├── export_readiness.py         # Layer 6 node function
├── fact_check/
│   ├── extractor.py            # heuristic claim extractor
│   ├── risk_classifier.py      # HIGH/MEDIUM/LOW risk
│   ├── llm_verifier.py         # LLM verify high-risk only (f.pro)
│   └── fact_checker.py         # orchestrate pipeline
└── presentation/
    ├── html_validator.py        # DOCTYPE, external assets, brand strings
    ├── age_checker.py           # grade-level appropriateness
    └── answer_key_guard.py      # no answer leakage in student view
```

## Node Signatures

```python
# gates/schema_validator.py
def step_09_schema_validate(state: OhMyClassState) -> dict:
    """Layer 1: Pydantic v2 schema validation with circuit breaker.
    Returns: schema_valid=True or fail_layer="schema" + fail_context
    """

# gates/content_reviewer.py
def step_10_content_review(state: OhMyClassState) -> dict:
    """Layer 2+3: FACT hybrid + HTML + age-appropriateness.
    Returns: content_review_passed=True or fail_layer="content" + fail_context
    """

# gates/llm_judge.py
def step_10b_llm_judge(state: OhMyClassState) -> dict:
    """Layer 4: G-Eval with f.pro judge.
    Returns: judge_score=X.X or fail_layer="judge"
    """

# gates/export_readiness.py
def step_11_export_readiness(state: OhMyClassState) -> dict:
    """Layer 6: Final export validation.
    Returns: export_ready=True or fail_layer="export"
    """
```

## Router Functions

```python
# graph.py additions

def route_after_schema(state: OhMyClassState) -> str:
    return "step_10_content_review" if state.get("schema_valid") else "healing_node"

def route_after_content_review(state: OhMyClassState) -> str:
    return "step_10b_llm_judge" if state.get("content_review_passed") else "healing_node"

def route_after_judge(state: OhMyClassState) -> str:
    score = state.get("judge_score", 0)
    return "gate_02_content_approval" if score >= 7.0 else "healing_node"

def route_after_export(state: OhMyClassState) -> str:
    return "step_12_finalize" if state.get("export_ready") else "escalate_node"
```

## Acceptance Criteria

- [ ] `step_09_schema_validate`, `step_10_content_review`, `step_10b_llm_judge`, `step_11_export_readiness` all registered as graph nodes
- [ ] Each node writes structured fail signal to state (`fail_layer`, `fail_context`) on failure
- [ ] Router functions route to `healing_node` on any failure
- [ ] `escalate_node` exists as terminal fail node
- [ ] Each gate node independently testable with mock state (no full graph needed)
- [ ] State fields (`fail_layer`, `fail_count`, `judge_score`, etc.) added to `OhMyClassState`

## Dependencies

- Blocked by: `agent-state-schema` (needs OhMyClassState extensions), `gate-config` (needs GateConfig), `hitl-gate-wrapper` (Layer 5 nodes)
- Blocks: `healing-orchestrator` (needs fail signal schema)
- Priority: p0 — core pipeline structure
