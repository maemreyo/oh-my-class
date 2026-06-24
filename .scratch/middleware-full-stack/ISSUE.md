---
title: "Middleware Full Stack: 29-Layer Oh-My-Class Middleware Chain"
status: done
labels: [architecture, agents, middleware]
created: 2026-06-24
priority: p1
report: "01"
---

## What to build

Implement the remaining 24 middleware layers (5 already done). Based on DeerFlow's 20-layer chain (CLAUDE.md source) + 4 custom oh-my-class additions + 5 educational intelligence layers = **29 layers total**.

**Design decision (grilling Q7):** All 24 layers, modular file structure, organized by tier subfolder. Each file ~200 lines, single-concern. No one file handles everything.

## Current State

**5/24 implemented:**
- `LoopDetectionMiddleware` ✅ (safety/loop_detection.py)
- `TokenBudgetMiddleware` ✅ (safety/token_budget.py) — oh-my-class custom
- `DanglingToolCallMiddleware` ✅ (safety/dangling_tool_call.py)
- `SummarizationMiddleware` ✅ (context/summarization.py — partial)
- `GuardrailMiddleware` ✅ (quality/guardrail.py)

**Registry:** `packages/agents/middleware/registry.py` — needs update to include all 24

## Target File Structure

```
packages/agents/middleware/
├── base.py                             # BaseMiddleware ABC — EXISTS
├── registry.py                         # ORDERED_MIDDLEWARE_LIST — UPDATE
├── safety/                             # Tier 1: run blockers
│   ├── input_sanitization.py           # NEW: validate teacher request schema
│   ├── token_budget.py                 ✅ EXISTS
│   ├── thread_data.py                  # NEW (from DeerFlow)
│   ├── uploads.py                      # NEW (from DeerFlow, fine-tuned)
│   ├── content_safety.py               # NEW: replaces SandboxMiddleware
│   ├── dangling_tool_call.py           ✅ EXISTS
│   ├── llm_error_handling.py           # NEW (from DeerFlow)
│   ├── guardrail.py                    ✅ EXISTS (fine-tune for K-12)
│   ├── teacher_audit_log.py            # NEW: replaces SandboxAuditMiddleware
│   ├── tool_error_handling.py          # NEW (from DeerFlow)
│   ├── loop_detection.py               ✅ EXISTS
│   └── safety_finish_reason.py         # NEW (custom)
├── context/                            # Tier 2: enrichment
│   ├── dynamic_context.py              # NEW: inject class_info, school calendar
│   ├── skill_activation.py             # NEW (from DeerFlow, fine-tuned)
│   ├── summarization.py                ✅ EXISTS (complete)
│   ├── todo_list.py                    # NEW (from DeerFlow, fine-tuned)
│   ├── token_usage.py                  # NEW (from DeerFlow)
│   ├── title.py                        # NEW (from DeerFlow, fine-tuned)
│   ├── memory.py                       # NEW (from DeerFlow, fine-tuned)
│   ├── view_image.py                   # NEW (from DeerFlow, fine-tuned)
│   ├── deferred_tool_filter.py         # NEW (from DeerFlow)
│   └── system_message_coalescing.py    # NEW (from DeerFlow)
├── quality/                            # Tier 3: quality gates
│   ├── tool_output_budget.py           # NEW (custom)
│   ├── subagent_limit.py               # NEW (from DeerFlow)
│   └── curriculum_alignment.py        # NEW: oh-my-class specific
└── terminal/                           # MUST BE LAST
    └── clarification.py               # NEW (from DeerFlow, fine-tuned)
```

## Implementation Spec

### `registry.py` — ordered list (24 layers, CLARIFICATION always last)

