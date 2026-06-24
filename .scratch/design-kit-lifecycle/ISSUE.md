---
title: "Design Kit Lifecycle: DK4 — Regex Fast Path + f.light Fallback for HTML Import"
status: ready
labels: [renderer, typescript, branding, ui]
created: 2026-06-24
priority: p1
report: "03"
---

## What to build

Teacher imports their own HTML → system extracts CSS tokens → proposes `ThemeTokens` → teacher reviews → saved as named `theme.json`. Hybrid approach: regex extracts CSS custom properties fast, f.light LLM fallback for HTML without CSS vars.

**Design decision (DK4):**
- Fast path: regex on `:root { --var: value }` blocks — covers HTML like `template.html` (already uses CSS vars)
- LLM fallback (f.light): when regex finds < 3 tokens — parses hardcoded hex/rgb values
- Output includes `{ method: 'regex' | 'llm', tokens: ThemeTokens, confidence: number }` — auditable

## File Structure

```
packages/renderer/src/design-kit/
├── index.ts              # importDesignKit(html, options?): Promise<ImportResult>
├── extractor.ts          # extractCSSTokens(html): CSSVar[] — pure regex, no LLM
├── mapper.ts             # mapToThemeTokens(vars): Partial<ThemeTokens> — pure fn
├── llm-extractor.ts      # llmExtractTokens(html, llmClient): ThemeTokens — f.light
├── proposer.ts           # proposeThemeJSON(partial): ThemeTokens — fills gaps with defaults
└── validator.ts          # validateThemeTokens(tokens): ValidationResult
```

## Implementation Spec

### `design-kit/extractor.ts`

```ts
/**
 * Pure regex extraction of CSS custom properties from :root {} blocks.
 * No LLM, no DOM — works on any HTML string.
 */

export interface CSSVar {
  name:    string    // e.g. "--paper"
  value:   string    // e.g. "#FBF4F0"
  source:  string    // the :root rule it was found in
}

// Matches :root { ... } blocks (handles multiline)
const ROOT_BLOCK_RE = /:root\s*\{([^}]+)\}/gs

// Matches --var-name: value; pairs
const CSS_VAR_RE = /--([a-zA-Z0-9-]+)\s*:\s*([^;]+);/g

export function extractCSSVars(html: string): CSSVar[] {
  const vars: CSSVar[] = []
  let rootMatch: RegExpExecArray | null

  while ((rootMatch = ROOT_BLOCK_RE.exec(html)) !== null) {
    const block = rootMatch[1]
    let varMatch: RegExpExecArray | null

    while ((varMatch = CSS_VAR_RE.exec(block)) !== null) {
      vars.push({
        name:   `--${varMatch[1]}`,
        value:  varMatch[2].trim(),
        source: rootMatch[0].slice(0, 30) + '...',
      })
    }
  }

  return vars
}
```

### `design-kit/mapper.ts`

```ts
/**
 * Map extracted CSS vars to ThemeTokens semantic fields.
 * Heuristic: matches common naming patterns (--paper, --ink, --color-*, --bg-*, etc.)
 */
import type { ThemeTokens } from '../theme/tokens.js'
import type { CSSVar } from './extractor.js'

// Heuristic patterns for well-known CSS var names → semantic token fields
const SEMANTIC_MAP: Array<{ patterns: RegExp[]; key: keyof ThemeTokens['semantic'] }> = [
  { patterns: [/--paper$/, /--bg$/, /--background$/],                 key: 'colorBg' },
  { patterns: [/--card$/, /--surface$/, /--bg-card$/],                key: 'colorBgCard' },
  { patterns: [/--paper-deep$/, /--bg-deep$/],                        key: 'colorBgDeep' },
  { patterns: [/--ink$/, /--text$/, /--foreground$/],                 key: 'colorText' },
  { patterns: [/--ink-soft$/, /--text-soft$/, /--text-secondary$/],   key: 'colorTextSoft' },
  { patterns: [/--ink-faint$/, /--text-faint$/, /--text-muted$/],     key: 'colorTextFaint' },
  { patterns: [/--line$/, /--border$/],                               key: 'colorBorder' },
  { patterns: [/--line-soft$/, /--border-soft$/],                     key: 'colorBorderSoft' },
  { patterns: [/--red$/, /--accent$/, /--primary$/],                  key: 'colorAccent' },
  { patterns: [/--red-deep$/, /--accent-deep$/, /--primary-deep$/],   key: 'colorAccentDeep' },
  { patterns: [/--green$/, /--success$/],                             key: 'colorSuccess' },
  { patterns: [/--gold$/, /--warning$/],                              key: 'colorWarning' },
]

export function mapToSemanticTokens(
  vars: CSSVar[],
): Partial<ThemeTokens['semantic']> {
  const result: Partial<ThemeTokens['semantic']> = {}

  for (const { patterns, key } of SEMANTIC_MAP) {
    const match = vars.find(v => patterns.some(p => p.test(v.name)))
    if (match) (result as Record<string, unknown>)[key] = match.value
  }

  // Category colors: --c-a, --c-b, etc. or --color-category-a
  const categoryColors: Record<string, { base: string; tint: string }> = {}
  for (const v of vars) {
    const m = v.name.match(/--c-([a-e])$/) ?? v.name.match(/--color-category-([a-e])$/)
    if (m) {
      const letter = m[1]
      categoryColors[letter] = categoryColors[letter] ?? { base: v.value, tint: `rgba(0,0,0,0.1)` }
      categoryColors[letter].base = v.value
    }
    // tint variants: --c-a-tint → rgba(...)
    const tintM = v.name.match(/--c-([a-e])-tint$/)
    if (tintM) {
      const letter = tintM[1]
      categoryColors[letter] = categoryColors[letter] ?? { base: '#000', tint: v.value }
      categoryColors[letter].tint = v.value
    }
  }
  if (Object.keys(categoryColors).length > 0) result.categoryColors = categoryColors

  return result
}
```

