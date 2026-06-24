/**
 * Structural validation for ThemeTokens — checks required semantic fields are present.
 */
import type { ThemeTokens } from "../theme/tokens.js";

export interface ValidationResult {
  valid: boolean;
  missing: string[];
}

const REQUIRED_SEMANTIC_FIELDS: Array<keyof ThemeTokens["semantic"]> = [
  "colorBg",
  "colorBgCard",
  "colorBgDeep",
  "colorText",
  "colorTextSoft",
  "colorTextFaint",
  "colorBorder",
  "colorAccent",
  "colorSuccess",
  "colorWarning",
];

export function validateThemeTokens(tokens: ThemeTokens): ValidationResult {
  const missing: string[] = [];

  for (const field of REQUIRED_SEMANTIC_FIELDS) {
    if (!tokens.semantic[field]) {
      missing.push(field);
    }
  }

  return { valid: missing.length === 0, missing };
}
