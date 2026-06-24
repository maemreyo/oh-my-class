---
title: "Preview Server: PV2 — Dedicated Endpoint, Strict CSP, TTL Store"
status: ready
labels: [renderer, typescript, security, api]
created: 2026-06-24
priority: p1
report: "03"
---

## What to build

A dedicated preview endpoint that serves rendered HTML artifacts at `/api/preview/{run_id}` with strict CSP headers. No `allow-same-origin` + `allow-scripts` together — proper iframe isolation. TTL-based store (1h default) for rendered artifacts.

**Design decision (PV2):** Separate endpoint gives full CSP header control. `sandbox="allow-scripts"` without `allow-same-origin` = strongest iframe isolation. `packages/renderer/src/preview-server/` is its own module: router, store, CSP builder each independently testable. Teacher previews the artifact exactly as students see it.

## File Structure

```
packages/renderer/src/preview-server/
├── index.ts              # mount(): registers routes on Express/Hono app
├── router.ts             # GET /api/preview/:runId route handler
├── store.ts              # PreviewStore: TTL-based artifact cache
├── csp.ts                # buildCSPHeader(artifactType): CSP string
└── iframe-wrapper.ts     # wrapInIframe(url): React/HTML iframe embed code
```

## Implementation Spec

### `preview-server/store.ts`

```ts
/**
 * In-memory TTL store for rendered artifacts awaiting preview.
 * No database — artifacts are transient, expire after TTL.
 */

interface StoredArtifact {
  html:       string
  type:       string
  createdAt:  number   // Date.now()
  ttlMs:      number
}

export class PreviewStore {
  private _store = new Map<string, StoredArtifact>()
  private _ttlMs: number

  constructor(ttlMs = 60 * 60 * 1000) {  // default: 1 hour
    this._ttlMs = ttlMs
  }

  set(runId: string, html: string, type: string): void {
    this._store.set(runId, {
      html,
      type,
      createdAt: Date.now(),
      ttlMs: this._ttlMs,
    })
  }

  get(runId: string): StoredArtifact | null {
    const entry = this._store.get(runId)
    if (!entry) return null

    if (Date.now() - entry.createdAt > entry.ttlMs) {
      this._store.delete(runId)
      return null
    }

    return entry
  }

  delete(runId: string): void {
    this._store.delete(runId)
  }

  purgeExpired(): number {
    let count = 0
    const now = Date.now()
    for (const [id, entry] of this._store) {
      if (now - entry.createdAt > entry.ttlMs) {
        this._store.delete(id)
        count++
      }
    }
    return count
  }
}

// Singleton — shared across all route handlers
export const previewStore = new PreviewStore()
```

### `preview-server/csp.ts`

```ts
import type { ArtifactType } from '../contracts/index.js'

/**
 * CSP headers per artifact type.
 * All types: no external resources (standalone HTML contract).
 * Interactive types (quiz, drill, flashcard_deck): allow-scripts for inline JS.
 * Static types (lesson, recap, answer_key): no-scripts for maximum safety.
 */

const STATIC_TYPES = new Set<ArtifactType>([
  'lesson', 'recap', 'infographic', 'answer_key', 'reading_passage', 'exit_ticket'
])

const INTERACTIVE_TYPES = new Set<ArtifactType>([
  'quiz', 'drill', 'worksheet', 'flashcard_deck'
])

export function buildCSPHeader(type: ArtifactType): string {
  const isInteractive = INTERACTIVE_TYPES.has(type)

  const directives = [
    "default-src 'none'",                           // block everything by default
    "style-src 'unsafe-inline'",                    // CSS custom props + inline styles
    isInteractive ? "script-src 'unsafe-inline'" : "script-src 'none'",
    "img-src data:",                                 // only data URIs (base64)
    "font-src 'none'",                              // system fonts only — no external
    "connect-src 'none'",                           // no fetch/XHR
    "frame-src 'none'",                             // no nested frames
    "object-src 'none'",                            // no plugins
    "base-uri 'none'",                              // no <base> tag
    "form-action 'none'",                           // no form submissions
  ]

  return directives.join('; ')
}

export function buildSandboxAttribute(type: ArtifactType): string {
  const isInteractive = INTERACTIVE_TYPES.has(type)
  // Critical: never combine allow-scripts + allow-same-origin
  // allow-same-origin alone = read session cookies (bad)
  // allow-scripts alone = run JS but can't access parent DOM (safe)
  if (isInteractive) {
    return 'allow-scripts allow-forms'
  }
  return 'allow-scripts'    // even static types need minimal scripts for theming
}
```

### `preview-server/router.ts`

```ts
import type { Request, Response } from 'express'
import { previewStore } from './store.js'
import { buildCSPHeader } from './csp.js'
import type { ArtifactType } from '../contracts/index.js'

export function handlePreviewRequest(req: Request, res: Response): void {
  const { runId } = req.params
  const artifact = previewStore.get(runId)

  if (!artifact) {
    res.status(404).json({ error: 'Preview expired or not found', runId })
    return
  }

  const csp = buildCSPHeader(artifact.type as ArtifactType)

  res
    .setHeader('Content-Type', 'text/html; charset=utf-8')
    .setHeader('Content-Security-Policy', csp)
    .setHeader('X-Frame-Options', 'SAMEORIGIN')      // only our own UI can iframe it
    .setHeader('X-Content-Type-Options', 'nosniff')
    .setHeader('Cache-Control', 'no-store')           // never cache preview in browser
    .status(200)
    .send(artifact.html)
}
```

### `preview-server/index.ts`

