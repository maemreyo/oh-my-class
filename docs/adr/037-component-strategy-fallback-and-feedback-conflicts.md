# ADR-037: Component Strategy Fallback and Feedback Conflicts

## Status

**Proposed** (2026-07-05) — Define fallback topology, teacher feedback conflicts, strategy revisions, and recovery behavior for the Component Strategist. Complements ADR-035 and ADR-036.

## Context

The Component Strategist must produce reliable teaching architecture even when ideal component paths are unavailable, research signals are incomplete, export constraints are narrow, or teacher feedback conflicts with validity. A naive fallback can silently collapse rich pedagogy into prose. A naive teacher-feedback loop can let preferences override objective coverage, renderability, or compliance. Both would recreate the current prompt-driven failure mode under a more complex name.

Fallback therefore needs to be explicit, reviewed, testable, and visible when it changes what the teacher will experience.

## Decision

1. **Fallback graph is reviewed knowledge, not an ad hoc code path.** Production fallback paths are authored in YAML as an explicit directed fallback graph between component bindings/learning moves. Affordance similarity may assist authoring, validation, and gap reporting, but runtime does not invent production fallback paths by nearest-neighbor guess.
2. **Fallback preserves pedagogical intent first.** Fallback ranking prioritizes core objective coverage, learning move intent, audience/export constraints, approved budget, strategy quality, and only then implementation simplicity.
3. **Every production-selectable binding declares fallback policy.** `fallback_policy` is `required`, `terminal_safe`, or `no_fallback_allowed`. Missing required fallback fails knowledge validation. `no_fallback_allowed` is permitted only for rare compliance, mandated format, or pedagogy cases where substitution would misrepresent the strategy; it must carry reason, severity, teacher message, and blocking options.
4. **`evidence_balanced_basic` is fallback-only.** It is an explicit strategy family/profile with tests and thresholds, but it is not shown as a normal selectable variant. When active, it appears as a fallback note explaining why the richer strategy path was not available.
5. **Fallback is not silent scope/profile mutation.** Pre-approval healing may repair implementation paths inside the selected/default profile: replace a component by explicit fallback, add scaffold within budget, relax implicit old preferences, or use conservative risk defaults. It may not silently switch to another strategy profile, drop a core objective, remove a required export, or change delivery context.
6. **Content-fill failure uses a repair ladder.** First retry the same selected slot/component with improved fill guidance, then optionally escalate generation, then use an explicit fallback component for the same move, then replace the move within the same objective/phase, then recompute the affected projection or whole pack only when global coherence breaks.
7. **Teacher feedback is influence, not command.** `prefer_component_family` applies capped score influence. `reject_component_family` can exclude a family only when a valid strategy remains. If explicit teacher feedback would eliminate all valid paths, the engine returns a typed conflict instead of forcing invalid output.
8. **Explicit conflicts are teacher-visible.** Implicit/default preference conflicts can be auto-relaxed with audit warning. Current-session explicit feedback conflicts must be shown with engine-authored typed options such as keep recommended, relax rejection, remove optional export, switch variant, increase duration, or downgrade objective.
9. **Materiality is engine-owned.** The strategy engine classifies whether a fallback or revision is a material teacher-visible change. Reapproval is required for learning move changes, material component family changes, objective coverage changes, budget changes outside approved range, export availability changes, or audience-policy changes. Internal retries and wording-only repairs do not require teacher reapproval.
10. **Revisions are append-only after approval.** Pre-approval healing is recorded in the initial snapshot. After teacher approval, material strategy changes create append-only revisions with parent lineage, preserved decisions, changed slots, trigger, and reapproval reason.
11. **Artifact scope is advisory, not silently mutated.** The strategist plans within requested artifact types. It may emit recommendations to add/remove artifacts, but v1 shows those as lightweight suggestions and does not add a new one-click artifact-scope mutation flow unless the existing blueprint UI already safely supports it.

## Consequences

- Fallback behavior is reproducible, testable, and explainable.
- Teacher trust is preserved because explicit feedback is never silently ignored.
- Content generation can recover from fill failures without immediately changing approved pedagogy.
- Knowledge authoring has more validation burden, but runtime no longer improvises unsafe substitutes.
- Some requests will block rather than produce degraded output when no honest fallback exists.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Explicit reviewed fallback graph (chosen) | Auditable; testable; preserves pedagogy; supports explainable conflicts | Requires authoring and validation work |
| Infer fallback by affordance similarity | Flexible; low authoring cost | Can choose plausible but pedagogically wrong substitutes |
| Always fall back to prose/basic components | Easy to implement | Recreates current prose-heavy failure mode and hides degradation |
| Treat teacher feedback as hard command | Feels user-controlled | Can break objective coverage, compliance, exportability, and sequence coherence |
| Silently relax all feedback conflicts | Smooth UX | Breaks trust when teacher choices appear ignored |

## References

- ADR-035 component strategist stage
- ADR-036 component strategy knowledge and governance
- ADR-038 component strategy validators and release gates
- `.scratch/component-strategist/README.md`
