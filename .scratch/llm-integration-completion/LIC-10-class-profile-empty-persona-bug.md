---
title: "_class_profile silently discards real class_info when persona_snapshot={}"
status: ready
labels: [bug, planner, correctness]
created: 2026-07-08
priority: p1
epic: llm-integration-completion
sequence: 10
---

> Found while implementing `LIC-04` (planner fallback condition). Not fixed there — this bug's blast radius is wider (the already-shipped `staged_engine` path, not just the new coverage check), so it needs its own scoped fix and test pass rather than a quiet change bundled into LIC-04.

## What's broken

`packages/agents/sub_agents/planner/staged_engine.py`'s `_class_profile`:

```python
def _class_profile(state: PlannerNodeState) -> ClassProfile:
    persona = state.get("persona_snapshot")
    if isinstance(persona, dict):
        return ClassProfile.model_validate(persona)
    return class_profile_from_class_info(dict(state.get("class_info", {})))
```

`isinstance(persona, dict)` is `True` for an **empty** dict `{}`, not just a real persona. `packages/agents/teaching_pack/nodes.py`'s planner call site always sets `"persona_snapshot": _json_object(state.get("persona_snapshot"))`, which defaults to `{}` whenever no real persona exists (the common case — most runs have no stored persona). So `_class_profile` takes the `ClassProfile.model_validate({})` branch essentially always, not the `class_info`-based branch.

`ClassProfile`'s `map_legacy_class_info` validator backfills missing fields when given `{}`: `grade` → `"Unknown"`, `subject_focus` → `"general"`, `language` → `"en"` (from a missing `locale`). The result: **the real `class_info` the teacher/system actually specified (grade, subject, language) is silently replaced by these generic defaults** in `staged_engine.build_staged_lesson_plan` — for every run without a real, non-empty persona snapshot. This has presumably been true since `staged_engine` shipped, independent of this session's LLM-integration work.

Confirmed via direct reproduction: `has_curriculum_coverage({"class_info": {"grade_band": "Grade 5", "subject": "math", "language": "vi", ...}, "persona_snapshot": {}})`-shaped state produces a `ClassProfile` with `grade="Unknown"`/`subject_focus="general"`/`language="en"` instead of the real values, purely because `persona_snapshot` is present-but-empty rather than absent.

## What to build

Fix `_class_profile` to treat an empty dict the same as absent:

```python
def _class_profile(state: PlannerNodeState) -> ClassProfile:
    persona = state.get("persona_snapshot")
    if persona:  # truthy check — {} falls through to class_info, same as missing
        return ClassProfile.model_validate(persona)
    return class_profile_from_class_info(dict(state.get("class_info", {})))
```

## Acceptance criteria

- [ ] `_class_profile({"persona_snapshot": {}, "class_info": {...real values...}})` returns a `ClassProfile` built from `class_info`, not defaults.
- [ ] A real (non-empty) `persona_snapshot` still takes precedence over `class_info`, unchanged.
- [ ] Audit `staged_engine.py`'s existing tests and any snapshot/golden fixtures for lesson plans generated under this bug — some may have been asserting on the buggy "Unknown grade / general subject" output and need updating to reflect the corrected grade/subject once this lands.
- [ ] Full `packages/agents/tests/` suite passes (or failures are triaged as pre-existing/unrelated).

## Blocked by

Nothing technically. Recommend landing with careful test review since this changes real output for any run without a persona snapshot — worth confirming with whoever owns `staged_engine`/persona features that no downstream code depends on the "Unknown" placeholder behavior.
