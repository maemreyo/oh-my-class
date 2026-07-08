---
title: "Planner: replace hard-coded use_staged_planner=True with a real coverage condition"
status: done
labels: [llm-integration, planner]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 4
---

> **Done (2026-07-08).** `has_curriculum_coverage(state)` (new, in `staged_engine.py`)
> reuses `retrieve_grounding` (the same grounding lookup `staged_engine` itself already
> calls) — routes to staged when `grounding_status != "ungrounded"`, to the real LLM
> branch otherwise. `teaching_pack/nodes.py`'s planner call site now computes this
> instead of hard-coding `True`.
>
> **Real bug found and fixed along the way**: `_class_profile`'s `isinstance(persona, dict)`
> check treats an explicitly-empty `persona_snapshot={}` the same as "persona provided" —
> and `teaching_pack/nodes.py` always sends `persona_snapshot={}` when no real persona
> exists (via `_json_object(...)` defaulting to `{}`). This means `ClassProfile.model_validate({})`
> silently backfills `grade="Unknown"`/`subject_focus="general"`/`language="en"` (via
> `map_legacy_class_info`'s defaults) *for every run without a real persona* — the real
> `class_info` (grade/subject/language the teacher actually specified) was being silently
> discarded in favor of these generic defaults, in the **existing, already-shipped**
> `staged_engine.build_staged_lesson_plan` path, not just in this new function. Did not
> fix `_class_profile` itself here (that's a separate, wider-blast-radius fix — flagged
> below) — instead, `has_curriculum_coverage` deliberately bypasses `_class_profile`
> entirely and builds the profile straight from `class_info` via `class_profile_from_class_info`,
> so the coverage check is correct regardless of that latent bug.

> Companion implementation task for ADR-048. Independent of `LIC-01`/`LIC-02`/`LIC-03`.

## What to build

`packages/agents/teaching_pack/nodes.py:327` hard-codes `"use_staged_planner": True`, permanently disabling `planner_node`'s real LLM branch and its `expand_lesson_plan_from_seed` branch (`packages/agents/sub_agents/planner/nodes.py:34-48`). Per ADR-048, replace the literal with a real coverage check: `"use_staged_planner": seed_exists_for(raw_request)` (name TBD), so the LLM fallback is reachable when the staged engine has no matching template.

## Acceptance criteria

- [x] A real function determines whether `staged_engine` can produce a lesson plan for the given `raw_request`/`class_info` — `has_curriculum_coverage`, reusing `retrieve_grounding`.
- [x] When coverage is missing, `planner_node` runs its real LLM branch (`nodes.py:50-106`) instead of `staged_engine` (verified: `use_staged_planner` is now a real computed bool, not a literal).
- [x] `ensure_seed_alignment`/`PlannerDriftError` still apply when a seed is present, regardless of which branch generated the plan — untouched, `planner_node`'s branching order is unchanged.
- [x] Added `test_has_curriculum_coverage_true_for_parseable_grade` / `test_has_curriculum_coverage_false_for_unparseable_grade` to `test_planner_staged.py` — the fallback condition is now directly testable (was impossible when it was a literal).
- [x] Full `packages/agents/tests/` sweep: same 13 pre-existing failures as baseline, zero new ones.

**Follow-up filed, not fixed here** (found while implementing, real but separate bug, wider blast radius than this issue): `_class_profile`'s empty-`persona_snapshot` handling silently discards real `class_info` in the already-shipped staged path — see `.scratch/llm-integration-completion/LIC-10-class-profile-empty-persona-bug.md`.

## Blocked by

Nothing.
