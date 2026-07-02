# Artifact UI — Component Reference

Companion to ADR-023 and Issues 001–003. Catalogs every primitive and
family component actually implemented in this handoff, the CSS classes
that back them, and the view-model shape engineering should reconcile
against `common/contracts` when wiring this into `packages/renderer`.

Source of truth for visual behavior is the CSS itself
(`tokens/*.css`, `primitives.css`, `families/*.css`) — this document
describes intent and data shape, not pixel values.

## 1. Token architecture

Three tiers, one contract (`tokens/contract.css`):

```
PRIMITIVES (raw hex, per family)  →  SEMANTIC TOKENS (--art-*)  →  COMPONENT TOKENS (scoped, e.g. --card-accent)
```

Core primitives and family components are written **only** against the
semantic tier. This is what lets `data-artifact-theme` swap the entire
visual language without touching markup — proven live in
`showcase/core-primitives.html`'s theme switcher.

Four families ship: `navy-ticket`, `paper-dossier`, `transit-route`,
`investigation-folder` (`tokens/<family>.css`). Adding a fifth family
later means writing one new token file that satisfies the same semantic
contract — no primitive CSS changes.

### Typography without webfonts

AGENTS.md §8.4 requires a system-font-only stack (zero network weight).
The reference templates use webfonts (Be Vietnam Pro, Space Grotesk,
Spectral, Oswald, IBM Plex Mono) that Artifact UI does not load. Instead:

| Family | Reference webfont pairing | Artifact UI substitute |
|---|---|---|
| navy-ticket | Be Vietnam Pro + IBM Plex Mono | System sans, mono role used liberally for labels/eyebrows, heavy weight (800–900) on display |
| paper-dossier | Spectral (serif) + Be Vietnam Pro | `Georgia, Cambria, "Times New Roman"` as `--art-font-display` (pre-installed serif, zero download) |
| transit-route | Space Grotesk + Inter | System sans (both source fonts are grotesk-family already; character loss is minor) |
| investigation-folder | Oswald (condensed) + Be Vietnam Pro | `font-stretch: condensed` + uppercase + tight tracking on display type (`families/investigation-folder.css`) |

This is a documented deviation worth revisiting: if the product later
decides self-hosted/base64-inlined fonts are worth the byte weight for
brand character, only the four family token files need a
`--art-font-display` override — no primitive or family-component CSS
changes required.

## 2. Core primitives (`primitives.css`) — Issue 001

