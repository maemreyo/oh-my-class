---
title: "Theme Pipeline + Renderer"
status: done
labels: []
created: 2026-06-23
github: 10
---

## What to build

Implement the theme generation pipeline in `common/branding/generate_theme.py` and the Eta template renderer in `packages/renderer/src/renderer.ts`. Both files exist with stubs.

## Current State

```typescript
// packages/renderer/src/renderer.ts (lines 8-22)
export function renderArtifact(_data: ArtifactContent): string {
    // TODO: Select template based on data.artifact_type
    throw new Error("Not yet implemented");
}

export function renderTemplate(_templateName: string, _data: Record<string, unknown>): string {
    // TODO: Use Eta to render template
    throw new Error("Not yet implemented");
}

// packages/renderer/src/sanitizer.ts — STUB (not read yet)
// common/branding/generate_theme.py — NOT YET CREATED
// packages/renderer/templates/ — 22 template files exist (COMPLETE)
```

## Implementation Spec

### 1. Create `common/branding/generate_theme.py` (new file)

```python
"""Theme generator — reads theme.json and generates theme_*.css files."""

from __future__ import annotations

import json
import os
from pathlib import Path


def generate_theme(theme_name: str, kit_dir: str) -> str:
    """Generate CSS from theme.json.
    
    Args:
        theme_name: Theme name (default, ocean, forest).
        kit_dir: Path to branding kits directory.
    
    Returns:
        Generated CSS content.
    """
    theme_path = Path(kit_dir) / theme_name / "theme.json"
    
    if not theme_path.exists():
        raise FileNotFoundError(f"Theme not found: {theme_path}")
    
    with open(theme_path) as f:
        theme_data = json.load(f)
    
    # Generate CSS with three-tier token system
    css = f"""/* Auto-generated from theme.json — DO NOT EDIT MANUALLY */
/* Theme: {theme_name} */

:root {{
    /* Primitives */
    --color-primary: {theme_data.get('colors', {}).get('primary', '#3b82f6')};
    --color-secondary: {theme_data.get('colors', {}).get('secondary', '#10b981')};
    --color-accent: {theme_data.get('colors', {}).get('accent', '#f59e0b')};
    --color-background: {theme_data.get('colors', {}).get('background', '#ffffff')};
    --color-surface: {theme_data.get('colors', {}).get('surface', '#f8fafc')};
    --color-text: {theme_data.get('colors', {}).get('text', '#1e293b')};
    
    /* Semantic tokens */
    --color-success: var(--color-secondary);
    --color-warning: var(--color-accent);
    --color-error: #ef4444;
    
    /* Spacing */
    --space-xs: {theme_data.get('spacing', {}).get('xs', '0.25rem')};
    --space-sm: {theme_data.get('spacing', {}).get('sm', '0.5rem')};
    --space-md: {theme_data.get('spacing', {}).get('md', '1rem')};
    --space-lg: {theme_data.get('spacing', {}).get('lg', '1.5rem')};
    --space-xl: {theme_data.get('spacing', {}).get('xl', '2rem')};
    
    /* Typography */
    --font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    --font-size-sm: {theme_data.get('typography', {}).get('size_sm', '0.875rem')};
    --font-size-base: {theme_data.get('typography', {}).get('size_base', '1rem')};
    --font-size-lg: {theme_data.get('typography', {}).get('size_lg', '1.125rem')};
    
    /* Border radius */
    --radius-sm: {theme_data.get('borderRadius', {}).get('sm', '0.25rem')};
    --radius-md: {theme_data.get('borderRadius', {}).get('md', '0.5rem')};
    --radius-lg: {theme_data.get('borderRadius', {}).get('lg', '1rem')};
}}
"""
    
    # Write CSS file
    output_path = Path(kit_dir) / theme_name / f"theme_{theme_name}.css"
    with open(output_path, "w") as f:
        f.write(css)
    
    return css


def generate_all_themes(kit_dir: str) -> dict[str, str]:
    """Generate CSS for all themes in the kit directory.
    
    Args:
        kit_dir: Path to branding kits directory.
    
    Returns:
        Dict mapping theme name to generated CSS.
    """
    themes = {}
    for theme_name in ["default", "ocean", "forest"]:
        try:
            css = generate_theme(theme_name, kit_dir)
            themes[theme_name] = css
        except FileNotFoundError:
            print(f"Theme {theme_name} not found, skipping")
    
    return themes


if __name__ == "__main__":
    kit_dir = os.path.join(os.path.dirname(__file__), "kits")
    themes = generate_all_themes(kit_dir)
    print(f"Generated {len(themes)} themes")
```