```python
ORDERED_MIDDLEWARE_LIST: list[type[BaseMiddleware]] = [
    # ── Tier 1: Safety (always run) ───────────────────────────────────
    InputSanitizationMiddleware,         # 1: validate teacher request schema
    TokenBudgetMiddleware,               # 2: per-run cost ceiling
    ThreadDataMiddleware,                # 3: run directory setup
    UploadsMiddleware,                   # 4: teacher source materials
    ContentSafetyMiddleware,             # 5: K-12 age-appropriate check
    DanglingToolCallMiddleware,          # 6: crash recovery
    LLMErrorHandlingMiddleware,          # 7: provider error normalization
    GuardrailMiddleware,                 # 8: PII + content authorization
    TeacherAuditLogMiddleware,           # 9: compliance logging
    ToolErrorHandlingMiddleware,         # 10: exception → ToolMessage
    LoopDetectionMiddleware,             # 11: infinite loop prevention
    SafetyFinishReasonMiddleware,        # 12: suppress truncated calls

    # ── Tier 2: Context enrichment ────────────────────────────────────
    DynamicContextMiddleware,            # 13: inject class_info, calendar, teacher prefs
    SkillActivationMiddleware,           # 14: curriculum standards injection
    SummarizationMiddleware,             # 15: token limit management
    TodoListMiddleware,                  # 16: lesson plan step tracking
    TokenUsageMiddleware,                # 17: usage metrics
    TitleMiddleware,                     # 18: auto-generate lesson run title
    MemoryMiddleware,                    # 19: teacher preferences persistence
    ViewImageMiddleware,                 # 20: teacher visual materials
    DeferredToolFilterMiddleware,        # 21: hide irrelevant tools
    SystemMessageCoalescingMiddleware,   # 22: merge system messages

    # ── Tier 3: Quality gates ─────────────────────────────────────────
    SubagentLimitMiddleware,             # 23: concurrency enforcement

    # ── Tier 5: Educational Intelligence (oh-my-class specific) ──────
    ReadabilityLevelMiddleware,          # 25: Flesch-Kincaid score vs grade level
    PedagogicalQualityMiddleware,        # 26: Bloom's taxonomy + scaffolding check
    BiasDetectionMiddleware,             # 27: cultural/gender bias in K-12 content
    ArtifactCoherenceMiddleware,         # 28: lesson+worksheet+quiz coherent
    LearningObjectiveAlignmentMiddleware, # 29: activities → objectives mapping

    # ── Terminal (MUST BE LAST) ───────────────────────────────────────
    ClarificationMiddleware,             # 24: teacher clarification interrupts
                                         # NOTE: logical order 24, list position 30
]
```

### Key implementations for oh-my-class custom layers

#### `safety/input_sanitization.py`

```python
class InputSanitizationMiddleware(BaseMiddleware):
    """Validates teacher request schema before any LLM call.

    Checks: raw_request non-empty, grade level valid (K-12),
    subject in supported list, class_info has required fields.
    Raises InputValidationError on failure (does not call LLM).
    """
    name = "input_sanitization"
    order = 1

    VALID_GRADES = {f"grade_{i}" for i in range(1, 13)} | {"kindergarten", "k"}
    SUPPORTED_SUBJECTS = {"math", "science", "ela", "english", "history", "art", "music"}

    async def before_model(self, state, context: MiddlewareContext) -> None:
        raw_request = state.get("raw_request", "").strip()
        if not raw_request:
            raise InputValidationError("raw_request cannot be empty")

        class_info = state.get("class_info", {})
        grade = str(class_info.get("grade", "")).lower()
        subject = str(class_info.get("subject", "")).lower()

        if grade and grade not in self.VALID_GRADES:
            raise InputValidationError(f"Invalid grade level: {grade}")
        if subject and subject not in self.SUPPORTED_SUBJECTS:
            raise InputValidationError(f"Unsupported subject: {subject}")
```

#### `safety/content_safety.py`

```python
class ContentSafetyMiddleware(BaseMiddleware):
    """K-12 age-appropriate content check (replaces SandboxMiddleware).

    Before model: checks input for inappropriate content for school context.
    After model: checks output for content inappropriate for stated grade level.
    """
    name = "content_safety"
    order = 5

    BLOCKED_PATTERNS = [
        r"\b(violence|gore|explicit|adult)\b",
        r"\b(weapon|drug|alcohol)\b",
    ]

    async def before_model(self, state, context: MiddlewareContext) -> None:
        grade = state.get("class_info", {}).get("grade", 12)
        raw_request = state.get("raw_request", "")
        self._check_content(raw_request, grade)

    async def after_model(self, state, context: MiddlewareContext) -> None:
        artifacts = state.get("artifacts", [])
        grade = state.get("class_info", {}).get("grade", 12)
        for artifact in artifacts:
            content = artifact.get("content", "")
            self._check_content(content, grade)

    def _check_content(self, text: str, grade: int) -> None:
        import re
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                raise ContentSafetyError(f"Content blocked for grade {grade}")
```

#### `safety/teacher_audit_log.py`

