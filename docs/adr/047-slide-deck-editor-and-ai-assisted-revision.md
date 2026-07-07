# ADR-047: Slide Deck In-Browser Editor and AI-Assisted Revision

## Status

**Proposed** (2026-07-07) — Amends ADR-045's SDTF-06 deferral of manual/WYSIWYG editing. Defines the in-browser editor, the real LLM step inside `SlideDeckEngine`, and the AI-assisted rewrite action for slide decks. Produced from a 50-question design interview; see `.scratch/slide-deck-editor/issues/` (SDE-01..11) for the implementation slices.

## Context

ADR-040 decided that `SlideDeckEngine` phases are "deterministic orchestration with schema-bound LLM steps," but the current implementation makes **zero LLM calls** across all 9 phases (`llm_calls=0` is a hardcoded literal in `SlideDeckTraceMetadata`; no phase file references `llm_client`). Slide content today is fully templated. ADR-041 specifies a 21-value `SlideLayout` registry; the current contract has 5. Neither gap was a deliberate scope cut recorded in an ADR — they are simply unimplemented.

Separately, ADR-045/SDTF-06 explicitly deferred "full manual/WYSIWYG editing," anticipating "structured edits later." There is now a concrete, product-level need for teachers to edit slide content in the browser (goal: make the slide deck a feature-rich core product). The only existing human-edit mechanism in the codebase — `TeachingPackSectionEditor` → `apply_scoped_section_edit()`, which does verbatim string replacement on a flat `artifact["sections"]` list — is structurally incompatible with `SlideDeckData`'s `slides[].blocks[]` shape and cannot be reused as-is.

This ADR resolves both gaps together because the editor's registry-driven block model and the engine's real content-generation step are the same seam: an editor cannot safely let teachers or AI touch content that isn't validated by a real, typed registry.

## Decision

1. **`ContentMaterializer` gets a real, schema-bound LLM call.** All other phases (`PedagogicalPlanner`, `SlideArchitecturePlanner`, `LayoutComposer`, `InteractionPlanner`, density/accessibility/export auditors) remain deterministic. Only slide wording, examples, and activity text are LLM-authored, and every output is parsed into typed blocks and re-validated by the existing registry/density/accessibility gates before acceptance.
2. **The full 21-layout/block/interaction registry is declared as a typed contract now** (Python `Literal`/enum + generated TS types), closing ADR-041's gap at the schema level immediately. Renderer/template support for each layout ships incrementally, prioritized by ADR-044's 3 official scenarios; an undelivered layout fails closed with an explicit "not yet supported" error, never a silent fallback.
3. **Editing is structured-visual, not freeform WYSIWYG.** Teachers see and click directly on rendered slide content, but every editable region maps 1:1 to a registry-defined block field (heading, bullet list, image caption, etc.). Arbitrary HTML/CSS entry is rejected — this preserves ADR-041's validation/accessibility guarantees, which freeform WYSIWYG would break.
4. **AI-assisted rewrite is a first-class, teacher-confirmed editor action, scoped to one block at a time.** Teachers pick a preset ("shorter," "add an example," "simplify language"...) or optional freeform instruction; the same `ContentMaterializer` LLM step (decision 1) regenerates just that block; a generic before/after confirmation modal (one component, reused for every block type) gates the result before it enters the draft. Rewrite never touches `layout_composition`/`slide_architecture` in v1 — this is a deliberate boundary, not a technical ceiling, and widening it to slide- or deck-level rewrite requires its own ADR.
   - **Exception:** bilingual (EN↔VI) deck translation is scoped at the deck level, because translation is a 1:1 text substitution across many blocks with no layout/structure change — see SDX-01.