### 2. Replace `packages/renderer/src/renderer.ts` (lines 8-22)

```typescript
/**
 * Core renderer — takes ArtifactContent JSON and produces standalone HTML.
 * Uses Eta templates. All output is self-contained: no CDN, no external assets.
 */

import { Eta } from "eta";
import type { ArtifactContent } from "@oh-my-class/schemas";
import { sanitizeHtml } from "./sanitizer";

// Initialize Eta with template directory
const eta = new Eta({ views: "./templates" });

// Template mapping
const TEMPLATE_MAP: Record<string, string> = {
    lesson: "pages/lesson",
    worksheet: "pages/worksheet",
    quiz: "pages/quiz",
    drill: "pages/drill",
    recap: "pages/recap",
    infographic: "pages/infographic",
};

// Theme CSS cache
const themeCache: Map<string, string> = new Map();

/**
 * Load theme CSS for inline embedding.
 */
function loadThemeCss(theme: string): string {
    if (themeCache.has(theme)) {
        return themeCache.get(theme)!;
    }
    
    // In production, this would read from the generated CSS file
    // For now, return a minimal CSS string
    const css = `
        :root {
            --color-primary: #3b82f6;
            --font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
        }
        body { font-family: var(--font-family); }
    `;
    
    themeCache.set(theme, css);
    return css;
}

/**
 * Render ArtifactContent to standalone HTML.
 */
export function renderArtifact(data: ArtifactContent): string {
    // 1. Select template based on artifact_type
    const templatePath = TEMPLATE_MAP[data.artifact_type];
    if (!templatePath) {
        throw new Error(`Unknown artifact type: ${data.artifact_type}`);
    }
    
    // 2. Load and inline theme CSS
    const themeCss = loadThemeCss(data.theme);
    
    // 3. Render via Eta template engine
    const html = eta.render(templatePath, {
        ...data,
        themeCss,
        brand: "oh-my-class",
    });
    
    // 4. Run sanitizer
    return sanitizeHtml(html);
}

/**
 * Render a specific template with data.
 */
export function renderTemplate(
    templateName: string,
    data: Record<string, unknown>,
): string {
    return eta.render(templateName, data) as string;
}
```

### 3. Create `packages/renderer/src/sanitizer.ts` (new file)

```typescript
/**
 * HTML sanitizer — strips dangerous content using DOMPurify.
 */

import DOMPurify from "dompurify";

/**
 * Sanitize HTML output to remove dangerous content.
 * 
 * - Strips <script> tags
 * - Strips event handlers (onclick, onerror, etc.)
 * - Preserves safe HTML structure
 */
export function sanitizeHtml(html: string): string {
    // Use DOMPurify with strict settings
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
            "html", "head", "body", "div", "span", "p", "h1", "h2", "h3", "h4", "h5", "h6",
            "ul", "ol", "li", "table", "tr", "td", "th", "thead", "tbody",
            "img", "svg", "path", "circle", "rect",
            "style", "link", "meta", "title",
            "strong", "em", "u", "s", "code", "pre",
            "a", "br", "hr",
            "input", "select", "option", "textarea", "button",
            "label", "fieldset", "legend",
        ],
        ALLOWED_ATTR: [
            "class", "id", "style", "src", "href", "alt", "title",
            "width", "height", "viewBox", "xmlns",
            "type", "name", "value", "placeholder", "checked", "disabled",
            "for", "action", "method",
        ],
        FORBID_TAGS: ["script", "iframe", "object", "embed", "form"],
        FORBID_ATTR: ["onerror", "onclick", "onload", "onmouseover"],
    });
}
```