```ts
import type { Application } from 'express'
import { handlePreviewRequest } from './router.js'
import { previewStore } from './store.js'

export { previewStore }

export function mountPreviewServer(app: Application): void {
  app.get('/api/preview/:runId', handlePreviewRequest)
}

// Periodic cleanup — purge expired artifacts every 30 minutes
let _cleanupInterval: ReturnType<typeof setInterval> | null = null

export function startCleanup(intervalMs = 30 * 60 * 1000): void {
  _cleanupInterval = setInterval(() => {
    const purged = previewStore.purgeExpired()
    if (purged > 0) console.info(`[preview-server] Purged ${purged} expired artifacts`)
  }, intervalMs)
}

export function stopCleanup(): void {
  if (_cleanupInterval) clearInterval(_cleanupInterval)
}
```

### `preview-server/iframe-wrapper.ts`

```ts
import { buildSandboxAttribute } from './csp.js'
import type { ArtifactType } from '../contracts/index.js'

/**
 * Returns HTML for embedding the preview iframe in the teacher dashboard.
 * Used by the frontend — renders iframe with correct sandbox attribute.
 */
export function buildIframeEmbed(runId: string, type: ArtifactType): string {
  const sandbox = buildSandboxAttribute(type)
  const src = `/api/preview/${runId}`

  return `
<iframe
  src="${src}"
  sandbox="${sandbox}"
  title="Artifact preview"
  class="artifact-preview-frame"
  loading="lazy"
  style="width:100%; height:100%; border:none; border-radius:var(--radius-md)"
  aria-label="Preview of generated artifact"
></iframe>`
}
```

### How preview is triggered from gate nodes

```ts
// packages/agents/gates/gate_02_content.ts

import { previewStore } from 'packages/renderer/src/preview-server/index.js'
import { renderArtifact } from 'packages/renderer/src/renderer.js'

async function gate_02_content_approval(state: OhMyClassState) {
  // Render each artifact and store for preview
  for (const artifact of state.artifacts) {
    const html = await renderArtifact(artifact.type, artifact.data)
    previewStore.set(`${state.run_id}:${artifact.id}`, html, artifact.type)
  }

  // Notify teacher (SSE + Telegram)
  await dispatcher.notify(ApprovalEvent({
    ...
    approve_url: `${settings.app_url}/runs/${state.run_id}`,
  }))

  // HITL interrupt
  const response = interrupt({ run_id: state.run_id, artifacts: state.artifacts })
  ...
}
```

## Tests

```ts
// __tests__/preview-server.test.ts

import { PreviewStore } from '../src/preview-server/store.js'
import { buildCSPHeader, buildSandboxAttribute } from '../src/preview-server/csp.js'

test('store returns artifact before TTL', () => {
  const store = new PreviewStore(60_000)
  store.set('r1', '<html>test</html>', 'quiz')
  expect(store.get('r1')?.html).toBe('<html>test</html>')
})

test('store returns null after TTL expired', async () => {
  const store = new PreviewStore(1)   // 1ms TTL
  store.set('r2', '<html>x</html>', 'quiz')
  await new Promise(r => setTimeout(r, 10))
  expect(store.get('r2')).toBeNull()
})

test('purgeExpired removes expired entries', async () => {
  const store = new PreviewStore(1)
  store.set('r3', '<html>x</html>', 'quiz')
  store.set('r4', '<html>y</html>', 'lesson')
  await new Promise(r => setTimeout(r, 10))
  const count = store.purgeExpired()
  expect(count).toBe(2)
})

test('CSP for interactive type includes script-src unsafe-inline', () => {
  const csp = buildCSPHeader('quiz')
  expect(csp).toContain("script-src 'unsafe-inline'")
})

test('CSP for static type blocks scripts', () => {
  const csp = buildCSPHeader('lesson')
  expect(csp).toContain("script-src 'none'")
})

test('CSP blocks all external resources for all types', () => {
  for (const type of ['quiz', 'lesson', 'infographic'] as const) {
    const csp = buildCSPHeader(type)
    expect(csp).toContain("default-src 'none'")
    expect(csp).toContain("connect-src 'none'")
    expect(csp).toContain("img-src data:")
  }
})

test('sandbox attribute never combines allow-scripts + allow-same-origin', () => {
  for (const type of ['quiz', 'lesson', 'drill', 'flashcard_deck'] as const) {
    const sandbox = buildSandboxAttribute(type)
    const hasScripts = sandbox.includes('allow-scripts')
    const hasSameOrigin = sandbox.includes('allow-same-origin')
    expect(hasScripts && hasSameOrigin).toBe(false)  // never both
  }
})
```

## Acceptance Criteria

- [ ] `PreviewStore` — `set()/get()/delete()/purgeExpired()`, TTL-based expiry
- [ ] `get()` returns `null` after TTL, never throws
- [ ] `buildCSPHeader()` — interactive types get `script-src 'unsafe-inline'`, static types get `script-src 'none'`
- [ ] All types: `default-src 'none'`, `connect-src 'none'`, `img-src data:`
- [ ] `buildSandboxAttribute()` — NEVER produces `allow-scripts` + `allow-same-origin` together
- [ ] Route handler returns `404` for expired/missing run IDs
- [ ] `X-Frame-Options: SAMEORIGIN` — only dashboard can embed preview
- [ ] `Cache-Control: no-store` — never cached in browser
- [ ] `mountPreviewServer(app)` registers the route, `startCleanup()` starts periodic purge

## Dependencies

- Blocked by: `html-template-system` (renderArtifact), `sanitizer-module` (sanitized HTML stored)
- Blocks: `hitl-gate-wrapper` update (gate_02 stores rendered artifacts before interrupt)
- Priority: p1
