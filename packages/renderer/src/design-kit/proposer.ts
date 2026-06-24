/**
 * Fill gaps in partial ThemeTokens with sensible defaults.
 * Returns a complete ThemeTokens ready to save as theme.json.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import type { ThemeTokens } from "../theme/tokens.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_THEME: ThemeTokens = JSON.parse(
  readFileSync(
    path.resolve(__dirname, "../theme/themes/default.json"),
    "utf-8",
  ),
);

export function proposeThemeJSON(
  partial: Partial<ThemeTokens["semantic"]>,
  name: string,
): ThemeTokens {
  return {
    name,
    primitives: DEFAULT_THEME.primitives,
    semantic: {
      ...DEFAULT_THEME.semantic,
      ...partial,
    },
  };
}
