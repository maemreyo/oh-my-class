# ADR-023: Artifact UI Layer from Template Corpus

## Status

**Decided** (2026-07-01) — Generated teaching artifacts will use a dedicated Artifact UI layer derived from `docs/templates/*`, separate from the product dashboard design system.

## Context

The current product `DESIGN.md` describes a calm teacher command center: white/card surfaces, restrained indigo accent, shadcn-style cards, and dashboard-first interaction patterns. That system is appropriate for the web dashboard, job status, gates, and review tools.

The generated artifact surfaces have a different job. They must feel like polished, print-and-use learning materials, not dashboard panels. The current vocabulary-batch artifacts are technically correct and student-safe, but they do not match the craft level shown by the reference templates in `docs/templates/`.

The template corpus shows several strong visual languages:

- `neo-tu-duy-template.html`: navy/paper semantic-anchor tickets, brass/rust accents, large expressive hero, mono labels, tactile ticket cards, and print-friendly sections.
- `learning-vocab-template.html` and `path-template.html`: warm paper dossier layout, sticky sidebar, stat cards, section rhythm, concept boxes, tables, practice cards, roleplay scripts, and homework lists.
- `key-template.html`: dense exam answer-key layout with sidebar navigation, question grids, answer states, explanation cards, and review mode controls.
- `learning-via-video-template.html`: transit-route metaphor with ticket header, route map, station cards, timeline dots, and lesson station rhythm.
- `inverse-thinking-template.html`: investigation dossier style with folder cover, tabs, case cards, stamps, process strips, and rotated paper-card motion.

These templates are reference material, not production output. They currently use external Google Fonts and some template-specific raw styles. Production artifacts must still satisfy the standalone HTML invariant: no external assets, no CDN, no hidden teacher-only content in student files, and deterministic rendering from typed contracts.

The user explicitly chose **Artifact UI layer** as the direction: improve generated artifacts through reusable and specialized components without replacing the dashboard's command-center UI.

## Decision

### 1. Introduce a separate Artifact UI layer

The product UI and generated artifact UI are separate layers:

| Layer | Owns | Visual posture |
|---|---|---|
| Product UI | Dashboard, gates, review editors, job status, operations | calm command center, restrained, shadcn-compatible |
| Artifact UI | Exported/previewed learning materials | expressive, tactile, print-ready, template-derived |

The Artifact UI layer may define its own tokens, component primitives, and template families, but must remain inside renderer/exporter boundaries. It must not import from `apps/*` or `services/*`.

### 2. Derive the Artifact UI system from the template corpus

The template corpus becomes the design reference for the Artifact UI layer. Implementers should extract reusable component language, not copy one template wholesale.

The shared core primitives include:

- artifact shell and print-safe page scaffold;
- hero / cover block;
- sidebar or route navigation;
- section header and section rhythm;
- stat card and metadata chips;
- callout / note box;
- content card with accent rail;
- table and comparison matrix;
- tag / stamp / badge;
- teacher-only and student-safe projection wrappers;
- diagnostics and review-state panels.

Specialized families extend the core primitives:

| Family | Source templates | Specialized components |
|---|---|---|
| Semantic vocabulary | `neo-tu-duy-template.html` | ticket card, stub, impression badge, semantic chain, contrast quote, teacher script panel |
| Lesson/path dossier | `learning-vocab-template.html`, `path-template.html` | sticky sidebar, stat grid, objective card, concept box, roleplay script, homework list |
| Exam answer key | `key-template.html` | question grid, answer-state card, option state, explanation block, review mode controls |
| Video learning route | `learning-via-video-template.html` | ticket header, mini route map, station card, timeline step, video placeholder wrapper |
| Investigation/inverse thinking | `inverse-thinking-template.html` | folder cover, tabs, case card, process strip, stamp, evidence block |

### 3. Keep contracts first; components render projections

The Artifact UI layer renders typed artifact contracts and projections. It must not become a raw HTML editing system.

For vocabulary batch, `SemanticAnchorCluster` and `PracticeSet` remain the source of truth. The Artifact UI components render teacher/student projections from those contracts. Student projections must never contain teacher scripts, source notes, answer keys, rationales, or hidden teacher-only DOM.

For future lesson/path/key/video families, components should consume typed contracts or explicit projection view models. If the contract is missing, the issue should add the contract or view model before adding visual components.

### 4. Artifact tokens are standalone and offline

Artifact UI tokens may use the template corpus palettes and typography intent, but production output must be offline:

- no Google Fonts links in exported HTML;
- no remote CSS, images, scripts, iframes, or `@import`;
- use system fallback stacks or self-hosted/inlined font strategy if font character is required;
- inline CSS in the artifact HTML or bundle it into the standalone output;
- preserve print styles and `print-color-adjust` behavior where useful.

The initial token families are:

- **paper dossier**: warm paper, card white, ink navy, red/gold/green semantic accents;
- **navy ticket**: navy background, cream paper cards, brass/rust accents;
- **transit route**: off-white paper, dark ticket header, route color stops;
- **investigation folder**: folder ochre, paper card, stamped red/blue/gold evidence accents.

### 5. Build a component showcase before broad rollout

The first implementation should produce a browser-visible artifact component showcase that renders core primitives and at least one specialized component from each family. Product screens should not be rewritten until the Artifact UI layer can be inspected at mobile/tablet/desktop widths.

The showcase is not a dashboard feature. It is a development/QA artifact used to verify visual grammar, print behavior, and standalone invariants.

### 6. Roll out by projection family

After the core showcase, rollout should happen in independently testable slices:

1. semantic vocabulary projection redesign;
2. lesson/path dossier family;
3. exam key / dense answer family;
4. video-route and inverse-thinking specialized families.

Each rollout slice must include tests for standalone HTML, no external assets, student-safe redaction, and browser-based visual QA at 375, 768, and 1280px.

## Consequences

- Generated artifacts can become visually distinctive without contaminating dashboard UI with print-artifact styling.
- Renderer/exporter code gets a reusable vocabulary for artifact surfaces instead of one-off inline CSS per template.
- The template corpus becomes a governed source of design language, not a set of copy-pasted examples.
- More design-system work is required before broad implementation: tokens, primitives, showcase, and projection-specific tests.
- The offline invariant remains binding, so visual richness must be achieved with inline CSS, system/self-hosted fonts, texture/pattern CSS, and local assets only.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Replace the global dashboard design with template language | Strong visual unity | Dashboard would become too expressive/noisy for operational workflows |
| Keep current `DESIGN.md` only | Minimal architecture change | Continues producing generic dashboard-like artifacts |
| Copy each template into renderer outputs | Fast visual win | Duplicates CSS, violates standalone rules if copied naively, weak reuse |
| Build one universal artifact theme | Simple naming | Flattens distinct families; loses ticket/dossier/route/investigation craft |
| Make artifact HTML freely editable | Maximum flexibility | Breaks typed contracts, projection safety, re-rendering, and quality gates |
