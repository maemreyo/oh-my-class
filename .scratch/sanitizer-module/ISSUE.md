---
title: "Sanitizer Module: SA4 — sanitize-html Server-side + DOMPurify Client-side"
status: ready
labels: [security, renderer, typescript]
created: 2026-06-24
priority: p0
report: "03"
---

## What to build

Two-layer HTML sanitization: `sanitize-html` (Node.js, no jsdom) on the server with per-template allowlist configs, and DOMPurify loaded in the preview iframe for client-side defense-in-depth.

**Design decisions:**
- **SA4**: Server-side `sanitize-html` (allowlist per artifact type) + client-side DOMPurify in preview iframe
- **Modular**: each artifact type has its own allowlist config file in `sanitizer/configs/`
- **No jsdom**: `sanitize-html` works without a DOM environment

## File Structure

```
packages/renderer/src/sanitizer/
├── index.ts              # sanitize(html, type): string — main entry point
├── base-config.ts        # shared baseline allowlist (common safe tags)
├── configs/
│   ├── lesson.ts         # extends base + <section> <aside> <figure> + vocab tags
│   ├── quiz.ts           # extends base + <fieldset> <legend> <input type=radio>
│   ├── drill.ts          # extends base + quiz config
│   ├── worksheet.ts      # extends base + <input> <textarea> + answer lines
│   ├── recap.ts          # extends base + summary tags
│   ├── infographic.ts    # extends base + <svg> <path> <g> <text> <circle> <rect>
│   ├── answer_key.ts     # extends quiz config + teacher-only elements
│   ├── flashcard_deck.ts # extends base + flip card markup
│   ├── reading_passage.ts # extends base + passage markup
│   └── exit_ticket.ts    # extends base + form elements
└── client-side-loader.ts # generates <script> block that loads DOMPurify in iframe
```

## Implementation Spec

### `sanitizer/base-config.ts`

```ts
import type { IOptions } from 'sanitize-html'

/**
 * Baseline allowlist used by all artifact types.
 * Each type extends this — never restricts below it.
 */
export const BASE_CONFIG: IOptions = {
  allowedTags: [
    // structure
    'html', 'head', 'body', 'main', 'header', 'footer', 'section', 'article', 'aside', 'nav',
    // headings + text
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'strong', 'em', 'b', 'i', 'u', 's',
    // lists
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    // tables
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'colgroup', 'col',
    // media (inline only — src must be data: URI or relative)
    'img', 'figure', 'figcaption',
    // semantic
    'blockquote', 'pre', 'code', 'abbr', 'mark', 'time', 'cite', 'q',
    // layout
    'div', 'br', 'hr',
    // meta (for base.html <head>)
    'meta', 'title', 'style', 'link',
  ],
  allowedAttributes: {
    '*': ['class', 'id', 'lang', 'dir', 'aria-label', 'aria-labelledby',
          'aria-describedby', 'aria-hidden', 'aria-expanded', 'aria-controls',
          'aria-live', 'aria-checked', 'role', 'tabindex', 'data-*'],
    'a':    ['href'],   // href validated below
    'img':  ['src', 'alt', 'loading', 'decoding', 'width', 'height'],
    'meta': ['charset', 'name', 'content', 'http-equiv'],
    'link': ['rel', 'type'],
    'time': ['datetime'],
    'td':   ['colspan', 'rowspan'],
    'th':   ['colspan', 'rowspan', 'scope'],
    'col':  ['span'],
  },
  allowedSchemes: ['data'],     // block http/https — no external assets
  allowedSchemesAppliedToAttributes: ['src', 'href'],
  exclusiveFilter: (frame) => {
    // block any element that sneaks in an external URL
    if (frame.attribs.src && !frame.attribs.src.startsWith('data:')) return true
    if (frame.attribs.href && frame.attribs.href.startsWith('http')) return true
    return false
  },
}
```

### `sanitizer/configs/quiz.ts`

```ts
import type { IOptions } from 'sanitize-html'
import { BASE_CONFIG } from '../base-config.js'
import merge from 'lodash-es/merge.js'

export const QUIZ_CONFIG: IOptions = merge({}, BASE_CONFIG, {
  allowedTags: [
    ...BASE_CONFIG.allowedTags!,
    'fieldset', 'legend', 'label', 'input', 'button',
  ],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    'input': ['type', 'name', 'value', 'checked', 'disabled', 'id'],
    'label': ['for'],
    'button': ['type', 'aria-expanded', 'aria-controls', 'onclick', 'id'],
  },
})
```

### `sanitizer/configs/infographic.ts`

