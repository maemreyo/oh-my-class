/**
 * Runtime theme CSS loader — reads theme.json → generates CSS custom properties.
 *
 * TH2 decision: runtime generation (not build-time) so teachers can define
 * custom themes without a build step. Falls back to default.json when the
 * named theme is not found.
 */

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ThemeCSSGenerator } from "./generator.js";
import type { ThemeTokens } from "./tokens.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SOURCE_THEMES_DIR = path.resolve(__dirname, "../../src/theme/themes");
const THEMES_DIR = existsSync(path.resolve(__dirname, "themes"))
  ? path.resolve(__dirname, "themes")
  : SOURCE_THEMES_DIR;

const generator = new ThemeCSSGenerator();
const _cache = new Map<string, string>();

function loadTokens(name: string): ThemeTokens {
  const filePath = path.join(THEMES_DIR, `${name}.json`);
  try {
    return JSON.parse(readFileSync(filePath, "utf-8")) as ThemeTokens;
  } catch {
    return JSON.parse(
      readFileSync(path.join(THEMES_DIR, "default.json"), "utf-8"),
    ) as ThemeTokens;
  }
}

/**
 * Load theme by name and return a CSS custom-properties string.
 * Result is cached — same name returns the same string reference.
 * Falls back to default theme for unknown names.
 */
export function loadTheme(name: string): string {
  if (_cache.has(name)) return _cache.get(name)!;
  const tokens = loadTokens(name);
  const css = generator.generate(tokens);
  _cache.set(name, css);
  return css;
}

/**
 * Clear the theme cache (used in tests to avoid cross-test state).
 */
export function clearThemeCache(): void {
  _cache.clear();
}