### `design-kit/proposer.ts`

```ts
/**
 * Fill gaps in partial ThemeTokens with sensible defaults.
 * Returns a complete ThemeTokens ready to save as theme.json.
 */
import type { ThemeTokens } from '../theme/tokens.js'
import defaultTheme from '../theme/themes/default.json' assert { type: 'json' }

export function proposeThemeJSON(
  partial: Partial<ThemeTokens['semantic']>,
  name: string,
): ThemeTokens {
  return {
    name,
    primitives: defaultTheme.primitives,   // preserve default type scale, spacing
    semantic: {
      ...defaultTheme.semantic,            // fill unrecognized vars with default values
      ...partial,                          // overlay extracted vars
    },
  }
}
```

### `design-kit/llm-extractor.ts`

```ts
/**
 * LLM-based token extraction — f.light fallback for HTML without CSS custom properties.
 * Only called when extractCSSVars() finds < 3 tokens.
 */
import type { ThemeTokens } from '../theme/tokens.js'

const EXTRACT_PROMPT = `You are a CSS design token extractor.

Analyze the following HTML and extract its visual design tokens.
Look for background colors, text colors, accent colors, border colors, and font families.
Map them to this schema:
- colorBg: main page background color
- colorBgCard: card/surface background color
- colorText: primary text color
- colorTextSoft: secondary/muted text color
- colorAccent: primary accent/brand color

Return ONLY valid JSON matching this structure:
{
  "colorBg": "#hex",
  "colorBgCard": "#hex",
  "colorText": "#hex",
  "colorTextSoft": "#hex",
  "colorAccent": "#hex"
}

HTML (first 8000 chars):
{html_excerpt}`

export async function llmExtractTokens(
  html: string,
  llmClient: { chat: (opts: unknown) => Promise<{ content: string }> },
): Promise<Partial<ThemeTokens['semantic']>> {
  const excerpt = html.slice(0, 8000)  // first 8KB sufficient for style block
  const response = await llmClient.chat({
    model: 'f.light',                  // cheap — extraction is simple mapping
    messages: [{ role: 'user', content: EXTRACT_PROMPT.replace('{html_excerpt}', excerpt) }],
    temperature: 0.0,
  })

  return JSON.parse(response.content)
}
```

### `design-kit/index.ts`

