---
title: Wire safety/quality middleware into the deterministic pipeline
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Today the 30-entry `ORDERED_MIDDLEWARE_LIST` is wired into **nothing** (the Lead Agent's `create_react_agent` gets no middleware; the teaching-pack stages call sub-agents directly). So safety/quality guards do not run on the generation path. Wire the relevant subset by **attachment point** (not "wrap all 30 around every agent").

**Call-level middleware runner** in `llm_client` (issue 001): a thin `(messages-in → guards → LLM → guards → output)` pipeline — distinct from `BaseMiddleware.before_model/after_model` which operate on full agent state.

Attach by group:
- **G1 run-entry (once, at `setup_contract`)**: InputSanitization, Uploads, ThreadData, Title, Memory, TokenBudget(init).
- **G2 per-LLM-call (runner, every agent)**: ContentSafety(in+out), Guardrail(out), SafetyFinishReason, LLMErrorHandling, TokenUsage, TokenBudget(check), SystemMessageCoalescing **+ 4 new**: `StructuredOutput` (JSON validity + bounded repair — DRY the per-agent retry), `PiiOutputGuard` (scrub/flag PII in output), `LocaleEnforcement` (output language == contract locale), `Tracing/CostTag` (guarantee INVARIANT-07 + Langfuse trace per call).
- **G3 generation-context (planner, content_creator only)**: DynamicContext, SkillActivation.
- **G4 post-artifact quality**: CurriculumAlignment, ReadabilityLevel, PedagogicalQuality, BiasDetection, ArtifactCoherence, LearningObjectiveAlignment → **consolidated into the 6-layer quality gate** (`runtime-parity/001`), NOT run per-call (avoid double-run / dual source of truth).
- **G5 gate-layer**: TeacherAuditLog (gate resume), Clarification (clarification gate).
- **G6 ReAct-only (parked, retained)**: DanglingToolCall, ToolErrorHandling, LoopDetection, SubagentLimit, DeferredToolFilter, Summarization, TodoList, ViewImage — keep the code, **mark `parked` (not wired)** with a note for a future conversational/tool-using use case.

## Acceptance criteria

- [ ] A call-level middleware runner exists in `llm_client` and wraps every sub-agent LLM call with the G2 set.
- [ ] G1 runs once at run entry; G3 enriches only planner/content_creator; G5 at the gate layer.
- [ ] The 4 new middleware (StructuredOutput, PiiOutputGuard, LocaleEnforcement, Tracing/CostTag) exist and run in G2.
- [ ] G4 quality middleware are consolidated into the quality gate (not per-call); no double-run.
- [ ] G6 middleware are retained but explicitly marked `parked`/not-wired with a documented future use case.
- [ ] Per-agent ad-hoc JSON retry is replaced by `StructuredOutput` (DRY).

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_call_middleware_runner.py`: a malicious/unsafe input is blocked by ContentSafety; PII in output is scrubbed/flagged; non-locale output is caught; every call is traced + tagged.
- [ ] `packages/agents/tests/test_structured_output_mw.py`: a malformed JSON response triggers bounded repair; persistent failure fails closed (replacing per-agent retry).
- [ ] `packages/agents/tests/test_g3_context.py`: planner/content_creator receive DynamicContext + SkillActivation; researcher/reviewer do not.
- [ ] `packages/agents/tests/test_g6_parked.py`: G6 middleware are present but not in the active runner; a lint asserts they are marked parked.
- [ ] Run `uv run pytest packages/agents/tests/test_call_middleware_runner.py packages/agents/tests/test_structured_output_mw.py -v`.

## Blocked by

- .scratch/technical-debt/001-llm-client-consolidation.md
