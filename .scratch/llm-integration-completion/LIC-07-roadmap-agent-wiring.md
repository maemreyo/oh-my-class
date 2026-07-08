---
title: "Investigate and wire roadmap_agent's real entry point"
status: ready
labels: [llm-integration, dark-code, roadmap]
created: 2026-07-08
priority: p3
epic: llm-integration-completion
sequence: 7
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0c. Needs investigation before it can move to `ready-for-agent` — see "What to build" below.

## What to build

`packages/agents/sub_agents/roadmap_agent/nodes.py`'s `roadmap_node` generates a personalized `RoadmapContent` artifact from `DiagnosticReport` + `StudentProfile` (using `milestone_calculator`/`book_recommender` tools), has a real LLM branch, but has zero production callers (`packages/agents/llm/compiled_chat.py:15` lists it "not yet migrated").

This is **distinct** from `content_creator`'s `artifact_type="roadmap"` (`hierarchical.py:111`, a generic templated artifact from `lesson_plan`/`research_bundle`, in scope for `LIC-02`'s flip) — `roadmap_agent` is diagnosis-driven and personalized per student, not lesson-driven.

Before wiring: confirm there is (or should be) a product surface that calls this — a route, a UI entry point, or a pipeline stage after `diagnostician_node` that isn't built yet. This may be a feature that was scaffolded ahead of its UI/route, not just a wiring gap.

## Acceptance criteria

- [ ] Confirm via `common/contracts/roadmap.py` and any product docs whether a "personalized roadmap" feature is expected to exist as a user-facing surface.
- [ ] If yes: wire `roadmap_node` into the pipeline (likely after `_diagnostic_preplanning` in `teaching_pack/nodes.py`, in `diagnose_then_generate` mode) and build/confirm the missing route.
- [ ] If the feature turns out to be superseded by `content_creator`'s `roadmap` artifact type: mark `roadmap_agent` `status: superseded` per the retirement-ritual convention (`LGH-04`) instead of wiring it, and delete or archive the module.

## Blocked by

Investigation step above must resolve which of the two acceptance-criteria branches applies.
