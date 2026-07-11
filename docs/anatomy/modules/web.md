# Module: web

**Path:** `apps/web`
**Role:** Next.js 16 teacher dashboard — the frontend SPA that provides the UI for creating, monitoring, approving, and exporting teaching packs, plus a live teaching cockpit for classroom sessions.

## Public interface

- **Dashboard routes**: `/runs` (list), `/runs/new` (create), `/runs/[runId]` (detail with SSE), `/units/[parentRunId]` (unit workspace), `/approvals`, `/effectiveness`
- **Editor routes**: `/runs/[runId]/decks/[deckId]/edit` (full-screen slide deck editor)
- **Session routes**: `/sessions/[sessionId]/cockpit` (live teaching cockpit, role-gated via session token)
- `apiClient` — singleton APIClient for all gateway communication (`src/lib/api-client.ts:130`)
- 14 custom hooks in `src/hooks/` for teaching pack CRUD, SSE subscriptions, approval flow, live sessions

## Internal structure

### App Router (`src/app/`)
- `(dashboard)/layout.tsx` — Dashboard layout with sidebar, ErrorBoundary wrapper
- `(dashboard)/runs/page.tsx` — Runs list with client-side filtering (`filter-runs.ts`)
- `(dashboard)/runs/new/page.tsx` — Teaching brief creator (TSP-01)
- `(dashboard)/runs/[runId]/page.tsx` — Run detail with `TeachingPacksGateShell` + SSE status
- `(dashboard)/approvals/page.tsx` — Pending approvals list
- `(dashboard)/effectiveness/page.tsx` — Effectiveness metrics
- `(dashboard)/units/[parentRunId]/page.tsx` — Unit workspace with session cards
- `(deck-editor)/layout.tsx` — Full-screen editor layout (no sidebar)
- `(deck-editor)/runs/[runId]/decks/[deckId]/edit/page.tsx` — Slide deck editor (SDE-03)
- `sessions/[sessionId]/cockpit/page.tsx` — Live teaching cockpit (role-gated)
- `error.tsx` / `global-error.tsx` / `not-found.tsx` — Error handling chain

### HTTP Client (`src/lib/api-client.ts`)
```typescript
const GATEWAY_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8101";
export const apiClient = new APIClient(GATEWAY_URL);
```
- Cookie-based JWT auth (reads `auth-token` from cookies)
- X-Request-ID tracing via `crypto.randomUUID()`
- Methods: `get<T>`, `post<T>`, `put<T>`, `patch<T>`, `postForm<T>`
- Idempotency keys on teaching pack creation (`Idempotency-Key` header)

### Hooks (`src/hooks/`)
| Hook | File | Purpose |
|------|------|---------|
| `use-teaching-packs.ts` | CRUD + SSE status stream | Core teaching pack operations |
| `use-teaching-brief.ts` | Brief CRUD + launch | TSP-01 brief creator flow |
| `use-teaching-session-live.ts` | Live session SSE + state reducer | Classroom cockpit |
| `use-unit.ts` | Unit view + SSE + actions | Multi-session unit workspace |
| `use-artifact.ts` | Artifact fetching | Artifact preview |
| `use-artifact-versions.ts` | Version history (SDE-05) | Artifact versioning |
| `use-approval.ts` | Approve/reject/edit mutations | Gate interactions |
| `use-export-status.ts` | Export staleness detection | SDE-06 |
| `use-error-logger.ts` | Error logging + `/webhook/error` POST | Client error reporting |
| `use-pacing-nudge-preference.ts` | TSP-04 pacing preference | Live session config |
| `use-run.ts` | Legacy run CRUD | Pre-decommission surface |

### State Management
- **Server state**: TanStack Query v5 (`staleTime=30s`, `refetchOnWindowFocus=false`)
- **Client state**: Zustand v5 (`stores/ui-store.ts` — sidebar toggle, theme only)
- **Live state**: SSE events folded directly in React state via hooks + `teaching-session-live-reducer.ts`

### Components (`src/components/`)
- `teaching-packs-gate-shell.tsx` — Gate interaction orchestrator (dispatches to gate-specific bodies)
- `teaching-packs-gate-bodies.tsx` — Gate body rendering by type
- `teaching-packs-content-approval-body.tsx` — Content approval gate body
- `teaching-packs-slide-deck-preview.tsx` — Slide deck preview + scoped feedback
- `teaching-packs-scoped-rejection.tsx` — Artifact rejection + section editor
- `teaching-packs-strategy-panel.tsx` — Component strategy variant display
- `teaching-packs-trust-panel.tsx` — Trust score / fast-lane auto-approve revert
- `teaching-packs-stage-progress.tsx` — Pipeline stage progress bar
- `slide-deck-editor/` — Full slide deck editor (SDE-03): deck-editor, deck-save, block-constraints, draft store, version history
- `methodology/` — Methodology picker: mode-registry, mode-surfaces, detail-panels
- `teaching-session/` — Live cockpit: teaching-cockpit.tsx, teaching-cockpit-logic.ts
- `vocabulary-batch-*.tsx` — Vocabulary batch review/normalization UI
- `ui/` — shadcn primitives (button, card, dialog, input, table, badge)

## Depends on

- **`schemas`** — 18 type imports + 1 runtime Zod import in production code; ArtifactContent, SlideDeckData, SemanticAnchorCluster

### @oh-my-class/schemas (type-only imports + 1 runtime Zod import)

**Type imports (erased at compile, no Turbopack issue):**

