---
title: "Theme System: TH2 — ThemeCSSGenerator, loadTheme, Three-tier ThemeTokens"
status: ready
labels: [renderer, typescript, branding]
created: 2026-06-24
priority: p0
report: "03"
---

## What to build

Runtime CSS generation from `theme.json` → CSS custom properties injected into `base.html`. Three-tier token structure: primitives → semantic → component. `ThemeCSSGenerator` and `loadTheme()` are separate modules independently testable.

**Design decision (TH2):** Runtime generation (not build-time pre-generation) so teachers can define custom themes without a build step. Generator and loader are separate concerns.

## File Structure

```
packages/renderer/src/theme/
├── index.ts              # re-exports: loadTheme, ThemeCSSGenerator, ThemeTokens
├── tokens.ts             # ThemeTokens type — three-tier structure
├── generator.ts          # ThemeCSSGenerator: ThemeTokens → CSS :root block string
├── loader.ts             # loadTheme(name): reads theme.json → returns CSS string
└── themes/
    ├── default.json      # default theme (warm neutral — matches template.html palette)
    ├── forest.json       # green nature theme
    └── ocean.json        # blue calm theme
```

## Implementation Spec

### `theme/tokens.ts`

```ts
/**
 * Three-tier CSS token structure.
 * Tier 1 (primitives): raw values — not used directly in templates
 * Tier 2 (semantic):   purpose-named — used in components
 * Tier 3 (component):  component-scoped overrides — optional
 */

export interface PrimitiveTokens {
  // Color palette — raw hex values
  colorPalette: Record<string, string>   // e.g. { red500: '#B23A2E', gold400: '#A8782E' }
  // Spacing scale
  spacing: Record<string, string>        // e.g. { '1': '4px', '2': '8px', ... }
  // Typography
  fontFamilyHeading: string              // CSS font-family string
  fontFamilyBody: string
  fontFamilyMono: string
  fontSizeScale: Record<string, string>  // e.g. { sm: '13px', base: '15.5px', lg: '18px' }
  fontWeightScale: Record<string, number>
  // Radius + shadow
  borderRadius: Record<string, string>
  shadow: Record<string, string>
}

export interface SemanticTokens {
  // Surfaces
  colorBg:          string   // page background
  colorBgCard:      string   // card surface
  colorBgDeep:      string   // deeper background variant
  // Text
  colorText:        string   // primary text
  colorTextSoft:    string   // secondary text
  colorTextFaint:   string   // muted text
  // Borders
  colorBorder:      string
  colorBorderSoft:  string
  // Accent colors (mapped from palette)
  colorAccent:      string   // primary accent
  colorAccentDeep:  string
  colorAccentTint:  string   // rgba light version
  // Status
  colorSuccess:     string
  colorWarning:     string
  colorError:       string
  // Category colors (for quiz section color-coding)
  categoryColors:   Record<string, { base: string; tint: string }>
}

export interface ComponentTokens {
  // Per-component token overrides (optional)
  questionCardRadius?: string
  questionCardShadow?: string
  flashcardHeight?:    string
  flashcardRadius?:    string
}

export interface ThemeTokens {
  name:        string
  primitives:  PrimitiveTokens
  semantic:    SemanticTokens
  component?:  ComponentTokens
}
```

### `theme/generator.ts`

