# Module: web

**Path:** `apps/web`
**Role:** Next.js 16 teacher dashboard — the frontend SPA that provides the UI for creating, monitoring, approving, and exporting teaching packs, plus a live teaching cockpit for classroom sessions.

## Public interface

- **Dashboard routes**: `/runs` (list), `/runs/new` (create), `/runs/[runId]` (detail with SSE), `/units/[parentRunId]` (unit workspace), `/approvals`, `/effectiveness`
- **Editor routes**: `/runs/[runId]/decks/[deckId]/edit` (full-screen slide deck editor)
- **Session routes**: `/sessions/[sessionId]/cockpit` (live teaching cockpit, role-gated via session token)
- `apiClient` — singleton APIClient for all gateway communication (`src/lib/api-client.ts`)
- 24+ custom hooks for teaching pack CRUD, SSE subscriptions, approval flow, live sessions

## Internal structure

- `src/app/` — Next.js App Router with 3 layout groups: `(dashboard)` with sidebar, `(deck-editor)` full-screen, standalone session cockpit
- `src/lib/api-client.ts` — Central API client: cookie JWT auth, X-Request-ID, SSE, idempotency keys
- `src/hooks/` — 24 hooks: `use-teaching-packs.ts` (CRUD + SSE), `use-unit.ts` (unit view + SSE), `use-teaching-session-live.ts` (live session SSE), `use-artifact-versions.ts`, `use-export-status.ts`, etc.
- `src/stores/ui-store.ts` — Zustand: UI-only state (sidebar toggle, theme); never stores server data
- `src/components/` — 49 components across 29 dirs: shadcn UI primitives, slide-deck-editor, teaching-session, methodology, standard-pack
- `src/types/teaching-pack-api.ts` — TypeScript types mirroring gateway API shapes
- `src/middleware.ts` — JWT auth middleware protecting all routes except `/` and `/api/auth`

### State Management
- **Server state**: TanStack Query v5 (staleTime=30s, refetchOnWindowFocus=false)
- **Client state**: Zustand v5 (UI only)
- **Live state**: SSE events folded directly in React state via hooks

## Depends on

- **`schemas`** — imports ArtifactContentSchema, RunContractSchema, + generated types (35 imports)
- **`renderer`** — imports preview rendering functions (3 imports)
- external: `next`, `react`, `@tanstack/react-query`, `@tanstack/react-table`, `zustand`, `react-hook-form`, `zod`, `motion`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`

## Used by

- No internal modules depend on web (leaf module)

## Data & side effects

- Network calls: Gateway API at `NEXT_PUBLIC_GATEWAY_URL` (default `http://localhost:8101` local dev, `http://localhost:8001` Docker)
- SSE channels: `/teaching-packs/runs/{id}/status` (14 event types), `/teaching-sessions/{sessionId}/stream` (7 event types), `/teaching-packs/units/{id}/status`

---

_Traced from source on 2026-07-10. Files examined: all 161 files. The dual API surface (legacy `/run` + authoritative `/teaching-packs`) is a key architectural note._
