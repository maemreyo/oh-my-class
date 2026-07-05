# ADR-038: Component Strategy Validators and Release Gates

## Status

**Proposed** (2026-07-05) — Define validator composition, lineage validation, golden scenarios, rendered-output checks, and release gates for Component Strategist v1. Complements ADR-035 through ADR-037.

## Context

The Component Strategist makes a promise before content generation: selected learning moves, components, audiences, budgets, objective coverage, and export projections will survive generation and rendering. Existing quality gates check schema, content, HTML, judge output, teacher approval, and export readiness, but component strategy needs an additional contract: generated artifacts must preserve the approved pedagogical architecture.

A single generic validator cannot know what makes a misconception probe, worked example, retrieval check, or MOET true/false item pedagogically valid. Conversely, per-move validators alone would duplicate baseline checks such as slot lineage, audience separation, and budget caps.

## Decision

1. **Use a two-layer validation model.** Generic slot validation proves the artifact followed the approved architecture: slot IDs, component types, objective refs, audience policy, budgets, export constraints, and lineage markers. Learning-move/component validators prove pedagogy-specific requirements such as misconception-mapped distractors, worked-example steps, retrieval affordances, or MOET scoring validity.
2. **Declarative validators first, plugin validators when needed.** Common checks live in reviewed YAML policies. Complex structural checks use code validators registered through plugin registries keyed by learning move or component type. No central `if/elif` chain owns validator dispatch.
3. **Every production learning move has a fill-validation policy.** Even simple moves require at least declarative validation. Missing required validator policy for production-selectable entries fails knowledge validation. Draft entries may skip only in explicit non-production mode.
4. **Validator composition is deterministic.** Validators declare category, severity, priority, version, and output codes. Hard failures stop progression at the relevant gate. Soft warnings accumulate. Same-priority validators run in deterministic registry order.
5. **Validator outputs are typed.** Validators return structured issues with code, severity, slot ID, learning move ID, component type, teacher-facing summary, audit detail, and optional repair recommendation. Teacher UI renders concise messages; debug ledgers retain structured details.
6. **Strategy lineage is required through generation/rendering.** Every generated component traces to either a strategy slot or an allowed supporting micro-component under a parent slot. Slot IDs are deterministic and stable for unchanged pedagogical semantics across revisions. Artifacts store lineage in JSON metadata and safe opaque HTML `data-*` markers where appropriate.
7. **Micro-components inherit lineage.** Supporting components such as hints or vocabulary notes are allowed only through slot-scoped expansion policy with explicit component allowlists and budgets. They carry their own component IDs plus `parent_slot_id` and support role.
8. **Rendered HTML validation is part of release proof.** Strategy golden tests stop at plan JSON; render integration tests prove selected components survive fill/render, standalone HTML invariants hold, safe lineage markers exist, and teacher-only data does not leak. End-to-end tests cover request through final strategy, approval UI, content fill, render, and export.
9. **Golden scenarios assert pedagogical promises, not brittle snapshots.** Golden tests check objective coverage, expected move families, no unsupported components, fallback reasons, quality thresholds, and focused baseline improvements. They do not require an entire 900-line plan JSON to match exactly.
10. **Baseline comparison uses frozen fixtures.** Release gates compare new strategist behavior against frozen old-path baseline metrics, not live execution of the old prompt/prose path. Baselines are migration artifacts and can be archived/minimized after the old path is deleted.
11. **Release gate includes operational checks.** CS v1 is not releasable until functional tests, rendered-output tests, UI visual QA, latency budgets, rollback path, feature-flag behavior, and reviewer gate pass. Knowledge updates require rebuild/redeploy in v1; no hot reload.

## Consequences

- Content Creator cannot satisfy a strategy by merely producing valid-looking prose.
- New learning moves/components need explicit validation policy before production selection.
- Validation remains modular and extensible without central dispatch chains.
- QA can trace rendered output back to strategy slots without exposing score ledgers or teacher-only data.
- Release evidence proves the new system is better than the baseline and safe to roll out.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Generic slot validator + move/component plugin validators (chosen) | Balances shared architecture checks with pedagogy-specific validation | Requires registry and validator-version discipline |
| One generic validator only | Simple | Cannot verify learning-move promises like misconception probes |
| Code validators for everything | Expressive | Harder to author/review; requires code changes for simple policy tweaks |
| YAML validators for everything | Data-driven | Complex structural checks become unreadable or underpowered |
| Full-plan golden snapshots | Easy to diff | Brittle; blocks valid scoring/ordering improvements |
| Live old-path baseline comparison | Always current | Keeps legacy path alive and makes tests slower/flakier |

## References

- ADR-031 full output test matrix
- ADR-032 verification integrity and engineering discipline
- ADR-035 component strategist stage
- ADR-036 component strategy knowledge and governance
- ADR-037 component strategy fallback and feedback conflicts
- `docs/testbook/runbook.md`
- `.scratch/component-strategist/README.md`