```ts
import type { ThemeTokens } from './tokens.js'

export class ThemeCSSGenerator {
  /**
   * Convert ThemeTokens → CSS custom properties string for injection into :root {}.
   * Only semantic + component tokens become CSS vars — primitives are internal.
   */
  generate(tokens: ThemeTokens): string {
    const vars: string[] = []

    // Semantic tokens → --color-bg, --color-text, etc.
    const { semantic } = tokens
    vars.push(
      `--color-bg: ${semantic.colorBg};`,
      `--color-bg-card: ${semantic.colorBgCard};`,
      `--color-bg-deep: ${semantic.colorBgDeep};`,
      `--color-text: ${semantic.colorText};`,
      `--color-text-soft: ${semantic.colorTextSoft};`,
      `--color-text-faint: ${semantic.colorTextFaint};`,
      `--color-border: ${semantic.colorBorder};`,
      `--color-border-soft: ${semantic.colorBorderSoft};`,
      `--color-accent: ${semantic.colorAccent};`,
      `--color-accent-deep: ${semantic.colorAccentDeep};`,
      `--color-accent-tint: ${semantic.colorAccentTint};`,
      `--color-success: ${semantic.colorSuccess};`,
      `--color-warning: ${semantic.colorWarning};`,
      `--color-error: ${semantic.colorError};`,
    )

    // Category colors (for quiz section color-coding)
    for (const [key, val] of Object.entries(semantic.categoryColors ?? {})) {
      vars.push(
        `--color-category-${key}: ${val.base};`,
        `--color-category-${key}-tint: ${val.tint};`,
      )
    }

    // Font families from primitives (used directly in templates)
    vars.push(
      `--font-heading: ${tokens.primitives.fontFamilyHeading};`,
      `--font-body: ${tokens.primitives.fontFamilyBody};`,
      `--font-mono: ${tokens.primitives.fontFamilyMono};`,
    )

    // Component token overrides (optional)
    if (tokens.component) {
      const c = tokens.component
      if (c.questionCardRadius) vars.push(`--question-card-radius: ${c.questionCardRadius};`)
      if (c.questionCardShadow) vars.push(`--question-card-shadow: ${c.questionCardShadow};`)
      if (c.flashcardHeight)    vars.push(`--flashcard-height: ${c.flashcardHeight};`)
    }

    return vars.join('\n      ')
  }
}
```

### `theme/loader.ts`

```ts
import path from 'path'
import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import { ThemeCSSGenerator } from './generator.js'
import type { ThemeTokens } from './tokens.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const THEMES_DIR = path.resolve(__dirname, 'themes')
const generator = new ThemeCSSGenerator()

// Simple LRU cache — avoid re-reading file on every render
const _cache = new Map<string, string>()

export function loadTheme(name: string): string {
  if (_cache.has(name)) return _cache.get(name)!

  const filePath = path.join(THEMES_DIR, `${name}.json`)
  let tokens: ThemeTokens
  try {
    tokens = JSON.parse(readFileSync(filePath, 'utf-8'))
  } catch {
    // fallback to default theme if named theme not found
    tokens = JSON.parse(readFileSync(path.join(THEMES_DIR, 'default.json'), 'utf-8'))
  }

  const css = generator.generate(tokens)
  _cache.set(name, css)
  return css
}

export function clearThemeCache(): void {
  _cache.clear()
}
```

### `theme/themes/default.json` (excerpt)

```json
{
  "name": "default",
  "primitives": {
    "colorPalette": {
      "paper": "#FBF4F0",
      "paperDeep": "#F3E2D9",
      "ink": "#22273A",
      "inkSoft": "#5C6275",
      "inkFaint": "#8B8FA0",
      "line": "#E8D8CD",
      "red": "#B23A2E",
      "redDeep": "#8C2C22",
      "gold": "#A8782E",
      "green": "#2E6F4E"
    },
    "fontFamilyHeading": "'Spectral', Georgia, 'Times New Roman', serif",
    "fontFamilyBody": "-apple-system, BlinkMacSystemFont, 'Be Vietnam Pro', 'Segoe UI', sans-serif",
    "fontFamilyMono": "'IBM Plex Mono', 'Fira Code', 'Courier New', monospace",
    "borderRadius": { "sm": "7px", "md": "10px", "lg": "12px" }
  },
  "semantic": {
    "colorBg": "#FBF4F0",
    "colorBgCard": "#FFFFFF",
    "colorBgDeep": "#F3E2D9",
    "colorText": "#22273A",
    "colorTextSoft": "#5C6275",
    "colorTextFaint": "#8B8FA0",
    "colorBorder": "#E8D8CD",
    "colorBorderSoft": "#EFE3DA",
    "colorAccent": "#B23A2E",
    "colorAccentDeep": "#8C2C22",
    "colorAccentTint": "rgba(178,58,46,0.07)",
    "colorSuccess": "#2E6F4E",
    "colorWarning": "#A8782E",
    "colorError": "#B23A2E",
    "categoryColors": {
      "a": { "base": "#33508F", "tint": "rgba(51,80,143,0.08)" },
      "b": { "base": "#B9762A", "tint": "rgba(185,118,42,0.09)" },
      "c": { "base": "#3C7A4E", "tint": "rgba(60,122,78,0.08)" },
      "d": { "base": "#1F7A8C", "tint": "rgba(31,122,140,0.08)" },
      "e": { "base": "#8A4F7E", "tint": "rgba(138,79,126,0.08)" }
    }
  }
}
```