| Component | Classes | Purpose | Typed input (proposed) |
|---|---|---|---|
| Shell | `.art-shell`, `.art-shell--wide`, `.art-shell--split`, `.art-shell-aside`, `.art-shell-main` | Print-safe page scaffold; split variant for sticky-sidebar dossiers, collapses to stacked layout ≤880px | `{ layout: 'single'\|'split' }` |
| Print button | `.art-print-btn` | Floating `window.print()` trigger, hidden in `@media print` | none |
| Cover / hero | `.art-cover`, `.art-cover-eyebrow`, `.art-cover-sub`, `.art-cover-copy`, `.art-cover-pills`, `.art-pill` | Full-bleed hero band | `{ eyebrow, title, subtitle, lede, pills: string[] }` |
| Compact page head | `.art-page-head`, `.art-lede` | Non-hero header for practice/answer-key/diagnostics pages | `{ eyebrow, title, lede }` |
| Sidebar nav | `.art-nav-brand`, `.art-nav-title`, `.art-nav-sub`, `.art-nav-list` | Vertical dossier navigation | `{ brand, title, subtitle, items: {label, href, active}[] }` |
| Route nav | `.art-route-nav`, `.art-stop`, `.art-track` | Horizontal station-style navigation | `{ stops: {code, active}[] }` |
| Section header | `.art-section`, `.art-section-head`, `.art-section-eyebrow`, `.art-section-sub`, `.art-time-chip` | Consistent section rhythm | `{ eyebrow, title, subtitle?, timeChip? }` |
| Stat card | `.art-stat-grid`, `.art-stat-card`, `.art-k`, `.art-v` | 2–4 up metric grid, collapses to 2-col ≤820px | `{ stats: {k, v, unit?}[] }` |
| Chip | `.art-chip`, `.art-chiplist` | Small metadata pill | `{ label }` |
| Callout | `.art-callout`, `.art-callout--dashed` | Note/warning box, solid or dashed-on-bg variant | `{ glyph, text, variant? }` |
| Content card | `.art-card`, `.art-card--rail`, `.art-card-title`, `.art-card-meta` | Card with accent-colored left rail (color via `--card-accent`) | `{ meta, title, body, accent? }` |
| Table | `.art-table-wrap`, `.art-table-head`, `.art-table`, `.art-hide-mobile`, `.art-strong`, `.art-accented`, `.art-mono-cell` | Comparison matrix; low-priority columns hide ≤600px | `{ title, badge, columns, rows }` |
| Tag | `.art-tag`, `.art-tag--cat1..6`, `.art-tag--positive/caution/critical` | Small status/category label | `{ label, variant }` |
| Stamp | `.art-stamp`, `.art-stamp--positive/caution/critical` | Circular rotated stamp | `{ text, variant }` |
| Diagnostics panel | `.art-diagnostics`, `.art-diagnostics--passed/needs_review/failed`, `.art-diagnostics-row` | Review-state report, 3 required statuses per ADR-021 | `{ status: 'passed'\|'needs_review'\|'failed', title, rows: {k,v}[] }` |
| Projection flag | `.art-projection-flag` | Visual "teacher-only" marker banner | `{ text }` — **never used to hide content; see §4** |
| Teacher block | `.art-teacher-block`, `.art-teacher-block-label` | Dashed-border teacher-only content region | `{ label, html }` |
| Footer | `.art-footer`, `.art-signoff` | Brand signature (contains required "oh-my-class" string) | `{ note?, signoff? }` |
| Anchor timeline | `.art-anchor-timeline`, `.art-anchor-timeline-svg`, `.art-anchor-timeline-legend` | SVG axis with one future "anchor" point, a backward-glance arc, and 0–n events placed before/at/after the anchor | `{ axisLabel, anchor: {label}, events: {label, position: 'before'\|'at'\|'after', state?}[] }` |
| Controlled comparison | `.art-controlled-comparison`, `.art-controlled-comparison-constant`, `.art-controlled-comparison-grid` | One fixed constant band + n variant columns (n = 2–6, auto-fit, not hard-coded) | `{ constant: {label, value}, axis, variants: {label, value, note?}[] }` |
| Scenario anchor | `.art-scenario-anchor`, `.asa-eyebrow`, `.asa-scenario` | Single vivid-scenario opener for a concept; no title/rule field, so it can't be used rule-first | `{ scenario }` |
| Generalization checkpoint | `.art-generalization-checkpoint`, `.agc-claim`, `.agc-verdict--confirmed/corrected` | Two-state block: learner's own proposed wording, then a leading confirmed/corrected verdict | `{ learnerClaim, verdict: 'confirmed'\|'corrected', correction?, explanation }` |
| Stress test | `.art-stress-test`, `.ast-attempt`, `.ast-why` | Learner-authored deliberately-broken example + why it breaks, visually distinct from `.art-wrong-item`'s teacher-authored distractor | `{ learnerAttempt, breaksBecause, tiesBackTo? }` |
| Metaphor log | `.art-metaphor-log`, `.aml-landed`, `.aml-attempts` | Stack of 1–n metaphor attempts; the one that landed is promoted, earlier attempts collapsed but not deleted | `{ attempts: {device, text, landed: boolean}[] }` |
| Mastery marker | `.art-mastery-marker`, `.art-mastery-marker--open/clicked` | Small learner-comprehension chip; separate namespace from ADR-021 content-QA states | `{ concept, state: 'open'\|'clicked' }` |

## 3. Family components — Issue 003

