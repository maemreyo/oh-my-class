---
title: Mode combination rules and composite projections
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Define how methodology modes combine. The current issue set treats modes as mostly independent, but teachers can plausibly request combinations such as inverse thinking + active recall, contrastive pairs + timed quiz, or shy-student 1:1 + roleplay. Some combinations are compatible, some conflict pedagogically, and some require composite projections. Without explicit rules, UI and pipeline may accept impossible combinations.

## Acceptance criteria

- [ ] Methodology registry includes `compatible_with`, `conflicts_with`, and neutral/default behavior for every tag pair.
- [ ] Teacher mode picker disables conflicted combinations with teacher-readable rationale.
- [ ] Pipeline computes a composite projection plan listing required components and source methodology tags.
- [ ] Quality gates validate the composite plan, not only individual tags.
- [ ] Compatible combinations have deterministic precedence/order rules.
- [ ] Unknown pairings fail closed until explicitly classified.

## Detailed test suite

- [ ] Registry test: Given all pairwise tag combinations, when classified, then every pair is compatible, conflicted, or neutral; none are undefined.
- [ ] UI test: Given `shy_student_1on1` selected, when `timed_quiz` conflicts, then it is disabled with rationale.
- [ ] UI test: Given `inverse_thinking` selected, when `active_recall` is compatible, then both can be selected and combined preview metadata appears.
- [ ] Pipeline test: Given compatible tags, when building artifact generation input, then `composite_projection` lists required components from both tags.
- [ ] Quality test: Given a composite projection missing a required component from one tag, when gate runs, then it fails with source tag context.
- [ ] Regression test: Single-mode runs remain unchanged.

## Blocked by

- .scratch/inverse-thinking/020-methodology-tag-registry-and-ci-guard.md
- .scratch/inverse-thinking/002-methodology-package-and-projections.md
- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