## Tests

```ts
// __tests__/theme.test.ts

import { ThemeCSSGenerator } from '../src/theme/generator.js'
import { loadTheme, clearThemeCache } from '../src/theme/loader.js'
import type { ThemeTokens } from '../src/theme/tokens.js'

const minimalTokens: ThemeTokens = {
  name: 'test',
  primitives: {
    colorPalette: {},
    spacing: {},
    fontFamilyHeading: 'serif',
    fontFamilyBody: 'sans-serif',
    fontFamilyMono: 'monospace',
    fontSizeScale: {},
    fontWeightScale: {},
    borderRadius: {},
    shadow: {},
  },
  semantic: {
    colorBg: '#fff', colorBgCard: '#fff', colorBgDeep: '#eee',
    colorText: '#000', colorTextSoft: '#666', colorTextFaint: '#999',
    colorBorder: '#ccc', colorBorderSoft: '#ddd',
    colorAccent: '#f00', colorAccentDeep: '#c00', colorAccentTint: 'rgba(255,0,0,0.1)',
    colorSuccess: '#0f0', colorWarning: '#fa0', colorError: '#f00',
    categoryColors: {},
  },
}

test('generator produces --color-bg CSS var', () => {
  const gen = new ThemeCSSGenerator()
  const css = gen.generate(minimalTokens)
  expect(css).toContain('--color-bg: #fff;')
})

test('generator produces --font-heading CSS var', () => {
  const gen = new ThemeCSSGenerator()
  const css = gen.generate(minimalTokens)
  expect(css).toContain('--font-heading: serif;')
})

test('generator maps category colors', () => {
  const tokens = { ...minimalTokens, semantic: {
    ...minimalTokens.semantic,
    categoryColors: { a: { base: '#33508F', tint: 'rgba(51,80,143,0.08)' } }
  }}
  const css = new ThemeCSSGenerator().generate(tokens)
  expect(css).toContain('--color-category-a: #33508F;')
  expect(css).toContain('--color-category-a-tint: rgba(51,80,143,0.08);')
})

test('loadTheme returns CSS string for default theme', () => {
  clearThemeCache()
  const css = loadTheme('default')
  expect(css).toContain('--color-bg:')
  expect(typeof css).toBe('string')
})

test('loadTheme falls back to default for unknown theme', () => {
  clearThemeCache()
  const css = loadTheme('nonexistent-theme-xyz')
  expect(css).toContain('--color-bg:')
})

test('loadTheme caches result (same reference)', () => {
  clearThemeCache()
  const first = loadTheme('default')
  const second = loadTheme('default')
  expect(first).toBe(second)
})
```

## Acceptance Criteria

- [ ] `ThemeTokens` type has three-tier structure: `primitives`, `semantic`, `component?`
- [ ] `ThemeCSSGenerator.generate()` — only semantic + component tokens become CSS vars
- [ ] `loadTheme('default')` returns valid CSS custom properties string
- [ ] `loadTheme('unknown')` falls back to default (no throw)
- [ ] Cache in `loadTheme` — same theme name returns same string reference
- [ ] `clearThemeCache()` exported — used in tests to avoid cross-test state
- [ ] `themes/default.json` palette matches the `template.html` CSS vars (`--paper`, `--ink`, `--red`, `--gold`, `--green`, `--c-a` through `--c-e`)
- [ ] Three themes shipped: `default.json`, `forest.json`, `ocean.json`

## Dependencies

- Blocked by: nothing (standalone module)
- Blocks: `html-template-system` (renderer.ts calls `loadTheme`), `design-kit-lifecycle` (proposes ThemeTokens)
- Priority: p0
