---
title: Scoped repair loop + content update mechanism + teacher editor
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

The closure across reviewer → content fix → teacher (cross-agent). Today repair is coarse (whole-artifact-type regen). Make it scoped, issue-class-driven, transparent, and immutable-versioned.

- **Issue-precise routing:** an evidence-cited reviewer issue maps to `(artifact, section, component)` + failure-class → a **scoped repair** (regenerate just that section via the hierarchical content_creator, with the critique injected as a constraint), not a blind whole-artifact regen. Upgrade `quality_routing` from coarse to issue-precise.
- **Strategy by failure-class** (reuse `QualityFailureClass → HealingStrategy`, scoped): schema→re-emit; factual(∉verified)→re-ground (researcher) or caveat/remove; pedagogical/objective-misalignment→replan-scoped (planner); presentation→renderer-fix; methodology-missing-component→inject required component.
- **Bounded loop + local re-review:** repair → re-review **only the repaired part** (not the whole pack) → bounded N → escalate residual to the teacher with the specific issue.
- **Content update = immutable + versioned:** every change (agent repair OR teacher edit) creates a **new snapshot version** (content_hash, lineage) — never in-place mutation; the run state is updated by merge (replace the changed section).
- **Transparency:** every update emits a RunEvent → SSE with a **diff/changelog** (what changed + why = the reviewer critique); the teacher sees the diff vs the prior version at the content gate before final approval.
- **Edit tooling:** a **teacher structured section/component editor** at the content gate (generalize `inverse-thinking-editor`) → produces a new version. Agents do NOT get a general edit tool — agent "edits" are scoped section-regeneration only.
- **Authority (Plot-Ark 3-layer):** low-risk (schema/format) auto-applies (teacher sees diff); substantive (pedagogy/factual) is teacher-suggested / shown at the gate; never silently change content the teacher already approved.
- **Cross-run learning:** recurring issue types feed the component-effectiveness / prompt priors.

## Acceptance criteria

- [ ] Repair is scoped to `(artifact, section, component)` + failure-class with the critique injected; whole-artifact blind regen is removed.
- [ ] Each failure-class routes to the correct scoped strategy (re-emit / re-ground / replan-scoped / presentation-fix / inject-component).
- [ ] Repair re-reviews only the repaired part, bounded, then escalates residual to the teacher.
- [ ] Every content change is a new immutable snapshot version with lineage; no in-place mutation.
- [ ] Every update emits an event + a teacher-visible diff/changelog; the teacher sees diffs before final approval.
- [ ] A teacher section/component editor exists at the content gate; agents have no general edit tool (scoped-regen only).
- [ ] Authority tiers: low-risk auto-apply (with diff), substantive teacher-gated; approved content is never silently changed.

## Detailed test suite

(Real DB + real LLM via 9router `:20228`/`4omc`.)

- [ ] `services/gateway/tests/test_scoped_repair.py`: a reviewer issue on section 3 regenerates only section 3 (critique injected); other sections unchanged; a new snapshot version is created with lineage.
- [ ] `test_repair_strategy_routing.py`: each failure-class routes to its scoped strategy; bounded loop escalates residual.
- [ ] `test_content_update_transparency.py`: an update emits an event + diff; an approved artifact is not silently changed by an auto-repair.
- [ ] `apps/web/tests/section-editor.test.tsx`: the teacher editor edits a section → new version.
- [ ] Run `uv run pytest -m real_llm services/gateway/tests/test_scoped_repair.py services/gateway/tests/test_repair_strategy_routing.py -v` + `pnpm -F web test`.

## Blocked by

- .scratch/agent-upgrades/003-content-creator-hierarchical-resilient.md
- .scratch/agent-upgrades/004-reviewer-revive-and-quality.md