5. **The editor has two write paths sharing one business function.** The existing gate-resume `action: "edit"` flow continues to work for first-draft approval edits. A new standalone endpoint, decoupled from graph/gate state, lets a teacher revise **any existing snapshot at any time** (including after approval/export). Both paths call the same slide-scoped equivalent of `apply_scoped_section_edit()` and emit the same `content_version.created` event with `authority: "teacher_edit"` (or `"ai_assisted_edit"` for AI-rewritten content, so provenance is auditable).
6. **Every edit creates a new immutable snapshot version; concurrent writes use optimistic locking.** Clients submit `base_snapshot_id`; a mismatch returns 409 and the client must reload. No pessimistic locks, no silent last-write-wins.
7. **Version history is a linear, restorable list — not a diff/rollback UI.** Teachers can view any past version read-only and restore it (creating a new version that copies the old content). Side-by-side diffing is explicitly out of scope for v1.
8. **Exports are versioned artifacts, never silently invalidated.** Each export records the `snapshot_id` it was generated from and remains valid/accessible. The editor shows a "re-export needed" indicator when the latest export's snapshot lags the current one; re-export is always a manual teacher action, never automatic.
9. **Authorization reuses `check_run_owner` unchanged.** No new co-editor/shared-ownership model is introduced. When `organization_id` is added to the `users` table (unblocking `SCHOOL_ADMIN` same-org access), editor access inherits that fix automatically — it needs no slide-deck-specific code.
10. **Saves are local-draft-then-commit, not autosave-per-keystroke.** Draft state is buffered client-side and mirrored to `localStorage` (reusing SDH-03's precedent) for crash recovery; exactly one request creates a new version, on explicit "Save" or navigation-away. This keeps version history (decision 7) meaningful instead of keystroke-noisy.
11. **The editor is a dedicated full-screen route that keeps `run_id` in the path** (`/runs/[runId]/decks/[deckId]/edit`), separate from the existing narrow-column run-status page. Rendering is a new, purpose-built React component tree operating directly on `SlideDeckData`/the block registry — `slide-deck-projection.ts` is untouched and keeps its existing read-only display/export role.
12. **ADR-044's real-LLM harness is extended, not duplicated.** New scenarios cover edit-then-reexport staleness and AI-rewrite-through-registry-validation, using the same model (`4omc`), same gateway, same evidence-bundle format. Passing these scenarios is a completion gate for this ADR's scope, the same way it already gates generation.
13. **Two independent feature flags gate rollout.** One flag covers manual structured edit (low risk — teacher-authored data only); a second, separately toggleable flag covers AI-rewrite (higher risk — live LLM cost and content-validation exposure). Either can be disabled without the other.
14. **AI-rewrite has a simple, self-contained call-count rate limit per teacher**, reusing the in-memory/Redis sliding-window pattern already used for webhook rate-limiting — not a full per-teacher dollar cost cap (that remains `ops-observability/004`'s job, which this ADR does not block on).
15. **Success is measured via existing observability events, not a new dashboard.** A short list of concrete, queryable events (edit-within-24h rate, AI-rewrite accept rate from the confirmation modal, return-usage) is emitted through the existing `ObservabilityEventType` pipeline per ADR-032's live-emitter rule, reviewed manually — no dashboard is built on top of it in v1.

## Consequences

- Slide content becomes genuinely LLM-authored where it matters (wording/examples), while structure/layout/safety stay fully deterministic and testable — closing the ADR-040 gap without reopening its safety model.
- The registry gap (5 vs. 21 layouts) stops silently diverging from ADR-041; the schema is honest immediately, even though renderer coverage lands incrementally.
- Editing and AI-rewrite reuse existing infrastructure end-to-end (ownership checks, event/versioning model, rate-limiter pattern, feature-flag convention, ADR-044 harness) rather than inventing parallel systems — consistent with this project's "no new zero-caller module" discipline (ADR-032).
- The block-level rewrite boundary (decision 4) means slide- or deck-level AI restructuring is explicitly not supported yet; product pressure to widen this should produce a new ADR, not a quiet scope creep inside this one.
- `.scratch/slide-deck-editor/issues/` (SDE-01..11) carries the implementation breakdown; see the updated `.scratch/ROADMAP.md` Slide Deck track for sequencing against SDH/SDTF/TSP.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Freeform WYSIWYG editing | Best-in-class editing UX, familiar to PowerPoint/Slides users | Breaks ADR-041's registry/validation/accessibility guarantees; re-opens exactly the risk ADR-041 was written to close |
| Reuse `TeachingPackSectionEditor`'s flat-section model as-is | Zero new backend code | `SlideDeckData` has no `sections` field; would require a lossy adapter or a parallel content model |
| Edit only during the gate-resume pause window (no standalone endpoint) | No new API surface | Teachers cannot revise a deck after approval/export, which is the common real-world case |
| Full version diff/rollback UI now | Most feature-rich | Disproportionate engineering cost before any teacher has asked for cross-version diffing |
| Autosave on every keystroke | Familiar (Google Docs) | Floods the version history with noise; increases optimistic-lock conflicts between tabs |
| Slide- or deck-level AI rewrite in v1 | More powerful single action | Requires reopening `layout_composition`/`slide_architecture` to the LLM, contradicting the safety boundary this ADR sets |
| Wait for `ops-observability/004` before shipping AI-rewrite | One unified cost-cap system | Blocks a shipped feature on an unrelated, audit-flagged-POTEMKIN epic with no ETA |

## References

- ADR-032 Verification Integrity (Green-but-Hollow Correction)
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- ADR-041 Slide Deck Registries and Interaction Modules
- ADR-042 Slide Deck Surfaces, Quality, and Release Gates
- ADR-044 Slide Deck Real-LLM Acceptance Harness
- ADR-045 Slide Deck as Teaching Session Foundation (SDTF-06 amended by this ADR)
- `common/contracts/slide_deck.py`
- `packages/agents/slide_deck_engine/`
- `packages/renderer/src/slide-deck-projection.ts`
- `services/gateway/routers/teaching_pack_previews.py`
- `packages/agents/teaching_pack/scoped_regeneration.py`
- `apps/web/src/components/teaching-packs-scoped-rejection.tsx`
- `services/gateway/auth/ownership.py`
- `.scratch/slide-deck-editor/issues/` (SDE-01..11)