```python
class TeacherAuditLogMiddleware(BaseMiddleware):
    """Compliance logging for teacher decisions and gate outcomes (replaces SandboxAuditMiddleware).

    Logs every gate decision (approve/reject/edit), revision count,
    and final artifact delivery for compliance and audit trails.
    """
    name = "teacher_audit_log"
    order = 9

    async def after_model(self, state, context: MiddlewareContext) -> None:
        teacher_decision = state.get("teacher_decision")
        if teacher_decision:
            import logging
            logger = logging.getLogger("oh_my_class.audit")
            logger.info(
                "teacher_gate_decision",
                extra={
                    "run_id": state.get("run_id"),
                    "teacher_id": state.get("teacher_id"),
                    "decision": teacher_decision,
                    "feedback": state.get("teacher_feedback"),
                    "step": context.step,
                    "gate": context.metadata.get("gate"),
                },
            )
```

#### `context/dynamic_context.py`

```python
class DynamicContextMiddleware(BaseMiddleware):
    """Injects dynamic context into the agent's working state.

    Injects: current date, class_info summary, teacher preferences (if available),
    school calendar events (if configured).
    """
    name = "dynamic_context"
    order = 13

    async def before_model(self, state, context: MiddlewareContext) -> None:
        from datetime import date
        context.metadata["injected_context"] = {
            "today": date.today().isoformat(),
            "class_summary": self._build_class_summary(state),
            "teacher_prefs": state.get("teacher_preferences", {}),
        }

    def _build_class_summary(self, state: dict) -> str:
        class_info = state.get("class_info", {})
        grade = class_info.get("grade", "unknown")
        subject = class_info.get("subject", "unknown")
        size = class_info.get("class_size", "unknown")
        return f"Grade {grade} {subject} class ({size} students)"
```

#### `quality/curriculum_alignment.py`

```python
class CurriculumAlignmentMiddleware(BaseMiddleware):
    """Verifies generated content aligns with the requested curriculum standard.

    Only runs after_model when artifacts are present and curriculum_standard
    is specified in the lesson plan. Adds alignment_score to review_results.
    """
    name = "curriculum_alignment"
    order = 23  # before ClarificationMiddleware

    async def after_model(self, state, context: MiddlewareContext) -> None:
        artifacts = state.get("artifacts")
        lesson_plan = state.get("lesson_plan", {})
        curriculum_standard = lesson_plan.get("curriculum_standard")

        if not artifacts or not curriculum_standard:
            return  # nothing to check

        # Lightweight check: verify standard code appears in objectives
        objectives = lesson_plan.get("learning_objectives", [])
        aligned = any(curriculum_standard.split(".")[0] in obj for obj in objectives)

        if not aligned:
            context.metadata["curriculum_alignment_warning"] = (
                f"Content may not align with {curriculum_standard}"
            )
```

## Tests (per tier)

```python
# packages/agents/middleware/tests/test_input_sanitization.py
def test_empty_raw_request_raises():
    mw = InputSanitizationMiddleware()
    with pytest.raises(InputValidationError):
        asyncio.run(mw.before_model({"raw_request": ""}, ctx))

def test_valid_request_passes():
    mw = InputSanitizationMiddleware()
    state = {"raw_request": "Teach fractions", "class_info": {"grade": 4, "subject": "math"}}
    asyncio.run(mw.before_model(state, ctx))  # no exception

# packages/agents/middleware/tests/test_content_safety.py
def test_inappropriate_content_blocked():
    mw = ContentSafetyMiddleware()
    with pytest.raises(ContentSafetyError):
        asyncio.run(mw.before_model(
            {"raw_request": "adult violence", "class_info": {"grade": 5}}, ctx
        ))

# packages/agents/middleware/tests/test_curriculum_alignment.py
def test_no_check_without_curriculum_standard():
    mw = CurriculumAlignmentMiddleware()
    state = {"artifacts": [{"content": "..."}], "lesson_plan": {}}
    asyncio.run(mw.after_model(state, ctx))  # no exception, no warning
```

## Acceptance Criteria

- [ ] All 24 layers implemented with their own files in the correct tier subfolder
- [ ] `registry.py` `ORDERED_MIDDLEWARE_LIST` contains all 24 layers in correct order
- [ ] `ClarificationMiddleware` is ALWAYS last (order=24, position 24 in list)
- [ ] `GuardrailMiddleware` updated with K-12 PII rules (minors' data, school context)
- [ ] `SummarizationMiddleware` completed (not partial stub)
- [ ] `SkillActivationMiddleware` loads from `packages/agents/skills/` directory
- [ ] Each new middleware has at least 3 tests (happy path, error case, no-op when not applicable)
- [ ] No single file > 300 lines

## Dependencies

- Blocked by: `agent-state-schema` (uses OhMyClassState fields)
- Blocks: `prompt-management` (SkillActivation integration)
- Can partially run in parallel with `sub-agent-compiled-graphs`
