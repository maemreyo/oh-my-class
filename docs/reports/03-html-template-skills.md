# Báo cáo Kỹ thuật 03: Đóng gói Branding HTML & Kỹ năng (Skills)

> **Mục tiêu**: Thiết kế hệ thống template HTML, asset pipeline, và skill packaging cho oh-my-class.
>
> **Phiên bản**: 1.0 | **Ngày**: 2026-06-23

---

## Mục lục

1. [Template Engine Comparison](#1-template-engine-comparison)
2. [Kiến trúc Template System](#2-kiến-trúc-template-system)
3. [Branding & Theme System](#3-branding--theme-system)
4. [Standalone HTML Packaging](#4-standalone-html-packaging)
5. [Asset Pipeline](#5-asset-pipeline)
6. [DeerFlow Skill System](#6-deerflow-skill-system)
7. [Sandboxed HTML Rendering](#7-sandboxed-html-rendering)
8. [Cấu hình cho oh-my-class](#8-cấu-hình-cho-oh-my-class)

---

## 1. Template Engine Comparison

### 1.1 Ma trận So sánh (2026)

| Feature | **Jinja2** (Python) | **Eta** (JS/TS) | **Nunjucks** (JS) | **Handlebars** (JS) |
|---|---|---|---|---|
| Template inheritance | `{% extends %}` + `{% block %}` | Plugins/partials only | Same as Jinja2 | Partials only (no blocks) |
| Layout composition | Native blocks + macros | Layout plugin | Native blocks + macros | Must use partials + helpers |
| Sandboxed execution | Built-in sandbox | Via sandbox plugin | No built-in sandbox | No built-in sandbox |
| Auto-escaping | ✅ Default on | ✅ Default on | ✅ Default on | ⚠️ Triple-stash bypasses |
| Bundle size | N/A (server-side) | **~3.5 KB** gzipped | ~20 KB | ~18 KB |
| XSS-safe by default | ✅ | ✅ | ✅ | ⚠️ Triple-stash `{{{ }}}` |
| TypeScript native | ❌ | ✅ | ❌ | ❌ |
| Async render | ✅ | ✅ native | ✅ | ❌ |
| Browser-compatible | ❌ | ✅ (3.5 KB!) | ✅ | ✅ (precompiled) |
| Best for AI output | **Python agents** | **JS/TS agents** | JS apps | Email templates |

### 1.2 Khuyến nghị

oh-my-class dùng **Node.js + TypeScript** runtime → **Eta** là lựa chọn tối ưu.

- **3.5 KB** gzipped — nhẹ nhất
- Native TypeScript — type-safe templates
- `{% extends %}` support qua plugin — composition được
- Browser-compatible — có thể render ở cả client nếu cần

Nếu chuyển sang Python pipeline trong tương lai → **Jinja2** là fallback tốt nhất.

---

## 2. Kiến trúc Template System

### 2.1 Cấu trúc Thư mục

```
oh-my-class/
├── templates/
│   ├── base.html                    # Shell layout (shared across all artifacts)
│   ├── pages/                       # Page-specific templates
│   │   ├── lesson.html              # {% extends "base.html" %}
│   │   ├── worksheet.html
│   │   ├── quiz.html
│   │   ├── drill.html
│   │   ├── recap.html
│   │   └── infographic.html
│   ├── components/                  # Reusable partials
│   │   ├── header.html              # Brand header + navigation
│   │   ├── footer.html              # Credits, copyright
│   │   ├── question_mc.html         # Multiple choice (A/B/C/D)
│   │   ├── question_fill.html       # Fill-in-the-blank
│   │   ├── question_match.html      # Matching pair
│   │   ├── question_order.html      # Ordering / sequencing
│   │   ├── hint_box.html            # Expandable hint
│   │   ├── feedback.html            # Correct/incorrect explanation
│   │   ├── progress_bar.html        # Section progress
│   │   ├── math_block.html          # LaTeX rendering
│   │   ├── timeline.html            # Historical timeline
│   │   ├── concept_map.html         # Concept relationship map
│   │   ├── comparison_table.html    # Side-by-side comparison
│   │   └── data_chart.html          # Data visualization
│   └── branding/
│       ├── theme_default.css        # CSS custom properties (default)
│       ├── theme_ocean.css          # Alternate theme
│       └── theme_forest.css         # Alternate theme
├── common/
│   └── branding/
│       ├── kits/
│       │   ├── default/
│       │   │   ├── theme.json       # Brand config (single source of truth)
│       │   │   ├── logo.svg         # Inline SVG logo
│       │   │   ├── fonts/           # Subsetted WOFF2 (optional)
│       │   │   └── palette.json     # Color palette
│       │   ├── ocean/
│       │   └── forest/
│       └── shared.css               # Base reset + utilities
└── data/                            # Input JSON data
    ├── lesson_fractions.json
    ├── quiz_fractions.json
    └── ...
```

### 2.2 Base Template (Shell Layout)

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="{{ lang | default('vi') }}" data-theme="{{ theme | default('default') }}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}oh-my-class{% endblock %}</title>

  <!-- Branding CSS (inlined, no CDN) -->
  <style>
    /* TIER 1: PRIMITIVES */
    :root {
      --color-blue-50: #eff6ff;
      --color-blue-500: #3b82f6;
      --color-blue-700: #1d4ed8;
      --color-gray-50: #f9fafb;
      --color-gray-900: #111827;
    }

    /* TIER 2: SEMANTIC TOKENS (from theme.json) */
    {% include "branding/theme_" + (theme | default('default')) + ".css" %}
  </style>

  <!-- Component CSS (inlined) -->
  <style>{% block component_css %}{% endblock %}</style>

  <!-- Page-specific CSS -->
  <style>{% block page_css %}{% endblock %}</style>
</head>
<body>
  {% block header %}{% include "components/header.html" %}{% endblock %}

  <main class="container">
    {% block content %}{% endblock %}
  </main>

  {% block footer %}{% include "components/footer.html" %}{% endblock %}

  <!-- Inline JS (minimal, no external) -->
  <script>
    {% block inline_js %}{% endblock %}
  </script>
</body>
</html>
```

### 2.3 Quiz Template (Extends Base)

```html
<!-- templates/pages/quiz.html -->
{% extends "base.html" %}

{% block title %}{{ quiz.title }} — oh-my-class{% endblock %}

{% block component_css %}
  .quiz-question {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md, 0.5rem);
    padding: var(--space-4, 1rem);
    margin-bottom: var(--space-4);
  }
  .quiz-question h3 {
    color: var(--color-text);
    font-size: var(--text-base);
    margin-bottom: var(--space-2);
  }
  .quiz-options {
    display: grid;
    gap: var(--space-2);
  }
  .quiz-option {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm, 0.25rem);
    cursor: pointer;
    transition: background 0.15s;
  }
  .quiz-option:hover {
    background: var(--color-blue-50);
  }
  .quiz-option input[type="radio"] {
    display: none; /* Hide native radio */
  }
  .quiz-option .custom-radio {
    width: 18px;
    height: 18px;
    border: 2px solid var(--color-border);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .quiz-option.selected .custom-radio {
    border-color: var(--color-primary);
  }
  .quiz-option.selected .custom-radio::after {
    content: '';
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--color-primary);
  }
{% endblock %}

{% block content %}
  <section class="quiz" data-quiz-id="{{ quiz.id }}">
    <header class="quiz-header">
      <h1>{{ quiz.title }}</h1>
      {% if quiz.description %}
        <p class="quiz-description">{{ quiz.description }}</p>
      {% endif %}
      <div class="quiz-meta">
        <span>{{ quiz.questions | length }} câu hỏi</span>
        <span>Thời gian: {{ quiz.duration_minutes }} phút</span>
      </div>
    </header>

    <div class="quiz-progress" id="progress">
      <div class="progress-bar" style="width: 0%"></div>
    </div>

    <div class="quiz-questions">
      {% for question in quiz.questions %}
        {% include "components/question_mc.html" %}
      {% endfor %}
    </div>

    <div class="quiz-actions no-print">
      <button class="btn btn-primary" id="submit-btn">Nộp bài</button>
      <button class="btn btn-secondary" id="review-btn" style="display:none">Xem lại</button>
    </div>
  </section>
{% endblock %}

{% block inline_js %}
  // Minimal interaction JS (no external deps)
  document.querySelectorAll('.quiz-option').forEach(option => {
    option.addEventListener('click', function() {
      const group = this.closest('.quiz-options');
      group.querySelectorAll('.quiz-option').forEach(o => o.classList.remove('selected'));
      this.classList.add('selected');
      this.querySelector('input[type="radio"]').checked = true;

      // Update progress
      const answered = document.querySelectorAll('input[type="radio"]:checked').length;
      const total = document.querySelectorAll('.quiz-question').length;
      document.querySelector('.progress-bar').style.width = `${(answered/total)*100}%`;
    });
  });
{% endblock %}
```

### 2.4 Question Component

```html
<!-- templates/components/question_mc.html -->
<div class="quiz-question" data-question-id="{{ question.id }}" data-correct="{{ question.correct_answer }}">
  <h3>
    <span class="question-number">Câu {{ loop.index }}.</span>
    {{ question.text }}
  </h3>

  {% if question.image %}
    <div class="question-image">
      <img src="{{ question.image }}" alt="{{ question.image_alt | default('') }}" loading="lazy">
    </div>
  {% endif %}

  <div class="quiz-options" role="radiogroup" aria-label="Câu trả lời">
    {% for option in question.options %}
      <label class="quiz-option" tabindex="0" role="radio" aria-checked="false">
        <input type="radio"
               name="q{{ question.id }}"
               value="{{ option.key }}"
               aria-label="{{ option.key }}: {{ option.text }}">
        <span class="custom-radio" aria-hidden="true"></span>
        <span class="option-key">{{ option.key }}.</span>
        <span class="option-text">{{ option.text }}</span>
      </label>
    {% endfor %}
  </div>

  {% if question.hint %}
    <div class="hint-box" hidden>
      <button class="hint-toggle" aria-expanded="false">💡 Gợi ý</button>
      <div class="hint-content">{{ question.hint }}</div>
    </div>
  {% endif %}
</div>
```

---

## 3. Branding & Theme System

### 3.1 Three-Tier Token Architecture

```
PRIMITIVES → SEMANTIC TOKENS → COMPONENT TOKENS
   (raw values)    (meaning)        (scoped)
```

### 3.2 Theme Config (Single Source of Truth)

```json
// common/branding/kits/default/theme.json
{
  "name": "Default",
  "version": "2.1.0",
  "brand": {
    "logo": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 40'>...</svg>",
    "favicon": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>...</svg>",
    "colors": {
      "primary": "#3b82f6",
      "primaryHover": "#1d4ed8",
      "secondary": "#8b5cf6",
      "accent": "#f59e0b",
      "success": "#16a34a",
      "warning": "#f59e0b",
      "error": "#dc2626",
      "surface": "#ffffff",
      "surfaceAlt": "#f9fafb",
      "text": "#111827",
      "textMuted": "#6b7280",
      "border": "#e5e7eb",
      "borderLight": "#f3f4f6"
    },
    "fonts": {
      "body": "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', sans-serif",
      "heading": "'Georgia', 'Times New Roman', 'Noto Serif', serif",
      "mono": "'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace"
    },
    "spacing": {
      "xs": "0.25rem",
      "sm": "0.5rem",
      "md": "1rem",
      "lg": "1.5rem",
      "xl": "2rem",
      "2xl": "4rem"
    },
    "borderRadius": {
      "sm": "0.25rem",
      "md": "0.5rem",
      "lg": "0.75rem",
      "full": "9999px"
    },
    "shadows": {
      "sm": "0 1px 2px rgba(0,0,0,0.05)",
      "md": "0 4px 6px -1px rgba(0,0,0,0.1)",
      "lg": "0 10px 15px -3px rgba(0,0,0,0.1)"
    }
  },
  "darkMode": {
    "surface": "#1a1a2e",
    "surfaceAlt": "#16213e",
    "text": "#e5e7eb",
    "border": "#374151"
  }
}
```

### 3.3 CSS Custom Properties Generator

```python
from pathlib import Path
import json

class ThemeCSSGenerator:
    """Generate CSS custom properties từ theme.json."""

    def generate(self, theme_path: str, output_path: str):
        theme = json.loads(Path(theme_path).read_text())
        brand = theme["brand"]

        css = f"""/* Auto-generated from {theme['name']} v{theme['version']} */
/* DO NOT EDIT MANUALLY — regenerate from theme.json */

:root {{
  /* TIER 1: PRIMITIVES */
  --color-primary: {brand['colors']['primary']};
  --color-primary-hover: {brand['colors']['primaryHover']};
  --color-secondary: {brand['colors']['secondary']};
  --color-accent: {brand['colors']['accent']};
  --color-success: {brand['colors']['success']};
  --color-warning: {brand['colors']['warning']};
  --color-error: {brand['colors']['error']};

  /* TIER 2: SEMANTIC TOKENS */
  --color-surface: {brand['colors']['surface']};
  --color-surface-alt: {brand['colors']['surfaceAlt']};
  --color-text: {brand['colors']['text']};
  --color-text-muted: {brand['colors']['textMuted']};
  --color-border: {brand['colors']['border']};
  --color-border-light: {brand['colors']['borderLight']};

  /* Typography */
  --font-body: {brand['fonts']['body']};
  --font-heading: {brand['fonts']['heading']};
  --font-mono: {brand['fonts']['mono']};

  /* Fluid Typography */
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.375vw, 1rem);
  --text-base: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.625vw, 1.375rem);
  --text-xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.75rem);
  --text-2xl: clamp(1.5rem, 1.3rem + 1vw, 2.25rem);
  --text-3xl: clamp(2rem, 1.7rem + 1.5vw, 3rem);

  /* Spacing */
  --space-xs: {brand['spacing']['xs']};
  --space-sm: {brand['spacing']['sm']};
  --space-md: {brand['spacing']['md']};
  --space-lg: {brand['spacing']['lg']};
  --space-xl: {brand['spacing']['xl']};
  --space-2xl: {brand['spacing']['2xl']};

  /* Border Radius */
  --radius-sm: {brand['borderRadius']['sm']};
  --radius-md: {brand['borderRadius']['md']};
  --radius-lg: {brand['borderRadius']['lg']};
  --radius-full: {brand['borderRadius']['full']};

  /* Shadows */
  --shadow-sm: {brand['shadows']['sm']};
  --shadow-md: {brand['shadows']['md']};
  --shadow-lg: {brand['shadows']['lg']};
}}

/* Dark Mode */
[data-theme="dark"] {{
  --color-surface: {theme['darkMode']['surface']};
  --color-surface-alt: {theme['darkMode']['surfaceAlt']};
  --color-text: {theme['darkMode']['text']};
  --color-border: {theme['darkMode']['border']};
}}

/* Base Reset */
*, *::before, *::after {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}
img, svg {{
  max-width: 100%;
  height: auto;
  display: block;
}}
body {{
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--color-text);
  background: var(--color-surface);
}}
.container {{
  width: min(100% - 2rem, 1200px);
  margin-inline: auto;
}}
/* Print styles */
@media print {{
  @page {{ margin: 1.5cm; }}
  .no-print {{ display: none !important; }}
  .page-break {{ page-break-after: always; }}
}}
"""
        Path(output_path).write_text(css)

# Usage
generator = ThemeCSSGenerator()
generator.generate("common/branding/kits/default/theme.json",
                   "templates/branding/theme_default.css")
```

### 3.4 Theme JSON → CSS Pipeline

```
theme.json  ──→  generate_css_vars()  ──→  branding/theme_{name}.css
                        ↓
             Inlined into <style> by Eta/Jinja2
                        ↓
             Every template reads from CSS vars
```

---

## 4. Standalone HTML Packaging

### 4.1 Font Embedding Strategy

| Strategy | Size | When to use |
|---|---|---|
| **System font stack** | 0 bytes | Production default — no FOUT/FOIT |
| **Base64 single WOFF2** | ~15-30 KB per weight | Logo / heading font, subset to ~50 glyphs |
| **@font-face with local()** | 0 bytes, graceful fallback | "Use system font if available" |
| **Google Fonts @import** | ~50-200 KB | ❌ Avoid for standalone — breaks offline |

```css
/* System font stack — zero weight, always works */
:root {
  --font-body: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  --font-heading: 'Georgia', 'Times New Roman', serif;
  --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
}

/* Optional: Embedded brand font (subsetted) */
@font-face {
  font-family: 'BrandHeading';
  src: url('data:font/woff2;base64,d09GMgABAAAA...') format('woff2');
  font-weight: 700;
  font-style: normal;
  font-display: swap;  /* Show text immediately, swap when font loads */
}
```

```bash
# Subset a font to only ASCII + common math symbols
pyftsubset HeadingFont.woff2 --unicodes="U+0020-007F,U+00A9,U+00AE,U+2013,U+2014,U+2026,U+2212"
```

### 4.2 Image Handling

| Type | Method | Size impact |
|---|---|---|
| **SVG icons/logos** | Inline raw SVG in HTML (best) | 0.5-3 KB each |
| **Small PNG/JPG (< 15 KB)** | Base64 data URI | +33% overhead |
| **Large images** | ❌ Don't embed. Host separately or omit. | File balloons |
| **Mathematical diagrams** | CSS-generated or inline SVG | Most compact |

```css
/* CSS background inline */
.logo {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E...");
}
```

### 4.3 Responsive Design Without CDN

```css
/* ─── Fluid Typography ─── */
:root {
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.375vw, 1rem);
  --text-base: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.625vw, 1.375rem);
  --text-xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.75rem);
  --text-2xl: clamp(1.5rem, 1.3rem + 1vw, 2.25rem);
  --text-3xl: clamp(2rem, 1.7rem + 1.5vw, 3rem);
}

/* ─── Layout ─── */
.container {
  width: min(100% - 2rem, 1200px);
  margin-inline: auto;
}

.grid {
  display: grid;
  gap: var(--space-md, 1rem);
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
}

/* ─── Quiz-specific responsive ─── */
.quiz-question {
  padding: var(--space-4);
}

@media (max-width: 640px) {
  .quiz-options {
    grid-template-columns: 1fr;
  }
  .quiz-option {
    padding: var(--space-2) var(--space-3);
  }
}

/* ─── Print ─── */
@media print {
  @page { margin: 1.5cm; }
  .no-print { display: none !important; }
  .page-break { page-break-after: always; }
  .quiz-question { break-inside: avoid; }
}

/* ─── Dark Mode ─── */
@media (prefers-color-scheme: dark) {
  :root {
    /* Override CSS vars for dark mode */
  }
}
```

---

## 5. Asset Pipeline

### 5.1 Build Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  theme.json  │────▶│  CSS Gen     │────▶│  Template    │────▶│  Standalone  │
│  (config)    │     │  (Python)    │     │  Render (Eta)│     │  HTML Output │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │                     │
       ▼                    ▼                    ▼                     ▼
  Brand tokens        CSS vars file        HTML + inlined CSS     .html file
  (colors, fonts,     (auto-generated)     (Jinja2/Eta)          (self-contained)
   spacing, etc.)
```

### 5.2 Eta Template Rendering

```typescript
// src/templates/renderer.ts
import { Eta } from "eta";
import { readFileSync } from "fs";
import { join } from "path";

const eta = new Eta({
  views: join(__dirname, "../../templates"),
  cache: true,           // Cache compiled templates
  escapeFn: Eta.escapeFn, // Auto-escape HTML
});

interface ArtifactData {
  artifact_type: string;
  theme: string;
  title: string;
  sections: any[];
  metadata: Record<string, any>;
}

function renderArtifact(data: ArtifactData): string {
  const templateFile = `pages/${data.artifact_type}.html`;

  return eta.render(templateFile, {
    ...data,
    lang: data.metadata?.language || "vi",
    theme: data.theme || "default",
  });
}

// Usage
const quizData: ArtifactData = {
  artifact_type: "quiz",
  theme: "default",
  title: "Bài kiểm tra: Phân số",
  sections: [...],
  metadata: { language: "vi", grade: "Grade 5" },
};

const html = renderArtifact(quizData);
// Output: standalone HTML with inlined CSS, no CDN
```

### 5.3 Asset Inlining Build Step

```typescript
// src/build/inline-assets.ts
import { readFileSync, writeFileSync } from "fs";
import { resolve } from "path";

function inlineCSS(html: string, cssPath: string): string {
  const css = readFileSync(resolve(cssPath), "utf-8");
  return html.replace(
    '<style>{% block component_css %}{% endblock %}</style>',
    `<style>${css}</style>`
  );
}

function inlineBrandCSS(html: string, themeName: string): string {
  const cssPath = resolve(__dirname, `../../templates/branding/theme_${themeName}.css`);
  const css = readFileSync(cssPath, "utf-8");
  return html.replace(
    '{% include "branding/theme_" + (theme | default(\'default\')) + ".css" %}',
    css
  );
}

function buildStandaloneHTML(data: ArtifactData): string {
  let html = renderArtifact(data);

  // Step 1: Inline branding CSS
  html = inlineBrandCSS(html, data.theme);

  // Step 2: Inline component CSS (already in template)

  // Step 3: Remove any remaining template tags
  html = html.replace(/\{%[^%]*%\}/g, "");

  // Step 4: Validate — no external assets
  if (html.includes('href="http') || html.includes('src="http')) {
    throw new Error("External asset detected in output HTML");
  }

  return html;
}
```

---

## 6. DeerFlow Skill System

### 6.1 Skill Structure

DeerFlow skills are **Markdown files** injected into the agent's system prompt. oh-my-class should adopt this pattern for its 12-step run lifecycle.

```
skills/
├── zamery-agent-orchestrator/
│   └── SKILL.md              # Master router skill
├── zamery-blueprint-designer/
│   └── SKILL.md              # Blueprint design skill
├── zamery-pack-generator/
│   └── SKILL.md              # HTML artifact generation
├── zamery-artifact-reviewer/
│   └── SKILL.md              # QA review skill
├── zamery-validation-fixer/
│   └── SKILL.md              # Repair validation errors
├── zamery-export-assistant/
│   └── SKILL.md              # Export to platforms
├── zamery-design-kit-importer/
│   └── SKILL.md              # Kit management
└── engineering/              # 20 engineering skills
    ├── diagnose/
    ├── tdd/
    ├── review/
    └── ...
```

### 6.2 Skill Content Example

```markdown
<!-- skills/zamery-pack-generator/SKILL.md -->
# Zamery Pack Generator

## Description
Generates HTML teaching pack artifacts (lesson, worksheet, quiz, drill, recap, infographic)
from structured JSON data using Jinja2/Eta templates with branding.

## Trigger
- User requests to generate a teaching pack
- After blueprint approval
- Content creation phase

## Workflow

### Step 1: Load Template
```
Read template: templates/pages/{artifact_type}.html
Read branding: common/branding/kits/{theme}/theme.json
```

### Step 2: Generate Content JSON
```
For each section in the blueprint:
  1. Call LLM to generate structured JSON content
  2. Validate against artifact schema (Pydantic/Zod)
  3. If validation fails → retry with feedback (max 3)
```

### Step 3: Render HTML
```
1. Load template engine (Eta/Jinja2)
2. Inject content JSON + branding tokens
3. Render to standalone HTML
4. Inline all CSS (no CDN, no external assets)
```

### Step 4: Post-Render Validation
```
1. Validate HTML structure (html-validate)
2. Check responsive breakpoints (Playwright)
3. Verify brand strings present
4. Check answer key separation
```

## Constraints
- MUST output standalone HTML (no CDN, no external assets)
- MUST use CSS custom properties for theming
- MUST separate student/teacher views
- MUST include WCAG accessibility attributes
- MUST NOT embed student PII in artifacts

## References
- ./templates/  # Template files
- ./common/branding/  # Brand assets
- ./contracts/  # JSON schemas
```

### 6.3 Skill Injection into System Prompt

```python
# DeerFlow's skill injection pattern
def get_skills_prompt_section(available_skills: set[str], app_config) -> str:
    """Build XML section listing available skills."""
    skills_xml = "<available_skills>\n"
    for skill_name in sorted(available_skills):
        skill_path = get_skill_path(skill_name, app_config)
        skill_desc = get_skill_description(skill_name, app_config)
        skills_xml += f"""    <skill>
        <name>{skill_name}</name>
        <description>{skill_desc}</description>
        <location>{skill_path}</location>
    </skill>\n"""
    skills_xml += "</available_skills>"

    return f"""
<skill_system>
You have access to skills that provide optimized workflows for specific tasks.

**Progressive Loading Pattern:**
1. When a user query matches a skill's use case, immediately call `read_file` on the skill's main file
2. Read and understand the skill's workflow
3. Load referenced resources only when needed

{skills_xml}
</skill_system>
"""
```

---

## 7. Sandboxed HTML Rendering

### 7.1 Multi-Layer Defense

```
LAYER 1: TEMPLATE ENGINE AUTO-ESCAPING
    Eta <%= value %> / Jinja2 {{ value }}
    → Escapes <>&"' to HTML entities

LAYER 2: DOMPurify (server-side post-render)
    DOMPurify.sanitize(html, {ALLOWED_TAGS: [...]})
    → Strips script tags, event handlers

LAYER 3: iframe sandboxing (client render)
    <iframe sandbox="allow-scripts" srcdoc="...">
    → No navigation, no popups, no top-level access

LAYER 4: Content Security Policy (CSP)
    Content-Security-Policy: default-src 'self'; script-src 'none'
    → Browser-enforced policy

LAYER 5: html-validate (CI/build-time)
    → Validates HTML structure, accessibility
```

### 7.2 DOMPurify Configuration

```typescript
import DOMPurify from "dompurify";

const clean = DOMPurify.sanitize(dirtyHTML, {
  ALLOWED_TAGS: [
    "p", "br", "strong", "em", "u", "s",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "div", "span", "section", "header", "footer",
    "img", "svg",
    "code", "pre", "blockquote", "hr",
    "sup", "sub",
  ],
  ALLOWED_ATTR: [
    "class", "id", "style",
    "src", "alt", "width", "height",
    "href", "target", "rel",
    "data-*", "role", "aria-*",
    "tabindex", "loading",
  ],
  ALLOW_DATA_ATTR: true,
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|data):)/,
});
```

### 7.3 iframe Sandboxing

```html
<!-- Preview generated HTML safely -->
<iframe
  class="preview-frame"
  sandbox="allow-scripts"  <!-- NO allow-same-origin, NO allow-popups -->
  srcdoc="<!DOCTYPE html>
    <html>
    <head>
      <meta charset='utf-8'>
      <base href='about:srcdoc'>
    </head>
    <body>
      <!-- Sanitized HTML goes here -->
    </body>
    </html>"
></iframe>
```

> ⚠️ **Critical**: Never combine `allow-scripts` + `allow-same-origin`. That allows the iframe to escape the sandbox entirely.

---

## 8. Cấu hình cho oh-my-class

### 8.1 Eta Config

```json
{
  "eta": {
    "views": "./templates",
    "cache": true,
    "debug": false,
    "escapeFn": "eta.escapeFn",
    "autoFilter": true,
    "autoImport": false
  }
}
```

### 8.2 Design Kit Lifecycle

```
1. IMPORT: Teacher uploads HTML → extract CSS tokens → propose theme.json
2. REVIEW: Preview theme on sample artifacts → approve/reject
3. SET DEFAULT: Mark theme as default for all future artifacts
4. VERSION: Semantic versioning (major.minor.patch)
```

### 8.3 Component Work Orders

```json
{
  "work_order_id": "WO-001",
  "component": "quiz-question",
  "design_intent": "Interactive multiple choice with custom radio buttons",
  "requirements": [
    "WCAG 2.1 AA compliant",
    "Keyboard navigable",
    "Touch-friendly (min 44px tap target)",
    "Responsive (mobile-first)",
    "Dark mode support"
  ],
  "theme": "default",
  "version": "1.0.0"
}
```

---

> **Nguồn tham khảo**:
> - Eta Template Engine: https://eta.js.org/
> - Jinja2 Documentation: https://jinja.palletsprojects.com/
> - CourseForge: https://github.com/rmichak/courseforge
> - TheGeminiLoop: https://github.com/Yknld/TheGeminiLoop
> - DOMPurify: https://github.com/cure53/DOMPurify
> - DeerFlow Skills: https://github.com/bytedance/deer-flow