| File:Line | Types imported |
|-----------|---------------|
| `types/index.ts:5-10` | `Artifact`, `ArtifactContent`, `LessonPlan`, `Run` |
| `components/slide-deck-editor/deck-editor.tsx:4` | `SlideDeckData`, `SlideDeckSlide` |
| `components/slide-deck-editor/deck-draft-store.ts:1` | `SlideDeckData` |
| `components/slide-deck-editor/deck-save.ts:1` | `SlideDeckBlock`, `SlideDeckData` |
| `components/slide-deck-editor/use-deck-editor-draft.ts:4` | `SlideDeckData` |
| `components/slide-deck-editor/slide-canvas.tsx:3` | `SlideDeckBlock`, `SlideDeckInteraction`, `SlideDeckSlide` |
| `components/slide-deck-editor/slide-block-editor.tsx:4` | `SlideDeckBlock` |
| `components/slide-deck-editor/block-rewrite-controls.tsx:4` | `SlideDeckBlock` |
| `components/slide-deck-editor/quick-check-interaction.tsx:3` | `SlideDeckInteraction` |
| `components/slide-deck-editor/blocks/heading-block.tsx:3` | `SlideDeckBlock` |
| `components/slide-deck-editor/blocks/paragraph-block.tsx:3` | `SlideDeckBlock` |
| `components/slide-deck-editor/blocks/callout-block.tsx:3` | `SlideDeckBlock` |
| `components/slide-deck-editor/blocks/image-block.tsx:4` | `SlideDeckBlock`, `SlideDeckMedia` |
| `components/slide-deck-editor/blocks/interaction-prompt-block.tsx:3` | `SlideDeckBlock` |
| `components/slide-deck-editor/blocks/media-library-picker.tsx:4` | `SlideDeckMedia` |
| `app/(deck-editor)/runs/[runId]/decks/[deckId]/edit/page.tsx:5` | `SlideDeckData` |
| `components/vocabulary-batch-dashboard.tsx:1` | `SemanticAnchorCluster` |
| `components/vocabulary-batch-normalization-preview.tsx:1` | `InputNormalizationReport` |

**Runtime Zod value import (production code):**

| File:Line | Import |
|-----------|--------|
| `components/vocabulary-batch-review-editor.tsx:5` | `SemanticAnchorClusterSchema` |

**Zod value imports in test files only** (Vitest, not Turbopack): `SlideDeckBlockSchema`, `SlideDeckDataSchema`, `SlideDeckInteractionSchema`, `SlideDeckMediaSchema` — all in `.test.ts` files.

### Direct path imports bypassing workspace package

| File:Line | Import path |
|-----------|-------------|
| `components/methodology/mode-registry.ts:1` | `../../../../../common/schemas/src/generated/methodology_registry` → `METHODOLOGY_REGISTRY` |
| `components/methodology/mode-registry.ts:2` | `../../../../../common/schemas/src/generated/lesson_plan` → `MethodologyMetadata` |

These bypass `@oh-my-class/schemas` because the generated methodology registry isn't re-exported from the package's public API. `block-constraints.ts` documents the Turbopack limitation: type-only imports work, but value imports of untranspiled workspace packages fail.

### @oh-my-class/renderer

**Listed as workspace dependency in `package.json:17` but NEVER imported in any source file.** Zero runtime or type imports exist. This is either a dead dependency or a peer dependency for build tooling.

### External dependencies

`next`, `react`, `@tanstack/react-query`, `@tanstack/react-table`, `zustand`, `react-hook-form`, `zod`, `motion`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`

## Used by

_No confirmed callers discovered during this trace._

- **No internal modules** — web is a leaf module in the dependency graph.

## Data & side effects

- **Network:** Gateway API at `NEXT_PUBLIC_GATEWAY_URL` (default `http://localhost:8101` local dev, `http://localhost:8001` Docker)
- **SSE channels:**
  - `/teaching-packs/runs/{id}/status` — teaching pack pipeline events
  - `/teaching-sessions/{sessionId}/stream` — live session events
  - `/teaching-packs/units/{id}/status` — unit progress events
  - `/run/{runId}/status` — legacy run status (pre-decommission)
- **Error reporting:** `POST /webhook/error` with `{ component, error_message, stack, extra, timestamp }`
- **Client storage:** localStorage for slide deck draft persistence (`deck-draft-store.ts`)
- **Cookie:** `auth-token` for JWT authentication

## Notes / discrepancies vs existing docs

- **Phase 3 hypothesis "web → renderer: 3 imports" is WRONG.** Renderer is listed in `package.json` but has **zero imports** in source code. It's a dead dependency or build-time peer dependency.
- **Phase 3 hypothesis "web → schemas: 35 imports" is approximately correct.** I count 18 type-only imports in production code + 12 Zod imports in test files + 2 direct-path imports = ~32 total import sites. The previous count of 35 may include test files.
- **Two imports bypass the `@oh-my-class/schemas` package** via relative paths into `common/schemas/src/generated/` (`mode-registry.ts:1-2`). This should be fixed by re-exporting from the package barrel.
- **Gateway port:** local dev = `:8101` (confirmed at `api-client.ts:7`), Docker = `:8001` (via `NEXT_PUBLIC_GATEWAY_URL` in `docker-compose.yml:134`).
- **Legacy `/run/*` API surface** still exists alongside authoritative `/teaching-packs/*` — both hooks and gateway routes are present.
- The `use-error-logger.ts` webhook endpoint (`/webhook/error`) is a simple error reporting sink — not related to the notification system.

---
_Traced from source on 2026-07-11. Files examined in depth: all 162 files in apps/web/src. Key findings: renderer dependency is dead (0 imports), methodology/mode-registry.ts bypasses workspace package with direct paths, only 1 runtime Zod import in production code._
