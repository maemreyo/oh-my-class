---
title: Roadmap — macro layer (milestone→unit), implement personalization, KT-adaptive
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The roadmap agent is dormant; its documented personalization is never invoked, and there's no link between diagnosed gaps and roadmap focus. Position it as the **macro/temporal** layer (Phase 3).

- **Wire as the macro layer (ADR-017):** a roadmap run produces month-scale milestones; **each milestone composes into a topic-decomposition unit** (the deferred compose seam). Roadmap does **not** generate content directly — it orchestrates a sequence of units.
- **Divide-and-conquer (no mega-prompt):** generate **per-milestone** (focused) then assemble the roadmap.
- **Error-tolerance:** StructuredOutput/retry middleware.
- **Implement the documented personalization:** branch the prompt on `StudentProfile` traits (shy → avoid group work; film_learner → video; depth_oriented → explain why) — currently in `system.md` but never invoked. Exam-specific structure (HSA / IELTS / TOEIC differ).
- **Link diagnosed gaps → roadmap focus (the missing bridge):** milestones must **target the gaps** from the `DiagnosticReport`; focus areas derive from gaps, not generic.
- **Smart mechanism:** **re-adapt milestones as KT mastery updates** (RISE continuous-improvement); use **skill-based milestones**, not only score-based.

## Acceptance criteria

- [ ] Roadmap produces milestones; each milestone composes into a topic-decomposition unit; roadmap emits no content directly.
- [ ] Per-milestone divide-and-conquer + StructuredOutput retry.
- [ ] Prompt branches on StudentProfile traits (shy/film_learner/depth_oriented) and exam type — actually invoked, not just documented.
- [ ] Roadmap focus areas are derived from the DiagnosticReport gaps (explicit link).
- [ ] Milestones re-adapt as KT mastery updates; skill-based milestones supported.

## Detailed test suite

(Real DB + real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_roadmap_compose.py`: a milestone maps to a unit-decomposition input; roadmap output contains no raw artifact content.
- [ ] `test_roadmap_personalization.py`: shy vs depth_oriented profiles yield different roadmap prompts/structure (invoked, not ignored).
- [ ] `test_roadmap_gap_link.py`: roadmap focus areas match the DiagnosticReport gaps.
- [ ] `test_roadmap_kt_adapt.py`: a KT mastery update shifts the milestones.
- [ ] Run `uv run pytest -m real_llm packages/agents/tests/test_roadmap_*.py -v`.

## Blocked by

- .scratch/agent-upgrades/005-diagnostician-wire-and-upgrade.md
- .scratch/effectiveness-loop/004-bkt-knowledge-tracing-engine.md