## Acceptance criteria

- [ ] `generate_theme()` reads theme.json and produces CSS
- [ ] `generate_theme()` includes CSS custom properties (variables)
- [ ] `generate_theme()` uses three-tier token system
- [ ] `renderArtifact()` selects correct template for each artifact_type
- [ ] `renderArtifact()` inlines theme CSS in output
- [ ] `renderArtifact()` runs sanitizer on output
- [ ] `renderTemplate()` uses Eta engine
- [ ] `sanitizeHtml()` strips <script> tags
- [ ] `sanitizeHtml()` strips event handlers
- [ ] Output HTML has no external links (CDN-free)
- [ ] Output HTML has <!DOCTYPE html>
- [ ] Output HTML contains "oh-my-class" brand string
- [ ] Unit test: generate_theme produces valid CSS
- [ ] Unit test: renderArtifact produces valid HTML
- [ ] Unit test: sanitizeHtml removes dangerous content

## Test suite

Create `packages/renderer/tests/test_renderer.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { renderArtifact, renderTemplate } from "../src/renderer";
import { sanitizeHtml } from "../src/sanitizer";
import type { ArtifactContent } from "@oh-my-class/schemas";

describe("renderArtifact", () => {
    const mockArtifact: ArtifactContent = {
        artifact_type: "lesson",
        theme: "default",
        title: "Test Lesson",
        sections: [{ title: "Intro", content: "Content" }],
        metadata: {},
        accessibility: { language: "en" },
    };

    it("produces valid HTML", () => {
        const html = renderArtifact(mockArtifact);
        expect(html).toContain("<!DOCTYPE html>");
        expect(html).toContain("oh-my-class");
    });

    it("includes theme CSS inline", () => {
        const html = renderArtifact(mockArtifact);
        expect(html).toContain("<style>");
        expect(html).not.toContain("<link");
    });

    it("throws for unknown artifact type", () => {
        const badArtifact = { ...mockArtifact, artifact_type: "unknown" };
        expect(() => renderArtifact(badArtifact)).toThrow("Unknown artifact type");
    });
});

describe("sanitizeHtml", () => {
    it("removes script tags", () => {
        const html = '<div>Safe</div><script>alert("xss")</script>';
        const clean = sanitizeHtml(html);
        expect(clean).not.toContain("<script>");
        expect(clean).toContain("Safe");
    });

    it("removes event handlers", () => {
        const html = '<div onclick="alert(1)">Safe</div>';
        const clean = sanitizeHtml(html);
        expect(clean).not.toContain("onclick");
    });

    it("preserves safe content", () => {
        const html = '<div class="content"><p>Hello</p></div>';
        const clean = sanitizeHtml(html);
        expect(clean).toContain("Hello");
        expect(clean).toContain("class=\"content\"");
    });
});
```

## File paths

| File | Action |
|------|--------|
| `common/branding/generate_theme.py` | CREATE: Theme generator |
| `common/branding/kits/*/theme.json` | EXISTING: Theme configs |
| `packages/renderer/src/renderer.ts` | MODIFY: Replace stub (lines 8-22) |
| `packages/renderer/src/sanitizer.ts` | CREATE: DOMPurify sanitizer |
| `packages/renderer/tests/test_renderer.ts` | CREATE: Full test suite |

## Dependencies

- `eta` — Template engine (already installed per package.json)
- `dompurify` — HTML sanitizer (already installed per package.json)
- `jsdom` — DOM implementation for DOMPurify (may need install)
- `@oh-my-class/schemas` — ArtifactContent type (already exists)

## Edge cases to handle

1. Unknown artifact type → throw Error
2. Missing theme → use default theme
3. Empty sections → still render (don't crash)
4. Malformed HTML → DOMPurify will sanitize
5. Theme JSON missing keys → use defaults
