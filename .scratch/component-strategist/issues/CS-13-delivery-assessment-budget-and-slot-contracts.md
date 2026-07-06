---
title: Add delivery, assessment, budget, and slot-fill contracts
status: completed
labels: [component-strategist, contracts, content-creator, testing]
created: 2026-07-05
---

## Parent

ADR-039.

## What to build

Extend Component Strategist contracts and core behavior with explicit delivery context, assessment intent, prerequisite readiness, global/slot budgets, teacher operational load, misconception targeting, and slot-fill constraints. The strategy should decide instructional intent and constraints; Content Creator should write concrete content inside those constraints.

This issue ensures the strategy is adapted to actual classroom use, not just a list of renderable components.

## Acceptance criteria

- [x] `ComponentStrategyRequest` and plan contracts include `delivery_context: in_class | homework | blended | printable_takehome`, with inference metadata and teacher override support for ambiguous/material cases.
- [x] `assessment_intent: none | formative | summative | exam_prep | diagnostic` exists independently of artifact type, with precedence: slot override > objective override > artifact default > pack default.
- [x] Strategy slots declare scoring intent/constraints: auto-gradable vs teacher-graded vs discussion-only vs self-check, partial credit allowed, rationale required, and feedback level.
- [x] Prerequisite readiness distinguishes met, missing_scaffoldable, and missing_blocking; scaffoldable gaps add budget-consuming scaffold slots while blocking gaps return typed prerequisite issue/replan options.
- [x] Global budget allocation precedes per-slot budgets; slot budgets include soft targets and hard caps for time, item count, reading level, cognitive load, scaffold level, print/page density, and teacher load.
- [x] Class size, teacher prep load, facilitation load, and grading load influence scoring/feasibility without overriding hard filters.
- [x] Theme contributes only coarse accessibility/layout constraints; it does not drive pedagogy or component preference.
- [x] Artifact scope recommendations are typed and teacher-visible when useful, but the strategist does not silently add/remove requested artifact types.
- [x] Offline/no-external-assets is always a hard requirement; printability and interactivity are handled as export/artifact-specific constraints.
- [x] Misconception targeting supports reviewed refs, research refs, and class/run-scoped local refs from sanitized teacher notes with explicit source/confidence/precedence.
- [x] Misconception-probe slots include required distractor coverage mappings and teacher-only rationale requirements; strategy does not generate exact distractor text.
- [x] Strategy slots include teacher-action intent, student-instruction intent/constraints, fill requirements, forbidden fill patterns, expansion policy, and allowed supporting micro-components.
- [x] Supporting micro-components trace to parent slots with inherited strategy lineage and remain inside explicit expansion budgets.
- [x] Tests cover homework vs in-class selection, formative vs summative quiz intent, prerequisite scaffold budget consumption, large-class teacher-load scoring, misconception-probe distractor requirements, artifact recommendation visibility, and supporting micro-component lineage.

## Completion notes

- Added delivery, assessment/scoring, budget/load, misconception target, artifact recommendation, and slot expansion contract types.
- Wired selector defaults for homework/self-check, summative quiz auto-grading, scaffoldable/blocking prerequisites, teacher-load score audit, artifact recommendations, and distractor-mapping fill constraints.
- Preserved supporting micro-component parent slot lineage in Content Creator output.
- Split enum, coverage, privacy, slot policy, and strategy lineage helpers to keep touched Python modules under the file-size ceiling.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-03 selector, scorer, and diversity core.
- CS-05 Content Creator fills selected components.

## References

- `docs/adr/039-component-strategy-blueprint-and-delivery-semantics.md`
- `docs/adr/035-component-strategist-stage.md`
- `docs/adr/038-component-strategy-validators-and-release-gates.md`
- `common/contracts/artifact.py`
- `common/contracts/components/__init__.py`
- `packages/agents/sub_agents/content_creator/nodes.py`
- `packages/agents/sub_agents/content_creator/prompt_contract.py`
- `.scratch/component-strategist/issues/CS-05-content-creator-fills-selected-components.md`
- `.scratch/component-strategist/issues/CS-06-strategy-quality-gates-and-observability.md`

## Implementation notes

- Strategy owns intent and constraints; Content Creator owns final wording, exact distractors, answers, rubrics, and teacher scripts.
- Do not allow arbitrary direct component placement from teacher controls in v1.
- There are no free instructional moves: remediation/scaffold slots consume budget.
