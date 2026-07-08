# ADR-048: Planner Blueprint Generation Remains Deterministic-by-Design

## Status

**Accepted** (2026-07-08) — produced from the `.scratch/design-reflection-2026-07-08.md` 100-question grill session auditing which "AI teaching-pack generator" sub-agents actually call an LLM in production.

## Context

`packages/agents/sub_agents/planner/nodes.py:34-41` contains a real, tested LLM branch (`nodes.py:50-106`, G-Eval-style prompt via `AgentRuntime`) and a seed-expansion branch (`expand_lesson_plan_from_seed`), but production (`packages/agents/teaching_pack/nodes.py:327`) hard-codes `"use_staged_planner": True` with no code path that ever sets it `False`. Both alternate branches are permanently dead in production. `staged_engine.build_staged_lesson_plan` generates the lesson blueprint (topics, Gagné-event structure, objectives, knowledge components) via pure string templating (`_gagne_plan`, `_verb_for`).

Read in isolation, this looks like the same "real code shadowed by a stale flag" pattern found across `content_creator`, `reviewer`, and `diagnostician` in the same audit. Planner is different: `ensure_seed_alignment`/`PlannerDriftError` (`nodes.py:145-157`) exist specifically to guarantee the blueprint stays consistent with an upstream `unit_planner` seed when one exists — a guarantee an LLM call would not automatically preserve. The blueprint stage also implements Gagné's Nine Events / backward design (UbD), a standardized instructional-design methodology where consistency has more product value than per-request creative variation.

## Decision

1. **Lesson blueprint generation stays deterministic** via `staged_engine.build_staged_lesson_plan`. This is a deliberate choice, not unfinished work: personalization belongs downstream in `content_creator` (see ADR context in `.scratch/llm-integration-completion/LIC-02-content-creator-real-llm.md`), not in the structural blueprint stage.
2. **The real LLM branch is kept as a fallback, not dead code**, gated by an actual condition instead of an unreachable literal: `use_staged_planner` becomes `seed_exists_for(raw_request)` (or equivalent coverage check) rather than a hard-coded `True`. When a teacher's `raw_request` doesn't match any unit/seed the staged engine has a template for, the pipeline falls through to the real LLM branch instead of producing a poor-fit template. See `.scratch/llm-integration-completion/LIC-04-planner-fallback-condition.md` for the implementation task.
3. **`expand_lesson_plan_from_seed`** remains the path used when a `unit_planner`-produced seed is present, preserving `ensure_seed_alignment`'s drift guarantees.

## Consequences

- A future reader of `nodes.py` sees a real, reachable condition instead of a literal `True` — the "is this deliberate or stale" ambiguity this ADR exists to resolve does not recur here.
- Personalization work for teaching content lands in `content_creator`, not by reopening this stage.
- If `staged_engine`'s template coverage turns out to be too narrow in practice (i.e., the LLM fallback fires often), that is a signal to revisit this ADR — it is not a silent failure, because the fallback path is real and observable.
