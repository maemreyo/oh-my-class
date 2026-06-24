/**
 * Runtime theme CSS loader — reads generated theme_*.css from branding/.
 *
 * TH2 decision: runtime generation (not build-time) so teachers can define
 * custom themes without a build step. Falls back to inline defaults when
 * the CSS file is not found.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BRANDING_DIR = path.resolve(__dirname, "../../branding");

const cache = new Map<string, string>();

const DEFAULT_CSS = `:root {
  --color-primary: #3b82f6;
  --color-secondary: #64748b;
  --color-accent: #f59e0b;
  --color-background: #ffffff;
  --color-surface: #f8fafc;
  --color-text: #1e293b;
  --color-text-muted: #64748b;
  --color-border: #e2e8f0;
  --font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-size-base: 16px;
  --font-size-sm: 0.875rem;
  --font-size-lg: 1.125rem;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
}`;

/**
 * Load theme CSS by name. Returns cached result after first read.
 * Falls back to inline default CSS when the theme file doesn't exist.
 */
export function loadTheme(themeName: string): string {
  if (cache.has(themeName)) return cache.get(themeName)!;

  const filePath = path.join(BRANDING_DIR, `theme_${themeName}.css`);
  let css: string;

  try {
    css = fs.readFileSync(filePath, "utf-8");
  } catch {
    css = DEFAULT_CSS;
  }

  cache.set(themeName, css);
  return css;
}

/**
 * Clear the theme cache (useful for tests).
 */
export function clearThemeCache(): void {
  cache.clear();
}
