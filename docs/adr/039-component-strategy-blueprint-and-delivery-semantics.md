# ADR-039: Component Strategy Blueprint and Delivery Semantics

## Status

**Proposed** (2026-07-05) — Define blueprint objective identity, delivery context, assessment intent, budgets, readiness, misconceptions, and teacher-facing controls for Component Strategist v1. Complements ADR-035 through ADR-038.

## Context

The Component Strategist can only produce trustworthy teaching architecture if its inputs have stable semantics. Several values that look like presentation details actually change strategy materially: objective identity and importance, assessability, delivery context, assessment intent, prerequisite readiness, class size, teacher load, artifact scope, export requirements, and misconceptions. If these remain implicit, the selector will infer inconsistently and implementation agents will encode hidden assumptions.

The product goal remains one-shot production quality: flexible and user-centric, but not a component editor or prompt-patch layer.

## Decision

1. **Planner objectives gain stable system-owned identity.** Planner may emit objective text, Bloom level, importance, assessability, and assessment intent. System normalization owns objective IDs and revisions. IDs are stable across reorder/light edits and change only when the learning target changes materially.
2. **Strategy snapshots reference blueprint/objective revisions.** A strategy is valid for a specific blueprint revision. Semantic objective changes invalidate final strategy and require recomputation; cosmetic changes can preserve strategy with recorded rationale.
3. **Objective importance is explicit when possible, inferred conservatively otherwise.** New production planner output should include `importance: core | supporting | extension` and `assessable`. Compatibility inference is deterministic and records reasons. Teachers can edit objective priority and assessability in the blueprint/strategy approval panel as typed revision feedback.
4. **Core objectives cannot be silently deferred.** Pack-level objective coverage must cover every core objective. Uncovered core objectives block final strategy with typed options. Supporting/extension deferrals are recorded; extension deferrals are visible non-blocking notes.
5. **Objective coverage is pack-complete, not artifact-identical.** The strategist owns an objective coverage matrix across lesson, worksheet, quiz, recap, and exports. Artifacts have role-specific minimums instead of every artifact covering every objective.
6. **Delivery context is explicit.** `delivery_context` is `in_class`, `homework`, `blended`, or `printable_takehome`. It can be inferred from request/artifact defaults, but low-confidence or materially important inference is teacher-visible and overrideable.
7. **Assessment intent is independent of artifact type.** `assessment_intent` is `none`, `formative`, `summative`, `exam_prep`, or `diagnostic`. Resolution precedence is slot override, objective override, artifact default, then pack default. Strategy owns scoring intent/constraints; Content Creator and exporters generate concrete answers/rubrics/format syntax.
8. **Prerequisite readiness gates strategy.** Blocking prerequisite gaps block or recommend prerequisite replan. Small scaffoldable gaps add scaffold/remediation slots, but those slots consume real time/item/space budget and may force compression or extension deferral.
9. **Budgets are global first, slot-specific second.** The strategist allocates global lesson/pack budget before slot budgets. Slot budgets include soft targets and hard caps for time, item count, reading level, cognitive load, scaffold level, print/page density, and teacher load.
10. **Teacher operational load is a strategy signal.** Class size, preparation load, facilitation load, and grading load influence scoring and feasibility. A strategy that is pedagogically strong but operationally unrealistic is not teacher-friendly.
11. **Theme is a constraint, not pedagogy.** Theme does not drive learning moves. Coarse theme/accessibility/layout capabilities can constrain density/readability where they materially affect output quality.
12. **Artifact scope is teacher-owned.** The strategist plans within requested artifacts and may emit recommendations to add/remove artifacts. It does not silently mutate artifact scope in v1.
13. **Offline safety is universal; printability is contextual.** Standalone/no-external-assets remains a hard requirement. Printability is hard or soft based on artifact/export context. Interactivity is an export projection enhancement unless interactive/H5P output is required primary output.
14. **Misconceptions are structured when possible.** Misconception refs can originate from reviewed knowledge, research signals, or class context with precedence: teacher/class known > research-confirmed > knowledge default. Teacher free-text misconceptions become run/class-scoped typed local refs after sanitization; raw text is not scored.
15. **Strategy owns intent, downstream owns wording/content.** Strategy slots include teacher-action intent, student-instruction intent/constraints, distractor coverage requirements, scoring intent, fill requirements, forbidden fill patterns, expansion policy, and allowed supporting micro-components. Content Creator writes the actual teacher script, student wording, exact distractors, answers, and rubrics.
16. **No component editor in v1.** Teacher feedback controls steer intent/style/objective priority/delivery context and select prevalidated variants. Teachers cannot force arbitrary exact component placement in v1.

## Consequences

- Strategy decisions become traceable to stable objective IDs and blueprint revisions.
- Teacher-facing controls remain simple while still affecting the actual core engine deterministically.
- Delivery/homework/assessment distinctions stop being hidden prompt interpretation.
- Budget and operational feasibility become first-class, reducing bloated or unrealistic packs.
- Content Creator receives stronger slot contracts without taking over architecture selection.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Explicit blueprint/delivery semantics (chosen) | Reproducible, teacher-friendly, testable, avoids hidden inference | Requires planner normalization and approval UI updates |
| Let strategist infer everything from raw lesson text | Fast to prototype | Unstable, hard to explain, privacy risk, prompt-patch behavior |
| Let teachers directly select exact components | Maximum manual control | Becomes component editor; can break pedagogy/export/compliance |
| Treat artifact type as assessment/delivery intent | Simple | Worksheet/quiz semantics vary too much; causes wrong strategies |
| Leave budgets to Content Creator/renderer | Easy integration | Bloated lessons and poor teacher operational fit |

## References

- ADR-035 component strategist stage
- ADR-036 component strategy knowledge and governance
- ADR-037 component strategy fallback and feedback conflicts
- ADR-038 component strategy validators and release gates
- `.scratch/component-strategist/README.md`