```ts
import { extractCSSVars } from './extractor.js'
import { mapToSemanticTokens } from './mapper.js'
import { llmExtractTokens } from './llm-extractor.js'
import { proposeThemeJSON } from './proposer.js'
import { validateThemeTokens } from './validator.js'
import type { ThemeTokens } from '../theme/tokens.js'

export interface ImportResult {
  method:     'regex' | 'llm'
  tokens:     ThemeTokens
  confidence: number    // 0.0–1.0: % of semantic fields successfully extracted
  warnings:   string[]  // fields that fell back to defaults
}

const MIN_VARS_FOR_REGEX = 3

export async function importDesignKit(
  html: string,
  options: {
    name?: string
    llmClient?: { chat: (opts: unknown) => Promise<{ content: string }> }
  } = {},
): Promise<ImportResult> {
  const name = options.name ?? 'custom'
  let method: 'regex' | 'llm' = 'regex'
  let extracted: Partial<ThemeTokens['semantic']>

  // Fast path: regex extraction
  const vars = extractCSSVars(html)
  const partial = mapToSemanticTokens(vars)
  const extractedCount = Object.keys(partial).length

  if (extractedCount < MIN_VARS_FOR_REGEX && options.llmClient) {
    // Fallback: f.light LLM extraction
    method = 'llm'
    extracted = await llmExtractTokens(html, options.llmClient)
  } else {
    extracted = partial
  }

  const tokens = proposeThemeJSON(extracted, name)
  const validation = validateThemeTokens(tokens)

  const TOTAL_SEMANTIC_FIELDS = 10  // colorBg, colorText, colorAccent, etc.
  const filledCount = Object.keys(extracted).length
  const confidence = Math.min(filledCount / TOTAL_SEMANTIC_FIELDS, 1.0)

  const warnings = validation.missing.map(
    field => `${field} not found in source HTML — using default value`
  )

  return { method, tokens, confidence, warnings }
}
```

## Tests

```ts
// __tests__/design-kit.test.ts

import { extractCSSVars } from '../src/design-kit/extractor.js'
import { importDesignKit } from '../src/design-kit/index.js'

const TEMPLATE_HTML_EXCERPT = `
<style>
:root {
  --paper: #FBF4F0;
  --ink: #22273A;
  --red: #B23A2E;
  --gold: #A8782E;
  --green: #2E6F4E;
  --c-a: #33508F;
  --c-a-tint: rgba(51,80,143,0.08);
}
</style>
`

test('extractCSSVars finds all vars in :root block', () => {
  const vars = extractCSSVars(TEMPLATE_HTML_EXCERPT)
  expect(vars.length).toBeGreaterThanOrEqual(7)
  expect(vars.find(v => v.name === '--paper')?.value).toBe('#FBF4F0')
  expect(vars.find(v => v.name === '--ink')?.value).toBe('#22273A')
})

test('importDesignKit uses regex path for well-formed HTML', async () => {
  const result = await importDesignKit(TEMPLATE_HTML_EXCERPT, { name: 'test' })
  expect(result.method).toBe('regex')
  expect(result.tokens.semantic.colorBg).toBe('#FBF4F0')
  expect(result.tokens.semantic.colorText).toBe('#22273A')
  expect(result.tokens.semantic.colorAccent).toBe('#B23A2E')
})

test('importDesignKit falls back to llm when < 3 vars found', async () => {
  const sparseHTML = '<style>body { background: #fff; }</style>'
  const mockLLM = {
    chat: vi.fn().mockResolvedValue({
      content: '{"colorBg":"#fff","colorText":"#000","colorAccent":"#f00"}'
    })
  }
  const result = await importDesignKit(sparseHTML, { llmClient: mockLLM })
  expect(result.method).toBe('llm')
  expect(mockLLM.chat).toHaveBeenCalledOnce()
})

test('category colors extracted from --c-a vars', async () => {
  const result = await importDesignKit(TEMPLATE_HTML_EXCERPT)
  expect(result.tokens.semantic.categoryColors?.a.base).toBe('#33508F')
})

test('confidence 1.0 when all semantic fields extracted', async () => {
  const result = await importDesignKit(TEMPLATE_HTML_EXCERPT)
  expect(result.confidence).toBeGreaterThan(0.3)  // at least some fields extracted
})
```

## Acceptance Criteria

- [ ] `extractor.ts` — pure regex, handles multi-line `:root {}`, no DOM/LLM
- [ ] `mapper.ts` — heuristic patterns map `--paper` → `colorBg`, `--ink` → `colorText`, `--red` → `colorAccent`, etc.
- [ ] Category color extraction: `--c-a` through `--c-e` → `categoryColors`
- [ ] Fast path used when ≥ 3 vars found; LLM path only when < 3
- [ ] `ImportResult` includes `method`, `confidence`, `warnings`
- [ ] `importDesignKit(template.html excerpt)` produces correct default theme tokens
- [ ] LLM path uses `f.light` model, tested with mock client only
- [ ] `proposer.ts` fills all missing fields from `default.json` (no undefined fields in output)

## Dependencies

- Blocked by: `theme-system` (ThemeTokens, proposeThemeJSON uses default.json)
- Blocks: nothing (standalone feature — teacher import flow)
- Priority: p1