### `families/navy-ticket.css` (Issue 002)
- `.art-ticket`, `.art-ticket-main`, `.art-ticket-stub` — semantic anchor card with perforated stub (impression badge). Stacks vertically ≤600px.
- `.art-semantic-chain` — mono chain: `word → impression → core_trigger → visual_cue`.
- `.art-contrast-quote` — boundary/contrast note, accent-colored left rail.
- `.art-teacher-script` — verbatim delivery-script text (always inside `.art-teacher-block`).
- `.art-practice-item` — practice question shell (recall / discrimination / boundary / reverse retrieval).

### `families/paper-dossier.css` (lesson/path + exam-key)
- `.art-objective-card` — lesson objectives list.
- `.art-concept-box`, `.art-triad` — grammar/concept explainer with a 3-slot comparison.
- `.art-script`, `.art-who--a/b`, `.art-blank` — roleplay dialogue with fill-in blanks.
- `.art-hw-list` — tagged homework list.
- `.art-phase-rail`, `.art-phase-block`, `.art-phase-card` — roadmap timeline, category-colored.
- `.art-qgrid`, `.art-qcard`, `.art-option--correct`, `.art-panel`, `.art-wrong-item` — exam question + answer-state + per-distractor rationale.
- `.art-jumpbox`, `.art-mode-toggle` — dense navigation + reveal-answers toggle.

### `families/transit-route.css`
- `.art-ticket-header` — boarding-pass style cover with perforated edge.
- `.art-miniroute` — overview strip of station dots.
- `.art-station`, `.art-station-body` — per-stop lesson card threaded on a vertical rail.
- `.art-video-embed` — **offline-safe placeholder only**; real video URLs are teacher-only metadata rendered elsewhere, never a live `<iframe>`/`<video src>` (AGENTS.md INVARIANT-04).
- `.art-cue-card`, `.art-counter-badge` — short prompts + self-check counters.

### `families/investigation-folder.css`
- `.art-cover--folder` — left-aligned folder cover with a torn-edge bottom.
- `.art-tabs` — section tabs.
- `.art-case`, `.art-case-tag` — case card.
- `.art-process-strip`, `.art-pstep` — numbered elimination steps.
- `.art-evidence` — dashed evidence/exhibit block.
- `.art-wanted-card`, `.art-key-row` — term summary card.

## 4. Teacher/student projection — the rule this system enforces

`.art-projection-flag` and `.art-teacher-block` are **visual markers for a
teacher-only build**, not a hiding mechanism. Per ADR-022 §3, teacher and
student projections must be **two separate rendered files** — the
renderer calls the teaching-page template twice with two different view
models (`{ audience: 'teacher' | 'student' }`), and the student call
never receives `teacher_script_vi`, `source_notes`, `edge_cases`, or
answer/rationale fields in its input at all. There is no
`display:none`/`visibility:hidden` toggle anywhere in this codebase that
is relied on for content safety.

`pages/semantic-vocabulary.js` implements this correctly: `teachingBody()`
and `practiceBody()` take an `isTeacher` boolean and conditionally build
different DOM strings — the student HTML string literally never contains
the teacher fragment. This was checked directly (not just visually) —
see HANDOFF.md §4 for the grep-based verification.

## 5. Diagnostics states — the three ADR-021 outcomes

Every batch item ends in exactly one of three states, each with a
distinct Artifact UI treatment:

| Status | Artifact UI treatment | What gets published |
|---|---|---|
| `passed` | `.art-diagnostics--passed` (in QA tooling); full teaching/practice pages | teacher HTML, student HTML, GIFT, H5P |
| `needs_review` | `.art-diagnostics--needs_review` + a single `review.<id>.teacher.html` built from `reviewBody()` | teacher review draft only — nothing published to students/LMS |
| `failed` | `.art-diagnostics--failed` + a single `diagnostics.<id>.html` built from `diagnosticsOnlyBody()` | diagnostics report only — no teaching content generated |

See `dist/semantic-vocabulary/` for one worked example of each.

## 6a. Interactivity layer (`interactivity.js`) — Issue 006

