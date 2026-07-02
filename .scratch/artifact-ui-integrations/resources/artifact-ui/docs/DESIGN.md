# oh-my-class Design System

## 0. Sources of truth

This document is the canonical visual contract for product UI, renderer previews, and future UI polish issues. Theme implementation remains config-driven:

- `common/branding/kits/default/theme.json` is the default classroom theme source.
- `common/branding/kits/ocean/theme.json` is the calm blue alternate theme source.
- `common/branding/kits/forest/theme.json` is the green nature alternate theme source.
- Generated `theme_*.css` files must be produced from those JSON files and must not be edited manually.
- Product UI tokens live in `apps/web/src/app/globals.css`; renderer teaching-pack theme tokens live under `common/branding/kits/*/theme.json` and `packages/renderer/src/theme/themes/*.json` until those sources are unified.

Accepted debt: the product dashboard and teaching-pack renderer currently use parallel token sets. New UI polish work may cite this document for visual rules, but may not invent local colors, spacing scales, motion timings, or typography rules outside these sources.

## 1. Atmosphere & Identity

oh-my-class feels like a calm teacher command center: clear enough for busy classroom planning, structured enough to trust an AI pipeline, and quiet enough not to compete with lesson content. The signature is staged assurance: every workflow surface shows where the teaching pack is, what needs the teacher's decision, and what evidence the system used.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | `--color-background` | `#ffffff` | `#0f172a` | Page background |
| Surface/elevated | `--color-card` | `#ffffff` | `#1e293b` | Cards, sidebars, modals |
| Surface/muted | `--color-muted` | `#f1f5f9` | `#1e293b` | Event logs, subtle panels |
| Text/primary | `--color-foreground` | `#0f172a` | `#f8fafc` | Headlines, body |
| Text/secondary | `--color-muted-foreground` | `#64748b` | `#94a3b8` | Metadata, helper copy |
| Border/default | `--color-border` | `#e2e8f0` | `#334155` | Dividers, cards, outlines |
| Input/default | `--color-input` | `#e2e8f0` | `#334155` | Form controls |
| Accent/primary | `--color-primary` | `#4f46e5` | `#818cf8` | Primary actions, focus, active step |
| Accent/on-primary | `--color-primary-foreground` | `#ffffff` | `#0f172a` | Text on primary actions |
| Status/error | `--color-destructive` | `#ef4444` | `#ef4444` | Destructive actions, failures |
| Status/on-error | `--color-destructive-foreground` | `#ffffff` | `#ffffff` | Text on destructive actions |

### Rules

- Use the indigo accent only for actions, active progress, and links.
- Status color is semantic, not decorative: failed/cancelled states use destructive, awaiting/queued states use muted surfaces.
- No new raw color values in UI code. Add a token here and in `apps/web/src/app/globals.css` first.
- Raw hex colors are allowed only in theme source files, generated theme CSS, and tests that intentionally assert token values.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| H1 | 30px / `text-3xl` | 700 | 1.2 | -0.01em | Run detail title |
| H2 | 24px / `text-2xl` | 700 | 1.25 | -0.01em | Page title |
| H3 | 18px / `text-lg` | 600 | 1.4 | 0 | Card and section title |
| Body | 16px / `text-base` | 400 | 1.6 | 0 | Main copy |
| Body/sm | 14px / `text-sm` | 400/500 | 1.5 | 0 | Controls, metadata |
| Caption | 12px / `text-xs` | 500/600 | 1.4 | 0.02em | Badges, event labels |

### Font Stack

- Primary: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
- Mono: `"SF Mono", "Cascadia Code", "Fira Code", monospace`.

### Rules

