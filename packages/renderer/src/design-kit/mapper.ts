/**
 * Map extracted CSS vars to ThemeTokens semantic fields.
 * Heuristic: matches common naming patterns (--paper, --ink, --color-*, --bg-*, etc.)
 */
import type { ThemeTokens } from "../theme/tokens.js";
import type { CSSVar } from "./extractor.js";

// Heuristic patterns for well-known CSS var names → semantic token fields
const SEMANTIC_MAP: Array<{
  patterns: RegExp[];
  key: keyof ThemeTokens["semantic"];
}> = [
  { patterns: [/--paper$/, /--bg$/, /--background$/], key: "colorBg" },
  { patterns: [/--card$/, /--surface$/, /--bg-card$/], key: "colorBgCard" },
  { patterns: [/--paper-deep$/, /--bg-deep$/], key: "colorBgDeep" },
  { patterns: [/--ink$/, /--text$/, /--foreground$/], key: "colorText" },
  {
    patterns: [/--ink-soft$/, /--text-soft$/, /--text-secondary$/],
    key: "colorTextSoft",
  },
  {
    patterns: [/--ink-faint$/, /--text-faint$/, /--text-muted$/],
    key: "colorTextFaint",
  },
  { patterns: [/--line$/, /--border$/], key: "colorBorder" },
  { patterns: [/--line-soft$/, /--border-soft$/], key: "colorBorderSoft" },
  {
    patterns: [/--red$/, /--accent$/, /--primary$/],
    key: "colorAccent",
  },
  {
    patterns: [/--red-deep$/, /--accent-deep$/, /--primary-deep$/],
    key: "colorAccentDeep",
  },
  { patterns: [/--green$/, /--success$/], key: "colorSuccess" },
  { patterns: [/--gold$/, /--warning$/], key: "colorWarning" },
];

export function mapToSemanticTokens(
  vars: CSSVar[],
): Partial<ThemeTokens["semantic"]> {
  const result: Partial<ThemeTokens["semantic"]> = {};

  for (const { patterns, key } of SEMANTIC_MAP) {
    const match = vars.find((v) => patterns.some((p) => p.test(v.name)));
    if (match) (result as Record<string, unknown>)[key] = match.value;
  }

  // Category colors: --c-a, --c-b, etc. or --color-category-a
  const categoryColors: Record<string, { base: string; tint: string }> = {};
  for (const v of vars) {
    const m =
      v.name.match(/--c-([a-e])$/) ??
      v.name.match(/--color-category-([a-e])$/);
    if (m) {
      const letter = m[1];
      categoryColors[letter] = categoryColors[letter] ?? {
        base: v.value,
        tint: `rgba(0,0,0,0.1)`,
      };
      categoryColors[letter].base = v.value;
    }
    // tint variants: --c-a-tint → rgba(...)
    const tintM = v.name.match(/--c-([a-e])-tint$/);
    if (tintM) {
      const letter = tintM[1];
      categoryColors[letter] = categoryColors[letter] ?? {
        base: "#000",
        tint: v.value,
      };
      categoryColors[letter].tint = v.value;
    }
  }
  if (Object.keys(categoryColors).length > 0)
    result.categoryColors = categoryColors;

  return result;
}