```ts
import type { IOptions } from 'sanitize-html'
import { BASE_CONFIG } from '../base-config.js'
import merge from 'lodash-es/merge.js'

// SVG tags needed for inline charts and concept maps
const SVG_TAGS = [
  'svg', 'g', 'path', 'circle', 'rect', 'line', 'polyline', 'polygon',
  'text', 'tspan', 'defs', 'linearGradient', 'stop', 'clipPath', 'use',
  'symbol', 'title', 'desc',
]

export const INFOGRAPHIC_CONFIG: IOptions = merge({}, BASE_CONFIG, {
  allowedTags: [...BASE_CONFIG.allowedTags!, ...SVG_TAGS],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    'svg':  ['xmlns', 'viewBox', 'width', 'height', 'aria-label', 'role'],
    'path': ['d', 'fill', 'stroke', 'stroke-width'],
    'g':    ['transform', 'fill', 'stroke'],
    'text': ['x', 'y', 'text-anchor', 'dominant-baseline', 'fill', 'font-size'],
    'circle': ['cx', 'cy', 'r', 'fill', 'stroke'],
    'rect': ['x', 'y', 'width', 'height', 'rx', 'ry', 'fill', 'stroke'],
    'line': ['x1', 'y1', 'x2', 'y2', 'stroke', 'stroke-width'],
    'linearGradient': ['id', 'x1', 'y1', 'x2', 'y2'],
    'stop': ['offset', 'stop-color', 'stop-opacity'],
    'use':  ['href', 'x', 'y', 'width', 'height'],
  },
})
```

### `sanitizer/index.ts`

```ts
import sanitizeHtml from 'sanitize-html'
import type { ArtifactType } from '../contracts/index.js'
import { BASE_CONFIG } from './base-config.js'
import { QUIZ_CONFIG } from './configs/quiz.js'
import { INFOGRAPHIC_CONFIG } from './configs/infographic.js'
// ... other configs

const CONFIG_MAP: Record<ArtifactType, import('sanitize-html').IOptions> = {
  lesson:          BASE_CONFIG,
  quiz:            QUIZ_CONFIG,
  drill:           QUIZ_CONFIG,
  worksheet:       WORKSHEET_CONFIG,
  recap:           BASE_CONFIG,
  infographic:     INFOGRAPHIC_CONFIG,
  answer_key:      QUIZ_CONFIG,
  flashcard_deck:  BASE_CONFIG,
  reading_passage: BASE_CONFIG,
  exit_ticket:     WORKSHEET_CONFIG,
}

export function sanitize(html: string, type: ArtifactType): string {
  const config = CONFIG_MAP[type] ?? BASE_CONFIG
  return sanitizeHtml(html, config)
}
```

### `sanitizer/client-side-loader.ts`

```ts
/**
 * Returns a <script> block that loads DOMPurify inside the preview iframe.
 * Injected by the preview-server into the served HTML response.
 * DOMPurify runs after the page loads — second sanitization pass.
 */
export function buildDOMPurifyScript(): string {
  return `
<script>
(function() {
  // Inline DOMPurify (minified, ~42KB) — no CDN
  // Content replaced by build step: npm run embed:dompurify
  /* __DOMPURIFY_INLINE__ */

  if (typeof DOMPurify !== 'undefined') {
    document.querySelectorAll('[data-sanitize]').forEach(el => {
      el.innerHTML = DOMPurify.sanitize(el.innerHTML, {
        ALLOWED_TAGS: ['b','i','em','strong','p','br','span'],
        ALLOWED_ATTR: ['class'],
      })
    })
  }
})()
</script>`
}
```

## Tests

```ts
// __tests__/sanitizer.test.ts

import { sanitize } from '../src/sanitizer/index.js'

test('blocks script tags', () => {
  const result = sanitize('<p>text</p><script>alert(1)</script>', 'lesson')
  expect(result).not.toContain('<script>')
})

test('blocks external image src', () => {
  const result = sanitize('<img src="https://evil.com/img.png" alt="x">', 'lesson')
  expect(result).not.toContain('https://evil.com')
})

test('allows data URI images', () => {
  const result = sanitize('<img src="data:image/png;base64,abc" alt="x">', 'lesson')
  expect(result).toContain('data:image/png')
})

test('quiz config allows radio inputs', () => {
  const result = sanitize('<input type="radio" name="q1" value="A">', 'quiz')
  expect(result).toContain('<input')
  expect(result).toContain('type="radio"')
})

test('lesson config blocks radio inputs', () => {
  const result = sanitize('<input type="radio" name="q1" value="A">', 'lesson')
  expect(result).not.toContain('<input')
})

test('infographic config allows SVG', () => {
  const svg = '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'
  const result = sanitize(svg, 'infographic')
  expect(result).toContain('<svg')
  expect(result).toContain('<circle')
})

test('blocks inline event handlers', () => {
  const result = sanitize('<div onclick="evil()">text</div>', 'lesson')
  // onclick is not in allowedAttributes for div — stripped
  expect(result).not.toContain('onclick')
})
```

## Acceptance Criteria

- [ ] `base-config.ts` — shared baseline, blocks all external URLs
- [ ] One config file per artifact type in `configs/`
- [ ] `sanitize()` selects correct config by artifact type
- [ ] Script tags stripped from all artifact types
- [ ] External `src` / `href` blocked (only `data:` URIs allowed)
- [ ] `infographic` config allows SVG tags, others do not
- [ ] `quiz`/`worksheet` configs allow form elements, `lesson` does not
- [ ] `client-side-loader.ts` generates DOMPurify script block (with inline embed placeholder)
- [ ] All tests pass with zero LLM dependency

## Dependencies

- Blocked by: `html-template-system` (ArtifactType import)
- Blocks: `html-template-system` (renderer.ts calls `sanitize()`)
- Priority: p0
