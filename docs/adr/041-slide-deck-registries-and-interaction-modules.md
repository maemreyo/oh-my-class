# ADR-041: Slide Deck Registries and Interaction Modules

## Status

**Proposed** (2026-07-06) — Defines how slide layouts, blocks, interactions, media, and themes are modeled so `slide_deck` can support broad classroom presentation use cases without arbitrary HTML.

## Context

The `slide_deck` artifact needs to cover more than a small MVP of static pages. Teachers need hooks, explanations, examples, discussion prompts, checks for understanding, media, reveal steps, timers, polls, exit tickets, and teacher facilitation notes. At the same time, the project has hard invariants: typed output, standalone HTML, no answer-key leakage, no external assets in the default path, and renderable templates rather than raw HTML from LLMs.

A naive implementation would either provide too few layouts or allow arbitrary HTML/CSS/JS. Both paths are risky: too few layouts under-deliver; arbitrary rendering breaks validation, accessibility, compliance, and tests.

## Decision

1. **Full slide support is registry-based, not arbitrary HTML.** The production design supports broad layout/block/interaction coverage through typed registries and module declarations.
2. **`LayoutRegistry` owns layout capability.** Initial production layout vocabulary includes, at minimum: `cover`, `agenda`, `objective`, `hook`, `concept`, `definition`, `comparison`, `timeline`, `process`, `diagram`, `worked_example`, `guided_practice`, `independent_practice`, `discussion`, `poll`, `quiz_check`, `reflection`, `summary`, `exit_ticket`, `homework`, and `appendix`. Each layout declares supported blocks, density budget, surfaces, print behavior, and accessibility requirements.
3. **`SlideBlockRegistry` owns renderable content blocks.** Blocks are typed and include text, heading, bullet list, media, table, callout, question, inline SVG/diagram, chart/stat grid, timeline, process steps, source callouts, and interaction slots. Blocks may carry stable IDs, source refs, reveal step metadata, and teacher-only flags.
4. **`SlideInteractionRegistry` owns interactive modules.** Interactions are typed modules, not ad hoc template branches. Initial production modules include `reveal`, `poll_prompt`, `quick_check`, `timer`, `discussion_prompt`, `exit_ticket`, and `think_pair_share`. More complex modules such as drag-match can be added later only as registered modules with tests.
5. **Interactive modules are offline-first and non-persistent in v1.** They may enhance classroom use through local client-side behavior, but they do not store student responses, require auth, or write backend state. If scoring requires a correct answer, that answer remains teacher-only and is not serialized into student-facing DOM.
6. **Reveal/progression is typed and has a no-JS fallback.** A slide or block may declare reveal steps. Presentation mode can reveal progressively, while print/export/no-JS mode remains understandable and complete.
7. **Media policy is two-tier.** Default export uses packaged/offline assets: inline SVG, data URI, or exported local assets. Online embeds are optional, explicitly flagged as `requires_network`, teacher-visible, and must provide fallback thumbnail/transcript/instructions. External media never silently enters the default offline export.
8. **Theme remains centralized.** `theme.json` remains the source of truth. Slide-specific component tokens may be added, but no separate slide theme system is introduced.
9. **Accessibility is a module contract.** Layouts, blocks, and interactions declare required alt text, heading semantics, focus behavior, reduced-motion behavior, color contrast requirements, and print fallback.
10. **Registries are the engine's extension seams.** New slide capability is added by registering a module with schema, renderer adapter, policy, accessibility contract, tests, and fallback behavior.

## Consequences

- The system can support a wide range of classroom slide experiences without letting LLM output bypass contracts and gates.
- Adding a new layout or interaction becomes localized and testable.
- The renderer, quality gates, and teacher preview can reason about capabilities from module metadata instead of template heuristics.
- Initial implementation must invest in registry interfaces and fixtures before broad module coverage pays off.
- Online media remains possible for teacher UX, but offline/standalone exports remain safe by default.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Typed registries for layout/block/interaction (chosen) | Flexible, modular, testable, safe | More upfront design and fixture work |
| Small hard-coded MVP layout set | Fast and reliable | Under-delivers on requested full slide support and quickly becomes patchy |
| Arbitrary HTML/CSS/JS emitted by LLM | Maximum flexibility | Violates typed contracts, sanitizer expectations, accessibility, and answer-key safety |
| Reuse only generic `ContentComponent` registry | Reuses existing contracts | Slide-specific density, reveal, teacher notes, and layout semantics would pollute shared components |
| Build separate slide theme system | High visual control | Breaks theme source-of-truth invariant and app consistency |

## References

- ADR-025 Renderer Artifact-Kind Plugin Registry Rewrite
- ADR-039 Component Strategy Blueprint and Delivery Semantics
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- `common/contracts/components/registry.py`
- `common/branding/kits/*/theme.json`
- `packages/renderer/templates/`
