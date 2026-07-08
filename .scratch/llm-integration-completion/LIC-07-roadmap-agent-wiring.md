---
title: "Investigate and wire roadmap_agent's real entry point"
status: done
labels: [llm-integration, dark-code, roadmap]
created: 2026-07-08
priority: p3
epic: llm-integration-completion
sequence: 7
---

> **Investigated, resolved as "leave dark" (2026-07-08).** Repo-wide grep for
> `RoadmapContent`/`roadmap_node`/`roadmap_agent` across `services/gateway/` and
> `docs/` found **zero references** anywhere outside the sub-agent module and its
> own test — no route, no UI mention, no product doc expects this specific
> diagnosis-driven personalized-roadmap feature to exist. This is neither AC
> branch as originally framed: not "wire it" (nothing calls for it), and not
> literally "superseded by content_creator's roadmap" (they're conceptually
> different — diagnosis-driven vs lesson-driven — so marking it `superseded`
> would misrepresent it as replaced when it's actually just unbuilt-for). Landed
> as a third outcome: moved to `KNOWN_DARK` in `tests/test_no_dark_runtime_modules.py`
> with the investigation finding recorded, so the next person who wants this
> feature has the wiring point ready and doesn't have to re-derive "does anything
> need this" from scratch. Building a new route for a feature nothing currently
> asks for is a product decision, not something to speculatively build in a
> code-hardening pass.
>
> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0c.

## What to build

`packages/agents/sub_agents/roadmap_agent/nodes.py`'s `roadmap_node` generates a personalized `RoadmapContent` artifact from `DiagnosticReport` + `StudentProfile` (using `milestone_calculator`/`book_recommender` tools), has a real LLM branch, but has zero production callers (`packages/agents/llm/compiled_chat.py:15` lists it "not yet migrated").

This is **distinct** from `content_creator`'s `artifact_type="roadmap"` (`hierarchical.py:111`, a generic templated artifact from `lesson_plan`/`research_bundle`, in scope for `LIC-02`'s flip) — `roadmap_agent` is diagnosis-driven and personalized per student, not lesson-driven.

Before wiring: confirm there is (or should be) a product surface that calls this — a route, a UI entry point, or a pipeline stage after `diagnostician_node` that isn't built yet. This may be a feature that was scaffolded ahead of its UI/route, not just a wiring gap.

## Acceptance criteria

- [x] Confirmed via repo-wide grep (`common/contracts/roadmap.py`, `services/gateway/`, `docs/`) that no product surface expects a "personalized roadmap" feature today.
- [ ] Not applicable — nothing calls for wiring it in yet. Revisit if/when a product ask for a diagnosis-driven personalized roadmap surfaces.
- [x] Not superseded (conceptually distinct from `content_creator`'s roadmap, see done-note) — left `KNOWN_DARK` with the investigation reason recorded instead of mislabeling it `superseded`.

## Blocked by

Investigation step above must resolve which of the two acceptance-criteria branches applies.
