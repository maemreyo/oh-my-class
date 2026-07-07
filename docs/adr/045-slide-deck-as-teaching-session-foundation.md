# ADR-045: Slide Deck as Teaching Session Foundation

## Status

**Proposed** (2026-07-07) — Establishes slide deck as the future foundation for live teaching and learning sessions while preserving the current production scope: standalone/exportable slide decks with no student-response persistence in the v1 hardening pass.

## Context

ADR-040 defines `slide_deck` as a native artifact and ADR-042 defines its surfaces, quality gates, and release evidence. ADR-043 and ADR-044 harden display preferences, print behavior, projection boundaries, and real-LLM acceptance evidence.

The next product question is whether slide decks remain static HTML artifacts or become the core surface for classroom teaching and student learning. Teachers use slides not only as visuals, but as pacing guides, quick-check prompts, guided practice anchors, vocabulary scaffolds, exit tickets, and post-lesson reflection material. Students may eventually need a companion experience that is readable on mobile and connected to the teacher's current slide or activity.

This ADR records the platform direction without expanding the immediate hardening scope into a full live-session product. The system should avoid decisions that would block future teaching sessions, response collection, analytics, annotations, remix, or related-artifact orchestration.

## Decision

1. **Slide deck is a static artifact now and a teaching-session-ready foundation.** V1 remains standalone/exportable HTML with no persistent student responses, but its content model, IDs, interactions, and projections must not block a future `TeachingSession` runtime.
2. **Teaching sessions bind to immutable deck snapshots.** A future session should reference `deck_id`, `snapshot_id`, slide IDs, block IDs, and interaction IDs. Live state, annotations, responses, and pacing data are overlays; they do not mutate generated deck content.
3. **Interactions are collectable-ready but local-only in v1.** Slide interactions must have stable IDs, typed interaction kinds, prompts, answer-bearing flags, no-JS fallbacks, accessibility labels, and teacher-only guidance. V1 standalone/student exports do not persist student responses.
4. **Planned pacing belongs in the deck foundation.** Slides/activities should support planned duration metadata so teacher preview can show total pacing and future sessions can compare planned vs actual time.
5. **Pedagogical role is distinct from visual layout.** Slides and key blocks should support typed pedagogical roles such as hook, objective, explain, model, guided practice, check understanding, independent practice, recap, and exit ticket. Layout remains a rendering concern; role drives density, quality, recovery, and future analytics.
6. **Related-artifact references are loose and safe.** Deck slides/blocks may reference lessons, worksheets, quizzes, drills, or objectives by stable IDs/semantic targets. They must not copy whole artifacts or answer keys into student-facing deck content.
7. **Future student runtime is a companion view, not only projector mirroring.** Presentation remains optimized for classroom display. Student runtime should default to mobile-readable companion cards keyed by slide/interaction IDs, with same-slide read-only fallback.
8. **Differentiation starts as teacher-only guidance.** V1 may include teacher-only scaffold/stretch notes. Student-facing output must not expose ability labels. Future sessions may support group/level variants keyed by interaction or activity IDs.
9. **Teacher annotations are future overlays.** Generated deck snapshots are immutable. Future annotations, highlights, circles, or notes attach as teacher-owned overlays keyed by slide/block IDs. Student visibility requires explicit live-session action.
10. **Teacher edits use scoped regeneration now and structured edits later.** Full arbitrary HTML/CSS/JS edits are not allowed. Current feedback should target deck/slide/block/interaction regeneration. Future manual edits should be structured patches or overlays that re-run projection and quality gates before export/share.
11. **Learning evidence starts with teacher reflection.** V1 does not persist student responses. The foundation should allow future teacher reflection, actual pacing, quick-check outcomes, exit-ticket analytics, and misconception reports to attach to stable slide/interaction IDs.
12. **Localization uses primary locale plus optional scaffolds.** Decks have a primary locale. Chrome and student-facing controls follow that locale. ESL/bilingual support may appear as typed scaffolds when appropriate. Parallel multilingual decks are future work.
13. **Visuals default to inline/offline-safe media.** Decks should support inline diagrams/icons/SVG-style visual blocks with alt text and fallback. External media remains optional under media policy and must not break standalone/offline exports.
14. **Slide deck should become a pedagogical component surface.** Over time, decks should use typed teaching components such as worked example, misconception check, think-pair-share, exit ticket, vocabulary scaffold, and guided practice. The LLM should assemble validated components, not freeform arbitrary slide patterns.
15. **Remix is snapshot lineage plus scoped regeneration.** Future reuse actions such as “make easier,” “reuse slides 3-5,” or “make a weaker-class version” should derive new immutable snapshots with lineage. Display preferences and export attempts are not content versions.
16. **Real-LLM evidence remains required for platform claims.** Any future teaching-foundation slice that changes generation, quality, projection, or export behavior must be accepted with real prompts, real model flow, real quality/export, and browser or session evidence according to ADR-044.

## Consequences

- Slide decks can grow into the core classroom teaching surface without abandoning standalone HTML or the existing teaching-pack lifecycle.
- Stable IDs become more important because they are the join points for future sessions, responses, annotations, pacing, reflections, related artifacts, and remix lineage.
- The current hardening pass should avoid storing student responses, adding live session state, or building a full editor, but it should not make those future capabilities impossible.
- Teacher-only information must remain projection-gated because future companion views and response collection increase the impact of leakage.
- Future work should be organized as teaching-foundation slices separate from print/display hardening so the v1 production release stays focused.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Static artifact only | Smaller scope; easy export story | Blocks slide deck from becoming the teacher/student classroom core |
| Full live teaching session now | Maximum product value | Too broad; requires session model, response storage, privacy, dashboard, and live sync now |
| Hybrid phased foundation (chosen) | Keeps current release shippable while preserving future session architecture | Requires discipline to add stable IDs, roles, refs, and overlays before they are fully used |
| Student view mirrors projector only | Simple implementation | Poor mobile/student UX; weak foundation for responses and companion activities |
| Freeform LLM slide patterns | Flexible | Hard to validate, analyze, remix, or attach learning evidence |

## References

- ADR-019 Learning Outcome Effectiveness Loop
- ADR-035 Component Strategist Stage
- ADR-039 Component Strategy Blueprint and Delivery Semantics
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- ADR-042 Slide Deck Surfaces, Quality Gates, and Release Evidence
- ADR-043 Slide Deck Display Preferences and Projection Boundaries
- ADR-044 Slide Deck Real-LLM Acceptance Harness
- `common/contracts/slide_deck.py`
- `packages/agents/slide_deck_engine/`
- `packages/agents/teaching_pack/scoped_regeneration.py`