- Body text never below `text-sm` except compact badges.
- Use tabular/mono styling for ids, hashes, and event sequence-like data.
- Prefer sentence case for gate headings and actions.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px via Tailwind spacing tokens.

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` / `p-1` | 4px | Icon-label gaps |
| `gap-2` / `p-2` | 8px | Compact buttons, badges |
| `gap-3` / `p-3` | 12px | Dense list rows |
| `gap-4` / `p-4` | 16px | Default panel padding |
| `gap-6` / `p-6` | 24px | Cards and modal bodies |
| `gap-8` | 32px | Section groups |
| `p-8` | 32px | Run detail page padding |

### Grid

- Max content width: `1280px` for dashboard content.
- Dashboard shell: fixed 256px sidebar plus flexible main content.
- Breakpoints: Tailwind defaults (`sm`, `md`, `lg`, `xl`, `2xl`).

### Rules

- Use `min-h-[100dvh]` for viewport-height app shells going forward.
- Use CSS grid for multi-column status/preview layouts; avoid percentage flex math.
- Mobile gates stack vertically; preview panes must not require horizontal scroll.
- Responsive QA covers 375, 768, 1280, and 1920px widths before a UI issue is called complete.

## 5. Components

### Button

- **Structure**: shadcn-style `Button` with `variant` and `size` props.
- **Variants**: default, secondary, destructive, outline, ghost, link.
- **Spacing**: default height `h-10`, horizontal padding `px-4`.
- **States**: hover shifts background opacity; focus uses `--color-ring`; disabled uses opacity and disables pointer events.
- **Accessibility**: native `<button>` unless `asChild` wraps a semantic link.
- **Motion**: color transition only.

### Card / panel

- **Structure**: `Card`, `CardHeader`, `CardTitle`, `CardContent`.
- **Variants**: default bordered surface; muted inline panel for logs and gate details.
- **Spacing**: `p-6` for cards, `p-4` for compact panels.
- **States**: interactive cards add hover surface shift, not heavy shadow.
- **Accessibility**: use semantic headings inside panels.
- **Motion**: mount fade/translate only when useful.

### Gate modal shell

- **Structure**: header with gate name/status, body mapped by gate type, footer with primary/secondary actions.
- **Variants**: clarification, contract confirmation, search plan confirmation, blueprint approval, content approval.
- **Spacing**: `p-6` body, `gap-4` between decision groups.
- **States**: loading disables primary action; backend errors render inline.
- **Accessibility**: labelled dialog title, keyboard-reachable controls, no `alert()`.
- **Motion**: overlay/content fade only.

### Stage progress

- **Structure**: ordered stage list with status badge and compact description.
- **Variants**: pending, active, blocked, complete, failed.
- **Spacing**: `gap-3` row, `p-3` row body.
- **States**: active uses primary accent; failed uses destructive text.
- **Accessibility**: ordered list communicates sequence; current stage labelled in text.
- **Motion**: no layout animation.

## 6. Motion & Interaction

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 100-150ms | ease-out | Button press, hover |
| Standard | 200ms | ease-in-out | Tab switch, modal state |
| Emphasis | 300-400ms | cubic-bezier(0.16, 1, 0.3, 1) | Panel entry |

### Rules

- Animate only `transform` and `opacity`; color transitions are acceptable for controls.
- Every interactive element needs hover, active, focus, disabled/loading states where relevant.
- Respect reduced motion; keep motion non-essential.
- Reduced-motion users must still receive all content and state changes without relying on animation.

## 7. Accessibility baseline

### Focus

- Every interactive control needs a visible focus state using `--color-ring` or an equivalent theme token.
- Focus order follows the visual reading order; modal and gate flows trap focus only while open.

### Contrast

- Body text and controls target WCAG AA contrast in both light and dark modes.
- Status text may use color, but must also include text labels or icons with accessible names.

### Reduced motion

- Honor `prefers-reduced-motion`; do not remove information when transitions are disabled.
- Use transform/opacity only for non-essential movement.

### CJK and Vietnamese text

- Vietnamese diacritics, CJK glyphs, and mixed-language labels must not clip vertically.
- Use system font stacks and line-height at or above 1.4 for compact text and 1.5 for body copy.
- Do not rely on all-caps for long Vietnamese labels; use sentence case unless a short badge needs uppercase.

## 8. Theme drift and token enforcement

- Run `pnpm verify:theme-drift` after editing `common/branding/kits/*/theme.json`.
- Run `pnpm --filter @oh-my-class/web test -- tests/methodology-token-guard.test.ts` after editing production UI components.
- CI rejects theme JSON edits that are not reflected in committed generated CSS.
- CI rejects manual generated CSS edits that do not match theme JSON.

## 9. Depth & Surface

### Strategy

Use borders plus tonal shifts. Existing shadcn cards keep `shadow-sm`, but new V2 workflow surfaces should prefer borders and muted panels over decorative shadows.

| Type | Value | Usage |
|------|-------|-------|
| Default border | `1px solid var(--color-border)` | Cards, dialogs, rows |
| Muted fill | `bg-muted` | Logs, status panels, skeletons |
| Elevated surface | `bg-card` | Sidebar, modal, preview frame |

### Rules

- Do not add arbitrary `box-shadow` values.
- Use `rounded-lg` for main panels, `rounded-md` for controls, `rounded-full` only for compact status badges.

## 10. Artifact UI Layer

Everything above this section governs the **product UI** — the
dashboard the teacher operates inside. It does not govern **artifacts**:
the standalone HTML documents the platform generates for teaching,
practice, and export (vocabulary tickets, lesson dossiers, exam keys,
video routes, investigation-style exercises). Artifacts are read
offline, printed, and handed to students — they intentionally use a
different, more expressive visual language than the calm/restrained
product UI, and they carry their own separate token system so that
product theme changes never bleed into shipped teaching material, and
vice versa. See ADR-023 for the full rationale.

### 10.1 Three-tier tokens, one contract, four families

Same tiering model as §8 (Theme drift and token enforcement), applied to
a second, independent set of custom properties prefixed `--art-`:

```
PRIMITIVES (raw hex, per family)  →  SEMANTIC (--art-*, one shared contract)  →  COMPONENT (scoped, e.g. --card-accent)
```

Four visual families exist today, one per reference template family
identified during the template-corpus review:

| Family | `data-artifact-theme` | Reference template | Used by |
|---|---|---|---|
| Navy Ticket | `navy-ticket` | `neo-tu-duy-template.html` | Semantic vocabulary anchors |
| Paper Dossier | `paper-dossier` | `learning-vocab-template.html`, `path-template.html`, `key-template.html` | Lesson/path dossiers, exam answer keys |
| Transit Route | `transit-route` | `learning-via-video-template.html` | Video learning routes |
| Investigation Folder | `investigation-folder` | `inverse-thinking-template.html` | Inverse-thinking exercises |

Every family implements the same semantic contract (background/surface/
ink/border/accent/status/categorical-palette tokens — see
`packages/renderer/src/artifact-ui/tokens/contract.css`), so core
primitives and family components are written once against semantic
tokens and re-skin completely by changing a single attribute. This is
not theoretical — the core-primitives showcase includes a live switcher
that proves it by re-rendering the same DOM under all four families.

### 10.2 Core primitives vs. family components

- **Core primitives** (`primitives.css`) — shell/print scaffold, cover/
  hero, sidebar + route navigation, section header, stat card, callout,
  content card with accent rail, table/comparison matrix, tag/stamp,
  diagnostics/review-state panel, teacher-only projection marker. Family
  agnostic; reused by all four families.
- **Family components** (`families/<family>.css`) — the small set of
  shapes that make each family visually distinct (ticket + stub,
  objective/concept/roleplay/phase-timeline, ticket-header + station
  route, folder cover + case + process strip). Depend on core primitives
  being loaded first.

Full catalog with CSS classes and proposed view-model shapes:
`docs/component-reference.md`.

### 10.3 Typography without webfonts

Artifact UI does not load or embed webfonts (zero network weight, per
the standalone HTML invariant below). Typographic identity per family is
carried by weight, tracking, case, and the display/body/mono role split
instead — see `docs/component-reference.md` §1 for the per-family
mapping and the tradeoff this implies.

### 10.4 Standalone HTML invariants (non-negotiable)

Every generated artifact file:
- Is openable directly from disk with zero network requests — no
  `<link rel="stylesheet">`, no remote `<script src>`, no webfont
  `@import`/`@font-face` URL, no `<iframe>`/`<video src>` pointing at a
  remote resource.
- Inlines all CSS in a single `<style>` block (token contract + one
  family file + primitives + that family's components, concatenated at
  render time).
- Contains the product brand string and remains legible when printed
  (`@media print` rules hide interactive-only chrome like the floating
  print button and theme switcher).
- Never uses `display:none`/`visibility:hidden` as the mechanism that
  keeps teacher-only content out of a student's hands — teacher and
  student projections are two separately rendered files from two
  different view models (ADR-022 §3).

### 10.5 Specialized families — when renderer/exporter code should choose each

| Family | Choose when the artifact is... | Example artifact types |
|---|---|---|
| Navy Ticket | A vocabulary/semantic-anchor item meant to feel collectible and memorable — one concept per "ticket" | Semantic anchor clusters, single-term flashcards |
| Paper Dossier | A multi-page teaching document with a persistent navigation sidebar, OR a scored assessment with an answer key | Lesson plans, multi-week path/roadmap dossiers, exam answer keys, quiz reviews |
| Transit Route | Content organized as an ordered sequence of timed steps tied to a media source | Video-based listening/viewing routes, any "watch → do → check" sequence |
| Investigation Folder | An exercise built around elimination/comparison reasoning between distractors | Inverse-thinking / near-synonym discrimination exercises, error-analysis case studies |
| Paper Dossier | A single-session, continuous-scroll Socratic/root-cause teaching record — no persistent sidebar, no scoring | Root-cause session dossiers (see Issue 005 verdict below) |

If an artifact type doesn't clearly match one row, default to
**Paper Dossier** (the most general-purpose family) rather than
inventing a fifth family — see ADR-023 for the process to propose a new
family when the fit is genuinely poor.

#### Issue 005 verdict: does Paper Dossier fit a root-cause/Socratic session?

**Fits — with one specific strain, not a structural break.** Built as
`dist/families/root-cause-session.html`, one continuous `.art-shell` (not
`.art-shell--split`, since a single session has no multi-week sidebar to
pin), carrying all 7 Issue 004 primitives end to end for the real Future
Perfect / Future Perfect Continuous transcript. It renders correctly,
passes the §10.4 standalone-HTML invariants, and nothing in
`families/paper-dossier.css` conflicts with any Issue 004 primitive — in
fact `families/paper-dossier.css` never touches `.art-shell`,
`.art-section`, or `.art-page-head` at all, so those are pure
`primitives.css` behavior regardless of family.

That last fact is itself the evidence worth naming: **this artifact uses
none of Paper Dossier's actual distinguishing family components** —
no `.art-phase-rail` roadmap, no `.art-concept-box`/`.art-triad`, no
`.art-script` dialogue, no `.art-qgrid` exam grid. What it inherits from
"Paper Dossier" is really just the token layer (serif display type, warm
cream palette) plus the family-agnostic shell — the same thing choosing
any other family's tokens would have given it. The fit here is by
**default neutrality**, exactly as §10.5's own fallback rule predicts,
not because Paper Dossier's specific idiom was designed with this content
shape in mind.

The one concrete strain: `.art-section`'s built-in rhythm
(`margin-bottom: var(--art-space-16)` in `primitives.css`) is tuned for
coarse, page-level breaks — a new week's phase, a new exam question, a
new lesson objective — where each section is a self-contained unit. A
Socratic session's sections are not self-contained; §02 (the two
anchor-timelines) is a direct continuation of §01's scenario under Rule
#11, and the large fixed gap between them reads as a bigger topic change
than actually occurred. This did not break anything or require a
workaround for Issue 005 — it is a pacing mismatch worth a follow-up
(e.g. a `.art-section--tight` modifier for continuous-scroll session
content), not a reason to open a new-family proposal.

### 10.6 Diagnostics states

Every generated item resolves to exactly one status —
`passed` / `needs_review` / `failed` (ADR-021) — and the Artifact UI
diagnostics panel is the one shared surface for reporting all three, in
both internal QA tooling and teacher-facing review drafts.

### 10.7 Interactivity layer (Issue 006)

Stateful primitives (§10.2's checkpoint, metaphor-log, and the
exception/wrinkle composite) and the pre-existing exam-key dense-nav
(`.art-reveal-btn`, `.art-mode-toggle`, `.art-jumpbox`) are wired by one
shared vanilla-JS file, `interactivity.js`, inlined via `render.js`'s
`script` option. It is deliberately generic — three data-*/aria-*
contracts (reveal/toggle, mode-toggle, jump-to-target), not per-page
logic — so one file backs every family without knowing which page it's
running on. Full contract reference: `docs/component-reference.md` §6a.

This is an addition to, not a relaxation of, §6/§7 above:

- Every reveal/toggle/jump control is a native `<button>`/`<input>`
  (never a `div` click target) and gets the same `:focus-visible` ring
  as everything else in §7.
- `prefers-reduced-motion` (§6) removes the reveal-entrance animation
  and the decorative jump `.art-flash`, but content, the
  `.art-jump-highlight` outline, scroll-into-view, and focus movement
  are load-bearing feedback and fire unconditionally regardless of the
  motion preference.
- Controls that only make sense on a screen (`.art-reveal-btn`,
  `.art-mode-toggle`, `.art-jumpbox`, `.art-qgrid`) carry `.art-no-print`
  per §10.4's print-safety requirement; the content they gate does the
  opposite and is forced visible under `@media print` so a printed copy
  never ships with an un-clicked, blank panel.
- `.art-mastery-marker` stays intentionally un-wired — see
  `interactivity.js`'s own non-goals comment and
  `docs/component-reference.md` §6a.