One vanilla-JS file, inlined via `render.js`'s `script` option
(`vanilla only, no eval, no remote src`), backs three generic
data-*/aria-* contracts rather than knowing about any single page's
components by name. Full contract docs live at the top of
`interactivity.js` itself; this is the pointer from the component
catalog to that file, plus which components actually use each contract.

| Contract | Attributes | Used by |
|---|---|---|
| 1 — reveal/toggle | `data-toggle-reveal`, `aria-controls`, `aria-expanded`, optional `data-hide-after-reveal` / `data-collapsed-label` + `data-expanded-label` / `data-toggle-group` | `.art-generalization-checkpoint`'s verdict (one-way — `data-hide-after-reveal`), the exception/wrinkle composite below, `.art-metaphor-log`'s earlier-attempts list, exam-key's per-question `.art-panel` (grouped under `"exam-answers"`) |
| 2 — mode toggle | `data-mode-toggle`, `data-toggles-group`, `role="switch"`, `aria-checked` | `.art-mode-toggle` (exam-key sidebar) — bulk reveal/hide of every contract-1 member sharing its group name |
| 3 — jump-to-target | `data-jump-input-el` / `data-jump-go` / `data-jump-input`, or a standalone `data-jump-to="N"` | `.art-jumpbox`'s typed input, and `.art-qgrid`'s per-question shortcut buttons — both land on `#q{N}`, scroll + focus it, and add `.art-jump-highlight` |

Two things worth calling out because they're easy to get wrong by
analogy with the rest of the catalog:

- **The exception/wrinkle reveal is not an 8th primitive.** Issue 006 is
  JS-wiring-only against Issue 004's existing CSS states — no new class
  was added. `renderExceptionReveal()` (`partials.js`) composes two
  primitives that already existed (`.art-callout--dashed` from Issue
  001, `.art-reveal-btn`) under contract 1, the same as everything else.
- **`.art-mastery-marker` is deliberately NOT wired.** It stays a static
  chip (`state: 'open'|'clicked'` picked at render time, same as the
  checkpoint's verdict) — see that row in §2 and `interactivity.js`'s
  own "non-goals" comment for why a reader-clickable version would be
  fake state given this catalog renders already-completed sessions.

**Print.** Every control this script drives (`.art-reveal-btn`,
`.art-mode-toggle`, `.art-jumpbox`, `.art-qgrid`) carries `.art-no-print`
— clicking things isn't meaningful on paper. Content gated behind a
reveal is the opposite: `.art-reveal-target[hidden]` is forced back to
`display: revert` under `@media print` (`primitives.css`) so a printed
Teacher Edition never ships a blank answer panel just because nobody
clicked "Xem đáp án" first.

**Accessibility.** Every interactive element is keyboard-reachable
(native `<button>`/`<input>`, no `div` click targets) with the shared
`:focus-visible` ring (`primitives.css`, DESIGN.md §7). One-way reveals
move focus to the revealed content so it isn't lost when the triggering
button disappears. `prefers-reduced-motion` removes the `.art-reveal-in`
entrance animation and the decorative `.art-flash` on jump-land, but
never removes content, the `.art-jump-highlight` outline, scroll, or
focus movement — those fire unconditionally (DESIGN.md §6).

## 6. What is explicitly out of scope here

- **GIFT / H5P exporters** — unchanged by this work. They already consume
  the same `ArtifactContent`-shaped JSON `packages/exporters` presumably
  reads today; nothing in this handoff touches that package. Issue 002's
  "as before" acceptance criterion is a regression guard, not new work.
- **Eta template wiring** — pages here are generated by plain Node string
  building (`render.js`) rather than the project's real Eta engine, since
  this sandbox has neither the real renderer package nor its contracts.
  The CSS (`tokens/*.css`, `primitives.css`, `families/*.css`) is
  genuinely production-ready and framework-agnostic; porting the HTML
  shape into actual `.html` Eta templates under
  `packages/renderer/templates/artifact/` is the main remaining
  integration step — see HANDOFF.md §5.
